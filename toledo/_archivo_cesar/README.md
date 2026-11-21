# El cifrado César y la criptografía básica dentro de la ingeniería social

Video narrado e ilustrado con código (Python + ffmpeg): siluetas tipo recorte de papel, niebla,
partículas, cámara lenta, cortes a negro, subtítulos en versalitas y efectos de sonido
sintetizados. No lleva música ni voz: la narración se graba aparte y se monta encima.

Hoy existe la **escena 1** (1:43,5, nueve planos).

## Requisitos

- Python 3.13 y ffmpeg en el `PATH` (en Windows: `winget install ffmpeg`).
- Dependencias de Python, en un entorno virtual dentro del proyecto:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

## Volver a renderizar

```bash
.venv/Scripts/python render.py
```

Genera en `salida/`:

| Archivo | Qué es |
|---|---|
| `escena01_prueba.mp4` | Video final: 1920×1080, 30 fps, H.264 CRF 18, yuv420p, audio AAC 48 kHz estéreo |
| `escena01_sfx.wav` | Solo los efectos, PCM 24 bits 48 kHz, para mezclar con la voz |
| `escena01.srt` | Subtítulos con los mismos tiempos que los quemados en el video |
| `planos/` | Un `.mp4` por plano; se unen con el demuxer concat y `-c copy` |

Otras formas de uso:

```bash
.venv/Scripts/python render.py --revision                 # solo los fotogramas de revision/
.venv/Scripts/python render.py --planos 6,8               # rehace esos planos y vuelve a unir
.venv/Scripts/python render.py --audio                    # rehace efectos, .srt y la mezcla final
.venv/Scripts/python render.py --fotograma 6:4.2 --salida prueba.png   # un cuadro suelto
```

Los planos se renderizan en paralelo; con 12 hilos la escena completa tardó 23 minutos (el
plano más lento manda). Para probar un cambio conviene `--fotograma` o `--planos`.

## Cambiar los tiempos después de grabar la voz

Todos los tiempos están en un solo archivo: `escenas/escena01.json`. Basta con editarlo y
volver a correr `render.py`.

- `inicio` / `fin` de cada plano, en `m:ss.s` o en segundos. Cada plano empieza donde termina el
  anterior; si no coinciden, el render se detiene y dice cuál está mal.
- `marcas`: segundos **desde el inicio del plano**. Mueven a la vez la imagen y su efecto de
  sonido. Las del plano 6, por ejemplo: `alto` (el caballo se detiene), `lanzamiento` (whoosh),
  `impacto` (la lanza se clava), `lapso` (empieza el paso de los días), `soldado` y `cabeza`.
- `pausa_final`: segundos sin narración al final del plano.
- `subtitulos` (opcional): si los bloques automáticos no caen con la voz, se escriben a mano:

```json
"subtitulos": [
  { "desde": 0.3, "hasta": 2.6, "texto": "El jinete llega. No puede entrar. Lanza." },
  { "desde": 2.8, "hasta": 6.9, "texto": "La lanza se clava en una torre del campamento y ahí se queda." }
]
```

Sin esa lista, el texto del plano se reparte solo a `palabras_por_minuto` (170), en bloques de
dos líneas como máximo.

## Nivel de los efectos

La pista de efectos se normaliza a **−28 LUFS integrados**, con pico real por debajo de −6 dBTP:
queda unos 12 dB debajo de una voz masterizada a −16 LUFS. Si la voz se masteriza a −14 LUFS,
se cambia `LUFS_EFECTOS` a −26 en `render.py`.

## Organización

| Archivo | Para qué |
|---|---|
| `paletas.py` | Paletas de color de las ocho épocas y lugares del video |
| `graficos.py` | Motor común: ruido, texturas, cámara con paralaje, luces, acabado, texto |
| `siluetas.py` | Figuras en silueta (personas, caballo con galope, torres, empalizada, armas) |
| `anatomia.py` | Figuras anatómicas por campos de distancia: persona de perfil, caballo, mano en 3D; borde de contraluz y translucidez |
| `atmosfera.py` | Niebla, humo, brasas, polvo y llamas |
| `sfx.py` | Los diez efectos sintetizados y la mezcla con normalización |
| `subtitulos.py` | Reparto del texto, `.srt` y subtítulos quemados |
| `escenas/escena01.py` | Los nueve planos de la escena 1 y su pista de sonido |
| `escenas/escena01.json` | Tiempos, texto narrado y marcas de la escena 1 |
| `render.py` | Render en paralelo, audio y ensamblado con ffmpeg |
| `fuentes/` | Cinzel y EB Garamond (licencia OFL) |

Para una escena nueva se crea `escenas/escenaNN.py` con su `PLANOS` y `pista_sonido`, y su
`escenaNN.json`; se renderiza con `render.py --escena escenaNN`.

## Dos estilos de figura

Las figuras de `siluetas.py` son recortes de papel: cápsulas de grosor casi parejo. Las de
`anatomia.py` se arman con primitivas que siguen la forma de cada músculo (conos de radios
distintos, elipses, contornos de cabeza, pie y torso) unidas con un mínimo suave, de modo que
hombro, codo y rodilla se funden como en un cuerpo real. La mano es un modelo 3D de falanges
que se proyecta desde cualquier ángulo, y el caballo tiene la anatomía de un caballo de silla
(paletilla, anca, corvejón, menudillo, crin y cola en hebras).

El campo de distancia también ilumina: su gradiente da la normal del contorno, de donde sale el
borde dorado que mira al sol, y el espesor local deja pasar luz rojiza por orejas, dedos y tela.

El plano 4 usa las figuras anatómicas; la versión de recorte sigue en el código como
`Plano4Recorte` y se recupera poniendo `4: Plano4Recorte` en `PLANOS`.

## Fuentes

Cinzel y EB Garamond vienen de Google Fonts (licencia SIL Open Font License; los textos de la
licencia están en `fuentes/originales/`). Pillow no aplica funciones OpenType sin libraqm, así
que `fuentes/preparar_fuentes.py` crea una copia de EB Garamond con las versalitas ya fijadas
(`EBGaramond-Versalitas.ttf`) y las instancias estáticas de Cinzel. Solo hace falta correrlo si
se cambian las fuentes originales.

Todas las imágenes y todos los sonidos se generan con código; el proyecto no usa material de
terceros aparte de esas dos fuentes libres.
