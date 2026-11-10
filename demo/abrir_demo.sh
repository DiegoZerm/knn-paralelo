#!/usr/bin/env bash
# Abre todo lo de la demo en un solo monitor, sin tocar los demás:
#   workspace 7  presentación (Brave)
#   workspace 8  terminal en el repo con el entorno knn-paralelo activo
#   workspace 9  video de respaldo (mpv, en pausa) y el repo en GitHub
#
# Uso: ./demo/abrir_demo.sh [MONITOR]
#   ./demo/abrir_demo.sh HDMI-A-1   en ese monitor (hyprctl monitors muestra los nombres)
#   ./demo/abrir_demo.sh            en el monitor que tenga el foco al ejecutarlo
# Requiere Hyprland 0.56 o más nuevo (dispatch en Lua), foot, mpv y Brave.
# Otro video de respaldo: KNN_VIDEO=/ruta/al/video.mp4 ./demo/abrir_demo.sh
set -u

DEMO=$(cd "$(dirname "$0")" && pwd)
export KNN_DIR=$(dirname "$DEMO")
PRESENTACION="https://claude.ai/artifact/S5mp9CiQBn2nrVNBbGvuK3"
REPO="https://github.com/DiegoZerm/knn-paralelo"
VIDEO=${KNN_VIDEO:-$HOME/Videos/knn-demo-respaldo.mp4}

MONITORES=$(hyprctl monitors -j | python3 -c "import json,sys;print(*[m['name'] for m in json.load(sys.stdin)])")
ENFOCADO=$(hyprctl monitors -j | python3 -c "import json,sys;print(next(m['name'] for m in json.load(sys.stdin) if m['focused']))")
MONITOR=${1:-$ENFOCADO}
if [[ " $MONITORES " != *" $MONITOR "* ]]; then
  echo "No existe el monitor $MONITOR. Monitores: $MONITORES" >&2
  exit 2
fi
fallos=0

ventanas() {  # clase
  hyprctl clients -j | python3 -c "import json,sys;print(*[c['address'] for c in json.load(sys.stdin) if c['class']==sys.argv[1]])" "$1"
}

# Abre un programa aparte de este script y mueve al workspace la ventana nueva que aparezca.
abrir() {  # workspace, clase, comando...
  local ws=$1 clase=$2 antes nueva intento
  shift 2
  antes=" $(ventanas "$clase") "
  setsid -f "$@" </dev/null >/dev/null 2>&1
  for intento in $(seq 1 80); do
    sleep 0.25
    for nueva in $(ventanas "$clase"); do
      if [[ "$antes" != *" $nueva "* ]]; then
        if [[ "$(hyprctl dispatch "hl.dsp.window.move({ workspace = \"$ws\", follow = false, window = \"address:$nueva\" })")" == ok ]]; then
          return 0
        fi
        echo "No se pudo mover a $ws: $*" >&2
        fallos=$((fallos + 1))
        return 1
      fi
    done
  done
  echo "No apareció la ventana: $*" >&2
  fallos=$((fallos + 1))
  return 1
}

abrir 7 brave-browser brave --new-window "$PRESENTACION"
abrir 8 foot foot --title="Demo KNN" --working-directory="$KNN_DIR" bash --rcfile "$DEMO/terminal_demo.sh" -i
if [ -f "$VIDEO" ]; then
  abrir 9 mpv mpv --pause --keep-open=yes --title="Respaldo demo KNN" "$VIDEO"
else
  echo "No está el video de respaldo: $VIDEO" >&2
  fallos=$((fallos + 1))
fi
abrir 9 brave-browser brave --new-window "$REPO"

# Hyprland crea los workspaces nuevos en cualquier monitor: se pasan todos al del foco.
for ws in 7 8 9; do
  [[ "$(hyprctl dispatch "hl.dsp.workspace.move({ workspace = \"$ws\", monitor = \"$MONITOR\" })")" == ok ]] ||
    { echo "No se pudo pasar el workspace $ws a $MONITOR" >&2; fallos=$((fallos + 1)); }
done

echo "Demo abierta en $MONITOR: 7 presentación · 8 terminal · 9 respaldo y repo."
exit $((fallos > 0))
