# Comparación entre equipos

**Correctitud entre máquinas:** misma huella en todas (56043b16668f313e).

| Equipo | CPU | Físicos/lógicos | RAM GB | Entorno | Versión | T₁ (s) | p físico máx. | S | E | S máx. | f | Memoria GB/s |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| axel | AMD Ryzen 5 4600H with Radeon Graphics | 6/12 | 7.4 | wsl | numba | 23.9 | 6 | 4.91 | 0.82 | 7.60 | 0.9549 | 18.8 |
| axel | AMD Ryzen 5 4600H with Radeon Graphics | 6/12 | 7.4 | wsl | mpi | 23.9 | 6 | 3.82 | 0.64 | 6.34 | 0.8798 | 18.8 |
| diego | AMD Ryzen 5 3550H with Radeon Vega Mobile Gfx | 4/8 | 22.9 | nativo | numba | 24.9 | 4 | 3.84 | 0.96 | 5.30 | 0.9880 | 13.2 |
| diego | AMD Ryzen 5 3550H with Radeon Vega Mobile Gfx | 4/8 | 22.9 | nativo | mpi | 24.9 | 4 | 3.62 | 0.91 | 4.80 | 0.9686 | 13.2 |
| irvingjaimez | AMD Ryzen 7 7435HS | 8/16 | 15.4 | nativo | numba | 18.9 | 8 | 6.74 | 0.84 | 8.92 | 0.9713 | 31.2 |
| irvingjaimez | AMD Ryzen 7 7435HS | 8/16 | 15.4 | nativo | mpi | 18.9 | 8 | 3.58 | 0.45 | 5.24 | 0.8091 | 31.2 |
