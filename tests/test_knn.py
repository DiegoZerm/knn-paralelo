"""Correctitud: contra scikit-learn, entre versiones y en casos borde."""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import scipy.sparse as sp
from sklearn.neighbors import NearestNeighbors

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from comun.datos import Dataset  # noqa: E402
from comun import nucleo  # noqa: E402
from paralelo_numba.knn_numba import resolver  # noqa: E402


def sintetico(n=200, items=80, densidad=0.15, semilla=1):
    m = sp.random(n, items, density=densidad, format="csr",
                  random_state=np.random.default_rng(semilla),
                  data_rvs=lambda s: np.random.default_rng(semilla).integers(1, 6, s).astype(float))
    m.sort_indices()
    normas = np.sqrt(np.bincount(np.repeat(np.arange(n), np.diff(m.indptr)),
                                 weights=m.data**2, minlength=n))
    normas[normas == 0] = 1
    data = m.data / np.repeat(normas, np.diff(m.indptr))
    return Dataset(m.indptr.astype(np.int64), m.indices.astype(np.int32), data, items,
                   m.data.astype(np.float32), np.arange(n), np.arange(items), {})


def secuencial(d, k):
    ids, sims = nucleo.nuevos_buffers(d.n_usuarios, k)
    nucleo.procesar_bloque(d.indptr, d.indices, d.data, 0, d.n_usuarios, ids, sims)
    nucleo.ordenar_top_k(ids, sims)
    return ids, sims


def fuerza_bruta(d, k):
    """Oráculo independiente: matriz densa completa y orden total explícito."""
    m = d.matriz_csr().toarray()
    s = m @ m.T
    np.fill_diagonal(s, 0)
    ids = np.full((d.n_usuarios, k), -1, dtype=np.int32)
    sims = np.zeros((d.n_usuarios, k))
    for u in range(d.n_usuarios):
        orden = np.lexsort((np.arange(d.n_usuarios), -np.round(s[u], 12)))[:k]
        for j, v in enumerate(orden):
            if s[u, v] > 0:
                ids[u, j], sims[u, j] = v, s[u, v]
    return ids, sims


def test_coincide_con_sklearn():
    d = sintetico()
    k = 10
    ids, sims = secuencial(d, k)
    nn = NearestNeighbors(n_neighbors=k + 1, metric="cosine", algorithm="brute").fit(d.matriz_csr())
    dist, vecinos = nn.kneighbors(d.matriz_csr())
    for u in range(d.n_usuarios):
        sk = [(1 - x, v) for x, v in zip(dist[u], vecinos[u]) if v != u][:k]
        sk_sims = np.array([s for s, _ in sk])
        # Sin coincidencias, sklearn devuelve vecinos arbitrarios con similitud 0.
        sk_sims[sk_sims < 1e-12] = 0
        assert np.allclose(sims[u], sk_sims, atol=1e-9), f"usuario {u}"


def test_coincide_con_fuerza_bruta():
    d = sintetico(n=120)
    ids, sims = secuencial(d, 7)
    ids_b, sims_b = fuerza_bruta(d, 7)
    assert np.allclose(sims, sims_b, atol=1e-9)
    # Fuera de empates numéricos, también los vecinos deben ser los mismos.
    claros = np.abs(sims - sims_b) < 1e-12
    assert (ids[claros] == ids_b[claros]).mean() > 0.99


@pytest.mark.parametrize("p", [1, 2, 3, 4])
@pytest.mark.parametrize("estrategia", ["filas", "trabajo"])
def test_numba_identico(p, estrategia):
    d = sintetico()
    ids, sims = secuencial(d, 10)
    ids_p, sims_p, tiempos = resolver(d, 10, p, estrategia)
    assert np.array_equal(ids, ids_p)
    assert np.array_equal(sims, sims_p)
    assert tiempos["pares"] == d.n_usuarios * (d.n_usuarios - 1) // 2


def test_buffers_de_numba_no_comparten_estado():
    """Dos corridas seguidas dan lo mismo: no hay estado residual."""
    d = sintetico()
    a = resolver(d, 5, 4)
    b = resolver(d, 5, 4)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])


@pytest.mark.parametrize("p", [1, 2, 3, 5])
def test_mpi_identico(tmp_path, p):
    """MPI sobre una muestra real contra la secuencial, proceso por proceso."""
    if not (RAIZ / "datos/ml-1m.npz").exists():
        pytest.skip("falta ml-1m: python -m comun.datos ml-1m")
    env = dict(os.environ, OMP_NUM_THREADS="1")
    sec = subprocess.run(
        [sys.executable, str(RAIZ / "secuencial/knn_secuencial.py"), "--usuarios", "300"],
        capture_output=True, text=True, check=True, env=env)
    mpi = subprocess.run(
        ["mpirun", "--bind-to", "none", "--oversubscribe", "-n", str(p), sys.executable,
         str(RAIZ / "paralelo_mpi/knn_mpi.py"), "--usuarios", "300"],
        capture_output=True, text=True, check=True, env=env, timeout=120)
    def fin(s):
        linea = next(l for l in reversed(s.splitlines()) if "{" in l)
        return json.loads(linea[linea.index("{"):])
    assert fin(sec.stdout)["huella"] == fin(mpi.stdout)["huella"]


def test_python_puro_identico():
    if not (RAIZ / "datos/ml-1m.npz").exists():
        pytest.skip("falta ml-1m")
    corre = lambda modo: json.loads(subprocess.run(
        [sys.executable, str(RAIZ / "secuencial/knn_secuencial.py"), "--usuarios", "120", "--modo", modo],
        capture_output=True, text=True, check=True).stdout.splitlines()[-1])["huella"]
    assert corre("puro") == corre("compilado")


# Casos borde ------------------------------------------------------------------

def construir(filas, items):
    indptr = [0]
    indices, data = [], []
    for fila in filas:
        norma = sum(v * v for _, v in fila) ** 0.5 or 1.0
        for i, v in fila:
            indices.append(i)
            data.append(v / norma)
        indptr.append(len(indices))
    return Dataset(np.array(indptr, np.int64), np.array(indices, np.int32),
                   np.array(data, np.float64), items, np.array(data, np.float32),
                   np.arange(len(filas)), np.arange(items), {})


def test_usuario_sin_coincidencias_queda_vacio():
    d = construir([[(0, 5.0)], [(0, 3.0)], [(9, 4.0)]], 10)
    ids, sims = secuencial(d, 2)
    assert ids[2].tolist() == [-1, -1] and sims[2].tolist() == [0.0, 0.0]
    assert ids[0, 0] == 1 and sims[0, 0] == pytest.approx(1.0)


def test_empates_se_resuelven_por_id_menor():
    d = construir([[(0, 1.0)], [(0, 2.0)], [(0, 3.0)], [(0, 4.0)]], 1)
    ids, _ = secuencial(d, 2)
    assert ids[0].tolist() == [1, 2]
    assert ids[3].tolist() == [0, 1]


def test_k_mayor_que_usuarios():
    d = construir([[(0, 1.0)], [(0, 1.0)]], 1)
    ids, _ = secuencial(d, 5)
    assert ids[0].tolist() == [1, -1, -1, -1, -1]


def test_no_es_su_propio_vecino():
    d = sintetico()
    ids, _ = secuencial(d, 10)
    assert not (ids == np.arange(d.n_usuarios)[:, None]).any()


def test_mas_procesos_que_usuarios():
    d = construir([[(0, 1.0)], [(0, 2.0)], [(0, 3.0)]], 1)
    ids_s, sims_s = secuencial(d, 2)
    ids_p, sims_p, _ = resolver(d, 2, 3, "filas")
    assert np.array_equal(ids_s, ids_p) and np.array_equal(sims_s, sims_p)


@pytest.mark.parametrize("estrategia", ["filas", "trabajo"])
def test_reparto_cubre_todas_las_filas(estrategia):
    d = sintetico()
    for p in (1, 2, 3, 7, 16):
        c = nucleo.repartir(d.indptr, p, estrategia)
        assert c[0] == 0 and c[-1] == d.n_usuarios and len(c) == p + 1
        assert (np.diff(c) >= 0).all()


def test_trabajo_balancea_mejor_que_filas():
    d = sintetico(n=1000, items=200)
    costo = nucleo.trabajo_por_fila(d.indptr)
    def desbalance(est):
        c = nucleo.repartir(d.indptr, 4, est)
        cargas = [costo[c[i]:c[i + 1]].sum() for i in range(4)]
        return max(cargas) / np.mean(cargas)
    assert desbalance("trabajo") < desbalance("filas")
    assert desbalance("trabajo") < 1.05
