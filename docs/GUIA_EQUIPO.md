# Guía para replicar en tu computadora

Vas a correr el proyecto completo en tu máquina y subir tus resultados. Se comparan
después entre todos. Toma unos 30 minutos, casi todos sin que hagas nada.

## Antes de empezar

- Conecta la laptop a la corriente.
- Cierra navegador, juegos y cualquier programa pesado. Si los dejas abiertos, tus tiempos
  salen ruidosos.
- No uses la computadora mientras corre.
- Necesitas 3 GB libres en disco.

## Opción A: Linux o WSL con conda

En Windows, primero abre PowerShell como administrador y ejecuta `wsl --install`. Reinicia
y sigue estos pasos dentro de la terminal de Ubuntu.

Si no tienes conda, instala Miniforge:

```bash
curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh -b
source ~/miniforge3/bin/activate
```

Después:

```bash
git clone https://github.com/DiegoZerm/knn-paralelo.git
cd knn-paralelo
git checkout -b resultados/<tu-nombre>
./replicar.sh <tu-nombre>
```

## Opción B: Docker

```bash
git clone https://github.com/DiegoZerm/knn-paralelo.git
cd knn-paralelo
git checkout -b resultados/<tu-nombre>
docker build -t knn-paralelo .
docker run --rm -v "$PWD/resultados:/app/resultados" knn-paralelo <tu-nombre>
```

Si la carpeta de resultados queda a nombre de root:
`sudo chown -R $USER resultados/<tu-nombre>`.

## Qué debe pasar

El script avanza de 1/6 a 6/6 y al final dice `Listo`. Si en algún paso aparece `ERROR`,
no sigas ni cambies nada: manda el mensaje completo al grupo.

Puedes interrumpirlo y volver a correrlo: salta lo que ya midió.

## Subir tus resultados

```bash
git add resultados/<tu-nombre>
git commit -m "Resultados de <tu-nombre>"
git push -u origin resultados/<tu-nombre>
```

No edites `corridas.csv` ni ningún resultado. Si una corrida sale mal, borra tu carpeta y
vuelve a correr todo. El valor de la comparación depende de que sean mediciones reales.

## Antes de la presentación

Lee `docs/PREGUNTAS.md`. El profesor puede preguntarle a cualquiera sobre cualquier parte
del código, y quien no pueda explicar su parte pierde esos puntos.
