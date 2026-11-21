# Forense digital en dispositivos móviles e IoT

Video narrado para exposición en clase (unos 35 minutos, 8 escenas): animación 3D realista hecha
con código en Blender (calles, río, tranvía, objetos), mapas, rótulos y diagramas animados, fotos
reales de las personas y efectos de sonido sintetizados. No lleva música. La narración es la voz
de Eduardo clonada en ElevenLabs, un archivo por subescena, y manda la duración de cada clip.

Las instrucciones del video están en `instrucciones_originales.md`; lo que se ve en cada subescena, sus fotos,
efectos y paletas, en `visuales.md`; el texto, en el guion de Word.

## Requisitos

- Python 3.13 y ffmpeg en el `PATH` (`winget install ffmpeg`).
- Blender 5.3 para los planos 3D. Se busca en
  `%LOCALAPPDATA%\Programs\Blender-5.3\ProgramFiles64Folder\Blender Foundation\Blender 5.3\blender.exe`;
  si está en otro lado, se indica con la variable de entorno `BLENDER`.
- Dependencias en el entorno virtual del proyecto:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

## Renderizar

```bash
.venv/Scripts/python render.py 1 --revision        # fotogramas clave en revision/
.venv/Scripts/python render.py 1 --3d              # solo los planos 3D (lo más lento; se puede cortar y seguir)
.venv/Scripts/python render.py 1                   # escena 1 completa -> salida/escena01.mp4
.venv/Scripts/python render.py 1 --clips 1.1       # rehace solo esa subescena y vuelve a unir
.venv/Scripts/python render.py 1 --audio           # rehace solo el sonido (voz nueva) y une
.venv/Scripts/python render.py --final             # une las escenas en salida/video_completo.mp4
.venv/Scripts/python render.py 1 --seguir          # sigue un render cortado: solo los clips que faltan
.venv/Scripts/python pausa_render.py --congelar    # congela los renders en curso (--reanudar los sigue)
```

Congelar deja cada render quieto en su cuadro, con la memoria ocupada. Apagar la computadora
también es seguro: los cuadros 3D y los clips terminados quedan guardados (un clip se escribe con su
nombre final solo cuando ffmpeg acaba bien). Al volver, se borran los `*.tmp.*` de `salida/clips/` y
se relanza cada escena con `--seguir`; el candado de Blender guarda el número de proceso de su dueño
y cuándo arrancó, así que uno que quedó de antes del apagado no bloquea nada.

Dos renders de la misma escena pueden correr a la vez sin pisarse: cada clip se reserva con un archivo
`salida/clips/escenaNN/<clip>.en_curso` que solo un proceso puede crear, y el otro lo salta. Para un
render de toda la noche, `pausa_render.py --despierta` evita que Windows se suspenda por inactividad
mientras haya renders (cerrar la tapa sí la suspende).

Al cambiar la voz de una subescena basta con dejar el archivo nuevo en `audios/` (por ejemplo
`audios/1.1.wav`) y correr `render.py 1 --clips 1.1`: la duración del clip pasa a ser la del audio
más medio segundo, y cada imagen se reacomoda sola en el silencio entre oraciones que le toca.
Sin audio, la duración se estima con el guion a 165 palabras por minuto.

## Narración (ElevenLabs)

Desde el 16 de noviembre de 2026 todo el guion, incluidas las subescenas que Eduardo ya había
grabado, se narra con su voz clonada en ElevenLabs (plan Creator, que él paga). Sus grabaciones
limpias se conservan en `audios_grabados/` (salida de `limpiar_audios.py`) y los originales en
`audios_originales/`, pero la narración ya no depende de ellas.

- **Voz:** «Eduardo», clon instantáneo hecho con `voz/elevenlabs/muestra_eduardo.mp3` (1 min 52 s de
  sus narraciones 2.2, 2.3 y 2.5).
- **Modelo y ajustes** (`voz_elevenlabs.py`, `MODELO` y `AJUSTES`): `eleven_multilingual_v2`,
  estabilidad 0.5, estilo 0.15, parecido 0.9, refuerzo de hablante, velocidad 0.9, español. v4 se
  descartó midiendo la 2.1 contra la grabada (`revision/voz/`): sonaba entusiasta (su tono sube y
  baja 77–89 Hz contra 16 de Eduardo) y metía suspiros entre frases (5 a 7 en 20 s). La primera
  pasada con estabilidad 0.8 y estilo 0 sonó «con el mismo tono en toda la narración»; la de 0.5/0.15
  tiene más énfasis sin respiraciones.
- **Pausas:** ElevenLabs casi no deja silencio entre oraciones (0.09–0.17 s contra 0.35–0.58 s de
  Eduardo). Al procesar, `espaciar` alarga los fines de oración a 0.38–0.55 s y las comas a
  0.16–0.24 s; cuántos hay de cada uno sale del texto, para no tocar silencios dentro de palabras.
- **Dos tomas y revisión automática:** cada subescena se genera dos veces (`voz/elevenlabs/tomas/`)
  y `revisar_voz.py` (Whisper en la GPU) mide en cada toma si dice todo el texto, si hay voz que no
  es palabra («mmm», bostezo), respiraciones y colas tras la última palabra
  (`voz/elevenlabs/revision.json`). `--elegir` se queda con la más limpia (`eleccion.json`) y al
  procesar se corta todo lo que sigue a la última palabra.
- **Cómo se genera:** con el conector oficial de ElevenLabs del asistente de código (OAuth, sin claves en la
  computadora), un nodo por subescena en el flujo «nA51rvpJL89PZzjRAI2z» de ElevenLabs, con el texto
  de `voz/elevenlabs/textos.json`. Los MP3 se guardan en `voz/elevenlabs/crudas/` y se procesan aquí:

```bash
.venv-voz/Scripts/python voz_elevenlabs.py --textos           # texto de cada subescena como se dice
.venv/Scripts/python revisar_voz.py "voz/elevenlabs/tomas/*.mp3"   # (con torch/lib de .venv-voz en el PATH)
.venv-voz/Scripts/python voz_elevenlabs.py --elegir           # la mejor toma de cada subescena -> crudas/
.venv-voz/Scripts/python voz_elevenlabs.py --procesar         # crudas -> audios/<id>.wav (para el render)
.venv-voz/Scripts/python voz_elevenlabs.py --escenas          # audios_escenas/escena01.wav … escena08.wav
```

La entrega de la narración es un audio por escena (`audios_escenas/`), con 1 s entre subescenas; los
audios por subescena de `audios/` son los que usa el render para sincronizar las imágenes.

El texto lleva cada nombre como se pronuncia según el guion, las cifras en palabras, las siglas
letra por letra y una pausa de 1.2 s en cada «(pausa)». Al procesar, cada audio se recorta y pasa
por la cadena de las grabaciones (`limpiar_audios.py --clonada`: compuerta, nivelación, tono de
micrófono de las grabaciones, −18 LUFS). El tono de micrófono es el espectro mediano de
`audios_grabados/`, guardado en `voz/espectro_grabaciones.json`; si las grabaciones no están, se usa
ese archivo. Cada audio queda anotado en `audios/GENERADOS.txt`.

## Voz clonada local

**Probada y descartada el 15 de noviembre de 2026**: con la 2.1 junto a la grabada
(`revision/voz/`), ninguna versión sonó a Eduardo ni con acento mexicano natural: Chatterbox
multilingüe, su versión afinada para México con huella promedio e igualación de sonido, F5-TTS
español (referencia limpia y original) y la conversión de voz de Seed-VC v2 con acento (la técnica
de los covers con IA), tanto sobre voz generada como sobre una narración humana real. Entrenar un
modelo con su voz (RVC) pide 8 GB de GPU y 10 minutos de audio (hay 4 GB y 6.5 min) y no se usan
servicios en línea; la narración se graba. Lo que sigue queda como referencia.

Las subescenas sin grabar se pueden narrar con la voz de Eduardo clonada en local (`voz.py`, con
Chatterbox Multilingual de Resemble AI en su versión afinada para el español de México y
Latinoamérica, licencia MIT). Los pesos se bajan una vez; después nada sale de la computadora. Corre
en su propio entorno, `.venv-voz` (instrucciones en `requirements-voz.txt`):

```bash
.venv-voz/Scripts/python voz.py --bajar                # una sola vez: los pesos del modelo (unos 3.2 GB)
.venv-voz/Scripts/python voz.py --muestra              # 12 s de habla continua de las grabaciones -> voz/muestra.wav
.venv-voz/Scripts/python voz.py --prueba 2.1           # revision/voz/2.1_clonada_mexico.wav, para comparar con la grabada
.venv-voz/Scripts/python voz.py --texto 3.6            # solo muestra lo que se diría
.venv-voz/Scripts/python voz.py --faltantes            # genera en audios/ todo lo que no tiene audio
```

El texto sale del guion de Word con cada nombre escrito como se pronuncia (lo que va entre
paréntesis), las cifras en palabras, las siglas e inglés según la tabla `PRONUNCIA` de `voz.py`
y con seseo («celdas» se le pasa como «seldas»): el modelo multilingüe general aprendió el
español sobre todo de España y, si ve una c ante e/i o una z, la pronuncia con la «z» española.
Se genera oración por oración, con silencios cortos entre oraciones y largos en cada «(pausa)».
Quién habla lo define una huella de voz promediada sobre todas las grabaciones (`voz/huella.npz`,
se rehace sola si cambia una grabación); la muestra de 12 s pone el estilo. Lo que sale del modelo
se guarda en `voz/crudas/` y pasa por la misma cadena que las grabaciones
(`limpiar_audios.py --clonada`): compuerta, nivelación, el tono de micrófono de las grabaciones y
−18 LUFS, para que una subescena grabada y una clonada seguidas suenen igual.
Una grabación de Eduardo nunca se sobrescribe; cada audio generado queda anotado en
`audios/GENERADOS.txt`. En esta laptop tarda unas 11 veces lo que dura el audio (un minuto de
narración, unos 11 minutos).

## Planos 3D

Cada plano 3D se arma con código en el archivo de planos de su escena (`tres_d/planos.py` para la
escena 1; `tres_d/planos_e02.py` … `planos_e08.py` para las demás, así varias escenas se escriben a
la vez sin pisarse) y se renderiza en la GPU a `salida/3d/<plano>_<huella>/`, un PNG por cuadro. Los
nombres de plano no se repiten entre archivos; `escenas/plano3d.py` encuentra solo en cuál está.
La huella resume el código del que depende ese plano (su función, las auxiliares de su archivo y
los módulos de `tres_d/` que importan), sus parámetros, su motor y su duración: mientras no cambien,
el plano no se vuelve a renderizar.

Blender corre de a uno (4 GB de GPU): el candado `salida/3d/.blender.lock` guarda el número de
proceso de quien renderiza y solo se libera solo si ese proceso ya no existe. Un plano completo se
renderiza por tandas de 10 a 15 minutos (300 cuadros en Eevee, 12 en Cycles) y suelta el candado
entre una y otra, para que un fotograma de revisión no espere horas. Si cambia algo (por ejemplo, la
duración porque llegó la voz), se renderiza de nuevo y la versión vieja se borra. Para la revisión
se renderizan solo los cuadros pedidos. En esta laptop (RTX 3050) cada cuadro tarda de 44 a 85 s
en Cycles y unos 2.5 s en Eevee; el motor de cada plano se elige en el diccionario `MOTOR` de su escena
(`escenas/escena01.py`).

Las texturas escaneadas y los cielos (HDRI) están en `recursos_3d/`, con sus fuentes en
`recursos_3d/LEEME.txt`. Las personas en 3D usan la extensión MPFB de Blender con los recursos de
MakeHuman (los dos archivos están en `recursos_3d/mpfb/`); por eso Blender se abre sin
`--factory-startup`.

## Sonido

La voz se normaliza a −16 LUFS; los efectos quedan 15 dB debajo y bajan otros 6 dB mientras se
habla, así en las pausas suben solos. El pico real queda por debajo de −1 dBTP. Cada clip guarda su
sonido en PCM y se codifica a AAC una sola vez por escena, para que no queden huecos al unir.

## Cifras en pantalla

Es un documental de casos reales: una hora, un monto o un contador en pantalla se lee como prueba.
Por eso solo se muestran cifras que dice la narración; si una gráfica necesita forma, lleva solo los
puntos documentados, y lo genérico (un volcado hexadecimal, una IP de ejemplo) se rotula como
ejemplo. Antes de renderizar una escena:

```bash
.venv/Scripts/python revisar_cifras.py 3        # sale con 1 si hay cifras que el guion no dice
```

## Fotos

- `imagenes/`: las fotos reales, con el nombre que indica `visuales.md`.
- `fuentes_imagenes.txt`: de dónde salió cada foto, su autor y su licencia.
- `faltantes.txt`: lo que falta. Mientras falte, el video pone una ilustración en su lugar; al
  copiar la foto con el nombre exacto basta volver a renderizar esa subescena.
- Las fotos de las víctimas van sin tinte ni efectos, quietas o con un acercamiento muy lento.

## Organización

| Archivo | Para qué |
|---|---|
| `paletas.py` | Colores de cada lugar (Friburgo, San Bernardino, Apple, Android, Connecticut, laboratorio, Arkansas) |
| `guion.py` | Lee el guion de Word: escenas, subescenas, oraciones y pausas |
| `escenas/base.py` | Tiempos que manda el audio, fotos con movimiento, textos, tarjeta de título |
| `escenas/escena01.py` … `escena08.py` | Una escena cada uno (una clase por subescena); sus piezas propias van en `escenas/*_eNN.py` |
| `tres_d/planos_eNN.py` | Planos 3D de cada escena, con sus objetos en `tres_d/*_eNN.py` (la casa de los Dabate, `casa_e05.py`, la usan la 5, la 6 y la 8) |
| `revisar_cifras.py` | Revisor: toda cifra en pantalla debe estar en el guion (con cifras o con letras); las genéricas van en `PERMITIDAS` con su razón |
| `escenas/plano3d.py` | Planos de Blender vistos como clips: caché por huella y render de lo que falte |
| `tres_d/` | Escenas 3D con código: calle y tranvía, río Dreisam, bolsillo, cielos, neblina, cámara |
| `pruebas_estilo/` | La comparación de estilos que llevó a elegir el 3D (resultados en `revision/estilos/`) |
| `graficos.py`, `atmosfera.py`, `dibujo.py` | Motor de imagen: ruido, luces, acabado, niebla, partículas, dibujo vectorial |
| `sfx.py` | Efectos de sonido sintetizados y su mezcla bajo la voz |
| `render.py` | Clips en paralelo, unión por escena y video final |
| `fuentes/` | Inter (licencia OFL) y las fuentes del proyecto anterior |
| `_archivo_cesar/` | Proyecto anterior (video del cifrado César), sin uso |

El motor de imagen y de sonido viene del proyecto del cifrado César (`_archivo_cesar/`); aquí se
dejó solo lo general.
