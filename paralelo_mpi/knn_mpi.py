"""Versión de memoria distribuida con mpi4py.

Cada proceso calcula un bloque de filas con su propia copia de los datos y genera
un top-k parcial para TODOS los usuarios. Los parciales se combinan en un árbol
binomial: en cada ronda la mitad de los procesos envía su parcial a un compañero,
así que el combinado tarda log2(p) rondas en vez de p-1 envíos a la raíz.

Ejecutar:
    mpirun --use-hwthread-cpus -n 4 python paralelo_mpi/knn_mpi.py --dataset ml-1m
"""
import argparse
import json
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
from mpi4py import MPI  # noqa: E402

from comun.datos import cargar  # noqa: E402
from comun import nucleo  # noqa: E402


_VENTANAS = []


def abortar_en_error(tipo, valor, traza):
    """Si un proceso falla, termina todos: los demás no quedarían esperando."""
    sys.__excepthook__(tipo, valor, traza)
    MPI.COMM_WORLD.Abort(1)


sys.excepthook = abortar_en_error


def repartir_datos(comm, nombre, usuarios):
    """La raíz lee el archivo y distribuye la matriz CSR con Bcast."""
    if comm.rank == 0:
        d = cargar(nombre, usuarios)
        forma = np.array([d.n_usuarios, d.nnz], dtype=np.int64)
        indptr, indices, data = d.indptr, d.indices, d.data
    else:
        forma = np.empty(2, dtype=np.int64)
    comm.Bcast(forma, root=0)
    if comm.rank != 0:
        indptr = np.empty(forma[0] + 1, dtype=np.int64)
        indices = np.empty(forma[1], dtype=np.int32)
        data = np.empty(forma[1], dtype=np.float64)
    comm.Bcast(indptr, root=0)
    comm.Bcast(indices, root=0)
    comm.Bcast(data, root=0)
    return indptr, indices, data


def datos_en_ventana(comm, nombre, usuarios):
    """Una sola copia de la matriz CSR para todos los procesos del nodo.

    La raíz aloja cada arreglo en una ventana compartida de MPI (MPI-3) y los demás
    procesos lo mapean. Sirve para medir cuánto cuesta duplicar los datos.
    """
    nodo = comm.Split_type(MPI.COMM_TYPE_SHARED)
    if nodo.size != comm.size:
        raise RuntimeError("--datos ventana requiere que todos los procesos estén en un nodo")
    d = cargar(nombre, usuarios) if comm.rank == 0 else None
    arreglos = []
    for campo, tipo in (("indptr", np.int64), ("indices", np.int32), ("data", np.float64)):
        largo = comm.bcast(len(getattr(d, campo)) if comm.rank == 0 else None, root=0)
        bytes_propios = largo * np.dtype(tipo).itemsize if comm.rank == 0 else 0
        ventana = MPI.Win.Allocate_shared(bytes_propios, 1, comm=nodo)
        memoria, _ = ventana.Shared_query(0)
        arreglo = np.ndarray(shape=(largo,), dtype=tipo, buffer=memoria)
        if comm.rank == 0:
            arreglo[:] = getattr(d, campo)
        comm.Barrier()
        arreglos.append(arreglo)
        _VENTANAS.append(ventana)  # deben seguir vivas mientras se usen los arreglos
    return tuple(arreglos)


def barrera(comm, modo):
    """`giro` es la barrera normal de MPI: quien termina sigue ocupando CPU.
    `dormir` libera el núcleo mientras espera a los demás."""
    if modo == "giro":
        comm.Barrier()
        return
    pendiente = comm.Ibarrier()
    while not pendiente.Test():
        time.sleep(0.001)


def combinar_en_arbol(comm, ids, sims):
    """Reducción binomial hacia el rank 0 con buffers NumPy (sin pickle)."""
    paso = 1
    while paso < comm.size:
        if comm.rank % (2 * paso) == paso:
            destino = comm.rank - paso
            comm.Send(ids, dest=destino, tag=1)
            comm.Send(sims, dest=destino, tag=2)
            return
        origen = comm.rank + paso
        if comm.rank % (2 * paso) == 0 and origen < comm.size:
            ids_r = np.empty_like(ids)
            sims_r = np.empty_like(sims)
            comm.Recv(ids_r, source=origen, tag=1)
            comm.Recv(sims_r, source=origen, tag=2)
            nucleo.fusionar(ids, sims, ids_r, sims_r)
        paso *= 2


def calentar():
    i, s = nucleo.nuevos_buffers(2, 1)
    nucleo.procesar_bloque(
        np.array([0, 1, 2], dtype=np.int64), np.array([0, 0], dtype=np.int32),
        np.array([1.0, 1.0]), 0, 2, i, s,
    )
    i2, s2 = nucleo.nuevos_buffers(2, 1)
    nucleo.fusionar(i, s, i2, s2)
    nucleo.ordenar_top_k(i, s)


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--dataset", default="ml-1m")
    a.add_argument("--usuarios", type=int, default=None)
    a.add_argument("-k", type=int, default=50)
    a.add_argument("--estrategia", choices=["filas", "trabajo"], default="trabajo")
    a.add_argument("--datos", choices=["copia", "ventana"], default="copia",
                   help="copia: Bcast a cada proceso; ventana: memoria compartida MPI-3")
    a.add_argument("--espera", choices=["giro", "dormir"], default="giro",
                   help="cómo espera un proceso que terminó su bloque")
    a.add_argument("--salida", default=None, help="guarda ids y sims en un .npz")
    args = a.parse_args()

    comm = MPI.COMM_WORLD
    t0 = MPI.Wtime()
    obtener = datos_en_ventana if args.datos == "ventana" else repartir_datos
    indptr, indices, data = obtener(comm, args.dataset, args.usuarios)
    t_carga = MPI.Wtime() - t0
    calentar()

    n = len(indptr) - 1
    cortes = nucleo.repartir(indptr, comm.size, args.estrategia)
    ids, sims = nucleo.nuevos_buffers(n, args.k)

    # Todos arrancan el cronómetro juntos; el tiempo es el del proceso más lento.
    comm.Barrier()
    t1 = time.perf_counter()
    pares = nucleo.procesar_bloque(
        indptr, indices, data, cortes[comm.rank], cortes[comm.rank + 1], ids, sims
    )
    t2 = time.perf_counter()
    barrera(comm, args.espera)
    t3 = time.perf_counter()
    combinar_en_arbol(comm, ids, sims)
    comm.Barrier()
    t4 = time.perf_counter()

    calculo_rank = t2 - t1
    calculos = comm.gather(calculo_rank, root=0)
    total_pares = comm.reduce(int(pares), op=MPI.SUM, root=0)
    memoria = comm.reduce(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, op=MPI.SUM, root=0)

    if comm.rank != 0:
        return
    nucleo.ordenar_top_k(ids, sims)
    t5 = time.perf_counter()
    if args.salida:
        np.savez(args.salida, ids=ids, sims=sims)
    print(json.dumps({
        "version": "mpi",
        "datos": args.datos,
        "p": comm.size,
        "n": n,
        "estrategia": args.estrategia,
        "pares": total_pares,
        "t_carga": t_carga,
        "t_calculo": t3 - t1,
        "t_calculo_ranks": calculos,
        "t_combinar": t4 - t3,
        "t_ordenar": t5 - t4,
        "t_total": t5 - t1,
        "rss_mb": memoria / 1024,
        "huella": nucleo.huella(ids, sims),
    }))


if __name__ == "__main__":
    main()
