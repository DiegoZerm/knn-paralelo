# Resultados de irvingjaimez

**Equipo:** x86_64, 8 núcleos físicos, 16 CPUs lógicas, 15.4 GB, nativo.

**Correctitud:** todas las versiones coinciden en 2 configuraciones de datos (108 mediciones).

## ml-1m (6,040 usuarios)

T₁ secuencial compilada = 18.90 ± 0.19 s.

| Versión | p | Reps | T (s) | DE | S(p) | E(p) | Karp-Flatt | Combinar (s) | RAM (MB) | MHz |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mpi | 1 | 3 | 21.40 | 0.073 | 0.88 | 0.88 | nan | 0.000 | 254 | 3620 |
| mpi | 2 | 3 | 11.91 | 0.882 | 1.59 | 0.79 | 0.2609 | 0.012 | 495 | 3391 |
| mpi | 3 | 3 | 9.68 | 0.174 | 1.95 | 0.65 | 0.2682 | 0.026 | 734 | 3005 |
| mpi | 4 | 3 | 7.83 | 0.529 | 2.41 | 0.60 | 0.2191 | 0.028 | 975 | 2698 |
| mpi | 6 | 3 | 6.20 | 0.146 | 3.05 | 0.51 | 0.1937 | 0.040 | 1451 | 2457 |
| mpi | 8 | 3 | 5.28 | 0.290 | 3.58 | 0.45 | 0.1762 | 0.046 | 1926 | 2420 |
| mpi | 12 | 3 | 4.88 | 0.029 | 3.88 | 0.32 | 0.1906 | 0.073 | 2879 | 2353 |
| mpi | 16 | 3 | 3.61 | 0.304 | 5.24 | 0.33 | 0.1369 | 0.080 | 3829 | 2274 |
| numba | 1 | 3 | 18.64 | 0.278 | 1.01 | 1.01 | nan | 0.000 | 202 | 4214 |
| numba | 2 | 3 | 9.69 | 0.223 | 1.95 | 0.98 | 0.0254 | 0.008 | 205 | 4001 |
| numba | 3 | 3 | 6.61 | 0.066 | 2.86 | 0.95 | 0.0247 | 0.012 | 209 | 3885 |
| numba | 4 | 3 | 5.13 | 0.158 | 3.68 | 0.92 | 0.0287 | 0.014 | 212 | 3700 |
| numba | 6 | 3 | 3.70 | 0.051 | 5.11 | 0.85 | 0.0347 | 0.011 | 219 | 3567 |
| numba | 8 | 3 | 2.80 | 0.061 | 6.74 | 0.84 | 0.0268 | 0.008 | 226 | 3320 |
| numba | 12 | 3 | 2.38 | 0.039 | 7.94 | 0.66 | 0.0464 | 0.014 | 240 | 2980 |
| numba | 16 | 3 | 2.12 | 0.040 | 8.92 | 0.56 | 0.0529 | 0.011 | 254 | 3086 |

| Fracción paralela f | numba | mpi |
|---|---:|---:|
| Ajuste con núcleos físicos (p ≤ 8) | 0.9713 | 0.8091 |
| Ajuste con todos los p | 0.9525 | 0.8348 |
| Medida por fases (solo cálculo y orden) | 0.9996 | 0.9996 |
| Medida por fases incluyendo carga de datos | 0.9983 | 0.9983 |

**Modelo de hardware** (G = 1.43, sin parámetros ajustados):

| p | S modelo | S numba | S mpi |
|---:|---:|---:|---:|
| 1 | 1.00 | 1.01 | 0.88 |
| 2 | 1.90 | 1.95 | 1.59 |
| 3 | 2.77 | 2.86 | 1.95 |
| 4 | 3.51 | 3.68 | 2.41 |
| 6 | 5.08 | 5.11 | 3.05 |
| 8 | 6.30 | 6.74 | 3.58 |
| 12 | 6.06 | 7.94 | 3.88 |
| 16 | 8.36 | 8.92 | 5.24 |

## Reparto por filas iguales

| Versión | p | T (s) | DE | S(p) | S teórico |
|---:|---:|---:|---:|---:|---:|
| mpi | 2 | 17.34 | 0.254 | 1.09 | 1.33 |
| mpi | 3 | 14.49 | 0.693 | 1.30 | 1.80 |
| mpi | 4 | 11.52 | 0.144 | 1.64 | 2.29 |
| mpi | 6 | 8.83 | 0.321 | 2.14 | 3.27 |
| mpi | 8 | 7.37 | 0.216 | 2.56 | 4.27 |
| mpi | 12 | 7.03 | 0.125 | 2.69 | 6.26 |
| mpi | 16 | 5.77 | 0.400 | 3.28 | 8.26 |
| numba | 2 | 14.33 | 0.435 | 1.32 | 1.33 |
| numba | 3 | 10.86 | 0.207 | 1.74 | 1.80 |
| numba | 4 | 8.63 | 0.033 | 2.19 | 2.29 |
| numba | 6 | 6.05 | 0.071 | 3.13 | 3.27 |
| numba | 8 | 4.70 | 0.088 | 4.02 | 4.27 |
| numba | 12 | 3.45 | 0.149 | 5.48 | 6.26 |
| numba | 16 | 2.92 | 0.068 | 6.48 | 8.26 |

## Otros experimentos

| Experimento | Versión | n | p | Afinidad | T (s) | DE |
|---:|---:|---:|---:|---:|---:|---:|
| smt | mpi | 6040 | 2 | hermanos | 17.83 | 0.110 |
| smt | numba | 6040 | 2 | hermanos | 13.69 | 0.043 |
| smt_mpi_defecto | mpi | 6040 | 2 | defecto | 17.70 | 0.020 |

## Python puro contra compilado

Con 500 usuarios: 11.36 s contra 0.133 s, **85 veces**. Esta ganancia viene de compilar, no de paralelizar; por eso no se usa para el speedup.

## Ancho de banda de memoria

| Hilos | GB/s |
|---:|---:|
| 1 | 23.0 |
| 2 | 29.7 |
| 3 | 31.2 |
| 4 | 30.8 |
| 6 | 29.4 |
| 8 | 29.4 |
| 12 | 29.2 |
| 16 | 28.9 |
