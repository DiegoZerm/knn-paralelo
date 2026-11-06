"""Versión de memoria compartida con hilos de numba (prange).

Cada hilo procesa un bloque de filas y escribe solo en su buffer privado, por lo
que no hay condiciones de carrera ni locks. Después, los hilos combinan los
top-k parciales fila por fila; cada fila la toca un solo hilo.
"""
import argparse
import json
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numba  # noqa: E402
import numpy as np  # noqa: E402
from numba import njit, prange  # noqa: E402

from comun.datos import cargar  # noqa: E402
from comun import nucleo  # noqa: E402


@njit(parallel=True, cache=True)
def calcular_bloques(indptr, indices, data, cortes, ids, sims):
    """Una iteración por bloque; p bloques con p hilos en reparto estático."""
    p = len(cortes) - 1
    pares = np.zeros(p, dtype=np.int64)
    for b in prange(p):
        pares[b] = nucleo.procesar_bloque(
            indptr, indices, data, cortes[b], cortes[b + 1], ids[b], sims[b]
        )
    return pares


@njit(parallel=True, cache=True)
def combinar(ids, sims):
    """Vierte los buffers 1..p-1 en el buffer 0, en paralelo por filas."""
    p, n, _ = ids.shape
    for u in prange(n):
        for b in range(1, p):
            nucleo.fusionar_fila(ids[0], sims[0], u, ids[b], sims[b], u)


def resolver(d, k, p, estrategia="trabajo"):
    """Regresa (ids, sims, tiempos por fase)."""
    numba.set_num_threads(p)
    n = d.n_usuarios
    cortes = nucleo.repartir(d.indptr, p, estrategia)
    ids = np.full((p, n, k), -1, dtype=np.int32)
    sims = np.zeros((p, n, k), dtype=np.float64)

    t0 = time.perf_counter()
    pares = calcular_bloques(d.indptr, d.indices, d.data, cortes, ids, sims)
    t1 = time.perf_counter()
    combinar(ids, sims)
    t2 = time.perf_counter()
    nucleo.ordenar_top_k(ids[0], sims[0])
    t3 = time.perf_counter()
    return ids[0], sims[0], {
        "pares": int(pares.sum()),
        "t_calculo": t1 - t0,
        "t_combinar": t2 - t1,
        "t_ordenar": t3 - t2,
        "t_total": t3 - t0,
    }


def calentar(p):
    """Compila o carga del caché antes de medir, con el mismo número de hilos."""
    from comun.datos import Dataset

    mini = Dataset(
        indptr=np.array([0, 1, 2], dtype=np.int64),
        indices=np.array([0, 0], dtype=np.int32),
        data=np.array([1.0, 1.0]),
        n_items=1,
        calificaciones=np.array([1.0], dtype=np.float32),
        usuarios=np.array([0, 1]),
        items=np.array([0]),
        titulos={},
    )
    resolver(mini, 1, p)


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--dataset", default="ml-1m")
    a.add_argument("--usuarios", type=int, default=None)
    a.add_argument("-k", type=int, default=50)
    a.add_argument("-p", type=int, default=numba.config.NUMBA_NUM_THREADS)
    a.add_argument("--estrategia", choices=["filas", "trabajo"], default="trabajo")
    a.add_argument("--salida", default=None, help="guarda ids y sims en un .npz")
    args = a.parse_args()

    t0 = time.perf_counter()
    d = cargar(args.dataset, args.usuarios)
    t_carga = time.perf_counter() - t0

    calentar(args.p)
    ids, sims, tiempos = resolver(d, args.k, args.p, args.estrategia)
    if args.salida:
        np.savez(args.salida, ids=ids, sims=sims)
    print(json.dumps({
        "version": "numba",
        "p": args.p,
        "n": d.n_usuarios,
        "estrategia": args.estrategia,
        "capa_hilos": numba.threading_layer(),
        "t_carga": t_carga,
        **tiempos,
        "rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "huella": nucleo.huella(ids, sims),
    }))


if __name__ == "__main__":
    main()
