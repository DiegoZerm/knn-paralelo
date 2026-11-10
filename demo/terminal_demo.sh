# Archivo de arranque (rcfile) de la terminal de la demo. Lo usa abrir_demo.sh:
#   bash --rcfile demo/terminal_demo.sh -i
# Carga la configuración normal de bash, activa el entorno y deja los comandos de la
# demo en el historial, para llamarlos con la flecha arriba.

[ -f ~/.bashrc ] && source ~/.bashrc

for base in "$HOME/miniforge3" "$HOME/mambaforge" "$HOME/miniconda3"; do
  if [ -f "$base/etc/profile.d/conda.sh" ]; then
    source "$base/etc/profile.d/conda.sh"
    break
  fi
done
conda activate knn-paralelo
# En Omarchy, mise pone su propio python antes que el de conda: se fuerza el del entorno.
[ -n "${CONDA_PREFIX:-}" ] && PATH="$CONDA_PREFIX/bin:$PATH" && hash -r

cd "${KNN_DIR:-$HOME/Work/knn-paralelo}"
history -s "python demo/demo.py --respaldo"
history -s "python demo/demo.py --usuario 42"

clear
echo "Demo KNN paralelo · entorno: ${CONDA_DEFAULT_ENV:-sin activar} · $(python --version)"
echo
echo "  Demo en vivo:  python demo/demo.py --usuario 42     (flecha arriba)"
echo "  Plan B:        python demo/demo.py --respaldo       (flecha arriba dos veces)"
echo "  Plan C:        video de respaldo en el workspace 9"
echo
