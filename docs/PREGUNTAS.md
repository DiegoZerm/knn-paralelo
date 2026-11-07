# Preparación para la presentación y las preguntas

El profesor puede preguntarle **a cualquiera sobre cualquier parte del código**, y quien no
pueda explicar su parte pierde esos puntos. Este documento tiene:

1. El reparto de la presentación.
2. Lo mínimo que los cuatro deben dominar.
3. Preguntas con respuesta, por tema.
4. Lo que **no** debemos afirmar.
5. El guion de la demo.

Para practicar, que otra persona te lea la pregunta y tú contestes **sin leer**, en menos de
un minuto. Si no puedes, abre el archivo que se indica y vuelve a intentarlo.

---

## 1. Reparto: 10 minutos y 5 de preguntas

| Quién | Tema | Min | Archivos que debe conocer a fondo |
|---|---|---:|---|
| Irving | Problema, datos y diseño del kernel | 2.5 | `comun/datos.py`, `comun/nucleo.py`, `secuencial/` |
| César | numba y MPI; cómo se combinan los top-k | 2.5 | `paralelo_numba/`, `paralelo_mpi/` |
| Axel | Metodología, experimentos y comparación entre máquinas | 2.5 | `experimentos/correr.py`, `analizar.py`, `comparar.py` |
| Diego | Interpretación, conclusiones y demo en vivo | 2.5 | `docs/ANALISIS.md`, `demo/demo.py` |

---

## 2. Lo mínimo que los cuatro deben saber de memoria

- **Problema:** para cada usuario, encontrar los 50 usuarios con gustos más parecidos
  (similitud coseno) y recomendarle lo que les gustó a ellos. Comparar todos contra todos
  es cuadrático: ML-1M tiene 6,040 usuarios y 18.2 millones de pares.
- **Tres versiones con el mismo kernel:** secuencial, numba (memoria compartida, hilos) y
  mpi4py (memoria distribuida, procesos). Las tres dan **exactamente** el mismo resultado,
  comprobado con una huella SHA-256 y contra scikit-learn.
- **Paralelización:** se reparten bloques de filas del triángulo superior. Cada trabajador
  guarda su propio top-k parcial y al final se combinan.
- **Números clave en ML-1M:** T₁ = 24.9 s; S(4) = 3.84; S(8) = 5.30 con numba.
- **Por qué no escala a 8:** la CPU tiene 4 núcleos físicos y 8 hilos con SMT. Dos hilos en
  un núcleo rinden 1.45 veces uno, no el doble. Además, la frecuencia baja al usar más
  núcleos.
- **La fracción serial medida es mínima:** f = 0.9996, así que Amdahl no es lo que limita.
- **Reto extra:** ML-25M necesitaría una matriz de 105.7 GB. Con top-k por bloques corrió en
  41 minutos usando 1.19 GB.
- **Uso de IA:** se usó Claude Code para desarrollar código, experimentos y documentación.
  Está declarado en el README. Cada integrante replicó el sistema en su computadora.

---

## 3. Preguntas y respuestas

### A. Problema y datos (Irving)

**¿Qué problema resuelven?**
Recomendación por filtrado colaborativo basado en usuarios. Para cada usuario buscamos sus
k = 50 vecinos más parecidos y le recomendamos películas que ellos calificaron y él no ha
visto.

**¿Por qué es un problema de alto rendimiento?**
Comparar todos los usuarios es O(n²). ML-1M tiene 18.2 millones de pares; ML-25M, 13,209
millones. Con 13 mil millones de pares, una sola corrida con 8 hilos tarda 41 minutos.

**¿Qué datos usaron?**
MovieLens 1M (6,040 usuarios, 3,706 películas, 1 millón de calificaciones), Goodbooks-10k
(muestra de 20,000 de 53,424 usuarios) y MovieLens 25M completo (162,541 usuarios). Se
descargan con `comun/datos.py`, que valida su SHA-256. No están en el repo porque MovieLens
no permite redistribuirlos.

**¿Cómo representan los datos?**
Como matriz dispersa CSR: `indptr` indica dónde empieza la fila de cada usuario, `indices`
las películas que calificó (ordenadas) y `data` las calificaciones. Cada fila está
**normalizada** (norma L2 = 1), así que el producto punto entre dos filas ya es la similitud
coseno.

**¿Por qué coseno?**
Mide si dos usuarios califican en la misma dirección, sin importar cuántas películas vio
cada uno. Es lo que pide el enunciado, junto con la euclidiana, y lo que usa scikit-learn
para verificar.

**¿Cómo calculan el coseno entre dos usuarios?**
Con la función `coseno` en `comun/nucleo.py`. Recorre las dos listas de películas
ordenadas, como en un *merge*: cuando coinciden, multiplica y suma; si no, avanza la menor.
Cuesta O(películas de u + películas de v), sin crear vectores densos.

**¿Qué pasa con las películas que un usuario no calificó?**
Cuentan como 0, igual que en scikit-learn con matrices dispersas. No restamos la media del
usuario; eso sería otra métrica (Pearson).

### B. Diseño del kernel (Irving; todos deben entender la idea)

**¿Qué hace `procesar_bloque`?**
Para cada usuario u del bloque, compara con cada v > u. Si la similitud es positiva, ofrece
v como vecino de u **y** u como vecino de v. Así cada par se calcula una sola vez.

**¿Por qué solo el triángulo superior?**
La similitud es simétrica, así que calcular (u, v) y (v, u) sería trabajo doble.

**¿Qué es el top-k y cómo lo guardan?**
Los 50 mejores vecinos de cada usuario, guardados en un **min-heap** de tamaño 50 por
usuario (`_insertar`). La raíz es el peor vecino retenido. Un candidato nuevo se compara
con la raíz; si es mejor, la reemplaza y baja hasta su lugar. Cuesta O(log k).

**¿Por qué no guardan la matriz completa?**
En ML-25M pesaría 105.7 GB. El top-k pesa n × 50 × 12 bytes: 97 MB por trabajador.

**¿Cómo resuelven empates?**
Con un orden total (`_es_peor`): gana la mayor similitud y, si empatan, el id menor. Gracias
a eso, el resultado no depende del orden en que lleguen los pares ni de cómo se repartió el
trabajo, y las tres versiones dan exactamente lo mismo.

**¿Cómo se asegura que un usuario no sea su propio vecino?**
Por construcción, v empieza en u + 1, así que u nunca se compara consigo mismo.

**¿Qué es la versión secuencial "con ciclos"?**
Es el mismo código del kernel, con ciclos explícitos. Con `--modo puro` se activa
`NUMBA_DISABLE_JIT=1` y corre como Python normal. Con `--modo compilado`, numba lo compila
sin hilos. Así la versión secuencial y las paralelas no pueden divergir.

### C. Memoria compartida con numba (César)

**¿Cómo paralelizan con numba?**
`calcular_bloques` en `paralelo_numba/knn_numba.py` usa `prange` sobre p bloques: cada hilo
procesa un bloque con `procesar_bloque`. Numba compila la función y crea los hilos sin el
GIL de Python. Usamos la capa de hilos de OpenMP.

**¿Hay condiciones de carrera?**
No. Cada hilo escribe solo en su propio buffer `ids[b]`, `sims[b]`, así que no hay datos
compartidos que se escriban ni hacen falta locks.

**¿Por qué cada hilo necesita un top-k de todos los usuarios?**
Porque el par (u, v) actualiza también a v, que puede caer en el bloque de otro hilo. Por eso
cada hilo produce un top-k parcial de todos los usuarios.

**¿Cómo se combinan los resultados de los hilos?**
`combinar` usa `prange` sobre los usuarios. Para cada fila u, vierte los heaps de los
buffers 1 a p − 1 en el buffer 0. Cada fila la toca un solo hilo, así que tampoco hay
carreras. Cada par vive en un solo bloque, así que no llegan duplicados.

**¿Cómo eligen los bloques?**
`repartir` en `comun/nucleo.py`. La fila u cuesta aproximadamente
`nnz(u)·(n − u − 1) + Σ nnz(v>u)`; las fronteras se eligen para que cada bloque tenga el
mismo costo acumulado. Con filas iguales, el primer bloque haría mucho más trabajo.

**¿Por qué numba y no OpenMP en C?**
El enunciado acepta cualquiera de los dos. Numba nos deja usar el **mismo** código para las
tres versiones, incluida la de Python puro. Por dentro, numba usa una capa de hilos de
OpenMP.

### D. Memoria distribuida con MPI (César)

**¿Cómo funciona la versión MPI?**
1. El rank 0 lee los datos y los envía a todos con `Bcast` (`repartir_datos`).
2. Cada proceso calcula su bloque con el **mismo** `procesar_bloque` y llena su top-k parcial.
3. Los parciales se combinan en un árbol binomial (`combinar_en_arbol`).
4. El rank 0 ordena e imprime el resultado.

**¿Por qué `Bcast` y no `Scatter`?**
Cada proceso compara sus filas contra **todos** los usuarios con v > u, así que necesita la
matriz completa. Solo se reparte el trabajo, no los datos.

**¿Cómo funciona el árbol binomial?**
En cada ronda, la mitad de los procesos que siguen activos envía su top-k a un compañero, que
lo combina con el suyo. Con 8 procesos son 3 rondas (log₂ 8) en lugar de 7 envíos a la raíz.

**¿Cuánto se comunica?**
Cada envío es un top-k de n × 50: 3.6 MB en ML-1M. Combinar tarda unos 75 ms con p = 8, de
unos 5 s en total.

**¿Por qué `Send` con mayúscula?**
En mpi4py, los métodos con mayúscula envían arreglos NumPy directamente como buffers. Los de
minúscula serializan con *pickle*, que es más lento y habría inflado el costo de comunicación.

**¿Qué pasa si un proceso falla?**
`abortar_en_error` llama a `MPI.COMM_WORLD.Abort(1)`, que termina a todos. Sin eso, los
demás procesos esperarían en `Bcast` para siempre. Nos pasó durante el desarrollo.

**¿Para qué son `--datos ventana` y `--espera dormir`?**
Son variantes para investigar por qué MPI es más lento que numba:
- `ventana` guarda una sola copia de los datos en memoria compartida de MPI-3, en lugar de
  una copia por proceso.
- `dormir` hace que un proceso que ya terminó espere sin ocupar CPU.

El control aleatorizado mostró que duplicar los datos cuesta 0.7–1.8 % y que la espera
activa cuesta 4.7 % con p = 6.

**¿Esto correría en varias computadoras?**
La versión con `Bcast` sí, porque no supone memoria compartida. La variante `ventana` exige
un solo nodo y lo verifica. No la probamos en un clúster.

### E. Metodología y experimentos (Axel)

**¿Qué es T₁ y por qué no es la versión de Python puro?**
T₁ es la secuencial compilada con 1 hilo: 24.92 s en ML-1M. Python puro es 123 veces más
lento. Si lo usáramos, el "speedup" incluiría la ganancia de compilar, no solo la de
paralelizar. Reportamos ambos por separado.

**¿Cuántas repeticiones y cómo reportan?**
5 repeticiones en los experimentos principales y 3 en los secundarios. Reportamos media ±
desviación estándar y no eliminamos atípicos.

**¿Qué valores de p probaron?**
1, 2, 3, 4, 6 y 8, más 16 para sobresuscripción.

**¿Por qué fijan la afinidad?**
Porque OpenMPI, con `--use-hwthread-cpus`, puso dos procesos en el mismo núcleo físico, y
tardaron 17.7 s en lugar de 12.9 s. `correr.py` usa `taskset`: primero un hilo por núcleo
físico y después los hermanos SMT.

**¿Qué otras precauciones tomaron?**
- `OMP_NUM_THREADS=1`, para que NumPy no use hilos ocultos.
- Compilar antes de medir, para que el JIT no cuente.
- Orden aleatorio de las corridas.
- Esperar a que la CPU baje de 70 °C.
- Registrar frecuencia y temperatura de cada corrida.

**¿Cómo verifican que todas las versiones den lo mismo?**
Cada corrida calcula una huella SHA-256 de los vecinos y similitudes. `correr.py` se
detiene si aparece una distinta. Además, `verificar.py` compara contra scikit-learn y hay
24 tests automáticos.

**¿Cómo calculan speedup, eficiencia y Amdahl?**
S(p) = T₁/Tₚ y E(p) = S(p)/p. La fracción f se calcula de dos formas: ajustando la fórmula
de Amdahl a la curva, y midiendo directamente el tiempo de la parte serial. Todo lo calcula
`analizar.py` desde el CSV crudo; ningún número se edita a mano.

**¿Qué es la escalabilidad débil y qué resultó?**
Aumentar el problema con p para que cada trabajador tenga la misma cantidad de pares (n
crece con √p). Lo ideal es que el tiempo no cambie. La eficiencia fue de 86 % con 4 y de
61 % con 8, por la misma causa: SMT.

**¿Para qué replicaron en varias máquinas?**
Para separar lo que depende del algoritmo de lo que depende del hardware. Cada máquina usa su
propio T₁. Los tiempos absolutos dicen qué máquina es más rápida; el speedup dice cuál
paraleliza mejor. Ver `resultados/comparacion/`.

### F. Interpretación (Diego; todos deben entender la idea)

**¿Por qué S(8) = 5.30 y no 8?**
Hay tres causas medidas:
1. Solo hay 4 núcleos físicos; los 8 hilos comparten núcleo con SMT, y un núcleo con dos
   hilos rinde 1.45 veces, no 2.
2. La frecuencia baja de 3666 a 3217 MHz al usar más núcleos.
3. Con reparto estático, los hilos que comparten núcleo van más lento y todos esperan al
   último.

**¿Qué dice la ley de Amdahl de su programa?**
La fracción paralela medida es 0.9996, que permitiría S(8) ≈ 7.98. Como medimos 5.30, la
parte serial **no** explica la pérdida. El f ajustado (0.935) solo resume el efecto del
hardware; si fuera una propiedad del código, no cambiaría al incluir más valores de p.

**¿Qué es Karp-Flatt y qué muestra?**
Es la fracción serial experimental: e = (1/S − 1/p)/(1 − 1/p). Si fuera código serial,
sería constante. En numba sube de 0.014 en p = 4 a 0.07 en p = 8, lo que indica sobrecarga
que crece con p, no código serial.

**¿Por qué con 4 núcleos no da exactamente 4?**
Da 3.84. La frecuencia bajó 7.4 %, de 3666 a 3394 MHz, y eso solo ya explicaría llegar a
3.70.

**¿Qué es el modelo de hardware?**
Predice S(p) usando solo la frecuencia medida y la ganancia SMT medida, sin ajustar nada a
la curva. Coincide con ±6.2 %, excepto numba con p = 6.

**¿Por qué numba es más rápido que MPI?**
- En una sola máquina, los hilos comparten los datos sin copiarlos y no hay que enviar
  mensajes.
- La diferencia más grande, 7.6 % con p = 6, viene sobre todo de que MPI espera girando en
  la barrera y le quita CPU al hilo hermano.
- Duplicar datos cuesta poco, y combinar resultados apenas 75 ms.

**¿Qué demuestra el experimento de filas iguales?**
El triángulo da más trabajo a las primeras filas. La teoría predice S = 1/[1 − (1 − 1/p)²]:
1.33, 1.80 y 2.29 para p = 2, 3 y 4. Medimos 1.34, 1.78 y 2.28. Repartir por trabajo
estimado lo corrige: 69 % más rápido con p = 4.

**¿Cómo resolvieron el reto de memoria?**
No construimos la matriz. Cada trabajador guarda un top-k parcial y al final se combinan.
La memoria pasa de O(n²) a O(n·k·p). ML-25M pasó de 105.7 GB necesarios a 1.19 GB, y numba
y MPI dieron la misma huella.

**¿Las recomendaciones son buenas?**
Ocultando una película bien calificada por usuario, KNN la pone entre sus 10 primeras
recomendaciones el 26.6 % de las veces. Recomendar lo más popular lo logra 10.2 %: KNN
acierta 2.6 veces más.

### G. Preguntas difíciles

**¿Por qué no usaron GPU si tienen una?**
El enunciado pide dos modelos distintos y elegimos memoria compartida y distribuida, que son
los que pide P7. La GPU sería trabajo futuro: el cálculo de pares también es paralelizable
ahí, pero la memoria de 4 GB obligaría a trabajar por bloques.

**¿Por qué no usaron la matriz densa y un producto de matrices con NumPy?**
Sería más rápido en ML-1M, pero imposible en ML-25M: 162,541 × 59,047 en densa, más la
matriz de resultados de 105.7 GB. Además, el enunciado pide ciclos y paralelizar el cálculo
por bloques.

**¿Por qué la eficiencia con p = 1 sale mayor que 1?**
Es ruido de medición: 24.59 contra 24.92 s está dentro de la variación entre repeticiones.

**¿El resultado depende de cuántos hilos usen?**
No. La huella es idéntica con cualquier p, en numba y en MPI, gracias al orden total con
desempate por id.

**¿Por qué scikit-learn da vecinos distintos en algunos casos?**
En 80 de 302,000 vecinos, siempre por empates de similitud. scikit-learn no fija un orden
entre empatados; nosotros desempatamos por id. Las similitudes coinciden hasta 1.7×10⁻¹⁴.

**¿Qué parte hizo la IA?**
Usamos Claude Code para desarrollar el código, los experimentos y la documentación, y lo
declaramos en el README. Cada integrante replicó el sistema en su computadora y estudió su
parte para poder explicarla. Respondan con honestidad; si no saben algo, digan qué parte sí
conocen.

**¿Cuánto durarían los cálculos sin paralelizar en Python puro?**
Con 1,000 usuarios, Python puro tarda 74.8 s. ML-1M completo tiene unas 36 veces más pares,
así que tomaría alrededor de 45 minutos. Es una **estimación**, no una medición.

---

## 4. Lo que NO debemos afirmar

| No digan | Digan |
|---|---|
| "El modelo explica todo" | "Coincide con ±6.2 %, excepto numba con p = 6, donde subestima 13 %" |
| "Duplicar datos no afecta a MPI" | "Cuesta poco: de 0.7 a 1.8 %" |
| "La memoria limita el rendimiento" | "El ancho de banda medido no parece limitar, pero esa medición varió y no lo usamos como argumento" |
| "En Goodbooks escala mejor porque…" | "Escala mejor; no medimos la causa" |
| Speedup de ML-25M | "En ML-25M demostramos viabilidad y memoria, no speedup" |
| "Funciona en un clúster" | "La versión con Bcast no supone memoria compartida, pero no la probamos en varias máquinas" |
| Cualquier número que no recuerden | "Está en `docs/ANALISIS.md`" y mostrarlo |

---

## 5. Guion de la demo (Diego, unos 2 minutos)

Prepararla antes de presentar: laptop conectada, todo lo demás cerrado, terminal en
`~/Work/knn-paralelo` y entorno activo (`conda activate knn-paralelo`).

1. Ejecutar `python demo/demo.py --usuario 42`.
2. Mientras corre la secuencial, unos 25 s, explicar: "Son 18 millones de pares en un
   núcleo".
3. Al terminar numba y MPI, señalar el speedup (~3.8) y que **las tres huellas son iguales**.
4. Mostrar las recomendaciones para el usuario 42 y sus películas favoritas.

**Si algo falla:** ejecutar `python demo/demo.py --respaldo`, que muestra la corrida guardada
sin calcular nada. Si tampoco funciona, poner el video de respaldo.
