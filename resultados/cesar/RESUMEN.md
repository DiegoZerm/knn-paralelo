# Resultados de cesar

**Equipo:** desconocido, 4 núcleos físicos, 8 CPUs lógicas, 30.4 GB, nativo.

**Correctitud:** todas las versiones coinciden en 2 configuraciones de datos (84 mediciones).

## ml-1m (6,040 usuarios)

T₁ secuencial compilada = 41.65 ± 0.10 s.

| Versión | p | Reps | T (s) | DE | S(p) | E(p) | Karp-Flatt | Combinar (s) | RAM (MB) | MHz |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mpi | 1 | 3 | 41.78 | 1.491 | 1.00 | 1.00 | nan | 0.000 | 214 | 2732 |
| mpi | 2 | 3 | 23.32 | 0.167 | 1.79 | 0.89 | 0.1200 | 0.024 | 431 | 2455 |
| mpi | 3 | 3 | 16.74 | 0.690 | 2.49 | 0.83 | 0.1027 | 0.052 | 649 | 2370 |
| mpi | 4 | 3 | 14.12 | 0.322 | 2.95 | 0.74 | 0.1188 | 0.062 | 866 | 2201 |
| mpi | 6 | 3 | 13.71 | 0.426 | 3.04 | 0.51 | 0.1951 | 0.125 | 1296 | 2081 |
| mpi | 8 | 3 | 12.30 | 0.742 | 3.38 | 0.42 | 0.1948 | 0.165 | 1725 | 2118 |
| numba | 1 | 3 | 41.69 | 1.213 | 1.00 | 1.00 | nan | 0.000 | 202 | 2660 |
| numba | 2 | 3 | 22.98 | 0.668 | 1.81 | 0.91 | 0.1036 | 0.014 | 206 | 2440 |
| numba | 3 | 3 | 16.59 | 0.130 | 2.51 | 0.84 | 0.0974 | 0.020 | 209 | 2320 |
| numba | 4 | 3 | 13.46 | 0.859 | 3.09 | 0.77 | 0.0975 | 0.021 | 212 | 2248 |
| numba | 6 | 3 | 11.95 | 0.038 | 3.49 | 0.58 | 0.1442 | 0.023 | 220 | 2214 |
| numba | 8 | 3 | 10.96 | 0.343 | 3.80 | 0.48 | 0.1578 | 0.028 | 226 | 2241 |

| Fracción paralela f | numba | mpi |
|---|---:|---:|
| Ajuste con núcleos físicos (p ≤ 4) | 0.9023 | 0.8853 |
| Ajuste con todos los p | 0.8559 | 0.8205 |
| Medida por fases (solo cálculo y orden) | 0.9997 | 0.9997 |
| Medida por fases incluyendo carga de datos | 0.9991 | 0.9991 |

**Modelo de hardware** (G = 1.35, sin parámetros ajustados):

| p | S modelo | S numba | S mpi |
|---:|---:|---:|---:|
| 1 | 1.00 | 1.00 | 1.00 |
| 2 | 1.83 | 1.81 | 1.79 |
| 3 | 2.62 | 2.51 | 2.49 |
| 4 | 3.38 | 3.09 | 2.95 |
| 6 | 3.37 | 3.49 | 3.04 |
| 8 | 4.54 | 3.80 | 3.38 |

## Reparto por filas iguales

| Versión | p | T (s) | DE | S(p) | S teórico |
|---:|---:|---:|---:|---:|---:|
| mpi | 2 | 33.69 | 0.412 | 1.24 | 1.33 |
| mpi | 3 | 27.08 | 0.060 | 1.54 | 1.80 |
| mpi | 4 | 23.63 | 0.240 | 1.76 | 2.29 |
| mpi | 6 | 21.85 | 1.305 | 1.91 | 3.27 |
| mpi | 8 | 20.38 | 0.381 | 2.04 | 4.27 |
| numba | 2 | 31.90 | 0.095 | 1.31 | 1.33 |
| numba | 3 | 25.93 | 1.797 | 1.61 | 1.80 |
| numba | 4 | 20.36 | 0.171 | 2.05 | 2.29 |
| numba | 6 | 15.61 | 0.128 | 2.67 | 3.27 |
| numba | 8 | 13.23 | 0.304 | 3.15 | 4.27 |

## Otros experimentos

| Experimento | Versión | n | p | Afinidad | T (s) | DE |
|---:|---:|---:|---:|---:|---:|---:|
| smt | mpi | 6040 | 2 | hermanos | 31.10 | 0.501 |
| smt | numba | 6040 | 2 | hermanos | 30.47 | 0.044 |
| smt_mpi_defecto | mpi | 6040 | 2 | defecto | 30.75 | 0.042 |

## Python puro contra compilado

Con 500 usuarios: 22.90 s contra 0.290 s, **79 veces**. Esta ganancia viene de compilar, no de paralelizar; por eso no se usa para el speedup.

## Ancho de banda de memoria

| Hilos | GB/s |
|---:|---:|
| 1 | 13.6 |
| 2 | 19.8 |
| 3 | 20.6 |
| 4 | 20.3 |
| 6 | 19.8 |
| 8 | 18.9 |
