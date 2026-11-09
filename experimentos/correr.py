"""Orquesta los experimentos y agrega cada corrida a resultados/<equipo>/corridas.csv.

    python experimentos/correr.py --equipo diego --perfil rapido
    python experimentos/correr.py --equipo diego --perfil completo

Es reanudable: si se interrumpe, al volver a correrlo salta lo ya medido.
Dentro de cada experimento el orden es aleatorio para que el calentamiento de la
máquina no favorezca a ninguna configuración.
"""
import argparse
import csv
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

COLUMNAS = [
    "experimento", "version", "dataset", "n", "k", "p", "estrategia", "afinidad", "rep",
    "t_total", "t_calculo", "t_combinar", "t_ordenar", "t_carga", "rss_mb", "pares",
    "huella", "mhz_medio", "temp_max", "carga_previa", "fecha",
]


def topologia():
    """[(cpu, nucleo)] de Linux. Si no se puede leer, cada CPU es su propio núcleo."""
    try:
        salida = subprocess.run(
            ["lscpu", "-p=CPU,CORE"], capture_output=True, text=True, check=True
        ).stdout
        pares = [tuple(map(int, l.split(",")[:2])) for l in salida.splitlines() if l[0] != "#"]
        if pares:
            return pares
    except (OSError, subprocess.CalledProcessError, ValueError):
        pass
    return [(c, c) for c in sorted(os.sched_getaffinity(0))]


def cpus_para(p, afinidad):
    """Lista de CPUs permitidas para p trabajadores.

    fisicos:  un hilo de cada núcleo físico antes de usar hermanos SMT.
    hermanos: llena cada núcleo físico con todos sus hilos antes de pasar al otro.
    """
    disponibles = os.sched_getaffinity(0)
    topo = [(c, n) for c, n in topologia() if c in disponibles]
    por_nucleo = {}
    for cpu, nucleo in sorted(topo):
        por_nucleo.setdefault(nucleo, []).append(cpu)
    if afinidad == "hermanos":
        orden = [c for n in sorted(por_nucleo) for c in por_nucleo[n]]
    else:
        orden = []
        ronda = 0
        while len(orden) < len(topo):
            orden += [v[ronda] for _, v in sorted(por_nucleo.items()) if ronda < len(v)]
            ronda += 1
    return orden[:p] if p <= len(orden) else orden


class Sensores(threading.Thread):
    """Muestrea frecuencia y temperatura mientras corre una medición."""

    def __init__(self, cpus):
        super().__init__(daemon=True)
        self.rutas = [Path(f"/sys/devices/system/cpu/cpu{c}/cpufreq/scaling_cur_freq") for c in cpus]
        self.temps = []
        for hw in Path("/sys/class/hwmon").glob("hwmon*"):
            try:
                if (hw / "name").read_text().strip() in ("k10temp", "coretemp", "zenpower"):
                    self.temps += list(hw.glob("temp*_input"))
            except OSError:
                pass
        self.mhz = []
        self.temp_max = None
        self.parar = threading.Event()

    def run(self):
        while not self.parar.wait(0.5):
            try:
                vals = [int(r.read_text()) / 1000 for r in self.rutas]
                self.mhz.append(sum(vals) / len(vals))
                for t in self.temps:
                    c = int(t.read_text()) / 1000
                    self.temp_max = c if self.temp_max is None else max(self.temp_max, c)
            except (OSError, ValueError, ZeroDivisionError):
                pass

    def resumen(self):
        return (round(sum(self.mhz) / len(self.mhz)) if self.mhz else "", self.temp_max or "")


def esperar_enfriamiento(limite, maximo=90):
    """Espera a que la CPU baje de `limite` °C para que el calor no sesgue la medición."""
    sensores = Sensores([])
    if not sensores.temps:
        return
    fin = time.time() + maximo
    while time.time() < fin:
        try:
            if max(int(t.read_text()) / 1000 for t in sensores.temps) <= limite:
                return
        except (OSError, ValueError):
            return
        time.sleep(2)


def entorno(p):
    """Un solo nivel de paralelismo: nada de hilos ocultos de BLAS."""
    e = dict(os.environ)
    e.update(
        OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
        NUMBA_THREADING_LAYER="omp", NUMBA_NUM_THREADS=str(p),
    )
    return e


def comando(c):
    base = ["--dataset", c["dataset"], "-k", str(c["k"])]
    if c["n"]:
        base += ["--usuarios", str(c["n"])]
    v = c["version"]
    if v.startswith("secuencial"):
        modo = v.split("_")[1]
        return [PYTHON, str(RAIZ / "secuencial/knn_secuencial.py"), "--modo", modo, *base]
    base += ["--estrategia", c["estrategia"]]
    if v == "numba":
        return [PYTHON, str(RAIZ / "paralelo_numba/knn_numba.py"), "-p", str(c["p"]), *base]
    base += c.get("extra", [])
    mpi = [shutil.which("mpirun") or "mpirun", "-n", str(c["p"])]
    if c["afinidad"] == "defecto":
        mpi += ["--use-hwthread-cpus"]
    else:
        mpi += ["--bind-to", "none", "--oversubscribe"]
    return [*mpi, PYTHON, str(RAIZ / "paralelo_mpi/knn_mpi.py"), *base]


def medir(c):
    cmd = comando(c)
    cpus = cpus_para(c["p"], c["afinidad"])
    # Con "defecto", OpenMPI llena un núcleo con sus dos hilos; se mide donde realmente corre.
    sensores = Sensores(cpus_para(c["p"], "hermanos") if c["afinidad"] == "defecto" else cpus)
    if c["afinidad"] != "defecto" and shutil.which("taskset"):
        cmd = ["taskset", "-c", ",".join(map(str, cpus)), *cmd]
    carga = os.getloadavg()[0]
    sensores.start()
    r = subprocess.run(cmd, capture_output=True, text=True, env=entorno(c["p"]), cwd=RAIZ)
    sensores.parar.set()
    sensores.join()
    if r.returncode != 0:
        raise RuntimeError(f"Falló {' '.join(cmd)}\n{r.stderr[-1500:]}")
    # mpirun puede anteponer códigos de terminal a la línea, por eso se busca la llave.
    linea = next(l for l in reversed(r.stdout.splitlines()) if "{" in l)
    d = json.loads(linea[linea.index("{"):])
    mhz, temp = sensores.resumen()
    return {
        **{col: c.get(col, "") for col in COLUMNAS},
        **{col: d.get(col, "") for col in
           ("t_total", "t_calculo", "t_combinar", "t_ordenar", "t_carga", "rss_mb", "pares", "huella")},
        "n": d["n"], "mhz_medio": mhz, "temp_max": temp,
        "carga_previa": round(carga, 2), "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def valores_p(maximo):
    """1, 2, 3, 4, 6, 8, 12... hasta el número de CPUs lógicas, incluido."""
    base = [q for q in (1, 2, 3, 4, 6, 8, 12, 16, 24, 32) if q <= maximo]
    return sorted(set(base + [maximo]))


def plan(perfil, logicos, fisicos):
    """Lista de experimentos: (nombre, corridas, repeticiones)."""
    ps = valores_p(logicos)
    def malla(exp, dataset, n, reps, procesos=ps, estrategia="trabajo", afinidad="fisicos",
              versiones=("numba", "mpi"), k=50, secuencial=True):
        cs = []
        if secuencial:
            cs.append(dict(experimento=exp, version="secuencial_compilado", dataset=dataset, n=n,
                           k=k, p=1, estrategia="", afinidad="fisicos", reps=reps))
        for v in versiones:
            for q in procesos:
                cs.append(dict(experimento=exp, version=v, dataset=dataset, n=n, k=k, p=q,
                               estrategia=estrategia, afinidad=afinidad, reps=reps))
        return cs

    reps = 5 if perfil == "completo" else 3
    n_puro = 1000 if perfil == "completo" else 500
    corridas = [
        dict(experimento="python_puro", version="secuencial_puro", dataset="ml-1m", n=n_puro,
             k=50, p=1, estrategia="", afinidad="fisicos", reps=3),
        dict(experimento="python_puro", version="secuencial_compilado", dataset="ml-1m", n=n_puro,
             k=50, p=1, estrategia="", afinidad="fisicos", reps=3),
    ]
    corridas += malla("fuerte", "ml-1m", None, reps)

    # Reparto: filas iguales contra trabajo igual.
    con_balanceo = [q for q in ps if q > 1]
    corridas += malla("balanceo", "ml-1m", None, reps, procesos=con_balanceo, estrategia="filas",
                      secuencial=False)

    # SMT: dos trabajadores en núcleos distintos contra el mismo núcleo.
    if logicos > fisicos:
        corridas += malla("smt", "ml-1m", None, reps, procesos=[2], afinidad="hermanos",
                          secuencial=False)
        corridas += malla("smt_mpi_defecto", "ml-1m", None, reps, procesos=[2], afinidad="defecto",
                          versiones=("mpi",), secuencial=False)

    if perfil == "completo":
        corridas += malla("fuerte", "goodbooks", 20000, reps)
        # ¿Qué frena a MPI cuando hay SMT? Variantes con el mismo reparto.
        altos = [q for q in ps if q >= fisicos]
        for nombre, extra in (("mpi_dormir", ["--espera", "dormir"]), ("mpi_ventana", ["--datos", "ventana"])):
            for c in malla(nombre, "ml-1m", None, reps, procesos=altos, versiones=("mpi",), secuencial=False):
                corridas.append({**c, "extra": extra})
        # Sobresuscripción: más trabajadores que CPUs lógicas.
        corridas += malla("sobresuscripcion", "ml-1m", None, 3, procesos=[logicos * 2],
                          secuencial=False)
        # Escalabilidad débil: pares por trabajador constantes (n crece con raíz de p).
        for q in valores_p(logicos):
            corridas += malla("debil", "ml-1m", int(2000 * q ** 0.5), 3, procesos=[q], secuencial=q == 1)
    return corridas


def medir_banda(destino, logicos):
    """Ancho de banda de memoria por número de hilos."""
    archivo = destino / "banda_memoria.csv"
    if archivo.exists():
        return
    filas = []
    for q in valores_p(logicos):
        cmd = [PYTHON, str(RAIZ / "experimentos/banda_memoria.py"), "-p", str(q)]
        if shutil.which("taskset"):
            cmd = ["taskset", "-c", ",".join(map(str, cpus_para(q, "fisicos"))), *cmd]
        r = subprocess.run(cmd, capture_output=True, text=True, env=entorno(q), check=True)
        filas.append(json.loads(r.stdout.splitlines()[-1]))
        print(f"Memoria p={q}: {filas[-1]['gb_s']:.1f} GB/s", flush=True)
    with open(archivo, "w", newline="") as f:
        w = csv.DictWriter(f, ["p", "gb_s"])
        w.writeheader()
        w.writerows(filas)


def especificaciones(equipo):
    def salida(*cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=20,
                                  env={**os.environ, "LC_ALL": "C"}).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""

    version_kernel = platform.release().lower()
    memoria = next((l.split()[1] for l in Path("/proc/meminfo").read_text().splitlines()
                    if l.startswith("MemTotal")), "0")
    energia = [p.read_text().strip() for p in Path("/sys/class/power_supply").glob("*/online")]
    gobernador = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    import mpi4py
    import numba
    import numpy
    topo = topologia()
    return {
        "equipo": equipo,
        "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu": next((l.split(":", 1)[1].strip() for l in salida("lscpu").splitlines()
                     if l.startswith("Model name")), platform.processor()),
        "cpus_logicas": len(topo),
        "nucleos_fisicos": len({n for _, n in topo}),
        "cpus_visibles": len(os.sched_getaffinity(0)),
        "ram_gb": round(int(memoria) / 1024 / 1024, 1),
        "gpu": salida("nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"),
        "sistema": platform.platform(),
        "entorno": "docker" if Path("/.dockerenv").exists()
                   else "wsl" if "microsoft" in version_kernel else "nativo",
        "conectado_a_corriente": any(e == "1" for e in energia) if energia else None,
        "gobernador": gobernador.read_text().strip() if gobernador.exists() else None,
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "numba": numba.__version__,
        "mpi4py": mpi4py.__version__,
        "mpi": salida("mpirun", "--version").splitlines()[0] if salida("mpirun", "--version") else "",
        "lscpu": salida("lscpu"),
    }


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--equipo", required=True, help="nombre corto: tu carpeta en resultados/")
    a.add_argument("--perfil", choices=["rapido", "completo"], default="rapido")
    a.add_argument("--enfriar", type=float, default=None, help="espera a esta temperatura antes de medir")
    a.add_argument("--plan", action="store_true", help="muestra qué correría, sin medir")
    args = a.parse_args()

    destino = RAIZ / "resultados" / args.equipo
    destino.mkdir(parents=True, exist_ok=True)
    espec = especificaciones(args.equipo)
    (destino / "especificaciones.json").write_text(json.dumps(espec, indent=2, ensure_ascii=False))
    print(f"{espec['cpu']} | {espec['nucleos_fisicos']} núcleos, {espec['cpus_visibles']} CPUs "
          f"| {espec['ram_gb']} GB | {espec['entorno']}")
    if espec["conectado_a_corriente"] is False:
        print("AVISO: la laptop no está conectada; los tiempos serán más ruidosos.")

    corridas = plan(args.perfil, espec["cpus_visibles"], espec["nucleos_fisicos"])
    azar = random.Random(2026)
    tareas = []
    for c in corridas:
        tareas += [{**c, "rep": r} for r in range(c["reps"])]
    # Se agrupa por experimento y se baraja dentro de cada grupo.
    grupos = {}
    for t in tareas:
        grupos.setdefault(t["experimento"], []).append(t)
    tareas = []
    for g in grupos.values():
        azar.shuffle(g)
        tareas += g

    if args.plan:
        for t in tareas:
            print(t["experimento"], t["version"], t["dataset"], t["n"], "p", t["p"],
                  t["estrategia"], t["afinidad"], "rep", t["rep"])
        print(len(tareas), "mediciones")
        return

    archivo = destino / "corridas.csv"
    hechas = set()
    if archivo.exists():
        with open(archivo, newline="") as f:
            for fila in csv.DictReader(f):
                hechas.add((fila["experimento"], fila["version"], fila["dataset"], fila["p"],
                            fila["estrategia"], fila["afinidad"], fila["rep"], fila["n"]))
    nuevo = not archivo.exists()
    huellas = {}
    with open(archivo, "a", newline="") as f:
        w = csv.DictWriter(f, COLUMNAS)
        if nuevo:
            w.writeheader()
        for i, t in enumerate(tareas, 1):
            sello = (t["experimento"], t["version"], t["dataset"], str(t["p"]), t["estrategia"],
                     t["afinidad"], str(t["rep"]))
            if any(h[:7] == sello and (not t["n"] or h[7] == str(t["n"])) for h in hechas):
                continue
            if args.enfriar:
                esperar_enfriamiento(args.enfriar)
            fila = medir(t)
            w.writerow(fila)
            f.flush()
            base = (fila["dataset"], fila["n"], fila["k"])
            if huellas.setdefault(base, fila["huella"]) != fila["huella"]:
                raise SystemExit(f"ERROR de correctitud: huella distinta en {fila}")
            print(f"[{i}/{len(tareas)}] {t['experimento']:<12} {t['version']:<22} {t['dataset']:<10} "
                  f"p={t['p']:<3} {t['estrategia']:<8} {float(fila['t_total']):8.2f} s "
                  f"{fila['mhz_medio']} MHz {fila['temp_max']} °C", flush=True)
    medir_banda(destino, espec["cpus_visibles"])
    print(f"Listo: {archivo}")


if __name__ == "__main__":
    main()
