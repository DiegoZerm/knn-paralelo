"""Convierte corridas.csv en métricas, figuras y un resumen en Markdown.

    python experimentos/analizar.py --equipo diego

Todo sale de los datos crudos: no se edita ningún número a mano.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.optimize import curve_fit  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent

COLOR = {"numba": "#2a78d6", "mpi": "#eb6834"}
NOMBRE = {"numba": "numba (memoria compartida)", "mpi": "mpi4py (memoria distribuida)"}
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
REJILLA = "#e4e3df"
NEUTRO = "#8a8984"
SUPERFICIE = "#fcfcfb"
MARCADOR = {"numba": "o", "mpi": "s"}

plt.rcParams.update({
    "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE, "savefig.facecolor": SUPERFICIE,
    "font.size": 11, "text.color": TINTA, "axes.labelcolor": TINTA_2,
    "xtick.color": TINTA_2, "ytick.color": TINTA_2,
    "axes.edgecolor": REJILLA, "axes.grid": True, "grid.color": REJILLA, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "legend.frameon": False, "lines.linewidth": 2, "lines.markersize": 7,
    "figure.dpi": 100, "savefig.dpi": 200,
})



def nombre_cpu(esp):
    """Modelo del CPU; si lscpu salió en otro idioma, lo busca en su salida completa."""
    cpu = esp.get("cpu", "")
    if cpu and cpu not in ("x86_64", "aarch64", ""):
        return cpu
    for linea in esp.get("lscpu", "").splitlines():
        clave, _, valor = linea.partition(":")
        if clave.strip() in ("Model name", "Nombre del modelo") and valor.strip():
            return valor.strip()
    return cpu or "desconocido"

def amdahl(p, f):
    return 1.0 / ((1.0 - f) + f / p)


def ajustar_f(ps, speedups):
    """Fracción paralela f por mínimos cuadrados sobre S(p)."""
    ps, speedups = np.asarray(ps, float), np.asarray(speedups, float)
    if len(ps) < 2:
        return float("nan")
    f, _ = curve_fit(amdahl, ps, speedups, p0=[0.95], bounds=(0.0, 1.0))
    return float(f[0])


def karp_flatt(s, p):
    """Fracción serial experimental: si crece con p, hay sobrecarga además de lo serial."""
    return (1.0 / s - 1.0 / p) / (1.0 - 1.0 / p)


def agregar(df):
    grupos = ["experimento", "version", "dataset", "n", "p", "estrategia", "afinidad"]
    df = df.copy()
    df["estrategia"] = df["estrategia"].fillna("")
    m = df.groupby(grupos, dropna=False).agg(
        reps=("t_total", "size"), t=("t_total", "mean"), sd=("t_total", "std"),
        calculo=("t_calculo", "mean"), combinar=("t_combinar", "mean"), ordenar=("t_ordenar", "mean"),
        carga=("t_carga", "mean"), rss=("rss_mb", "mean"), mhz=("mhz_medio", "mean"),
        temp=("temp_max", "max"),
    ).reset_index()
    return m


def metricas_fuertes(m, dataset):
    f = m[(m.experimento == "fuerte") & (m.dataset == dataset)]
    t1 = float(f[f.version == "secuencial_compilado"].t.iloc[0])
    sd1 = float(f[f.version == "secuencial_compilado"].sd.iloc[0])
    r = f[f.version.isin(["numba", "mpi"])].sort_values(["version", "p"]).copy()
    r["S"] = t1 / r.t
    # Propagación de error de un cociente de medias independientes.
    r["S_sd"] = r.S * np.sqrt((r.sd / r.t) ** 2 + (sd1 / t1) ** 2)
    r["E"] = r.S / r.p
    r["KF"] = [karp_flatt(s, p) if p > 1 else np.nan for s, p in zip(r.S, r.p)]
    return t1, sd1, r


def _eje_p(ax, ps, fisicos):
    ax.set_xticks(ps)
    ax.set_xlabel("Núcleos asignados (p)")
    if fisicos < max(ps):
        ax.axvline(fisicos, color=NEUTRO, lw=1, ls=":")
        ax.annotate("desde aquí se usa SMT", (fisicos, 1), xycoords=("data", "axes fraction"),
                    xytext=(5, -14), textcoords="offset points", color=TINTA_2, fontsize=9)


def _guardar(fig, carpeta, nombre):
    fig.tight_layout()
    fig.savefig(carpeta / f"{nombre}.png")
    plt.close(fig)


def fig_tiempo(r, t1, etiqueta, carpeta, fisicos):
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    for v in ("numba", "mpi"):
        d = r[r.version == v]
        ax.errorbar(d.p, d.t, yerr=d.sd, color=COLOR[v], marker=MARCADOR[v], capsize=3, label=NOMBRE[v])
    ax.axhline(t1, color=NEUTRO, ls="--", lw=1.5, label=f"Secuencial compilada: {t1:.1f} s")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%g"))
    ax.yaxis.set_minor_formatter(matplotlib.ticker.FormatStrFormatter("%g"))
    ax.tick_params(axis="y", which="minor", labelsize=8)
    ax.set_ylabel("Tiempo (s, escala log), media ± DE")
    ax.set_title(f"Tiempo contra núcleos: {etiqueta}")
    _eje_p(ax, sorted(r.p.unique()), fisicos)
    ax.legend()
    _guardar(fig, carpeta, f"tiempo_{etiqueta}")


def fig_speedup(r, etiqueta, carpeta, fisicos, fs):
    ps = sorted(r.p.unique())
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.plot(ps, ps, color=NEUTRO, ls="--", lw=1.5, label="Ideal, S(p) = p")
    finos = np.linspace(1, max(ps), 100)
    for v in ("numba", "mpi"):
        d = r[r.version == v]
        ax.errorbar(d.p, d.S, yerr=d.S_sd, color=COLOR[v], marker=MARCADOR[v], capsize=3,
                    label=f"{NOMBRE[v]}: f = {fs[v]:.4f}")
    # La curva de Amdahl se ajusta solo con núcleos físicos, como en la leyenda.
    ax.plot(finos, amdahl(finos, fs["numba"]), color=COLOR["numba"], lw=1, alpha=0.5, ls="-.",
            label="Amdahl ajustado (numba, núcleos físicos)")
    ax.set_ylabel("Speedup, S(p) = T₁ / Tₚ")
    ax.set_title(f"Speedup real contra ideal: {etiqueta}")
    _eje_p(ax, ps, fisicos)
    ax.set_ylim(bottom=0)
    ax.legend(loc="lower right", fontsize=9)
    _guardar(fig, carpeta, f"speedup_{etiqueta}")


def fig_eficiencia(r, etiqueta, carpeta, fisicos):
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for v in ("numba", "mpi"):
        d = r[r.version == v]
        ax.plot(d.p, d.E * 100, color=COLOR[v], marker=MARCADOR[v], label=NOMBRE[v])
    ax.axhline(100, color=NEUTRO, ls="--", lw=1.5)
    ax.set_ylabel("Eficiencia, E(p) = S(p) / p (%)")
    ax.set_ylim(0, 115)
    ax.set_title(f"Eficiencia: {etiqueta}")
    _eje_p(ax, sorted(r.p.unique()), fisicos)
    ax.legend(loc="lower left")
    _guardar(fig, carpeta, f"eficiencia_{etiqueta}")


def fig_combinar(r, etiqueta, carpeta):
    """Costo de combinar top-k, en ms: es la 'comunicación' de cada modelo."""
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for v in ("numba", "mpi"):
        d = r[r.version == v]
        ax.plot(d.p, d.combinar * 1000, color=COLOR[v], marker=MARCADOR[v], label=NOMBRE[v])
    ax.set_xticks(sorted(r.p.unique()))
    ax.set_xlabel("Núcleos asignados (p)")
    ax.set_ylabel("Combinar top-k (ms)")
    ax.set_ylim(bottom=0)
    ax.set_title(f"Costo de combinar resultados parciales: {etiqueta}")
    ax.legend()
    _guardar(fig, carpeta, f"combinar_{etiqueta}")


def speedup_triangulo(p):
    """Teoría con filas iguales: el primer bloque hace la fracción 1 - (1 - 1/p)^2 del
    triángulo, y el programa termina cuando termina ese bloque."""
    return 1.0 / (1.0 - (1.0 - 1.0 / p) ** 2)


def modelo_hardware(r, m, fisicos):
    """Predice S(p) con mediciones independientes del speedup, sin ajustar nada.

        p <= físicos:  S = p * (f_p / f_1)
        p >  físicos:  S = p * (G / 2) * (f_p / f_1)

    f_p es la frecuencia media medida con p trabajadores. G es lo que rinde un núcleo
    con sus dos hilos frente a un hilo, a igual frecuencia (experimento smt). Con bloques
    de igual trabajo, el programa va al ritmo de los hilos que comparten núcleo: G/2.
    """
    uno = r[(r.version == "numba") & (r.p == 1)]
    smt = m[(m.experimento == "smt") & (m.version == "numba")]
    if uno.empty or smt.empty or uno.mhz.isna().all() or smt.mhz.isna().all():
        return None
    f1, t_uno = float(uno.mhz.iloc[0]), float(uno.t.iloc[0])
    g = (t_uno / float(smt.t.iloc[0])) * (f1 / float(smt.mhz.iloc[0]))
    d = r[r.version == "numba"].sort_values("p")
    ajuste = np.where(d.p <= fisicos, 1.0, g / 2.0)
    return {"G": g, "p": d.p.to_numpy(), "S": (d.p * ajuste * d.mhz / f1).to_numpy()}


def fig_modelo(r, modelo, etiqueta, carpeta, fisicos):
    ps = sorted(r.p.unique())
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ax.plot(ps, ps, color=NEUTRO, ls="--", lw=1.5, label="Ideal")
    ax.plot(modelo["p"], modelo["S"], color="#1baf7a", marker="D",
            label=f"Modelo: frecuencia y SMT medidos (G = {modelo['G']:.2f})")
    for v in ("numba", "mpi"):
        d = r[r.version == v]
        ax.plot(d.p, d.S, color=COLOR[v], marker=MARCADOR[v], label=f"Real, {NOMBRE[v]}")
    ax.set_ylabel("Speedup")
    ax.set_title(f"Modelo de hardware contra medición: {etiqueta}")
    _eje_p(ax, ps, fisicos)
    ax.set_ylim(bottom=0)
    ax.legend(loc="lower right", fontsize=9)
    _guardar(fig, carpeta, f"modelo_{etiqueta}")


def fig_balanceo(m, t1, carpeta):
    b = m[m.experimento == "balanceo"]
    f = m[(m.experimento == "fuerte") & (m.dataset == "ml-1m") & (m.p > 1)]
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    ps = sorted(b.p.unique())
    ax.plot(ps, ps, color=NEUTRO, ls="--", lw=1.5, label="Ideal")
    teoria = [speedup_triangulo(q) for q in ps]
    ax.plot(ps, teoria, color=TINTA_2, ls=":", lw=1.5, label="Teoría del triángulo con filas iguales")
    d = f[f.version == "numba"].sort_values("p")
    ax.plot(d.p, t1 / d.t, color=COLOR["numba"], marker="o", label="Trabajo igual (numba)")
    d = b[b.version == "numba"].sort_values("p")
    ax.plot(d.p, t1 / d.t, color="#1baf7a", marker="D", label="Filas iguales (numba)")
    ax.set_xticks(ps)
    ax.set_xlabel("Núcleos asignados (p)")
    ax.set_ylabel("Speedup")
    ax.set_ylim(bottom=0)
    ax.set_title("El reparto importa: el triángulo castiga a filas iguales")
    ax.legend()
    _guardar(fig, carpeta, "balanceo")


def fig_memoria(m, dataset, carpeta):
    r = m[(m.experimento == "fuerte") & (m.dataset == dataset) & m.version.isin(["numba", "mpi"])]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for v in ("numba", "mpi"):
        d = r[r.version == v].sort_values("p")
        ax.plot(d.p, d.rss, color=COLOR[v], marker=MARCADOR[v], label=NOMBRE[v])
    ax.set_xticks(sorted(r.p.unique()))
    ax.set_xlabel("Núcleos asignados (p)")
    ax.set_ylabel("Memoria pico total (MB)")
    ax.set_ylim(bottom=0)
    ax.set_title(f"Memoria: {dataset}")
    ax.legend()
    _guardar(fig, carpeta, f"memoria_{dataset}")


def fig_frecuencia(m, dataset, carpeta):
    r = m[(m.experimento == "fuerte") & (m.dataset == dataset) & (m.version == "numba")].sort_values("p")
    if r.mhz.isna().all():
        return
    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    ax.plot(r.p, r.mhz, color=COLOR["numba"], marker="o")
    ax.set_xticks(sorted(r.p.unique()))
    ax.set_xlabel("Núcleos asignados (p)")
    ax.set_ylabel("Frecuencia media (MHz)")
    ax.set_title(f"Frecuencia de los núcleos en uso: {dataset}")
    _guardar(fig, carpeta, f"frecuencia_{dataset}")


def fig_banda(banda, carpeta):
    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    ax.plot(banda.p, banda.gb_s, color=COLOR["numba"], marker="o")
    ax.plot(banda.p, banda.gb_s.iloc[0] * banda.p, color=NEUTRO, ls="--", lw=1.5, label="Si escalara lineal")
    ax.set_xticks(banda.p)
    ax.set_xlabel("Hilos (p)")
    ax.set_ylabel("Ancho de banda (GB/s)")
    ax.set_ylim(bottom=0)
    ax.set_title("Ancho de banda de memoria medido (triad)")
    ax.legend()
    _guardar(fig, carpeta, "banda_memoria")


def tabla_md(df, columnas, formatos):
    filas = ["| " + " | ".join(columnas.values()) + " |",
             "|" + "|".join("---:" for _ in columnas) + "|"]
    for _, x in df.iterrows():
        filas.append("| " + " | ".join(formatos.get(c, "{}").format(x[c]) for c in columnas) + " |")
    return "\n".join(filas)


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--equipo", required=True)
    args = a.parse_args()
    carpeta = RAIZ / "resultados" / args.equipo
    figuras = carpeta / "figuras"
    figuras.mkdir(exist_ok=True)
    df = pd.read_csv(carpeta / "corridas.csv")
    esp = json.loads((carpeta / "especificaciones.json").read_text())
    fisicos = esp["nucleos_fisicos"]
    m = agregar(df)

    # Correctitud: una sola huella por dataset, tamaño y k.
    huellas = df.groupby(["dataset", "n", "k"]).huella.nunique()
    correcto = bool((huellas == 1).all())

    md = [f"# Resultados de {args.equipo}", "",
          f"**Equipo:** {nombre_cpu(esp)}, {fisicos} núcleos físicos, {esp['cpus_visibles']} CPUs lógicas, "
          f"{esp['ram_gb']} GB, {esp['entorno']}.", "",
          f"**Correctitud:** {'todas las versiones coinciden' if correcto else 'HAY HUELLAS DISTINTAS'} "
          f"en {len(huellas)} configuraciones de datos ({len(df)} mediciones).", ""]
    resumen = {"equipo": args.equipo, "correcto": correcto, "datasets": {}}

    for ds in m[m.experimento == "fuerte"].dataset.unique():
        t1, sd1, r = metricas_fuertes(m, ds)
        n = int(r.n.iloc[0])
        etiqueta = ds
        fs, fs_todos = {}, {}
        for v in ("numba", "mpi"):
            d = r[r.version == v]
            fis = d[d.p <= fisicos]
            fs[v] = ajustar_f(fis.p, fis.S)
            fs_todos[v] = ajustar_f(d.p, d.S)
        fig_tiempo(r, t1, etiqueta, figuras, fisicos)
        fig_speedup(r, etiqueta, figuras, fisicos, fs)
        fig_eficiencia(r, etiqueta, figuras, fisicos)
        fig_combinar(r, etiqueta, figuras)
        fig_memoria(m, ds, figuras)
        fig_frecuencia(m, ds, figuras)
        modelo = modelo_hardware(r, m, fisicos) if ds == "ml-1m" else None
        if modelo:
            fig_modelo(r, modelo, etiqueta, figuras, fisicos)

        serial = r[r.p == 1].iloc[0]
        f_fases = 1 - serial.ordenar / serial.t
        f_con_carga = 1 - (serial.ordenar + serial.carga) / (serial.t + serial.carga)
        md += [f"## {ds} ({n:,} usuarios)", "",
               f"T₁ secuencial compilada = {t1:.2f} ± {sd1:.2f} s.", "",
               tabla_md(r, {"version": "Versión", "p": "p", "reps": "Reps", "t": "T (s)", "sd": "DE",
                            "S": "S(p)", "E": "E(p)", "KF": "Karp-Flatt", "combinar": "Combinar (s)",
                            "rss": "RAM (MB)", "mhz": "MHz"},
                        {"t": "{:.2f}", "sd": "{:.3f}", "S": "{:.2f}", "E": "{:.2f}", "KF": "{:.4f}",
                         "combinar": "{:.3f}", "rss": "{:.0f}", "mhz": "{:.0f}"}), "",
               "| Fracción paralela f | numba | mpi |", "|---|---:|---:|",
               f"| Ajuste con núcleos físicos (p ≤ {fisicos}) | {fs['numba']:.4f} | {fs['mpi']:.4f} |",
               f"| Ajuste con todos los p | {fs_todos['numba']:.4f} | {fs_todos['mpi']:.4f} |",
               f"| Medida por fases (solo cálculo y orden) | {f_fases:.4f} | {f_fases:.4f} |",
               f"| Medida por fases incluyendo carga de datos | {f_con_carga:.4f} | {f_con_carga:.4f} |", ""]
        if modelo:
            real = r[r.version == "numba"].sort_values("p").S.to_numpy()
            md += [f"**Modelo de hardware** (G = {modelo['G']:.2f}, sin parámetros ajustados):", "",
                   "| p | S modelo | S numba | S mpi |", "|---:|---:|---:|---:|"]
            s_mpi = r[r.version == "mpi"].sort_values("p").S.to_numpy()
            for q, sm, sr, sp in zip(modelo["p"], modelo["S"], real, s_mpi):
                md.append(f"| {q} | {sm:.2f} | {sr:.2f} | {sp:.2f} |")
            md.append("")
        resumen["datasets"][ds] = {
            "n": n, "t1": t1, "t1_sd": sd1, "f_fisicos": fs, "f_todos": fs_todos,
            "f_fases": f_fases, "f_con_carga": f_con_carga,
            "curvas": {v: r[r.version == v][["p", "t", "sd", "S", "E"]].to_dict("list") for v in ("numba", "mpi")},
        }

    t1 = resumen["datasets"]["ml-1m"]["t1"]
    if (m.experimento == "balanceo").any():
        fig_balanceo(m, t1, figuras)
        b = m[m.experimento == "balanceo"].copy()
        b["S"] = t1 / b.t
        b["teoria"] = speedup_triangulo(b.p)
        md += ["## Reparto por filas iguales", "",
               tabla_md(b.sort_values(["version", "p"]),
                        {"version": "Versión", "p": "p", "t": "T (s)", "sd": "DE", "S": "S(p)", "teoria": "S teórico"},
                        {"t": "{:.2f}", "sd": "{:.3f}", "S": "{:.2f}", "teoria": "{:.2f}"}), ""]

    otros = m[m.experimento.isin(["smt", "smt_mpi_defecto", "mpi_dormir", "mpi_ventana", "sobresuscripcion", "debil"])]
    if len(otros):
        md += ["## Otros experimentos", "",
               tabla_md(otros.sort_values(["experimento", "version", "p"]),
                        {"experimento": "Experimento", "version": "Versión", "n": "n", "p": "p",
                         "afinidad": "Afinidad", "t": "T (s)", "sd": "DE"},
                        {"t": "{:.2f}", "sd": "{:.3f}", "n": "{:.0f}"}), ""]

    puro = m[m.experimento == "python_puro"]
    if len(puro) == 2:
        tp = float(puro[puro.version == "secuencial_puro"].t.iloc[0])
        tc = float(puro[puro.version == "secuencial_compilado"].t.iloc[0])
        resumen["python_puro"] = {"n": int(puro.n.iloc[0]), "t_puro": tp, "t_compilado": tc, "razon": tp / tc}
        md += ["## Python puro contra compilado", "",
               f"Con {int(puro.n.iloc[0])} usuarios: {tp:.2f} s contra {tc:.3f} s, "
               f"**{tp / tc:.0f} veces**. Esta ganancia viene de compilar, no de paralelizar; "
               "por eso no se usa para el speedup.", ""]

    archivo_banda = carpeta / "banda_memoria.csv"
    if archivo_banda.exists():
        banda = pd.read_csv(archivo_banda).sort_values("p")
        fig_banda(banda, figuras)
        resumen["banda_gb_s"] = banda.to_dict("list")
        md += ["## Ancho de banda de memoria", "",
               tabla_md(banda, {"p": "Hilos", "gb_s": "GB/s"}, {"p": "{:.0f}", "gb_s": "{:.1f}"}), ""]

    (carpeta / "RESUMEN.md").write_text("\n".join(md))
    (carpeta / "resumen.json").write_text(json.dumps(resumen, indent=2, default=float))
    print("\n".join(md))


if __name__ == "__main__":
    main()
