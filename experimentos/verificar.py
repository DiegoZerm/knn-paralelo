"""Verifica con scikit-learn sobre datos reales y guarda la evidencia.

    python experimentos/verificar.py --equipo diego

Compara similitud por similitud. Los vecinos pueden diferir solo en empates, porque
scikit-learn no fija un orden entre ellos; esos casos se cuentan y se revisan aparte.
"""
import argparse
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
from sklearn.neighbors import NearestNeighbors  # noqa: E402

from comun.datos import cargar  # noqa: E402
from paralelo_numba.knn_numba import resolver  # noqa: E402


def verificar(nombre, usuarios, k):
    d = cargar(nombre, usuarios)
    p = len(os.sched_getaffinity(0))
    ids, sims, _ = resolver(d, k, p)

    m = d.matriz_csr()
    nn = NearestNeighbors(n_neighbors=k + 1, metric="cosine", algorithm="brute").fit(m)
    dist, vecinos = nn.kneighbors(m)

    n = d.n_usuarios
    sk_sims = np.zeros((n, k))
    distintos = 0
    empate_justificado = 0
    for u in range(n):
        sk = [(1 - x, v) for x, v in zip(dist[u], vecinos[u]) if v != u][:k]
        sk_sims[u] = [s if s > 1e-12 else 0.0 for s, _ in sk]
        for j, (s, v) in enumerate(sk):
            if s > 1e-12 and ids[u, j] != v:
                distintos += 1
                # Un vecino distinto solo es válido si tiene la misma similitud.
                if abs(sims[u, j] - s) < 1e-9:
                    empate_justificado += 1
    return {
        "dataset": nombre,
        "usuarios": n,
        "k": k,
        "error_max_similitud": float(np.abs(sims - sk_sims).max()),
        "vecinos_comparados": int((sims > 0).sum()),
        "vecinos_distintos": distintos,
        "vecinos_distintos_por_empate": empate_justificado,
        "correcto": bool(np.abs(sims - sk_sims).max() < 1e-9 and distintos == empate_justificado),
    }


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--equipo", required=True)
    a.add_argument("--dataset", default="ml-1m")
    a.add_argument("--usuarios", type=int, default=None)
    a.add_argument("-k", type=int, default=50)
    args = a.parse_args()
    r = verificar(args.dataset, args.usuarios, args.k)
    destino = RAIZ / "resultados" / args.equipo
    destino.mkdir(parents=True, exist_ok=True)
    archivo = destino / f"verificacion_{args.dataset}.json"
    archivo.write_text(json.dumps(r, indent=2))
    print(json.dumps(r, indent=2))
    if not r["correcto"]:
        raise SystemExit("NO coincide con scikit-learn")


if __name__ == "__main__":
    main()
