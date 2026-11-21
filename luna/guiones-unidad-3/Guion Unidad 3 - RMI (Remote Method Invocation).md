# Guion: Unidad 3 · RMI (Remote Method Invocation)

## Escena 1. La unidad 3 (0:00 – 0:37)

Buenos días, soy Eduardo y hoy presentaré lo que aprendí en la unidad 3 de la materia Programación en Ambiente Cliente-Servidor.
La unidad se llama Erremeí, que viene de Rimóut Métod Invokéishon, y tiene 7 subtemas.
Para explicar cada tema usaré un proyecto real, el cual es Okári, un sistema para una red de hospitales donde el personal anota lo que hace con cada paciente durante su turno.
En el proyecto, el cliente corre en el navegador y ejecuta funciones del servidor por Achetetepé.
(pausa)

## Escena 2. Un método en otra máquina (0:37 – 2:49)

Comenzaré con el tema de la unidad, que es Erremeí, la forma que tiene Yáva de ejecutar el método de un objeto que vive en otra máquina.
Lo que promete es que el programa lo escribe como si el objeto fuera local.
Viene de la idea de Errepecé, que es ejecutar un procedimiento remoto, y la diferencia es que RMI ejecuta el método de un objeto.
Por ejemplo, un cliente ejecutaría el método registrar dosis de un objeto que está en el servidor.

**Escena 2.1:**

El proyecto no usa RMI, pero se le parece en la promesa, porque el cliente pide y el servidor ejecuta.
También se parece en el contrato, porque los tipos de cada función remota se generan desde el esquema de la base de datos.
Se distinguen en que RMI pide Java en los dos lados, y el proyecto usa Táipskript en el cliente y Esecuéle en el servidor.
Además, RMI usa su propio protocolo, y el proyecto usa HTTP con Yéison.

**Escena 2.2:**

RMI no se puede aplicar en el proyecto, porque necesita una máquina virtual de Java en el cliente, y el navegador no la tiene.
Aplicarlo pediría reescribir el cliente, el servidor y las reglas clínicas que hoy viven en las funciones de la base de datos.
Lo que sí tiene el proyecto es la portabilidad de HTTP, porque un navegador, un teléfono o un programa del hospital usarían el mismo protocolo.

**Escena 2.3:**

La idea más importante que me llevo es que una ejecución remota no es una ejecución local.
Una ejecución local responde o falla, pero una remota puede quedarse sin respuesta, y sin un plazo la pantalla esperaría sin fin.
El proyecto trata esos casos de tres formas, con un aviso y un botón para reintentar, con una cola que reenvía lo que se hizo sin conexión y con un plazo de espera.

## Escena 3. Características y estructura de RMI (2:49 – 3:40)

El primer subtema es la estructura de RMI, que tiene tres capas.
La primera es la del resguardo y el esqueleto, donde el resguardo, o stáb, empaqueta la petición en el cliente y el esqueleto ejecuta el método real en el servidor.
La segunda es la capa de referencia remota, que ubica el objeto remoto.
Y la tercera es la capa de transporte, que abre la conexión y mueve los báits por la red.
Un objeto remoto se ve igual que uno local para quien lo usa, pero la red se puede caer a media ejecución.
En el proyecto, el servicio del cliente cumple el papel del resguardo, porque empaqueta los argumentos en Yéison y los manda por HTTP.

## Escena 4. El API Java RMI (3:40 – 4:19)

El segundo subtema es el Apeí de Java RMI, que son las clases para exponer objetos remotos.
Obliga al programador a declarar una interfaz remota, para que el cliente solo conozca el contrato y no la implementación.
También lo obliga a declarar Rimóut Eksépshon en cada método, porque la red puede fallar en cualquier momento.
Y los parámetros tienen que ser serializables, o sea, que se puedan convertir en bytes para viajar por la red.
El proyecto cumple obligaciones parecidas sin Java, porque cada función declara sus argumentos en el esquema.

## Escena 5. Jerarquía de objetos RMI (4:19 – 4:50)

El tercer subtema es la jerarquía de objetos, que son las clases de las que hereda un objeto remoto.
La ventaja es que el objeto hereda la parte remota sin que el programador la escriba.
La rigidez es que en Java una clase solo hereda de una clase, y un objeto que ya hereda de otra tiene que exportarse aparte.
El proyecto no tiene esta jerarquía, porque su servidor ejecuta funciones y no objetos.

## Escena 6. El sistema de nombrado Registry (4:50 – 5:49)

El cuarto subtema es el registro de nombres, que en Java se llama Réyistri.
El servidor registra su objeto con un nombre, y el cliente pide ese nombre y recibe la referencia, sin conocer la dirección exacta.
En el proyecto, el cliente sabe dónde está su servidor por una variable de configuración que se fija al construir la aplicación.
Si la dirección estuviera escrita a mano en varios lugares, cambiar de servidor pediría buscar cada copia, y una copia olvidada seguiría apuntando al servidor viejo.
Se podría aplicar el descubrimiento dinámico, en el que el cliente lee la dirección de un archivo al abrir, y así un cambio de dominio no pediría publicar otra vez.
Esta decisión se toma en la planeación, y con una variable, cambiar la dirección en la ejecución es un solo cambio.

## Escena 7. Desarrollo de aplicaciones distribuidas (5:49 – 6:53)

El quinto subtema es el desarrollo de aplicaciones distribuidas con RMI, que sigue cuatro pasos.
Primero se define la interfaz, luego se implementa, después se registra el objeto y al final el cliente lo ejecuta.
Esa misma secuencia aparece en el proyecto, en la función que registra el alta médica.
El contrato es un documento de requisitos, la implementación es un cambio de esquema, la publicación la hace el integrador y el consumo lo hace el servicio del cliente.
Por eso la prueba se escribe desde el contrato antes que el código, y quien la escribe no ve la implementación.
Si se implementara primero, el contrato copiaría lo que el código ya hace, con todo y sus defectos, y las pruebas confirmarían el código en vez del requisito.
La práctica de este subtema produciría una aplicación mínima con RMI, fuera del proyecto, para comparar las dos secuencias lado a lado.

## Escena 8. Paso de parámetros a través de la red (6:53 – 7:36)

El sexto subtema es el paso de parámetros, que puede ser por copia o por referencia.
Por copia, el objeto viaja completo y llega un duplicado, y por referencia viaja un resguardo y cada uso se ejecuta en la máquina del objeto.
En el proyecto, el expediente pasa solo el identificador del paciente, y cada pestaña pide sus datos al abrirse.
Una pestaña cerrada no trae nada, y eso evita mandar datos clínicos que nadie pidió ver.
Ese criterio serviría para revisar las demás consultas, y empezaría por el censo de camas, porque junta muchas camas en una sola pantalla.

## Escena 9. Callbacks (7:36 – 8:30)

El último subtema son los kólbaks, en los que el servidor ejecuta un método del cliente para avisarle algo.
Así el cliente no tiene que preguntar cada pocos segundos.
En el proyecto, un código de emergencia tiene que llegar a las pantallas sin que nadie pregunte, y eso lo resuelve un canal persistente sobre Uebsóket.
Ese canal avisa en 6 áreas, que son camas, emergencias, notificaciones, indicaciones médicas, citas y notas de evolución.
Si cada pantalla preguntara cada 5 segundos, con 50 pantallas serían 600 peticiones por minuto, aunque nada cambiara.
Lo que le falta al canal es un acuse de recibo, porque el servidor no sabe qué pantalla recibió cada aviso, y llegar a más áreas, como la sala de espera.
(pausa)

## Escena 10. Conclusiones (8:30 – 9:04)

Para terminar, presentaré mis conclusiones.
La unidad 3 me enseñó que ejecutar algo en otra máquina no es igual que hacerlo en la misma, aunque el código lo parezca.
La decisión que saqué es que el proyecto no necesita RMI, porque HTTP y los tipos generados le dan el mismo contrato con más portabilidad.
Y el pendiente que me queda es que el canal persistente sepa quién recibió cada aviso, y que llegue a más áreas.
Gracias por su atención.
