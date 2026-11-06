"""Descarga, valida y prepara los datasets como matrices CSR normalizadas.

Uso:
    python -m comun.datos ml-1m goodbooks
    python -m comun.datos --lista
"""
from __future__ import annotations

import argparse
import hashlib
import io
import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

RAIZ = Path(__file__).resolve().parent.parent
DIR_DATOS = RAIZ / "datos"

FUENTES = {
    "ml-1m": {
        "url": "https://files.grouplens.org/datasets/movielens/ml-1m.zip",
        "sha256": "a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20",
    },
    "ml-25m": {
        "url": "https://files.grouplens.org/datasets/movielens/ml-25m.zip",
        "sha256": "8b21cfb7eb1706b4ec0aac894368d90acf26ebdfb6aced3ebd4ad5bd1eb9c6aa",
    },
    "goodbooks": {
        "url": "https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/ratings.csv",
        "url_titulos": "https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/books.csv",
        "sha256": "1ee8a97172bd6d97147a30d9cfb3029ac240bd27ba2aa9365981c051c65113f8",
    },
}


@dataclass
class Dataset:
    """Matriz usuario-ítem en CSR. `data` está normalizada por fila (L2),
    así el producto punto entre dos filas es directamente su similitud coseno."""

    indptr: np.ndarray
    indices: np.ndarray
    data: np.ndarray
    n_items: int
    calificaciones: np.ndarray
    usuarios: np.ndarray
    items: np.ndarray
    titulos: dict

    @property
    def n_usuarios(self) -> int:
        return len(self.indptr) - 1

    @property
    def nnz(self) -> int:
        return int(self.indptr[-1])

    def matriz_csr(self) -> sp.csr_matrix:
        return sp.csr_matrix(
            (self.data, self.indices, self.indptr), shape=(self.n_usuarios, self.n_items)
        )


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for trozo in iter(lambda: f.read(1 << 20), b""):
            h.update(trozo)
    return h.hexdigest()


def _bajar(url: str, destino: Path) -> None:
    if destino.exists():
        return
    print(f"Descargando {url}")
    temporal = destino.with_suffix(destino.suffix + ".parcial")
    peticion = urllib.request.Request(url, headers={"User-Agent": "knn-paralelo"})
    with urllib.request.urlopen(peticion, timeout=120) as r, open(temporal, "wb") as f:
        shutil.copyfileobj(r, f)
    temporal.rename(destino)


def _leer_crudo(nombre: str) -> tuple[pd.DataFrame, dict]:
    """Regresa (usuario, item, calificacion) y {id_item: titulo}."""
    fuente = FUENTES[nombre]
    if nombre == "goodbooks":
        crudo = DIR_DATOS / "goodbooks_ratings.csv"
        libros = DIR_DATOS / "goodbooks_books.csv"
        _bajar(fuente["url"], crudo)
        _bajar(fuente["url_titulos"], libros)
        _verificar(nombre, crudo)
        df = pd.read_csv(crudo).rename(
            columns={"user_id": "usuario", "book_id": "item", "rating": "calificacion"}
        )
        t = pd.read_csv(libros, usecols=["book_id", "title"])
        return df, dict(zip(t["book_id"], t["title"]))

    crudo = DIR_DATOS / f"{nombre}.zip"
    _bajar(fuente["url"], crudo)
    _verificar(nombre, crudo)
    with zipfile.ZipFile(crudo) as z:
        if nombre == "ml-1m":
            texto = z.read("ml-1m/ratings.dat").decode("latin-1")
            df = pd.read_csv(
                io.StringIO(texto), sep="::", engine="python",
                names=["usuario", "item", "calificacion", "ts"],
            )
            pelis = z.read("ml-1m/movies.dat").decode("latin-1")
            t = pd.read_csv(
                io.StringIO(pelis), sep="::", engine="python", names=["item", "titulo", "generos"]
            )
        else:
            with z.open(f"{nombre}/ratings.csv") as f:
                df = pd.read_csv(f).rename(
                    columns={"userId": "usuario", "movieId": "item", "rating": "calificacion"}
                )
            with z.open(f"{nombre}/movies.csv") as f:
                t = pd.read_csv(f).rename(columns={"movieId": "item", "title": "titulo"})
    return df, dict(zip(t["item"], t["titulo"]))


def _verificar(nombre: str, ruta: Path) -> None:
    esperado = FUENTES[nombre]["sha256"]
    real = _sha256(ruta)
    if esperado is not None and real != esperado:
        raise RuntimeError(f"{ruta.name}: sha256 {real} no coincide con {esperado}")


def preparar(nombre: str) -> Path:
    """Convierte el dataset crudo en un .npz CSR ordenado y normalizado."""
    DIR_DATOS.mkdir(exist_ok=True)
    salida = DIR_DATOS / f"{nombre}.npz"
    if salida.exists():
        return salida

    df, titulos = _leer_crudo(nombre)
    df = df[["usuario", "item", "calificacion"]].drop_duplicates(
        ["usuario", "item"], keep="last"
    )
    df = df[df["calificacion"] > 0]

    usuarios, fila = np.unique(df["usuario"].to_numpy(), return_inverse=True)
    items, columna = np.unique(df["item"].to_numpy(), return_inverse=True)
    m = sp.csr_matrix(
        (df["calificacion"].to_numpy(np.float64), (fila, columna)),
        shape=(len(usuarios), len(items)),
    )
    m.sort_indices()

    por_fila = np.repeat(np.arange(len(usuarios)), np.diff(m.indptr))
    normas = np.sqrt(np.bincount(por_fila, weights=m.data**2, minlength=len(usuarios)))
    normalizados = m.data / normas[por_fila]

    np.savez(
        salida,
        indptr=m.indptr.astype(np.int64),
        indices=m.indices.astype(np.int32),
        data=normalizados,
        calificaciones=m.data.astype(np.float32),
        n_items=len(items),
        usuarios=usuarios,
        items=items,
        id_titulos=np.array(list(titulos.keys())),
        titulos=np.array(list(titulos.values()), dtype=object),
    )
    return salida


def cargar(nombre: str, usuarios: int | None = None, semilla: int = 42) -> Dataset:
    """Carga el dataset; con `usuarios` toma una muestra aleatoria reproducible."""
    z = np.load(preparar(nombre), allow_pickle=True)
    indptr, indices, data = z["indptr"], z["indices"], z["data"]
    calif = z["calificaciones"]
    ids_usuario = z["usuarios"]

    total = len(indptr) - 1
    if usuarios is not None and usuarios < total:
        elegidos = np.sort(np.random.default_rng(semilla).choice(total, usuarios, replace=False))
        tamanos = np.diff(indptr)[elegidos]
        nuevo_indptr = np.concatenate(([0], np.cumsum(tamanos))).astype(np.int64)
        mascara = np.concatenate([np.arange(indptr[u], indptr[u + 1]) for u in elegidos])
        indptr, indices, data = nuevo_indptr, indices[mascara], data[mascara]
        calif, ids_usuario = calif[mascara], ids_usuario[elegidos]

    return Dataset(
        indptr=indptr,
        indices=indices,
        data=data,
        n_items=int(z["n_items"]),
        calificaciones=calif,
        usuarios=ids_usuario,
        items=z["items"],
        titulos=dict(zip(z["id_titulos"].tolist(), z["titulos"].tolist())),
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("datasets", nargs="*", choices=[*FUENTES, []], default=[])
    p.add_argument("--lista", action="store_true", help="muestra tamaños de lo ya preparado")
    a = p.parse_args()
    for nombre in a.datasets:
        d = cargar(nombre)
        print(
            f"{nombre}: {d.n_usuarios:,} usuarios, {d.n_items:,} ítems, {d.nnz:,} calificaciones"
        )
    if a.lista:
        for nombre in FUENTES:
            if (DIR_DATOS / f"{nombre}.npz").exists():
                d = cargar(nombre)
                print(f"{nombre}: {d.n_usuarios:,} usuarios, {d.nnz:,} calificaciones")


if __name__ == "__main__":
    main()
