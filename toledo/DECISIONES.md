# Proyecto: video "Forense digital en dispositivos móviles e IoT"

Aquí están las decisiones que Eduardo ya tomó sobre el video; no se vuelven a preguntar.

## Qué es
- Video narrado para una exposición de la escuela, de unos 35 minutos y 8 escenas. No se publica en internet.
- El video del cifrado César se canceló. Su código está en `_archivo_cesar/`: se puede consultar y copiar, pero no se modifica.
- Archivos que mandan: el guion de Word (texto narrado), `visuales.md` (qué se ve en cada subescena, fotos, efectos de sonido y paletas), `instrucciones_originales.md` (instrucciones originales) y `README.md` (cómo renderizar).
- Lo que va entre paréntesis después de un nombre en el guion es solo la pronunciación; nunca aparece en pantalla.

## Audio
- La voz de Eduardo viene en `audios/`, un archivo por subescena: `1.0` es la parte inicial de la escena 1, antes de "Escena 1.1"; luego `1.1`, `1.2`, etc.
- Desde el 16 de noviembre de 2026 toda la narración es su voz clonada en ElevenLabs (`voz_elevenlabs.py`, modelo multilingual_v2 en tono serio, sin suspiros); sus grabaciones limpias quedan en `audios_grabados/`. Detalles en el README («Narración (ElevenLabs)»).
- La duración de cada clip la manda su audio, más medio segundo.
- No hay música. Solo efectos de sonido sintetizados con código, 15 dB por debajo de la voz; bajan cuando hay voz y suben un poco en las "(pausa)".

## Imágenes
- Fotos de personas reales (cambio del 11 de noviembre de 2026; antes las ponía solo Eduardo): se buscan con el navegador, víctimas incluidas.
  - Primero, fuentes de licencia clara: Wikimedia Commons y fotos oficiales de dominio público (FBI, fichas policiales). Después, notas de prensa, anotadas como «uso escolar, no se publica».
  - Se guardan en `imagenes/candidatas/` y no entran al video hasta que Eduardo aprueba cada una. Las aprobadas pasan a `imagenes/` con el nombre de `visuales.md`.
  - No se toman de redes sociales. Si una foto de prensa salió de una red social, se avisa. Si hay duda de que la foto sea de la persona correcta, no se usa.
- Las fotos y clips de lugares, objetos, titulares y capturas de pantalla se consiguen con el navegador (Playwright), en las páginas normales de Pexels, Pixabay o Wikimedia Commons. Los clips van en `clips_reales/`.
- Cada fuente se anota en `fuentes_imagenes.txt`. Lo que falte va a `faltantes.txt` y mientras tanto se usa una ilustración.
- Sin APIs, claves ni servicios en línea. Todo el procesamiento (Depth Anything V2, rembg) corre en local.

## Estilo
- Documental con motion graphics, lo más realista posible.
- Para lugares y objetos se prefiere un clip de video real antes que una ilustración. Las ilustraciones quedan para los diagramas técnicos.
- Fotos fijas: movimiento de cámara 2.5D (parallax) con mapa de profundidad y personas recortadas, no solo acercamientos.
- Transición de foto real a animación: la foto aparece 2 o 3 segundos, se calcan sus contornos y se convierte en una ilustración en la misma posición, que luego se anima.
- Cada persona tiene un personaje ilustrado basado en su foto real (silueta, peinado, ropa, colores), en estilo plano y sin caricatura. Se usa el mismo personaje cada vez que esa persona vuelve a aparecer.
- Víctimas (María Ladenburger, Connie Dabate, Victor Collins): foto sin tinte ni efectos, quieta o con acercamiento muy lento. La violencia nunca se muestra; se sugiere con sombras, luces o el lugar vacío.
- Acabado de cine: grano suave, viñeta, corrección de color con la paleta de cada lugar y desenfoque de profundidad.
- Diagramas técnicos animados paso a paso al ritmo de la voz, con sombras suaves, brillo y profundidad.
- Cada escena abre con una tarjeta de título de 3 segundos sobre negro. Las transiciones entre subescenas son fundidos a negro, con movimientos de cámara lentos.
- Paletas por lugar: las de `visuales.md` y `paletas.py`.

## Técnico
- 1920x1080, 30 fps, H.264, yuv420p, CRF 18; audio AAC 48 kHz estéreo.
- Un clip por subescena, unidos por escena con concat y `-c copy`. Si cambia un audio o una foto, solo se renderiza esa subescena.

## Forma de trabajar
- Se avanza escena por escena.
- Antes de renderizar una escena completa, se guardan 4 fotogramas clave en `revision/` y se espera a que Eduardo los apruebe.
- Se trabaja en español.
