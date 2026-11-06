"""Núcleo de KNN: una sola fuente para las versiones secuencial, numba y MPI.

Si la variable de entorno NUMBA_DISABLE_JIT=1 está activa, @njit no compila y
este mismo código corre como Python puro. Así la versión "con ciclos" y las
versiones compiladas no pueden divergir.

Representación de un top-k parcial, para `n` usuarios:
    ids[u, :]   int32   id del vecino, o -1 si el lugar está vacío
    sims[u, :]  float64 similitud coseno, o 0.0 si el lugar está vacío
Cada fila es un min-heap cuya raíz es el PEOR vecino retenido.

El orden entre vecinos es total: mayor similitud gana y, si empatan, gana el id
menor. Por eso el resultado final no depende del orden de llegada de los pares
ni de cómo se repartió el trabajo.
"""
import numpy as np
from numba import njit


@njit(cache=True)
def _es_peor(sim_a, id_a, sim_b, id_b):
    """True si el vecino (sim_a, id_a) es peor que (sim_b, id_b)."""
    if sim_a != sim_b:
        return sim_a < sim_b
    return id_a > id_b


@njit(cache=True)
def _insertar(ids, sims, u, sim, v):
    """Ofrece el vecino v al heap del usuario u. Costo O(log k) si entra."""
    k = ids.shape[1]
    if not _es_peor(sims[u, 0], ids[u, 0], sim, v):
        return
    # Reemplaza la raíz y la hunde hasta recuperar la propiedad de heap.
    i = 0
    while True:
        izq = 2 * i + 1
        if izq >= k:
            break
        hijo = izq
        der = izq + 1
        if der < k and _es_peor(sims[u, der], ids[u, der], sims[u, izq], ids[u, izq]):
            hijo = der
        if not _es_peor(sims[u, hijo], ids[u, hijo], sim, v):
            break
        sims[u, i] = sims[u, hijo]
        ids[u, i] = ids[u, hijo]
        i = hijo
    sims[u, i] = sim
    ids[u, i] = v


@njit(cache=True)
def coseno(indptr, indices, data, u, v):
    """Producto punto de dos filas dispersas con índices ordenados (merge).

    Como las filas ya están normalizadas, el resultado es la similitud coseno.
    """
    i = indptr[u]
    j = indptr[v]
    fin_i = indptr[u + 1]
    fin_j = indptr[v + 1]
    total = 0.0
    while i < fin_i and j < fin_j:
        a = indices[i]
        b = indices[j]
        if a == b:
            total += data[i] * data[j]
            i += 1
            j += 1
        elif a < b:
            i += 1
        else:
            j += 1
    return total


@njit(cache=True)
def procesar_bloque(indptr, indices, data, inicio, fin, ids, sims):
    """Calcula los pares (u, v) con u en [inicio, fin) y v > u.

    Es la fila del triángulo superior: cada par se calcula una sola vez en todo
    el sistema, y actualiza el top-k de ambos usuarios en este buffer local.
    Regresa el número de pares calculados.
    """
    n = len(indptr) - 1
    pares = 0
    for u in range(inicio, fin):
        for v in range(u + 1, n):
            sim = coseno(indptr, indices, data, u, v)
            pares += 1
            if sim > 0.0:
                _insertar(ids, sims, u, sim, v)
                _insertar(ids, sims, v, sim, u)
    return pares


@njit(cache=True)
def fusionar_fila(ids_destino, sims_destino, u, ids_origen, sims_origen, u_origen):
    """Combina un heap parcial dentro de otro. Cada par vive en un solo bloque,
    así que nunca llegan vecinos duplicados."""
    for j in range(ids_origen.shape[1]):
        v = ids_origen[u_origen, j]
        if v >= 0:
            _insertar(ids_destino, sims_destino, u, sims_origen[u_origen, j], v)


@njit(cache=True)
def fusionar(ids_destino, sims_destino, ids_origen, sims_origen):
    """Combina dos top-k parciales completos, fila por fila."""
    for u in range(ids_destino.shape[0]):
        fusionar_fila(ids_destino, sims_destino, u, ids_origen, sims_origen, u)


@njit(cache=True)
def ordenar_top_k(ids, sims):
    """Convierte cada heap en una lista ordenada de mejor a peor vecino."""
    n, k = ids.shape
    for u in range(n):
        for i in range(1, k):
            s = sims[u, i]
            v = ids[u, i]
            j = i - 1
            while j >= 0 and _es_peor(sims[u, j], ids[u, j], s, v):
                sims[u, j + 1] = sims[u, j]
                ids[u, j + 1] = ids[u, j]
                j -= 1
            sims[u, j + 1] = s
            ids[u, j + 1] = v


@njit(cache=True)
def trabajo_por_fila(indptr):
    """Costo estimado de cada fila del triángulo: pasos del merge en los pares
    (u, v) con v > u. Una fila temprana compara contra casi todos los usuarios."""
    n = len(indptr) - 1
    costo = np.zeros(n, dtype=np.float64)
    resto = 0.0
    for u in range(n - 1, -1, -1):
        nnz = float(indptr[u + 1] - indptr[u])
        costo[u] = nnz * (n - u - 1) + resto
        resto += nnz
    return costo


def repartir(indptr, p, estrategia="trabajo"):
    """Fronteras de p bloques contiguos de filas.

    `filas`:   todos los bloques con el mismo número de filas. En un triángulo
               esto desbalancea: los primeros bloques hacen mucho más trabajo.
    `trabajo`: fronteras elegidas para igualar el costo estimado por bloque.
    """
    n = len(indptr) - 1
    if estrategia == "filas":
        return np.linspace(0, n, p + 1).astype(np.int64)
    if estrategia != "trabajo":
        raise ValueError(f"estrategia desconocida: {estrategia}")
    acumulado = np.cumsum(trabajo_por_fila(indptr))
    objetivos = acumulado[-1] * np.arange(1, p) / p
    cortes = np.searchsorted(acumulado, objetivos, side="left") + 1
    return np.concatenate(([0], cortes, [n])).astype(np.int64)


def nuevos_buffers(n, k):
    """Top-k vacío para n usuarios."""
    return np.full((n, k), -1, dtype=np.int32), np.zeros((n, k), dtype=np.float64)


def huella(ids, sims):
    """Hash del resultado: permite comparar versiones y máquinas sin guardar la
    matriz. Las similitudes se redondean para tolerar ruido de punto flotante."""
    import hashlib

    h = hashlib.sha256()
    h.update(ids.tobytes())
    h.update(np.round(sims, 9).tobytes())
    return h.hexdigest()[:16]
