Quiero que hagas un video narrado para una exposición de mi escuela. El tema es "Forense digital en dispositivos móviles e IoT". No se va a publicar en internet; es solo para presentarlo en clase. Dura unos 35 minutos y tiene 8 escenas. Primero haremos solo la escena 1 como prueba.

## Lo que hay en esta carpeta
- `Guion Forense digital en moviles e IoT.docx`: el guion completo que yo leo en voz alta. Cada escena tiene subescenas ("Escena 1.1:", "Escena 1.2:", etc.). Lo que está entre paréntesis después de un nombre es solo la pronunciación; no aparece en pantalla.
- `visuales.md`: lo que se ve en cada subescena, las fotos reales que van en cada una, los efectos de sonido y la paleta de color de cada lugar. Síguelo como guía principal.
- `audios/`: mi voz grabada, un archivo por subescena. `1.0.wav` es la parte inicial de la escena 1 (antes de "Escena 1.1"), `1.1.wav` es la subescena 1.1, y así. Puede haber archivos .wav o .mp3.
- `imagenes/`: fotos reales que yo conseguí, con los nombres que indica `visuales.md`.

## Reglas
1. La duración de cada subescena la manda su audio. Mide cada archivo con ffprobe y haz que el clip dure lo mismo, más medio segundo de respiro al final.
2. Usa solo las fotos que están en `imagenes/`. No descargues fotos de personas de internet. Si falta una foto, pon en su lugar una ilustración hecha con código (silueta, mapa, diagrama) y apúntala en una lista `faltantes.txt` para que yo la consiga.
3. Las fotos de las víctimas (María Ladenburger, Connie Dabate, Victor Collins) van quietas o con un acercamiento muy lento, sin efectos, filtros raros ni sonidos bruscos encima.
4. No hay música. Solo efectos de sonido generados con código (numpy/scipy), mezclados unos 15 dB por debajo de mi voz. Cuando yo hablo, los efectos bajan; en las "(pausa)" pueden subir un poco.
5. Cada escena empieza con una tarjeta de título de 3 segundos sobre negro con el nombre de la escena (por ejemplo "El testigo en el bolsillo"), con su efecto de sonido grave.
6. Las paletas de color de `visuales.md` se usan en las ilustraciones, diagramas, títulos y en un ligero tinte sobre las fotos. Cada lugar tiene su propio color: Friburgo, San Bernardino, el mundo Apple, Android, Connecticut, el laboratorio forense y Arkansas.

## Estilo
- Movimientos lentos de cámara sobre las fotos (acercamientos y paneos suaves), transiciones a negro entre subescenas y partículas discretas (polvo, brasas, datos) en las ilustraciones.
- Los diagramas técnicos (el chip, la clave, BFU y AFU, la dirección IP, JTAG y Chip-Off) deben ser claros y animados paso por paso, al ritmo de lo que digo en el audio.
- Textos en pantalla cortos: fechas, horas, cifras y nombres. Fuente sin serifa limpia (Inter o Roboto, de Google Fonts).

## Especificaciones técnicas
- 1920x1080, 30 fps, H.264, yuv420p, CRF 18; audio AAC 48 kHz estéreo.
- Herramientas: Python (numpy, Pillow o pycairo, scipy) y ffmpeg. Revisa si están instalados e instálalos si faltan (ffmpeg con `winget install ffmpeg`).
- Renderiza un .mp4 por subescena con la misma configuración, únelos por escena con el demuxer concat y `-c copy`, y al final une las 8 escenas.
- Guarda cada archivo con nombre temporal y renómbralo solo si ffmpeg termina sin error.
- Organiza el proyecto así: `paletas.py`, `sfx.py`, `escenas/escena01.py` … `escenas/escena08.py`, `render.py`, `salida/`.

## Forma de trabajar
1. Lee `visuales.md` y el guion. Revisa qué audios e imágenes existen y dime qué falta antes de empezar.
2. Haz solo la escena 1. Antes del render completo, guarda 4 fotogramas clave en `revision/` y pídeme que los revise. No sigas hasta que te diga que sí.
3. Después renderiza la escena 1 completa en `salida/escena01.mp4`.
4. Cuando la apruebe, seguimos escena por escena hasta el video final `salida/video_completo.mp4`.
5. Si vuelvo a grabar un audio, solo debe hacer falta volver a renderizar esa subescena y volver a unir.
