"""Versión secuencial con ciclos: la referencia de correctitud y de tiempo.

    --modo compilado  mismos ciclos compilados con numba, sin hilos (T1 del speedup)
    --modo puro       mismos ciclos en Python puro (solo para muestras pequeñas)
"""
import argparse
import json
import os
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--dataset", default="ml-1m")
parser.add_argument("--usuarios", type=int, default=None)
parser.add_argument("-k", type=int, default=50)
parser.add_argument("--salida", default=None, help="guarda ids y sims en un .npz")
parser.add_argument("--modo", choices=["compilado", "puro"], default="compilado")
args = parser.parse_args()

# Debe fijarse antes de importar numba: desactiva la compilación de @njit.
if args.modo == "puro":
    os.environ["NUMBA_DISABLE_JIT"] = "1"

import numpy as np  # noqa: E402

from comun.datos import cargar  # noqa: E402
from comun import nucleo  # noqa: E402


def main() -> None:
    t0 = time.perf_counter()
    d = cargar(args.dataset, args.usuarios)
    t_carga = time.perf_counter() - t0
    n = d.n_usuarios

    # Calentamiento: compila o carga del caché fuera de la zona medida.
    i, s = nucleo.nuevos_buffers(2, 1)
    nucleo.procesar_bloque(
        np.array([0, 1, 2], dtype=np.int64), np.array([0, 0], dtype=np.int32),
        np.array([1.0, 1.0]), 0, 2, i, s,
    )
    nucleo.ordenar_top_k(i, s)

    ids, sims = nucleo.nuevos_buffers(n, args.k)
    t1 = time.perf_counter()
    pares = nucleo.procesar_bloque(d.indptr, d.indices, d.data, 0, n, ids, sims)
    t2 = time.perf_counter()
    nucleo.ordenar_top_k(ids, sims)
    t3 = time.perf_counter()

    if args.salida:
        np.savez(args.salida, ids=ids, sims=sims)
    print(json.dumps({
        "version": f"secuencial_{args.modo}",
        "p": 1,
        "n": n,
        "pares": int(pares),
        "t_carga": t_carga,
        "t_calculo": t2 - t1,
        "t_combinar": 0.0,
        "t_ordenar": t3 - t2,
        "t_total": t3 - t1,
        "rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "huella": nucleo.huella(ids, sims),
    }))


if __name__ == "__main__":
    main()
