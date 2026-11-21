# Mapa de visuales: Forense digital en móviles e IoT

Cada subescena del guion tiene aquí su audio, lo que se ve, las fotos reales que la acompañan y sus efectos de sonido.

- El audio de cada subescena se llama igual que su número: `1.0.wav` es la parte inicial de la escena 1 (antes de "Escena 1.1"), `1.1.wav` es la subescena 1.1, y así.
- Las fotos reales van en la carpeta `imagenes/`, con el nombre que se indica aquí. Si una foto no está, se reemplaza con una ilustración.
- Los efectos de sonido van bajos, por debajo de la voz. No hay música.

## Paletas de color

| Mundo | Escenas | Colores (hex) |
|---|---|---|
| Friburgo, Alemania | 1, 2.0, 4 | verde de la Selva Negra #2F4A3A, rojo y blanco del escudo de Friburgo #C8102E / #F4F1EA, gris piedra #8C8C88, azul del río #3E6E8E |
| San Bernardino y el FBI | 3.0 a 3.9 | azul FBI #0B2D5B, dorado de California #FDB515, arena del desierto #D9C6A5 |
| Mundo Apple (iPhone, chips) | 2.3 a 2.8, 3.8 a 3.14 | gris espacial #2E2E30, blanco #F5F5F7, azul Apple #0071E3 |
| Mundo Android | 2.9 y 2.10 | verde Android #3DDC84, gris oscuro #202124, blanco #FFFFFF |
| Connecticut (caso Dabate) | 5 y 6 | azul de la bandera de Connecticut #1F3A93, beige de casa suburbana #D8CBB3, rojo y azul de patrulla #D7263D / #1B4AD6 |
| Laboratorio forense e IoT | 7.0 a 7.5 | verde de placa de circuito #1E5B32, cobre #B87333, negro #111111, verde de terminal #33FF66 |
| Arkansas (caso Bates) | 7.5 a 7.8 | rojo de la bandera de Arkansas #C8102E, azul #00205B, blanco #FFFFFF |
| Cierre | 8 | mezcla suave de la paleta de Friburgo y la de Connecticut, terminando en negro |

---

## Escena 1. El testigo en el bolsillo

**1.0** — Friburgo de noche, calles de piedra, el río Dreisam con su ciclovía. Al decir su nombre aparece la foto de María.
- Fotos: `1.0_friburgo_noche.jpg`, `1.0_dreisam.jpg`, `1.0_maria_ladenburger.jpg`
- SFX: viento, agua del río, rueda de bicicleta

**1.1** — Amanecer gris sobre el río; cinta policial; orilla vacía. Al final, la imagen se queda quieta en la pausa.
- Fotos: `1.1_escena_dreisam.jpg` (foto de prensa del lugar), `1.1_tranvia_friburgo.jpg`
- SFX: viento, sirena lejana muy baja

**1.2** — Silueta de un bolsillo con un teléfono que late con luz; un contador de pasos que avanza solo.
- Fotos: ninguna
- SFX: latido grave suave, clic de contador

## Escena 2. Un chip que no obedece

**2.0** — Fotogramas granulados de cámara de tranvía; foto del sospechoso; un iPhone sobre una mesa de evidencias con la pantalla de bloqueo encendida.
- Fotos: `2.0_hussein_khavari.jpg`, `2.0_tranvia_camara.jpg`
- SFX: zumbido de cámara de seguridad, bolsa de evidencia

**2.1** — Animación: se abre un teléfono y se ilumina el chip de memoria; dentro, ceros y unos.
- SFX: zumbido electrónico suave

**2.2** — Un cable del teléfono a una computadora de laboratorio; una barra de copia que avanza; un archivo "borrado" que sigue ahí; una computadora probando contraseñas a toda velocidad.
- SFX: transferencia de datos, teclado rápido

**2.3** — Diagrama del procesador con un segundo procesador aislado adentro (Secure Enclave); al final, el chip Titan M de Google.
- Fotos: `2.3_chip_a7.jpg`, `2.3_titan_m.jpg`
- SFX: candado que se cierra

**2.4** — Un número aleatorio que se graba dentro del silicio; un candado que nunca sale del chip.
- SFX: grabado láser, tono metálico

**2.5** — Diagrama: contraseña + UID = clave que abre los archivos. Con la contraseña correcta, los archivos se abren; con la incorrecta, quedan en ruido.
- SFX: clic de cerradura; estática

**2.6** — Contador de 80 milisegundos; números grandes: 10,000 → 13 minutos; 1,000,000 → 22 horas; 5 años y medio.
- SFX: tic de reloj rápido

**2.7** — Computadora de laboratorio con un bloque de datos cifrados; una flecha rota hacia el teléfono.
- SFX: error de sistema suave

**2.8** — Pantalla de bloqueo con los mensajes de espera: 1 minuto, 5, 15, 1 hora, 3 horas, 8 horas; al décimo, "iPhone no disponible".
- SFX: vibración de error en cada intento

**2.9** — Un teléfono Android reiniciado de noche, alarma muda y llamada perdida.
- SFX: alarma que no suena (silencio cortado)

**2.10** — La memoria dividida en dos zonas, una abierta y otra cerrada; transición a titulares de "FBI contra Apple".
- SFX: whoosh de transición

## Escena 3. 900,000 dólares por nada

**3.0** — Mapa de California con San Bernardino; fotos de los atacantes; el iPhone 5C.
- Fotos: `3.0_inland_regional_center.jpg`, `3.0_farook_malik.jpg`, `3.0_iphone_5c.jpg`
- SFX: sirenas lejanas, helicóptero

**3.1** — Pantalla de ajustes de iCloud con la contraseña cambiada; tres íconos: enchufe, wifi, candado; el respaldo que no sube.
- Fotos: `3.1_icloud_ajustes.png` (captura)
- SFX: notificación, error de conexión

**3.2** — La carta de Tim Cook "A Message to Our Customers"; titulares; fachada de un tribunal.
- Fotos: `3.2_carta_tim_cook.png`, `3.2_titulares_2016.jpg`, `3.2_tim_cook.jpg`
- SFX: papel, mazo de juez

**3.3** — Titular del Washington Post de 2021; el puerto Lightning en primer plano y un cable que se acerca.
- Fotos: `3.3_washington_post_2021.png`, `3.3_puerto_lightning.jpg`
- SFX: conector que entra

**3.4** — Animación: una biblioteca de código abierto que pasa de Mozilla al iPhone.
- Fotos: `3.4_logo_mozilla.png`
- SFX: teclado

**3.5** — Mark Dowd; líneas de código desplazándose y una línea resaltada en rojo.
- Fotos: `3.5_mark_dowd.jpg`
- SFX: lectura de código, tono de hallazgo

**3.6** — David Wang; tres puertas que se abren una tras otra; aparece la palabra "Cóndor".
- Fotos: `3.6_david_wang.jpg`
- SFX: tres cerraduras que se abren

**3.7** — Contador de contraseñas a toda velocidad; una docena de iPhone 5C en fila.
- SFX: ráfaga de clics

**3.8** — Comparación de chips: iPhone 5C sin Secure Enclave, iPhone 5S con Secure Enclave.
- Fotos: `3.8_chip_a6_vs_a7.jpg`
- SFX: tono grave

**3.9** — Cifra de 900,000 dólares; pantalla "Accesorios USB" en ajustes; la caja GrayKey.
- Fotos: `3.9_graykey.jpg`, `3.9_modo_usb.png`
- SFX: caja registradora suave, candado

**3.10** — Un teléfono que se desbloquea por primera vez y "suelta" claves a la memoria.
- SFX: desbloqueo de iPhone

**3.11** — Dos teléfonos: BFU (candado cerrado) y AFU (candado abierto); una bolsa de Faraday con un teléfono cargando.
- Fotos: `3.11_bolsa_faraday.jpg`
- SFX: cierre de bolsa

**3.12** — La carta de la policía de Detroit; Jiska Classen; la palabra inactivity_reboot; un reloj de 72 horas.
- Fotos: `3.12_carta_detroit.png`, `3.12_jiska_classen.jpg`
- SFX: reloj, reinicio de iPhone

**3.13** — Cadena de arranque: bootrom → cargador → iOS, cada eslabón con la firma de Apple.
- SFX: eslabones de cadena

**3.14** — El anuncio de checkm8 de axi0mX (2019); lista de modelos del iPhone 4S al X; el primer eslabón se agrieta.
- Fotos: `3.14_tweet_checkm8.png`
- SFX: grieta, cristal

## Escena 4. Escaleras donde no hay escaleras

**4.0** — El río Dreisam de día; la app Salud abierta.
- Fotos: `4.0_dreisam_dia.jpg`, `4.0_app_salud.png`
- SFX: río, pájaros

**4.1** — Animación del acelerómetro: una masa diminuta que se mueve con cada paso; íconos de caminar, correr, bicicleta.
- SFX: pasos

**4.2** — Una columna de aire sobre una persona que se acorta al subir; la app marcando "pisos subidos".
- Fotos: `4.2_pisos_subidos.png`
- SFX: viento suave, tono ascendente

**4.3** — Línea de tiempo de la madrugada con una barra marcada "subir escaleras"; la pendiente de la orilla. Pausa con la imagen fija.
- Fotos: `4.3_orilla_pendiente.jpg`
- SFX: silencio, agua

**4.4** — Un policía que baja y sube la pendiente con un teléfono en el bolsillo; la gráfica igual.
- Fotos: `4.4_recreacion_policia.jpg`
- SFX: pasos en tierra

**4.5** — Tribunal de Friburgo; radiografía dental para calcular la edad.
- Fotos: `4.5_tribunal_friburgo.jpg`, `4.5_juicio_khavari.jpg`
- SFX: murmullo de sala

**4.6** — Mapa de Europa con una línea de Corfú a Friburgo; huellas dactilares en la base Eurodac.
- Fotos: `4.6_corfu.jpg`
- SFX: escáner de huella

**4.7** — El noticiero Tagesschau; Angela Merkel; titular de la cadena perpetua.
- Fotos: `4.7_tagesschau.jpg`, `4.7_merkel.jpg`, `4.7_sentencia.jpg`
- SFX: mazo de juez

## Escena 5. Un hombre amarrado a una silla

**5.0** — Casa en Ellington con luces de patrulla; fotos de Richard y Connie.
- Fotos: `5.0_casa_ellington.jpg`, `5.0_richard_dabate.jpg`, `5.0_connie_dabate.jpg`
- SFX: alarma de casa, sirenas

**5.1** — Silueta borrosa de un hombre enmascarado con traje de camuflaje.
- SFX: tono inquietante grave

**5.2** — Escalera al sótano; brillo de un soplete. Pausa con la imagen fija.
- SFX: soplete encendiéndose

**5.3** — Documento de seguro de vida con la cifra de 475,000 dólares; foto de Sarah Ganzer.
- Fotos: `5.3_sarah_ganzer.jpg`
- SFX: papel

## Escena 6. La casa declara

**6.0** — Una casa con un módem; líneas de la laptop y del teléfono que salen con un solo número IP.
- SFX: módem, datos

**6.1** — Línea de tiempo: 9:01 inicio de sesión, 9:04 correo, 9:18 YMCA, 9:20 ESPN.
- SFX: clic de mouse en cada marca

**6.2** — Sensor magnético de puerta: imán y marco que se separan.
- Fotos: `6.2_sensor_puerta.jpg`
- SFX: clic magnético

**6.3** — Registro de la alarma: garaje 9:23, pánico 10:11, llamada 10:16; videos de Facebook a las 9:40 y 9:46. Pausa con la imagen fija.
- SFX: pitidos de alarma, notificación

**6.4** — El Fitbit One real; animación de los datos viajando por Bluetooth al teléfono y a la nube.
- Fotos: `6.4_fitbit_one.jpg`
- SFX: sincronización

**6.5** — Gráfica de pasos que sigue subiendo después de las 9:00 hasta las 10:05; 1,217 pies contra 125 pies.
- SFX: pasos que se detienen

**6.6** — Sala del juicio; Richard Dabate en la corte; titular "Fitbit murder".
- Fotos: `6.6_dabate_juicio.jpg`, `6.6_titular_fitbit.jpg`
- SFX: mazo de juez

## Escena 7. Cuando el aparato no quiere hablar

**7.0** — Mesa con aparatos distintos: cámara, reloj, bocina, termostato, sensor industrial.
- SFX: zumbido electrónico

**7.1** — Tres caminos: nube, app del teléfono, chip.
- SFX: whoosh

**7.2** — Placa de circuito con los puntos de prueba JTAG iluminados.
- Fotos: `7.2_puertos_jtag.jpg`
- SFX: chispa eléctrica suave

**7.3** — Cables muy delgados soldados a los puntos de prueba.
- Fotos: `7.3_soldadura_jtag.jpg`
- SFX: cautín, humo

**7.4** — Estación de aire caliente sobre un chip; pinzas que lo levantan; lector de memoria.
- Fotos: `7.4_chip_off.jpg`
- SFX: aire caliente, clic de pinzas

**7.5** — Volcado hexadecimal desplazándose; recuadros que encuentran archivos. Pausa. Transición a Bentonville.
- SFX: datos desplazándose

**7.6** — Jacuzzi de noche; bocina Amazon Echo; fotos de James Bates y Victor Collins.
- Fotos: `7.6_amazon_echo.jpg`, `7.6_james_bates.jpg`, `7.6_victor_collins.jpg`, `7.6_casa_bates.jpg`
- SFX: burbujas de jacuzzi

**7.7** — El anillo azul del Echo encendiéndose; titular de Amazon negándose a entregar las grabaciones.
- Fotos: `7.7_titular_amazon.jpg`
- SFX: tono de activación de bocina

**7.8** — Gráfica del medidor de agua con un pico entre la 1 y las 3 de la madrugada; titular de los cargos retirados.
- Fotos: `7.8_titular_cargos.jpg`
- SFX: agua corriendo, mazo de juez

## Escena 8. Las 10:05

**8.0** — Contador de pasos de un teléfono que sube; el Dreisam al atardecer; la cocina vacía en Connecticut; la última marca del Fitbit a las 10:05; corte a negro.
- Fotos: reutiliza `4.0_dreisam_dia.jpg` y `5.0_casa_ellington.jpg`
- SFX: viento suave; al final, silencio total
