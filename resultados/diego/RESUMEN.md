# Resultados de diego

**Equipo:** AMD Ryzen 5 3550H with Radeon Vega Mobile Gfx, 4 núcleos físicos, 8 CPUs lógicas, 22.9 GB, nativo.

**Correctitud:** todas las versiones coinciden en 9 configuraciones de datos (276 mediciones).

## goodbooks (20,000 usuarios)

T₁ secuencial compilada = 265.19 ± 0.65 s.

| Versión | p | Reps | T (s) | DE | S(p) | E(p) | Karp-Flatt | Combinar (s) | RAM (MB) | MHz |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mpi | 1 | 5 | 265.66 | 1.464 | 1.00 | 1.00 | nan | 0.000 | 356 | 3683 |
| mpi | 2 | 5 | 133.33 | 0.385 | 1.99 | 0.99 | 0.0055 | 0.050 | 622 | 3636 |
| mpi | 3 | 5 | 90.00 | 0.505 | 2.95 | 0.98 | 0.0090 | 0.098 | 887 | 3599 |
| mpi | 4 | 5 | 70.08 | 1.603 | 3.78 | 0.95 | 0.0190 | 0.115 | 1165 | 3563 |
| mpi | 6 | 5 | 59.46 | 0.831 | 4.46 | 0.74 | 0.0691 | 0.192 | 1707 | 3449 |
| mpi | 8 | 5 | 48.87 | 0.961 | 5.43 | 0.68 | 0.0677 | 0.241 | 2248 | 3372 |
| numba | 1 | 5 | 262.73 | 2.058 | 1.01 | 1.01 | nan | 0.000 | 292 | 3690 |
| numba | 2 | 5 | 131.63 | 1.497 | 2.01 | 1.01 | -0.0073 | 0.032 | 292 | 3646 |
| numba | 3 | 5 | 88.49 | 0.688 | 3.00 | 1.00 | 0.0005 | 0.043 | 292 | 3596 |
| numba | 4 | 5 | 67.28 | 0.216 | 3.94 | 0.99 | 0.0049 | 0.046 | 292 | 3568 |
| numba | 6 | 5 | 56.02 | 0.710 | 4.73 | 0.79 | 0.0535 | 0.054 | 297 | 3415 |
| numba | 8 | 5 | 45.45 | 0.624 | 5.84 | 0.73 | 0.0530 | 0.055 | 317 | 3452 |

| Fracción paralela f | numba | mpi |
|---|---:|---:|
| Ajuste con núcleos físicos (p ≤ 4) | 0.9962 | 0.9834 |
| Ajuste con todos los p | 0.9511 | 0.9370 |
| Medida por fases (solo cálculo y orden) | 0.9999 | 0.9999 |
| Medida por fases incluyendo carga de datos | 0.9993 | 0.9993 |

## ml-1m (6,040 usuarios)

T₁ secuencial compilada = 24.92 ± 0.22 s.

| Versión | p | Reps | T (s) | DE | S(p) | E(p) | Karp-Flatt | Combinar (s) | RAM (MB) | MHz |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mpi | 1 | 5 | 24.88 | 0.429 | 1.00 | 1.00 | nan | 0.000 | 261 | 3612 |
| mpi | 2 | 5 | 12.85 | 0.610 | 1.94 | 0.97 | 0.0310 | 0.016 | 508 | 3504 |
| mpi | 3 | 5 | 8.63 | 0.088 | 2.89 | 0.96 | 0.0197 | 0.032 | 756 | 3405 |
| mpi | 4 | 5 | 6.88 | 0.040 | 3.62 | 0.91 | 0.0348 | 0.035 | 1004 | 3361 |
| mpi | 6 | 5 | 6.34 | 0.049 | 3.93 | 0.65 | 0.1054 | 0.063 | 1496 | 3309 |
| mpi | 8 | 5 | 5.19 | 0.116 | 4.80 | 0.60 | 0.0951 | 0.075 | 1987 | 3249 |
| numba | 1 | 5 | 24.59 | 0.269 | 1.01 | 1.01 | nan | 0.000 | 203 | 3666 |
| numba | 2 | 5 | 12.76 | 0.359 | 1.95 | 0.98 | 0.0238 | 0.011 | 206 | 3549 |
| numba | 3 | 5 | 8.35 | 0.032 | 2.98 | 0.99 | 0.0029 | 0.014 | 209 | 3518 |
| numba | 4 | 5 | 6.49 | 0.075 | 3.84 | 0.96 | 0.0141 | 0.014 | 213 | 3394 |
| numba | 6 | 5 | 5.56 | 0.069 | 4.48 | 0.75 | 0.0676 | 0.015 | 220 | 3275 |
| numba | 8 | 5 | 4.70 | 0.031 | 5.30 | 0.66 | 0.0727 | 0.015 | 227 | 3217 |

| Fracción paralela f | numba | mpi |
|---|---:|---:|
| Ajuste con núcleos físicos (p ≤ 4) | 0.9880 | 0.9686 |
| Ajuste con todos los p | 0.9348 | 0.9100 |
| Medida por fases (solo cálculo y orden) | 0.9996 | 0.9996 |
| Medida por fases incluyendo carga de datos | 0.9989 | 0.9989 |

**Modelo de hardware** (G = 1.45, sin parámetros ajustados):

| p | S modelo | S numba | S mpi |
|---:|---:|---:|---:|
| 1 | 1.00 | 1.01 | 1.00 |
| 2 | 1.94 | 1.95 | 1.94 |
| 3 | 2.88 | 2.98 | 2.89 |
| 4 | 3.70 | 3.84 | 3.62 |
| 6 | 3.90 | 4.48 | 3.93 |
| 8 | 5.10 | 5.30 | 4.80 |

## Reparto por filas iguales

| Versión | p | T (s) | DE | S(p) | S teórico |
|---:|---:|---:|---:|---:|---:|
| mpi | 2 | 18.87 | 0.062 | 1.32 | 1.33 |
| mpi | 3 | 14.27 | 0.070 | 1.75 | 1.80 |
| mpi | 4 | 11.48 | 0.086 | 2.17 | 2.29 |
| mpi | 6 | 9.74 | 1.097 | 2.56 | 3.27 |
| mpi | 8 | 8.58 | 0.218 | 2.90 | 4.27 |
| numba | 2 | 18.62 | 0.165 | 1.34 | 1.33 |
| numba | 3 | 13.96 | 0.052 | 1.78 | 1.80 |
| numba | 4 | 10.94 | 0.084 | 2.28 | 2.29 |
| numba | 6 | 8.04 | 0.253 | 3.10 | 3.27 |
| numba | 8 | 7.01 | 0.398 | 3.55 | 4.27 |

## Otros experimentos

| Experimento | Versión | n | p | Afinidad | T (s) | DE |
|---:|---:|---:|---:|---:|---:|---:|
| debil | mpi | 2000 | 1 | fisicos | 2.52 | 0.039 |
| debil | mpi | 2828 | 2 | fisicos | 2.67 | 0.065 |
| debil | mpi | 3464 | 3 | fisicos | 2.88 | 0.012 |
| debil | mpi | 4000 | 4 | fisicos | 2.93 | 0.008 |
| debil | mpi | 4898 | 6 | fisicos | 3.98 | 0.022 |
| debil | mpi | 5656 | 8 | fisicos | 4.31 | 0.045 |
| debil | numba | 2000 | 1 | fisicos | 2.47 | 0.013 |
| debil | numba | 2828 | 2 | fisicos | 2.58 | 0.040 |
| debil | numba | 3464 | 3 | fisicos | 2.79 | 0.003 |
| debil | numba | 4000 | 4 | fisicos | 2.87 | 0.052 |
| debil | numba | 4898 | 6 | fisicos | 3.76 | 0.038 |
| debil | numba | 5656 | 8 | fisicos | 4.07 | 0.019 |
| debil | secuencial_compilado | 2000 | 1 | fisicos | 2.50 | 0.019 |
| mpi_dormir | mpi | 6040 | 4 | fisicos | 6.89 | 0.041 |
| mpi_dormir | mpi | 6040 | 6 | fisicos | 6.00 | 0.115 |
| mpi_dormir | mpi | 6040 | 8 | fisicos | 5.07 | 0.033 |
| mpi_ventana | mpi | 6040 | 4 | fisicos | 6.59 | 0.055 |
| mpi_ventana | mpi | 6040 | 6 | fisicos | 6.00 | 0.046 |
| mpi_ventana | mpi | 6040 | 8 | fisicos | 4.94 | 0.069 |
| smt | mpi | 6040 | 2 | hermanos | 17.78 | 0.156 |
| smt | numba | 6040 | 2 | hermanos | 17.32 | 0.300 |
| smt_mpi_defecto | mpi | 6040 | 2 | defecto | 17.69 | 0.111 |
| sobresuscripcion | mpi | 6040 | 16 | fisicos | 5.42 | 0.274 |
| sobresuscripcion | numba | 6040 | 16 | fisicos | 4.65 | 0.015 |

## Python puro contra compilado

Con 1000 usuarios: 74.79 s contra 0.608 s, **123 veces**. Esta ganancia viene de compilar, no de paralelizar; por eso no se usa para el speedup.

## Ancho de banda de memoria

| Hilos | GB/s |
|---:|---:|
| 1 | 12.8 |
| 2 | 13.2 |
| 3 | 12.5 |
| 4 | 12.6 |
| 6 | 12.8 |
| 8 | 12.4 |
