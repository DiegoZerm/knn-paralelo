"""Mini benchmark tipo STREAM (triad): ancho de banda de memoria por hilos.

Sirve para saber si la memoria limita la escalabilidad en cada máquina.
    python experimentos/banda_memoria.py -p 4
"""
import argparse
import json
import time

import numba
import numpy as np
from numba import njit, prange


@njit(parallel=True)
def triad(a, b, c, p):
    """a = b + 3c, repartido en p bloques contiguos."""
    n = len(a)
    for t in prange(p):
        for i in range(t * n // p, (t + 1) * n // p):
            a[i] = b[i] + 3.0 * c[i]


def main():
    arg = argparse.ArgumentParser(description=__doc__)
    arg.add_argument("-p", type=int, required=True)
    arg.add_argument("--mb", type=int, default=512, help="tamaño de cada arreglo")
    args = arg.parse_args()
    numba.set_num_threads(args.p)
    n = args.mb * 1024**2 // 8
    a, b, c = np.zeros(n), np.ones(n), np.full(n, 2.0)
    triad(a, b, c, args.p)  # compila y toca las páginas
    mejor = float("inf")
    for _ in range(5):
        t = time.perf_counter()
        triad(a, b, c, args.p)
        mejor = min(mejor, time.perf_counter() - t)
    print(json.dumps({"p": args.p, "gb_s": 3 * n * 8 / mejor / 1e9}))


if __name__ == "__main__":
    main()
