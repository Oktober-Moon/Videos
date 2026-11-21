# Guion: Unidad 3 · Marco de gobierno de tecnologías de información

## Escena 1. La unidad 3 (0:00 – 0:42)

Buenos días, soy Eduardo y hoy presentaré lo que aprendí en la unidad 3 de la materia Fundamentos de Gestión de Servicios de Teí.
La unidad se llama Marco de gobierno de tecnologías de información, y tiene 2 subtemas.
Para explicar cada tema usaré un proyecto real, el cual es Okári, un sistema para una red de hospitales donde el personal anota lo que hace con cada paciente durante su turno.
Lo que el proyecto tiene como objetivo es que lo que se le hace a un paciente se anote por completo y a tiempo.
(pausa)

## Escena 2. Quién decide (0:42 – 3:24)

Comenzaré con el tema de la unidad, que es el gobierno de Teí, o sea, decidir quién decide sobre la tecnología de una organización.
La administración de TI, en cambio, es hacer lo que el gobierno ya decidió.
Por ejemplo, la dirección de una red de hospitales decidiría qué parte se construye primero, y el equipo del proyecto la construiría y la operaría.
Para ordenar ese trabajo existe Kóbit 2019, que es un marco de referencia para el gobierno de TI.

**Escena 2.1:**

Lo primero que encontré es que el proyecto ya tiene gobierno, aunque no le diga así.
Tiene un documento con las reglas que no se negocian, y cada regla dice qué la vigila y qué no cubre.
Cuando alguien guarda un cambio que rompe una de esas reglas, el cambio no entra.
Antes de subir un cambio corren el formato, la compilación y las pruebas.
Además, las decisiones se anotan con un número, con quién las tomó y con su fundamento.
Y una decisión vieja solo cambia con otra decisión que lleva su propio número.

**Escena 2.2:**

Después me pregunté si un equipo tan chico necesita un gobierno formal, y la respuesta es que sí, pero a su medida.
El proyecto lo trabajaron 4 personas, y hoy solo una persona, el integrador, lo modifica.
Un comité se juntaría a revisar lo que una prueba revisa en segundos, entonces lo que vale la pena es la parte de las decisiones.
O sea, escribir quién decide, con qué fundamento y quién responde por el resultado.
Lo que todavía falta es la voz de los hospitales, porque hoy las prioridades las fijan el plan del proyecto y el integrador.

**Escena 2.3:**

Para ver qué pasaría sin gobierno, pensé en un cambio que llega directo a los hospitales sin que nadie lo pruebe.
Una pantalla de indicaciones médicas podría dejar de guardar, y el personal de enfermería sería el primero en notarlo.
Tendría que volver al papel mientras se arregla, y después capturar lo que escribió.
En el proyecto eso no pasa así, porque publicar a los hospitales es una actividad aparte que solo hace el integrador.
Lo que el proyecto todavía no tiene por escrito es qué funcionalidad sigue después del plan actual.
Si el integrador dejara el proyecto, nadie sabría qué área sigue.

## Escena 3. Fundamentos para la generación de estrategias de TI (3:24 – 5:03)

El primer subtema trata de la estrategia de TI, que dice cómo la tecnología apoya los objetivos de una organización.
No es lo mismo que una lista de funcionalidades, porque la lista dice qué falta construir y la estrategia dice por qué, para quién y en qué orden.
El proyecto tiene un plan de funcionalidades por versión, pero no tiene una estrategia escrita.

**Escena 3.1:**

Una estrategia a 12 meses diría qué hospitales se suman a la red y en qué orden.
También diría qué objetivo de cada departamento del hospital apoya cada área, y con qué indicador se mide su avance.
Por eso sí se podría redactar hoy, porque el proyecto ya tiene su objetivo escrito y un registro de decisiones.
Lo que faltaría reunir viene de fuera del código, como los objetivos de cada departamento y el costo de cada servicio.

**Escena 3.2:**

Sin estrategia, el proyecto atendería lo urgente antes que lo importante.
Un área nueva se abriría por el pedido más reciente, y un área a medias se quedaría detrás de otra nueva.
De hecho, el proyecto ya agregó funcionalidades fuera de su plan original, como el triaje, que es la revisión que dice qué tan grave viene el paciente.
Con una estrategia, cada funcionalidad nueva se compararía contra un objetivo de la red.
La estrategia se escribe en la fundamentación, y se revisaría cada 6 meses en la evaluación.

## Escena 4. Gobierno de tecnologías de la información (5:03 – 6:57)

El segundo subtema es el gobierno de tecnologías de la información, que reparte la autoridad sobre la tecnología.
Sus preguntas centrales son 3, que son quién decide, con qué autoridad y quién responde por el resultado.

**Escena 4.1:**

Con esas preguntas armé la matriz de decisiones del proyecto.
Lo clínico lo decide la norma oficial, el equipo la cita y el integrador aprueba.
Los requisitos de un área los decide el integrador, y una revisión aparte busca lo que les falta.
Un rol nuevo solo entra si el integrador lo autoriza por escrito, y una prueba revisa que los roles no cambien solos.
Y el detalle técnico lo decide quien programa, y lo verifican las pruebas y la revisión.

**Escena 4.2:**

Después pensé qué pasaría si dos personas creyeran decidir lo mismo.
Con un cambio de esquema, cada una escribiría su versión y la aplicaría con su número.
Entonces la base de datos quedaría distinta de lo que dice el código, y nadie sabría qué versión vale.
El proyecto lo evita porque solo el integrador aplica esos cambios, y una prueba impide que dos cambios compartan número.

**Escena 4.3:**

Por último, ordené las áreas según el daño que causaría un defecto.
Primero va la base de datos, porque un defecto puede perder datos clínicos.
Después van los permisos, porque un defecto dejaría ver un expediente a quien no debe.
Y al final va la apariencia de las pantallas, porque un defecto la desacomoda sin tocar los datos.
El proyecto ya gradúa su revisión así, porque un cambio de solo documentación no lleva revisores y uno de datos lleva 2.
(pausa)

## Escena 5. Conclusiones (6:57 – 7:29)

Para terminar, presentaré mis conclusiones.
La unidad 3 me enseñó que el gobierno de TI no es un comité, sino saber quién decide y con qué fundamento.
La decisión que saqué es que en un equipo chico el gobierno vive en reglas escritas y en pruebas que se ejecutan solas.
Y el pendiente que me queda es escribir la estrategia, para que la red sepa por qué se construye cada área.
Gracias por su atención.
