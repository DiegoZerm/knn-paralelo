# Guía para replicar en tu computadora

Vas a correr el proyecto completo en tu máquina y subir tus resultados. Se comparan
después entre todos. Toma de 25 a 40 minutos, casi todos sin que hagas nada.

## Antes de empezar

- Acepta la invitación al repo: https://github.com/DiegoZerm/knn-paralelo/invitations
- Conecta la laptop a la corriente.
- Cierra navegador, juegos y cualquier programa pesado. Si los dejas abiertos, tus tiempos
  salen ruidosos.
- No uses la computadora mientras corre.
- Necesitas unos 3 GB libres en disco.
- Usa como `<tu-nombre>` una sola palabra en minúsculas y sin acentos: `irving`, `cesar`, `axel`.

## Paso 1. Terminal de Linux

**Windows:** abre PowerShell como administrador y ejecuta:

```powershell
wsl --install -d Ubuntu
```

Reinicia, abre "Ubuntu" desde el menú de inicio y crea tu usuario. Todo lo que sigue va
dentro de esa terminal de Ubuntu, no en PowerShell.

**Linux:** usa tu terminal normal.

**macOS:** el script no corre de forma nativa; usa la opción con Docker al final.

## Paso 2. Herramientas, una sola vez

```bash
sudo apt update && sudo apt install -y git gh curl
curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh -b
source ~/miniforge3/bin/activate
```

Si cierras la terminal, al volver ejecuta otra vez `source ~/miniforge3/bin/activate`.

## Paso 3. Tu cuenta de GitHub y tu nombre, una sola vez

```bash
gh auth login
gh auth setup-git
git config --global user.name "Tu Nombre"
git config --global user.email "tu-correo@ejemplo.com"
```

En `gh auth login` elige: GitHub.com, HTTPS, Yes y "Login with a web browser". Copia el
código que te muestra y pégalo en el navegador.

## Paso 4. Clonar y correr

Clona en tu carpeta de Ubuntu (`~`), no en `/mnt/c`, porque ahí es mucho más lento.

```bash
cd ~
git clone https://github.com/DiegoZerm/knn-paralelo.git
cd knn-paralelo
git checkout -b resultados/<tu-nombre>
./replicar.sh <tu-nombre>
```

El script avanza de 1/6 a 6/6 y al final dice `Listo`. La primera vez tarda más porque
crea el entorno. Si en algún paso aparece `ERROR`, no sigas ni cambies nada: manda el
mensaje completo al grupo.

Puedes interrumpirlo y volver a correrlo: salta lo que ya midió.

## Paso 5. Subir tus resultados

```bash
git add resultados/<tu-nombre>
git commit -m "Resultados de <tu-nombre>"
git push -u origin resultados/<tu-nombre>
```

Si el `push` falla, manda tus resultados por el grupo:

```bash
tar czf resultados-<tu-nombre>.tar.gz resultados/<tu-nombre>
explorer.exe .
```

El segundo comando abre la carpeta en Windows. En Linux, el archivo queda en
`~/knn-paralelo`.

No edites `corridas.csv` ni ningún resultado. Si una corrida sale mal, borra tu carpeta y
vuelve a correr todo. El valor de la comparación depende de que sean mediciones reales.

## Opción con Docker

Solo si no puedes usar los pasos anteriores, por ejemplo en macOS. Necesitas Docker
Desktop abierto.

```bash
git clone https://github.com/DiegoZerm/knn-paralelo.git
cd knn-paralelo
git checkout -b resultados/<tu-nombre>
docker build -t knn-paralelo .
docker run --rm -v "$PWD/resultados:/app/resultados" knn-paralelo <tu-nombre>
```

Si la carpeta de resultados queda a nombre de root:
`sudo chown -R $USER resultados/<tu-nombre>`. Después sigue el paso 5.

## Antes de la presentación

El profesor puede preguntarle a cualquiera sobre cualquier parte del código, y quien no
pueda explicar su parte pierde esos puntos. Lee el README y la guía de preguntas en
`docs/PREGUNTAS.md`, que se agrega al repo antes del ensayo del lunes.
