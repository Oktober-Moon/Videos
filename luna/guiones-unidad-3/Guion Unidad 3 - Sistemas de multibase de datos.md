# Guion: Unidad 3 · Sistemas de multibase de datos

## Escena 1. La unidad 3 (0:00 – 0:41)

Buenos días, soy Eduardo y hoy presentaré lo que aprendí en la unidad 3 de la materia Tópicos de Base de Datos.
La unidad se llama Sistemas de multibase de datos, y tiene 5 subtemas.
Para explicar cada tema usaré un proyecto real, el cual es Okári, un sistema para una red de hospitales donde el personal anota lo que hace con cada paciente durante su turno.
El proyecto guarda los datos de los hospitales en una sola base de datos centralizada, y además mantiene copias de esa base con el mismo esquema.
(pausa)

## Escena 2. Varias bases que ya existían (0:41 – 2:46)

Comenzaré con el tema de la unidad, que es el sistema multibase, el cual junta varias bases de datos que ya existían por separado.
Cada base conserva su autonomía, o sea, decide su diseño, su gestor y sus transacciones.
Encima de ellas se pone una capa que las consulta juntas, para no tener que migrar todo a una sola base.
Por ejemplo, un hospital consultaría su laboratorio y su expediente desde una sola pantalla.

**Escena 2.1:**

Lo primero que me pregunté es si las copias de la base de datos del proyecto ya forman un sistema multibase.
La respuesta es que no, porque las copias no se consultan juntas y les falta un esquema global.
Eso sí, se parecen a uno en la autonomía, porque cada copia lleva su propio historial de cambios.
Un cambio de esquema se prueba primero en una copia, antes de llegar a los hospitales.

**Escena 2.2:**

Si nadie cuidara que las copias fueran iguales, una función tendría una versión en una copia y otra versión en otra.
Entonces una prueba pasaría en la copia de prueba, y la misma actualización fallaría en la base de los hospitales.
El personal de enfermería no podría registrar una dosis, y nadie sabría por qué.
El proyecto lo previene antes de subir un cambio, porque compara los cambios del código con los que ya se aplicaron en una copia.
Y en vez de un mediador, usa una disciplina de un solo sentido, en la que un cambio va primero a la copia de prueba y luego a la de los hospitales.
Después compara una suma de verificación de la estructura de las copias, para confirmar que quedaron iguales.
Lo que todavía se hace a mano es esa comparación, y convendría que corriera sola cada día.

## Escena 3. Características y clasificación (2:46 – 3:40)

El primer subtema es la clasificación de los sistemas multibase, que depende de cuánta autonomía conservan sus bases.
En uno no federado, las bases pierden su autonomía y se administran como una sola.
En uno federado, cada base conserva su autonomía y comparte solo una parte.
Si la federación tiene un esquema global que mantiene un administrador, está acoplada de forma fuerte.
Y si cada usuario arma su propia vista, sin esquema global, está acoplada de forma débil.
Aquí aprendí la diferencia con un sistema distribuido, que nace de un solo diseño repartido en nodos, mientras que el multibase junta bases que ya existían.
Con esa clasificación, las copias del proyecto se parecen a una federación débil, porque no tienen un esquema global declarado.

## Escena 4. Arquitectura de un sistema de multibase de datos (3:40 – 4:53)

El segundo subtema es la arquitectura de esquemas, que dice cómo cada base presenta sus datos al sistema multibase.
Tiene 4 niveles, que son el esquema local, el de exportación, el global y el externo.
El local es el diseño propio de cada base, el de exportación es la parte que comparte, el global junta esas partes y el externo es la vista que recibe cada aplicación.

**Escena 4.1:**

En el proyecto, el papel del esquema global lo cumplen los cambios de esquema versionados, porque cada cambio se guarda con su número.
Todas las copias se construyen aplicando la misma lista de cambios.
Y el esquema externo son los tipos que se generan para el cliente, que son la vista que usan las pantallas.
Se podría declarar un esquema global explícito con un archivo que tenga la estructura final, y así cada copia se compararía contra él.
Si dos copias se separan, lo primero que se rompe son las pruebas, porque corren contra una copia que quedó atrás aunque el código esté bien.

## Escena 5. Procesamiento de operaciones de actualización (4:53 – 6:08)

El tercer subtema es el procesamiento de actualizaciones, que es aplicar un cambio que toca varias bases autónomas.
Es más difícil que en un sistema distribuido, porque ahí un gestor coordina la transacción con el komít en dos fases.
En cambio, en un multibase cada base decide si acepta la actualización, y nadie puede obligar a la que rechazó.

**Escena 5.1:**

Llevar un cambio de una copia a otra es justo este problema.
Por eso no se pueden actualizar todas las copias al mismo tiempo, porque el orden importa.
Primero se prueba en una copia sin pacientes reales, y si falla ahí, no llega a los hospitales.
Y un cambio que quita un dato espera a que se publique la versión nueva, porque la versión anterior todavía lo consulta.
Para evitar que un cambio llegue a una copia y no a otra, el proyecto registra su llegada a los hospitales y compara la estructura.
Esa comparación garantiza que la estructura sea igual, pero no que los datos sean iguales, porque cada copia tiene sus propios datos.

## Escena 6. Procesamiento de consultas (6:08 – 6:54)

El cuarto subtema es el procesamiento de consultas, que es responder una consulta cuyos datos viven en varias bases.
El mediador recibe la consulta, la parte en una consulta por base, traduce cada parte al lenguaje de su base y junta los resultados.
En el proyecto, comparar el esquema de dos copias es una consulta multibase hecha a mano.
La misma consulta se corre en cada copia, y después una persona compara los resultados.
Un mediador haría ese trabajo solo, y diría al momento qué copia se quedó atrás.
Eso sí, no serviría para datos clínicos, porque juntar pacientes de varias copias mezclaría datos de prueba con datos reales.

## Escena 7. Aplicaciones de multibase de datos (6:54 – 7:57)

El último subtema son las aplicaciones, y en la industria los sistemas multibase se usan para integrar sistemas que ya existían.
Por ejemplo, cuando dos bancos se fusionan, el banco nuevo consulta las bases de los dos bancos anteriores.
En el proyecto, un enfoque multibase serviría para el laboratorio de cada hospital, que conservaría su base y su gestor.
El expediente mostraría el resultado sin guardarlo como suyo, y hoy esos resultados todavía no llegan, porque se dejaron para una versión futura.
El estándar Acheelesiéte Fáier serviría como el esquema de exportación común.
Si en cambio cada integración copiara los datos ajenos, habría dos copias de la verdad, y un resultado corregido en el laboratorio seguiría viejo en el proyecto.
El proyecto ya vive un caso parecido con el catálogo oficial de establecimientos de salud, que copia y sincroniza con su fuente.
(pausa)

## Escena 8. Conclusiones (7:57 – 8:32)

Para terminar, presentaré mis conclusiones.
La unidad 3 me enseñó que juntar bases que ya existían es más difícil que diseñar una sola, porque cada una conserva su autonomía.
La decisión que saqué es que las copias del proyecto no necesitan un mediador, sino un orden de un solo sentido y una comparación de su estructura.
Y el pendiente que me queda es que esa comparación corra sola, y declarar un esquema global contra el cual medir cada copia.
Gracias por su atención.
