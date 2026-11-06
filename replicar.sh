#!/usr/bin/env bash
# Replica todo el proyecto en esta máquina y deja los resultados en resultados/<nombre>/.
#   ./replicar.sh <nombre>
# Dura unos minutos: deja la máquina conectada y sin otros programas pesados abiertos.
set -euo pipefail
cd "$(dirname "$0")"

NOMBRE="${1:-}"
if [[ -z "$NOMBRE" ]]; then
  echo "Uso: ./replicar.sh <tu-nombre>" >&2
  exit 2
fi

if [[ "${EN_DOCKER:-0}" == "1" ]]; then
  CORRE=()
else
  if ! command -v conda >/dev/null; then
    echo "Falta conda. Instala Miniforge o usa Docker; revisa el README." >&2
    exit 1
  fi
  if ! conda env list | grep -q '^knn-paralelo '; then
    echo ">> Creando el entorno (solo la primera vez)"
    conda env create -q -f environment.yml -y
  fi
  CORRE=(conda run -n knn-paralelo --no-capture-output)
fi

export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

echo ">> 1/6 Datos"
"${CORRE[@]}" python -m comun.datos ml-1m
echo ">> 2/6 Tests"
"${CORRE[@]}" python -m pytest tests -q
echo ">> 3/6 Verificación contra scikit-learn"
"${CORRE[@]}" python experimentos/verificar.py --equipo "$NOMBRE"
echo ">> 4/6 Experimentos"
"${CORRE[@]}" python experimentos/correr.py --equipo "$NOMBRE" --perfil rapido
echo ">> 5/6 Calidad de recomendaciones"
"${CORRE[@]}" python experimentos/calidad.py --equipo "$NOMBRE"
echo ">> 6/6 Análisis"
"${CORRE[@]}" python experimentos/analizar.py --equipo "$NOMBRE" > /dev/null

echo
echo "Listo. Revisa resultados/$NOMBRE/RESUMEN.md y resultados/$NOMBRE/figuras/."
