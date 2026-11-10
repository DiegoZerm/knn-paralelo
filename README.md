# Sistema de recomendación con KNN paralelo

Evidencia de producto de Cómputo de Alto Rendimiento (P7). Calcula los k vecinos más
parecidos de cada usuario con similitud coseno, una tarea cuadrática en el número de
usuarios, y mide con experimentos cuánto mejora el rendimiento al paralelizarla y por qué.

## Equipo

- Diego Cortes Zermeño
- Irving Nahir Ferrusca Jaimez
- César Iván Ramírez Castañon
- Axel Miguel Quevedo Barrios

## Ejecución rápida

Requiere Linux o WSL con [Miniforge](https://github.com/conda-forge/miniforge), o Docker.

```bash
./replicar.sh <tu-nombre>          # todo: datos, tests, experimentos y análisis
```

Con Docker:

```bash
docker build -t knn-paralelo .
docker run --rm -v "$PWD/resultados:/app/resultados" knn-paralelo <tu-nombre>
```

Los resultados quedan en `resultados/<tu-nombre>/RESUMEN.md`. La guía paso a paso está en
[docs/GUIA_EQUIPO.md](docs/GUIA_EQUIPO.md).

Cada versión también corre por separado:

```bash
conda env create -f environment.yml && conda activate knn-paralelo
python -m comun.datos ml-1m

python secuencial/knn_secuencial.py                       # compilada, 1 núcleo
python secuencial/knn_secuencial.py --usuarios 500 --modo puro   # Python puro
python paralelo_numba/knn_numba.py -p 4
mpirun --bind-to none --oversubscribe -n 4 python paralelo_mpi/knn_mpi.py
python demo/demo.py --usuario 42                          # demo de la presentación
./demo/abrir_demo.sh HDMI-A-1                              # abre presentación, terminal y respaldo (Hyprland)
```

`environment.yml` define las dependencias y `environment.lock.yml` guarda las versiones
exactas usadas en las mediciones.

## Estructura

| Carpeta | Contenido |
|---|---|
| `comun/` | `nucleo.py`: kernel único de KNN. `datos.py`: descarga y CSR. `recomendador.py` |
| `secuencial/` | Versión con ciclos; es la referencia de tiempo y de correctitud |
| `paralelo_numba/` | Memoria compartida con hilos y `prange` |
| `paralelo_mpi/` | Memoria distribuida con mpi4py y combinación de top-k en árbol |
| `experimentos/` | Orquestador, análisis, verificación, calidad, control aleatorizado de MPI y comparación entre máquinas |
| `resultados/` | CSV crudos, figuras y resumen de cada máquina |
| `tests/` | Correctitud contra scikit-learn, entre versiones y en casos borde |
| `demo/` | Demo en vivo y respaldo |
| `docs/` | [Análisis](docs/ANALISIS.md), [guía para replicar](docs/GUIA_EQUIPO.md) y [preparación de preguntas](docs/PREGUNTAS.md) |

## Diseño

**Un solo kernel.** Las tres versiones llaman al mismo código de `comun/nucleo.py`. Con
`NUMBA_DISABLE_JIT=1`, ese código corre como Python puro: la versión "con ciclos" y las
compiladas no pueden divergir, y entre versiones solo cambia el modelo de paralelismo.

**Triángulo superior por bloques.** Cada par `(u, v)` con `u < v` se calcula una vez y
actualiza el top-k de ambos usuarios. Cada trabajador procesa un bloque contiguo de filas y
llena un top-k parcial privado, sin locks. Después los parciales se combinan.

**Top-k en lugar de matriz.** Se guarda un min-heap de tamaño k por usuario, no la matriz de
similitudes. La memoria pasa de O(n²) a O(n·k).

**Orden total.** Mayor similitud gana y, si empatan, gana el id menor. Por eso el resultado
no depende del reparto ni del orden de llegada, y todas las versiones producen la misma
huella SHA-256.

**Reparto por trabajo.** Una fila temprana del triángulo compara contra casi todos los
usuarios. Las fronteras de los bloques se eligen para igualar el costo estimado.

## Resultados

El análisis completo, con la interpretación de por qué no escala más, está en
[docs/ANALISIS.md](docs/ANALISIS.md). En ML-1M con numba: T₁ = 24.9 s, S(4) = 3.84 y
S(8) = 5.30; las tres versiones dan exactamente el mismo resultado.

Los cuatro integrantes replicaron el sistema en sus computadoras (de 4 a 8 núcleos, AMD e
Intel): las cuatro dan la misma huella y en la de 8 núcleos el speedup llega a 8.92 con 16 hilos (6.74 solo con los núcleos físicos). La
comparación está en [resultados/comparacion/](resultados/comparacion/COMPARACION.md).

## Metodología de medición

- `T₁` es la versión secuencial **compilada**, no la de Python puro. Si no, el speedup
  mezclaría la ganancia de compilar con la de paralelizar. Python puro se reporta aparte.
- Se fija la afinidad: primero un hilo por núcleo físico y luego los hermanos SMT.
- `OMP_NUM_THREADS=1` y similares evitan paralelismo oculto en bibliotecas.
- La compilación JIT ocurre antes de medir; la carga de datos se reporta aparte.
- El orden de las corridas es aleatorio, y se registran frecuencia y temperatura.
- Ningún número se edita a mano: las figuras y tablas salen de `corridas.csv`.

## Uso de IA

El código, los experimentos y la documentación se desarrollaron con apoyo de asistentes de
IA (Claude Code). El profesor autorizó su uso. Cada integrante replica el sistema en su
equipo y es responsable de poder explicarlo.

## Datos

[MovieLens](https://grouplens.org/datasets/movielens/) y
[Goodbooks-10k](https://github.com/zygmuntz/goodbooks-10k). No se incluyen en el repositorio:
`comun/datos.py` los descarga y valida su SHA-256. MovieLens no permite redistribuirlos.

F. Maxwell Harper y Joseph A. Konstan. 2015. The MovieLens Datasets: History and Context.
ACM Transactions on Interactive Intelligent Systems 5(4).
