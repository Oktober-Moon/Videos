# Guion: Unidad 3 · Aseguramiento de la calidad (SQA)

## Escena 1. La unidad 3 (0:00 – 0:34)

Buenos días, soy Eduardo y hoy presentaré lo que aprendí en la unidad 3 de la materia Calidad de los Sistemas de Información.
La unidad se llama Aseguramiento de la calidad de los sistemas de información, que se conoce como Esecuá, y tiene 4 subtemas.
Para explicar cada tema usaré un proyecto real, el cual es Okári, un sistema para una red de hospitales donde el personal anota lo que hace con cada paciente durante su turno.
(pausa)

## Escena 2. Cuidar el proceso (0:34 – 2:49)

Comenzaré con el tema de la unidad, que es el aseguramiento de la calidad, el cual cuida cómo se construye el producto y no solo el producto terminado.
El control de calidad, en cambio, revisa el producto cuando ya está hecho.
Por ejemplo, escribir la prueba automática antes que el código es aseguramiento, y encontrar un defecto en una pantalla terminada es control.

**Escena 2.1:**

El proyecto ya tiene varias actividades de aseguramiento, porque actúan antes de que el cambio llegue al hospital.
Tiene criterios de calidad escritos que no se negocian, y cuando un cambio rompe uno que se puede ejecutar, el cambio no entra.
Antes de subir, corren el formato, la compilación, las pruebas automáticas y la medición de su cobertura.
Y un cambio que toca datos lleva dos revisores que no ven la conclusión del autor ni al otro revisor.
Lo que no tiene es la revisión del código por otra persona, porque hoy solo el integrador modifica el proyecto.

**Escena 2.2:**

Lo que el proyecto tampoco tiene es un plan que junte todo eso, porque hoy está repartido en varios documentos.
Se podría redactar, porque casi todas sus partes ya existen, y faltaría nombrar a un responsable por cada papel.
Con ese plan, alguien nuevo sabría desde el primer día qué revisiones corren, dónde se anota un defecto y quién aprueba los requisitos.
Algo que todavía se revisa a mano es cómo se ve una pantalla en tres anchos y en tema oscuro, y una prueba automática podría capturarla y compararla.

**Escena 2.3:**

Sin aseguramiento, un defecto que mostrara datos de otro hospital llegaría a los hospitales, y el primero en notarlo sería el personal.
Por eso el tablero de deudas del proyecto pone primero lo que puede dañar a una persona.
Las áreas con más riesgo son las indicaciones médicas y la farmacia, porque una medicina mal registrada o mal surtida llega al paciente.

## Escena 3. Medidas de fiabilidad y de disponibilidad (2:49 – 4:12)

El primer subtema son las medidas de fiabilidad y de disponibilidad.
La fiabilidad es la probabilidad de que un servicio funcione sin fallar durante un tiempo, y la disponibilidad es la parte del tiempo en que está listo para usarse.
Se calculan con el tiempo medio entre fallos, que se conoce como Emetebeéfe, y con el tiempo medio de reparación, que se conoce como Emeteteérre.
La disponibilidad es el MTBF entre la suma del MTBF y el MTTR.

**Escena 3.1:**

Un hospital trabaja de día y de noche, y una disponibilidad del 99.9 por ciento dejaría 43 minutos sin servicio al mes.
El proyecto no puede medirla hoy, porque no registra sus caídas ni cuánto tarda en repararlas.
Lo que haría falta es empezar ese registro, con la hora en que se cayó, la hora en que volvió, las áreas afectadas y la causa.
Mientras tanto, el proyecto reduce el daño de una caída, porque el personal registra dosis sin conexión y una cola las reenvía al volver la red.
Las áreas que necesitan más disponibilidad son urgencias, luego el censo de camas y al final transparencia, que puede esperar unas horas sin dañar a un paciente.

## Escena 4. Seguridad de los sistemas de información (4:12 – 5:20)

El segundo subtema es la seguridad, que protege la información para que nadie la vea, la cambie o la pierda sin deber.
Se resume en tres partes, que son la confidencialidad, la integridad y la disponibilidad.
En el proyecto, la confidencialidad la cuidan la separación entre hospitales, los permisos según la función de cada persona y que los registros técnicos no guarden datos clínicos.
La integridad la cuida la auditoría automática, porque cada cambio clínico deja rastro.
Y la disponibilidad la cuida la cola de operaciones pendientes, porque el registro sigue sin conexión.
Lo primero que reforzaría es la disponibilidad, porque es la única de las tres que no tiene ninguna medición.
Si el personal de un hospital viera datos de otro, sería una vulneración de datos personales, y la ley obliga a avisar a los pacientes afectados.
Por eso la seguridad se diseña con los requisitos, en la planeación, porque cambia cómo se diseñan los datos.

## Escena 5. Relación de la ingeniería de sistemas de información con SQA (5:20 – 6:11)

El tercer subtema es la relación entre la ingeniería de sistemas de información y el Esecuá.
La ingeniería construye el sistema de información, y el SQA vigila que esa construcción siga un proceso que no produzca defectos.
En el proyecto, el aseguramiento interviene en cada momento del ciclo.
En los requisitos, una revisión aparte busca huecos antes de que el integrador los apruebe, y en el diseño cada requisito se liga a su prueba.
En la construcción, la prueba se ve fallar antes de escribir el código, y en las pruebas una verificación aparte revisa que cada requisito tenga la suya en verde.
Y en el mantenimiento, un cambio corrige primero el requisito, después la prueba y al final el código.

## Escena 6. Definición y propósito del SQA (6:11 – 7:28)

El último subtema es el plan de aseguramiento, que según el estándar I tríple é siéte tréinta dice para qué sirve, quién hace cada papel, qué actividades lleva, con qué herramientas y dónde queda la evidencia.
Las actividades del SQA son las revisiones, las auditorías, las pruebas y la gestión de configuración, y el proyecto hace las cuatro.
Los papeles son el responsable del aseguramiento, el revisor, el auditor, el responsable de pruebas y el de configuración, y en el proyecto se separan por actividad.
Las herramientas que usa revisan el código, su formato y sus tipos, corren las pruebas con su cobertura y revisan las librerías de terceros.
El plan completo se podría redactar este semestre, y solo dos partes quedarían como borrador.
La de disponibilidad quedaría así porque no hay datos, y la de los papeles, porque hay un solo integrador.
Un plan que nadie sigue es papel, y el proyecto lo evita porque cada criterio de calidad dice qué lo vigila, y el que se puede ejecutar detiene el cambio que lo rompe.
(pausa)

## Escena 7. Conclusiones (7:28 – 8:00)

Para terminar, presentaré mis conclusiones.
La unidad 3 me enseñó que la calidad se asegura en el proceso, antes de que el defecto exista, y no al final.
La decisión que saqué es que el proyecto ya tiene casi todo su aseguramiento, pero repartido, y lo que le falta es juntarlo en un plan.
Y el pendiente que me queda es medir la disponibilidad, empezando por anotar cada caída.
Gracias por su atención.
