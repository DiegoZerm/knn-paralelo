"""¿Las recomendaciones sirven? Evaluación leave-one-out contra popularidad.

A cada usuario se le oculta una película que calificó bien. Se calcula KNN sin ella
y se mide si aparece entre sus 10 primeras recomendaciones (HR@10, NDCG@10).

    python experimentos/calidad.py --equipo diego
"""
import argparse
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402

from comun.datos import Dataset, cargar  # noqa: E402
from comun.recomendador import puntuar  # noqa: E402
from paralelo_numba.knn_numba import resolver  # noqa: E402


def ocultar(d, semilla=7):
    """Regresa un Dataset sin un ítem bien calificado por usuario, y esos ítems."""
    azar = np.random.default_rng(semilla)
    n = d.n_usuarios
    conservar = np.ones(d.nnz, dtype=bool)
    ocultos = np.full(n, -1, dtype=np.int64)
    for u in range(n):
        inicio, fin = d.indptr[u], d.indptr[u + 1]
        buenos = np.flatnonzero(d.calificaciones[inicio:fin] >= 4)
        if fin - inicio >= 5 and len(buenos):
            pos = inicio + azar.choice(buenos)
            conservar[pos] = False
            ocultos[u] = d.indices[pos]
    tamanos = np.add.reduceat(conservar.astype(np.int64), d.indptr[:-1])
    indptr = np.concatenate(([0], np.cumsum(tamanos))).astype(np.int64)
    calif = d.calificaciones[conservar]
    por_fila = np.repeat(np.arange(n), tamanos)
    normas = np.sqrt(np.bincount(por_fila, weights=calif.astype(np.float64) ** 2, minlength=n))
    return Dataset(indptr, d.indices[conservar], calif / normas[por_fila], d.n_items,
                   calif, d.usuarios, d.items, d.titulos), ocultos


def resumir(rangos, total):
    rangos = np.array(rangos)
    return {
        "hr_10": float((rangos < 10).sum() / total),
        "ndcg_10": float((1 / np.log2(rangos[rangos < 10] + 2)).sum() / total),
    }


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--equipo", required=True)
    a.add_argument("--dataset", default="ml-1m")
    a.add_argument("-k", type=int, default=50)
    args = a.parse_args()

    d, ocultos = ocultar(cargar(args.dataset))
    ids, sims, _ = resolver(d, args.k, len(os.sched_getaffinity(0)))
    popularidad = np.bincount(d.indices, minlength=d.n_items).astype(float)

    r_knn, r_pop = [], []
    evaluados = np.flatnonzero(ocultos >= 0)
    for u in evaluados:
        vistos = d.indices[d.indptr[u]:d.indptr[u + 1]]
        p = puntuar(d, ids, sims, u)
        r_knn.append(int((p > p[ocultos[u]]).sum()))
        q = popularidad.copy()
        q[vistos] = -np.inf
        r_pop.append(int((q > q[ocultos[u]]).sum()))

    r = {
        "dataset": args.dataset, "k": args.k, "usuarios_evaluados": int(len(evaluados)),
        "knn": resumir(r_knn, len(evaluados)),
        "popularidad": resumir(r_pop, len(evaluados)),
    }
    destino = RAIZ / "resultados" / args.equipo
    destino.mkdir(parents=True, exist_ok=True)
    (destino / f"calidad_{args.dataset}.json").write_text(json.dumps(r, indent=2))
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
