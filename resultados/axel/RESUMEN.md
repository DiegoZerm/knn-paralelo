# Resultados de axel

**Equipo:** AMD Ryzen 5 4600H with Radeon Graphics, 6 núcleos físicos, 12 CPUs lógicas, 7.4 GB, wsl.

**Correctitud:** todas las versiones coinciden en 2 configuraciones de datos (96 mediciones).

## ml-1m (6,040 usuarios)

T₁ secuencial compilada = 23.90 ± 0.11 s.

| Versión | p | Reps | T (s) | DE | S(p) | E(p) | Karp-Flatt | Combinar (s) | RAM (MB) | MHz |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mpi | 1 | 3 | 25.25 | 0.142 | 0.95 | 0.95 | nan | 0.000 | 214 | nan |
| mpi | 2 | 3 | 14.29 | 0.123 | 1.67 | 0.84 | 0.1959 | 0.019 | 430 | nan |
| mpi | 3 | 3 | 10.29 | 0.334 | 2.32 | 0.77 | 0.1460 | 0.033 | 647 | nan |
| mpi | 4 | 3 | 8.26 | 0.331 | 2.89 | 0.72 | 0.1275 | 0.035 | 864 | nan |
| mpi | 6 | 3 | 6.26 | 0.191 | 3.82 | 0.64 | 0.1141 | 0.055 | 1293 | nan |
| mpi | 8 | 3 | 5.15 | 0.165 | 4.64 | 0.58 | 0.1036 | 0.061 | 1721 | nan |
| mpi | 12 | 3 | 3.77 | 0.442 | 6.34 | 0.53 | 0.0812 | 0.083 | 2582 | nan |
| numba | 1 | 3 | 23.46 | 0.450 | 1.02 | 1.02 | nan | 0.000 | 201 | nan |
| numba | 2 | 3 | 12.75 | 0.171 | 1.87 | 0.94 | 0.0669 | 0.009 | 205 | nan |
| numba | 3 | 3 | 8.72 | 0.080 | 2.74 | 0.91 | 0.0475 | 0.013 | 208 | nan |
| numba | 4 | 3 | 6.83 | 0.062 | 3.50 | 0.87 | 0.0478 | 0.014 | 212 | nan |
| numba | 6 | 3 | 4.86 | 0.044 | 4.91 | 0.82 | 0.0442 | 0.015 | 219 | nan |
| numba | 8 | 3 | 4.34 | 0.710 | 5.51 | 0.69 | 0.0646 | 0.016 | 226 | nan |
| numba | 12 | 3 | 3.14 | 0.143 | 7.60 | 0.63 | 0.0526 | 0.014 | 239 | nan |

| Fracción paralela f | numba | mpi |
|---|---:|---:|
| Ajuste con núcleos físicos (p ≤ 6) | 0.9549 | 0.8798 |
| Ajuste con todos los p | 0.9458 | 0.9083 |
| Medida por fases (solo cálculo y orden) | 0.9996 | 0.9996 |
| Medida por fases incluyendo carga de datos | 0.9983 | 0.9983 |

## Reparto por filas iguales

| Versión | p | T (s) | DE | S(p) | S teórico |
|---:|---:|---:|---:|---:|---:|
| mpi | 2 | 20.65 | 0.280 | 1.16 | 1.33 |
| mpi | 3 | 16.10 | 0.142 | 1.48 | 1.80 |
| mpi | 4 | 12.27 | 0.260 | 1.95 | 2.29 |
| mpi | 6 | 9.97 | 0.184 | 2.40 | 3.27 |
| mpi | 8 | 7.86 | 0.725 | 3.04 | 4.27 |
| mpi | 12 | 5.91 | 0.539 | 4.04 | 6.26 |
| numba | 2 | 18.12 | 0.039 | 1.32 | 1.33 |
| numba | 3 | 13.95 | 0.054 | 1.71 | 1.80 |
| numba | 4 | 11.18 | 0.218 | 2.14 | 2.29 |
| numba | 6 | 8.00 | 0.038 | 2.99 | 3.27 |
| numba | 8 | 6.33 | 0.024 | 3.77 | 4.27 |
| numba | 12 | 4.54 | 0.072 | 5.26 | 6.26 |

## Otros experimentos

| Experimento | Versión | n | p | Afinidad | T (s) | DE |
|---:|---:|---:|---:|---:|---:|---:|
| smt | mpi | 6040 | 2 | hermanos | 14.31 | 0.609 |
| smt | numba | 6040 | 2 | hermanos | 12.88 | 0.200 |
| smt_mpi_defecto | mpi | 6040 | 2 | defecto | 15.17 | 0.983 |

## Python puro contra compilado

Con 500 usuarios: 17.41 s contra 0.158 s, **110 veces**. Esta ganancia viene de compilar, no de paralelizar; por eso no se usa para el speedup.

## Ancho de banda de memoria

| Hilos | GB/s |
|---:|---:|
| 1 | 15.3 |
| 2 | 18.4 |
| 3 | 18.8 |
| 4 | 18.7 |
| 6 | 18.2 |
| 8 | 17.6 |
| 12 | 16.7 |
