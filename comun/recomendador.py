"""Convierte vecinos en recomendaciones (filtrado colaborativo por usuarios)."""
import numpy as np


def puntuar(d, ids, sims, u):
    """Puntaje de cada ítem para u: suma de similitud x calificación de sus vecinos."""
    puntaje = np.zeros(d.n_items)
    for v, s in zip(ids[u], sims[u]):
        if v < 0:
            continue
        rango = slice(d.indptr[v], d.indptr[v + 1])
        np.add.at(puntaje, d.indices[rango], s * d.calificaciones[rango])
    puntaje[d.indices[d.indptr[u]:d.indptr[u + 1]]] = -np.inf
    return puntaje


def recomendar(d, ids, sims, u, n=10):
    """Regresa [(índice de ítem, puntaje)] sin incluir lo que u ya calificó."""
    puntaje = puntuar(d, ids, sims, u)
    # Empates resueltos por índice, para que el resultado sea reproducible.
    orden = np.lexsort((np.arange(d.n_items), -puntaje))[:n]
    return [(int(i), float(puntaje[i])) for i in orden if np.isfinite(puntaje[i]) and puntaje[i] > 0]


def titulo(d, i):
    original = d.items[i]
    return d.titulos.get(int(original), f"Ítem {original}")
