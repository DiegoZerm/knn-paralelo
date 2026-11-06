"""Control aleatorizado: ¿qué recupera MPI frente a numba cuando hay SMT?

Las variantes se intercalan al azar en la misma sesión. Así el calor y la hora no se
confunden con la variante, como sí podría pasar entre bloques separados de correr.py.

    python experimentos/control_mpi.py --equipo diego --reps 5
"""
import argparse
import csv
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from correr import RAIZ, esperar_enfriamiento, medir  # noqa: E402
from scipy import stats  # noqa: E402

VARIANTES = {
    "numba": ("numba", []),
    "mpi_copia_giro": ("mpi", []),
    "mpi_ventana": ("mpi", ["--datos", "ventana"]),
    "mpi_dormir": ("mpi", ["--espera", "dormir"]),
    "mpi_ventana_dormir": ("mpi", ["--datos", "ventana", "--espera", "dormir"]),
}


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--equipo", required=True)
    a.add_argument("--reps", type=int, default=5)
    a.add_argument("--ps", type=int, nargs="+", default=[4, 6, 8])
    args = a.parse_args()

    tareas = [(v, p, r) for v in VARIANTES for p in args.ps for r in range(args.reps)]
    random.Random(2027).shuffle(tareas)
    archivo = RAIZ / "resultados" / args.equipo / "control_mpi.csv"
    filas = []
    with open(archivo, "w", newline="") as f:
        w = csv.DictWriter(f, ["variante", "p", "rep", "t_total", "t_calculo", "t_combinar",
                               "mhz_medio", "temp_max", "huella", "fecha"])
        w.writeheader()
        for i, (v, p, r) in enumerate(tareas, 1):
            esperar_enfriamiento(70)
            version, extra = VARIANTES[v]
            d = medir(dict(experimento="control", version=version, dataset="ml-1m", n=None, k=50,
                           p=p, estrategia="trabajo", afinidad="fisicos", rep=r, extra=extra))
            fila = {"variante": v, "p": p, "rep": r, **{c: d[c] for c in (
                "t_total", "t_calculo", "t_combinar", "mhz_medio", "temp_max", "huella", "fecha")}}
            w.writerow(fila)
            f.flush()
            filas.append(fila)
            print(f"[{i}/{len(tareas)}] {v:<20} p={p} {float(d['t_total']):.2f} s", flush=True)

    if len({x["huella"] for x in filas}) != 1:
        raise SystemExit("ERROR: huellas distintas")
    print("\nVariante | p | T medio | DE | Dif. contra copia | p-valor (Welch)")
    for p in args.ps:
        base = [float(x["t_total"]) for x in filas if x["p"] == p and x["variante"] == "mpi_copia_giro"]
        for v in VARIANTES:
            t = [float(x["t_total"]) for x in filas if x["p"] == p and x["variante"] == v]
            dif = (statistics.mean(t) / statistics.mean(base) - 1) * 100
            valor = stats.ttest_ind(t, base, equal_var=False).pvalue if v != "mpi_copia_giro" else float("nan")
            print(f"{v} | {p} | {statistics.mean(t):.3f} | {statistics.stdev(t):.3f} | {dif:+.1f} % | {valor:.4f}")


if __name__ == "__main__":
    main()
