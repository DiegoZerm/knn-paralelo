"""Demo en vivo: carrera entre versiones y recomendaciones para un usuario.

    python demo/demo.py --usuario 42         corre todo
    python demo/demo.py --solo-recomendar    usa el último resultado guardado
    python demo/demo.py --respaldo           plan B: reproduce la última corrida guardada
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "experimentos"))

import numpy as np  # noqa: E402

from comun.datos import cargar  # noqa: E402
from comun.recomendador import recomendar, titulo  # noqa: E402
from correr import cpus_para, entorno, topologia  # noqa: E402

RESPALDO = RAIZ / "demo" / "respaldo.json"
TOPK = RAIZ / "datos" / "demo_topk.npz"
B, D, V, X = "\033[1m", "\033[2m", "\033[32m", "\033[0m"


def correr(nombre, cmd, p):
    """Ejecuta una versión mostrando un cronómetro en vivo."""
    if shutil.which("taskset"):
        cmd = ["taskset", "-c", ",".join(map(str, cpus_para(p, "fisicos"))), *cmd]
    t0 = time.perf_counter()
    listo = threading.Event()

    def reloj():
        while not listo.wait(0.1):
            print(f"\r  {nombre:<30} {time.perf_counter() - t0:6.1f} s", end="", flush=True)

    h = threading.Thread(target=reloj, daemon=True)
    h.start()
    r = subprocess.run(cmd, capture_output=True, text=True, env=entorno(p), cwd=RAIZ)
    listo.set()
    h.join()
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])
    linea = next(l for l in reversed(r.stdout.splitlines()) if "{" in l)
    d = json.loads(linea[linea.index("{"):])
    print(f"\r  {nombre:<30} {d['t_total']:6.2f} s   huella {d['huella']}")
    return d


def carrera(args):
    fisicos = len({n for c, n in topologia() if c in os.sched_getaffinity(0)})
    p = args.p or fisicos
    py = sys.executable
    print(f"\n{B}Carrera: similitud entre {6040:,} usuarios de MovieLens 1M, top-{args.k}{X}\n")
    versiones = [
        (f"Secuencial (1 núcleo)", [py, "secuencial/knn_secuencial.py"], 1),
        (f"numba con {p} hilos", [py, "paralelo_numba/knn_numba.py", "-p", str(p), "--salida", str(TOPK)], p),
        (f"MPI con {p} procesos", ["mpirun", "--bind-to", "none", "--oversubscribe", "-n", str(p),
                                    py, "paralelo_mpi/knn_mpi.py"], p),
    ]
    filas = [(n, correr(n, c, q)) for n, c, q in versiones]
    t1 = filas[0][1]["t_total"]
    print()
    for n, d in filas[1:]:
        print(f"  {n:<30} speedup {t1 / d['t_total']:.2f}x, eficiencia {t1 / d['t_total'] / p:.0%}")
    iguales = len({d["huella"] for _, d in filas}) == 1
    print(f"\n  {V if iguales else ''}{'Las tres versiones dan exactamente el mismo resultado' if iguales else 'LAS HUELLAS NO COINCIDEN'}{X}")
    return {"p": p, "corridas": [{"nombre": n, "t": d["t_total"], "huella": d["huella"]} for n, d in filas]}


def recomendaciones(d, ids, sims, id_usuario, n=10):
    u = int(np.flatnonzero(d.usuarios == id_usuario)[0])
    salida = {"usuario": id_usuario, "vecinos": [], "gustos": [], "recs": []}
    for v, s in zip(ids[u][:3], sims[u][:3]):
        salida["vecinos"].append((int(d.usuarios[v]), float(s)))
    inicio, fin = d.indptr[u], d.indptr[u + 1]
    orden = np.argsort(-d.calificaciones[inicio:fin], kind="stable")[:5]
    salida["gustos"] = [titulo(d, d.indices[inicio + j]) for j in orden]
    salida["recs"] = [titulo(d, i) for i, _ in recomendar(d, ids, sims, u, n)]
    return salida


def mostrar(r):
    print(f"\n{B}Usuario {r['usuario']}{X}")
    print(f"{D}Vecinos más parecidos: " + ", ".join(f"{v} ({s:.3f})" for v, s in r["vecinos"]) + X)
    print(f"\n{B}Le gustó:{X}")
    for t in r["gustos"]:
        print(f"  {t}")
    print(f"\n{B}Le recomendamos:{X}")
    for i, t in enumerate(r["recs"], 1):
        print(f"  {i:>2}. {t}")
    print()


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--usuario", type=int, default=42)
    a.add_argument("-k", type=int, default=50)
    a.add_argument("-p", type=int, default=None, help="por defecto, los núcleos físicos")
    a.add_argument("--solo-recomendar", action="store_true")
    a.add_argument("--respaldo", action="store_true", help="no calcula; muestra la corrida guardada")
    a.add_argument("--guardar-respaldo", action="store_true")
    args = a.parse_args()

    if args.respaldo:
        g = json.loads(RESPALDO.read_text())
        print(f"\n{D}Corrida guardada el {g['fecha']} en {g['equipo']}{X}\n")
        t1 = g["carrera"]["corridas"][0]["t"]
        for c in g["carrera"]["corridas"]:
            print(f"  {c['nombre']:<30} {c['t']:6.2f} s  ({t1 / c['t']:.2f}x)  huella {c['huella']}")
        mostrar(g["recomendaciones"])
        return

    resultado = None
    if not args.solo_recomendar:
        resultado = carrera(args)
    z = np.load(TOPK)
    r = recomendaciones(cargar("ml-1m"), z["ids"], z["sims"], args.usuario)
    mostrar(r)
    if args.guardar_respaldo and resultado:
        cpu = next((l.split(":", 1)[1].strip() for l in subprocess.run(
            ["lscpu"], capture_output=True, text=True).stdout.splitlines() if l.startswith("Model name")), "")
        RESPALDO.write_text(json.dumps({
            "fecha": time.strftime("%Y-%m-%d %H:%M"), "equipo": cpu,
            "carrera": resultado, "recomendaciones": r,
        }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
