"""Compara los resultados de todos los equipos del grupo.

    python experimentos/comparar.py

Reglas: el speedup de cada máquina usa SU propio T1. Los tiempos absolutos indican
cuál es más rápida; speedup y eficiencia indican cuál paraleliza mejor.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analizar import COLOR, NEUTRO, RAIZ, ajustar_f, plt, _guardar, tabla_md  # noqa: F401

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
MARCADORES = ["o", "s", "D", "^", "v", "P", "X", "*"]


def cargar_equipos():
    salida = []
    for c in sorted((RAIZ / "resultados").iterdir()):
        if c.is_dir() and not c.name.startswith(("_", "comparacion")) and (c / "resumen.json").exists():
            salida.append((c.name, json.loads((c / "especificaciones.json").read_text()),
                           json.loads((c / "resumen.json").read_text()), c))
    return salida


def huella_ml1m(carpeta):
    df = pd.read_csv(carpeta / "corridas.csv")
    d = df[(df.dataset == "ml-1m") & (df.experimento == "fuerte")]
    return d.huella.iloc[0] if len(d) else ""


def main():
    equipos = cargar_equipos()
    if not equipos:
        raise SystemExit("No hay equipos analizados en resultados/")
    salida = RAIZ / "resultados" / "comparacion"
    salida.mkdir(exist_ok=True)

    filas = []
    fig, ax = plt.subplots(figsize=(8, 5))
    maximo = 1
    for i, (nombre, esp, res, carpeta) in enumerate(equipos):
        ds = res["datasets"]["ml-1m"]
        for v in ("numba", "mpi"):
            c = ds["curvas"][v]
            en_fisicos = [j for j, q in enumerate(c["p"]) if q <= esp["nucleos_fisicos"]]
            j = en_fisicos[-1]
            filas.append({
                "equipo": nombre, "cpu": esp["cpu"], "nucleos": f"{esp['nucleos_fisicos']}/{esp['cpus_visibles']}",
                "ram": esp["ram_gb"], "entorno": esp["entorno"], "version": v, "t1": ds["t1"],
                "p": c["p"][j], "S": c["S"][j], "E": c["E"][j],
                "Smax": max(c["S"]), "f": ds["f_fisicos"][v], "huella": huella_ml1m(carpeta),
                "banda": max(res.get("banda_gb_s", {}).get("gb_s", [float("nan")])),
            })
        c = ds["curvas"]["numba"]
        maximo = max(maximo, max(c["p"]))
        ax.plot(c["p"], c["S"], color=SERIES[i % 8], marker=MARCADORES[i % 8], label=f"{nombre}: {esp['cpu'][:28]}")
    ax.plot([1, maximo], [1, maximo], color=NEUTRO, ls="--", lw=1.5, label="Ideal")
    ax.set_xlabel("Núcleos asignados (p)")
    ax.set_ylabel("Speedup (cada máquina contra su propio T₁)")
    ax.set_title("¿Qué máquina paraleliza mejor? numba, ML-1M")
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=9)
    _guardar(fig, salida, "speedup_por_equipo")

    t = pd.DataFrame(filas)
    uno = t[t.version == "numba"].sort_values("t1")
    fig, ax = plt.subplots(figsize=(8, max(2.5, 0.8 * len(uno) + 1.2)))
    ax.barh(uno.equipo, uno.t1, color=SERIES[0], height=0.55)
    for y, x in enumerate(uno.t1):
        ax.annotate(f"{x:.1f} s", (x, y), xytext=(4, 0), textcoords="offset points", va="center")
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("T₁ secuencial compilada, ML-1M (s)")
    ax.set_title("¿Qué máquina es más rápida con un núcleo?")
    _guardar(fig, salida, "t1_por_equipo")

    misma = t.huella.nunique() == 1
    md = ["# Comparación entre equipos", "",
          f"**Correctitud entre máquinas:** {'misma huella en todas' if misma else 'hay diferencias, revisar'}"
          f" ({', '.join(sorted(set(t.huella)))}).", "",
          tabla_md(t, {"equipo": "Equipo", "cpu": "CPU", "nucleos": "Físicos/lógicos", "ram": "RAM GB",
                       "entorno": "Entorno", "version": "Versión", "t1": "T₁ (s)", "p": "p físico máx.",
                       "S": "S", "E": "E", "Smax": "S máx.", "f": "f", "banda": "Memoria GB/s"},
                   {"t1": "{:.1f}", "S": "{:.2f}", "E": "{:.2f}", "Smax": "{:.2f}", "f": "{:.4f}",
                    "banda": "{:.1f}"}), ""]
    (salida / "COMPARACION.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
