# Dirección visual del video

Decisiones de estilo acumuladas, en orden. Lo que dice `instrucciones_originales.md` sigue valiendo salvo
donde este archivo lo cambia; ante una duda, manda lo más reciente.

## 1. Base (de `instrucciones_originales.md` y `visuales.md`)

- Video para exposición en clase, no se publica. Unos 35 minutos, 8 escenas, voz grabada por
  Eduardo (un audio por subescena); sin música, solo efectos sintetizados con numpy/scipy,
  unos 15 dB debajo de la voz, que bajan mientras habla y suben un poco en las pausas.
- Cada subescena dura lo que su audio más medio segundo. Cada escena abre con una tarjeta de
  título de 3 s sobre negro y un golpe grave.
- Paleta de color por lugar (Friburgo, San Bernardino, Apple, Android, Connecticut, laboratorio,
  Arkansas, cierre), en `paletas.py`.
- Textos en pantalla cortos (fechas, horas, cifras, nombres) en Inter.
- 1920×1080, 30 fps, H.264 yuv420p CRF 18, AAC 48 kHz estéreo; un clip por subescena unido con
  concat y `-c copy`; archivos temporales que solo se renombran si ffmpeg termina bien.
- Flujo: antes de renderizar una escena completa, fotogramas clave en `revision/` y esperar el
  visto bueno de Eduardo.

## 2. Fotos de personas y víctimas

- Fotos de personas (desde el 11 de noviembre de 2026): se buscan con el navegador, víctimas
  incluidas. Primero Commons y fotos oficiales de dominio público, después prensa (anotada como uso
  escolar). Van a `imagenes/candidatas/` y solo pasan a `imagenes/` cuando Eduardo aprueba cada una.
  No se toman de redes sociales (si una foto de prensa salió de una, se avisa); ante la duda de
  identidad, no se usa.
- Víctimas (María Ladenburger, Connie Dabate, Victor Collins): quietas o con movimiento muy lento,
  sin efectos bruscos ni sonidos fuertes encima. La violencia nunca se muestra: se sugiere con
  sombras, luces o el lugar vacío.

## 3. Enfoque realista (11 de noviembre de 2026; reemplaza la idea de pasar las fotos a ilustración)

- Lugares y objetos (río, tranvía, calles, patrullas, teclados, computadoras, placas de circuito):
  clips de video reales, en `clips_reales/`, con su fuente en `fuentes_imagenes.txt`.
- Los clips se bajan con el navegador desde las páginas normales de Pexels, Pixabay o Wikimedia
  Commons. Sin API ni claves (no hay cuenta de Pexels). Si una página pide verificación o no deja
  descargar, se pasa a otra; si un clip no aparece en ninguna, va a `faltantes.txt`.
- Ilustraciones dibujadas solo para los diagramas técnicos (y gráficos informativos como mapas,
  contadores o líneas de tiempo).
- Fotos fijas (sobre todo personas y lugares): movimiento de cámara 2.5D con parallax, con mapa de
  profundidad de Depth Anything V2 y personas recortadas con rembg, en vez de solo acercamientos.
- Todo corre en local: Depth Anything V2 (ONNX) y rembg instalados con pip; ningún servicio en línea.
- Acabado de cine en todo: grano de película suave, viñeta, corrección de color con la paleta de
  cada escena y desenfoque de profundidad.
- Diagramas técnicos: se quedan como están, con más acabado (sombras suaves, brillo y profundidad).
- Titulares, capturas de pantalla y documentos: se muestran como imagen real.

## 4. Animación 3D realista (11 de noviembre de 2026; reemplaza los clips y el parallax de la sección 3)

- La escena 1 realista con clips y fotos en parallax no era lo buscado: se pidió «una animación que
  sea realista, detallada». Se probaron tres estilos sobre el mismo plano (foto pintada y animada,
  3D en Blender, ilustración dibujada con código; en `revision/estilos/` y `pruebas_estilo/`) y se
  eligió el **3D en Blender**.
- Lugares, objetos y ambientes (calles, río, tranvía, cinta policial, bolsillos, teléfonos) se
  construyen en 3D con código (`tres_d/`), sin modelos descargados, y se renderizan con Eevee en la
  GPU. Cada plano 3D se guarda por cuadros y solo se vuelve a renderizar si cambia su escena o le
  falta duración.
- Siguen igual: mapas, rótulos, contadores y diagramas técnicos como gráficos; fotos de personas
  reales sin efectos (víctimas quietas o con acercamiento muy lento); titulares y documentos como
  imagen real; la violencia nunca se muestra; las personas no se modelan en 3D (se sugieren con
  luces, siluetas lejanas o el lugar vacío).
- Costo aceptado: unos 5 a 10 s de render por cuadro; una escena de un minuto tarda horas.

## 5. Realismo: texturas escaneadas, cielo real, Cycles y personas a distancia (12 de noviembre de 2026; ajusta la sección 4)

- Se probó cuánto más realista podía verse el 3D (`revision/realismo/`) y se adoptó para todo el
  video: las superficies llevan texturas escaneadas y la luz ambiente sale de un cielo fotográfico
  (HDRI), todo con licencia CC0 de ambientCG, en `recursos_3d/` con sus fuentes en `LEEME.txt`. La
  geometría sigue hecha con código (`tres_d/`); las texturas se proyectan desde la posición en el
  mundo (`tres_d/pbr.py`).
- Donde el cielo queda a la vista y la foto del HDRI no corresponde al lugar (una plaza con casas
  sobre una calle o un río), la cámara ve el degradado de cielo de `base.CIELOS` y la foto solo
  ilumina y se refleja (`hdri(..., fondo_camara=...)`).
- Motor **mixto** (decidido el 12 de noviembre de 2026 tras ver los mismos 4 fotogramas en los
  dos motores, `revision/escena01_cycles_vs_eevee.jpg`): **Cycles** (la luz se calcula rebote por
  rebote, como en una foto) solo donde se nota, como las calles mojadas de noche, donde el empedrado
  refleja los faroles; **Eevee**, con las mismas texturas, cielo y árboles, donde los dos se ven
  casi iguales (el río, el amanecer nublado, los primeros planos con el fondo desenfocado). Cada
  plano nuevo se prueba en los dos y se elige; el motor de cada plano va en el diccionario `MOTOR`
  de su escena. La exposición de cada motor se calibra aparte (Cycles dispersa más luz en la neblina).
- Árboles: copas hechas de miles de hojas sueltas (triángulos de 9 a 20 cm, translúcidas), no de
  esferas abolladas.
- Personas en 3D (MPFB, recursos CC0 de MakeHuman; `tres_d/persona.py`): **solo a distancia media,
  de espaldas o en silueta**; de cerca la cara, los ojos y el pelo se ven artificiales. Las víctimas
  nunca se hacen como personaje 3D. Esto reemplaza «las personas no se modelan en 3D» de la sección 4.
- Las personas se mueven con **captura de movimiento real** (grabaciones de gente real, de la base
  pública de Carnegie Mellon, en `recursos_3d/mocap/`), pasada al esqueleto de MPFB con
  `tres_d/mocap.py`; nunca con movimientos animados a mano, que se ven de muñeco de videojuego. Una
  caminata grabada dura unos 2 s: se repite su ciclo de dos pasos sumando el avance.
- Braceo (aprobado el 12 de noviembre de 2026 con `revision/realismo/caminata_perfil_antes_despues.mp4`):
  el brazo entero se balancea desde el hombro, como péndulo, con el codo apenas doblado. En
  la grabación usada (08_01) la persona doblaba el codo hasta 60° y el antebrazo subía casi
  horizontal: de espaldas parecía que solo se movía del codo a la mano («no se ve natural»). Se
  conserva el ritmo grabado y se cambia el reparto (`mocap.BRAZOS`): el vaivén del hombro ×1.2, el
  doblez del codo ×0.45 y los brazos un poco más pegados al cuerpo (×0.8). Las clavículas y los
  hombros de MPFB no se copian de la grabación (subían los hombros hasta las orejas) y las manos
  cuelgan con los dedos un poco cerrados.
- Postura: la columna, el cuello y la cabeza conservan la curva de reposo de MPFB (la espalda alta
  inclinada unos 17° hacia adelante) y solo reciben el giro de la grabación (`mocap.COLUMNA`).
  Alinearlas con las vértebras de la grabación, casi rectas, echaba el tronco atrás y sacaba el
  pecho (`revision/realismo/caminata_postura_antes_despues.mp4`). Un cuerpo más delgado casi no
  cambia la silueta: la define la chamarra.
- Costo medido el 12 de noviembre de 2026 en la laptop (RTX 3050, 4 GB), por cuadro a 1080p:
  Cycles tarda de 44 s (calle) a 85 s (río de noche con neblina); Eevee, unos 2.5 s. La escena 1
  (1,830 cuadros 3D) son unas 36 h en Cycles y poco más de 1 h en Eevee. Casi todo el costo de
  Cycles es la neblina (volúmenes): donde el fondo va desenfocado, las dos neblinas se juntan en un
  solo volumen uniforme (`_rio_de_noche(..., pareja=True)`), que cuesta menos de la mitad y se ve
  igual. Se probaron y descartaron, por perder calidad visible: el método de neblina por pasos
  (`volume_biased`; borra el cono de luz del faro), el umbral adaptable 0.04 y el eliminador de
  ruido OIDN (borronean el asfalto y manchan las luces). Cada plano guarda su exposición de Cycles
  y la de Eevee (`exposicion_eevee`), igualadas en brillo medio.
- Como la duración de cada plano sale del audio, el render completo de una escena conviene hacerlo
  con la voz ya grabada.
