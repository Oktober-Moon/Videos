# Videos

Motor y guías para hacer videos narrados con el estilo de los que se hicieron para el Tec: el de
**Toledo** («Forense digital en dispositivos móviles e IoT») y los de **Luna** (los videos de las
materias). Todo se hace con código: Python y ffmpeg para la imagen y el sonido, Blender para los planos
3D y la voz de Eduardo clonada en ElevenLabs para la narración.

## Qué hay aquí

| Carpeta | Qué es |
|---|---|
| `toledo/` | El proyecto completo del video de Toledo, listo para copiarse como plantilla. Su `README.md` dice cómo se instala y se renderiza. |
| `toledo/DECISIONES.md` | Las decisiones de estilo, audio, imágenes y formato técnico de ese video. |
| `toledo/direccion_visual.md` | Las decisiones de estilo acumuladas, en el orden en que se tomaron. |
| `toledo/visuales.md` | Qué se ve en cada subescena, sus fotos, efectos de sonido y paletas: el ejemplo de cómo se describe un video. |
| `toledo/instrucciones_originales.md` | El encargo original del video, como lo escribió Eduardo. |
| `toledo/_archivo_cesar/` | El motor anterior (video del cifrado César, cancelado): siluetas de papel, niebla y subtítulos. Sólo de consulta. |
| `luna/ESTILO.md` | El estilo de los videos de las materias: cómo se escribe el guion, la edición y las animaciones. |
| `luna/guiones-unidad-3/` | Los cuatro guiones de la unidad 3, ejemplos del formato de guion para narrar. |

## Cómo se hace un video nuevo

1. **Se copia `toledo/`** a una carpeta nueva con el nombre del video. Toledo es la plantilla: su
   motor (`render.py`, `escenas/base.py`, `graficos.py`, `cine.py`, `atmosfera.py`, `sfx.py`, `tres_d/`)
   sirve tal cual; lo que es propio de Toledo son las escenas (`escenas/escenaNN.py` y sus piezas), los
   planos 3D de cada escena (`tres_d/planos_eNN.py` y los lugares) y las paletas (`paletas.py`).
2. **Se escribe el guion**, en Word, con escenas y subescenas («Escena 1.1:», «Escena 1.2:»…), como el
   de Toledo. `guion.py` lo lee y lo parte en escenas, subescenas, oraciones y pausas. La forma de
   escribirlo para el oído está en `luna/ESTILO.md` («El guion»).
3. **Se describe lo que se ve**, en un `visuales.md` como el de Toledo: qué pasa en cada subescena, qué
   fotos van, qué efectos de sonido y qué paleta tiene cada lugar. Las decisiones que valen para todo el
   video van en su `DECISIONES.md`.
4. **Se programan las escenas**, una por archivo en `escenas/`, con las piezas comunes de
   `escenas/base.py` (tiempos que manda el audio, fotos con movimiento de cámara, textos, tarjeta de
   título) y los planos 3D en `tres_d/`.
5. **Se genera la narración** con la voz clonada (ver abajo) y se deja un audio por subescena en
   `audios/`. La duración de cada clip la manda su audio.
6. **Se renderiza** escena por escena, revisando primero los fotogramas clave, y al final se une todo.
   Los comandos están en `toledo/README.md` («Renderizar»).

## La voz

La narración es la voz de Eduardo clonada en ElevenLabs (clon instantáneo). Las muestras con las que se
hizo el clon están en `toledo/voz/elevenlabs/` (`muestra_eduardo.mp3` y `muestra_eduardo_seria.mp3`), por
si hay que volver a crearlo. El modelo, los ajustes, cómo se arreglan las pausas y cómo se elige la mejor
de dos tomas están en `toledo/README.md` («Narración (ElevenLabs)»). La cadena de sonido que iguala la voz
clonada con el micrófono de sus grabaciones usa `toledo/voz/espectro_grabaciones.json`.

## Lo que no está en git

| Qué | Por qué | Dónde está |
|---|---|---|
| Los renders (`salida/`) y las revisiones | Se regeneran | Toledo: `Toledo.zip`. Luna: los cuatro videos de la unidad 3 en `Luna.zip` |
| La narración de Toledo (`audios/`, `audios_escenas/`) | Es de ese video y pesa 350 MB | `Toledo.zip` |
| Las fotos y clips reales de Toledo | Son de personas reales y de prensa, para uso escolar | `Toledo.zip`; sus fuentes, en `toledo/fuentes_imagenes.txt` |
| Los recursos 3D (texturas, cielo, personas de MakeHuman, captura de movimiento) | Pesan 600 MB y uno pasa del límite de 100 MB de GitHub; todos son públicos | Se bajan de los enlaces de `toledo/recursos_3d/LEEME.txt` |
| Los entornos de Python (`.venv`, `.venv-voz`) | Se recrean | Con `requirements.txt` y `requirements-voz.txt` (ver `toledo/README.md`) |

## Requisitos

Python, ffmpeg y Blender, en las versiones que dice `toledo/README.md` («Requisitos»).
