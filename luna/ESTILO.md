# Estilo de los videos de las materias (Luna)

Los videos de las materias del Tec se hicieron en dos tandas, con el mismo tono pero distinto montaje:

- **Unidades 1 y 2** (octubre de 2026): un video por materia, de unos 11 minutos. Eduardo sale a cámara
  un rato y el resto es su voz grabada con gráficos animados y capturas de pantalla encima. Se montaron
  con Remotion.
- **Unidad 3** (noviembre de 2026): un video por materia, de 7 a 9 minutos, narrado con su voz clonada
  en ElevenLabs y hecho con el motor de Toledo (escenas, planos 3D y gráficos con código).

El código de las dos tandas ya no existe (las carpetas `_videos` y `_videos_u3` se borraron). Lo que
sigue es el estilo, para repetirlo con el motor de `toledo/`.

## El guion

Se escribe para el oído, como una exposición frente al grupo:

- **Primera persona y registro de clase.** «Buenos días, soy Eduardo y hoy presentaré lo que aprendí en
  la unidad 3 de la materia…», «Comenzaré con…», «El segundo subtema fue…», «Ahora pasaré a…», «Para
  terminar, presentaré mis conclusiones», «Gracias por su atención». Nada de hablarle de tú al
  espectador («te cuento», «tienes que»), ganchos («Quédate con…»), muletillas («Fíjate», «Ojo»),
  preguntas de suspenso ni «Gracias por ver»: cada idea se afirma.
- **Oraciones completas y encadenadas.** Lo que describe a lo anterior va con «que», «el cual» o coma,
  no en oración nueva («…un proyecto real, el cual es Okári, un sistema para…»). Sin dos puntos que
  anuncian: «Lo que el proyecto tiene como objetivo es que…».
- **Palabras de todos los días.** El nombre de cada tema se dice como viene en la materia y enseguida se
  explica con palabras comunes («El triaje es la revisión que dice qué tan grave viene el paciente»).
- **Conectores** que unen cada idea con la anterior: «además», «por eso», «sin embargo», «entonces»,
  «o sea», «aun así». Sin «básicamente», «realmente» ni «muy».
- **Sin palabras que se atoran** al decirlas: «se anote por completo», no «quede anotado completo».
- **Cada corrección se aplica a todo el guion**, no sólo al renglón señalado: de cada una se saca la
  regla y se revisa el guion entero.

### Formato del guion de la unidad 3 (el que usa el motor)

Es el formato de los guiones de `guiones-unidad-3/`:

- Archivo `.md`, con `# Guion: …`, `## Escena N. Título (m:ss – m:ss)` y `**Escena N.M:**` para cada
  subescena; un renglón por oración y `(pausa)` en su propio renglón.
- **La pronunciación va escrita en la palabra**, no entre paréntesis: el término se escribe como se dice,
  con tilde en la vocal que carga aunque la ortografía no la pida (OKARI → Okári; COBIT → Kóbit; Java →
  Yáva; JSON → Yéison; Remote Method Invocation → Rimóut Métod Invokéishon). Las siglas que se deletrean
  van en una palabra, con tilde en la letra que carga (TI → Teí, RMI → Erremeí, HTTP → Achetetepé, SQL →
  Esecuéle, SQA → Esecuá). Los títulos de escena conservan el nombre oficial.
- Sin emojis ni negritas en el texto narrado.
- Tiempos calculados a 140 palabras por minuto, sin contar la pronunciación, y 1.5 s por pausa.

En los guiones de las unidades 1 y 2 (para grabarse con teleprompter), cada salto de renglón era una
pausa, la negrita marcaba el énfasis y cada bloque llevaba «Dices:» y «En pantalla:» con [Gráfico],
[Captura] o [Stock] anclado a una frase.

## Lo que se ve

- **Las ideas se actúan, no se escriben.** Las tarjetas de texto animadas no bastan: cada escena es una
  ilustración donde las piezas (un cilindro de base de datos, hospitales, un documento con secciones,
  paquetes, tablas, un candado, un escudo, un cronómetro…) hacen lo que se dice en el momento en que se
  dice. La fuente de cada escena es lo que el guion pide que se vea.
- **Cinco técnicas de animación:** texto con máscara, movimientos encadenados, cámara que sigue lo
  importante, un objeto que se transforma en el de la escena siguiente y entradas o énfasis sincronizados
  con la voz.
- **Piezas grandes** (texto de 26 px o más en un escenario de 1680×620). Una escena no pasa más de un
  segundo con sólo el título: lo que se nombra después entra tenue y late al nombrarse.
- **Entre dos gráficos seguidos el fondo se queda**, para que no se asome otra cosa medio segundo.
- **Identidad visual propia de cada proyecto**, no la de la referencia: de un video de referencia se
  toma el *cómo* (ritmo, técnicas), nunca su estilo (colores, rótulos). Para OKARI fue azul noche, acento
  azul acero, vidrio y las fuentes Outfit e Inter.
- **Capturas de pantalla fijas**, a 2x, con el encuadre y las marcas medidas; la cámara va de marca en
  marca y nunca deja ver datos sensibles ni rótulos de desarrollo.
- **Un solo estilo de subtítulo**; las palabras clave, más grandes y en el color de acento.
- **Color:** sólo contraste y brillo; más saturación se ve falso.

## El sonido

- Voz aislada y masterizada a −16 LUFS (unidades 1 y 2) o la cadena de la voz clonada de Toledo
  (unidad 3, ver `../toledo/README.md`).
- Para el audio tipo pódcast: ecualización, de-esser y compresión (rango de sonoridad de 7).
- Con voz grabada, los tropiezos y las frases dichas dos veces se cortan quedándose con la última, y los
  cortes se hacen por tramos de energía de la voz, no por los tiempos de palabra de Whisper (que llegan
  tarde y se comen palabras).

## Unidades 1 y 2: grabación y montaje

- Las tomas a cámara se graban leyendo, y la mirada se corrige a la cámara con NVIDIA Maxine Eye
  Contact al 100 %; si una mano cruza los ojos, ese tramo vuelve al original.
- Lo que se espera de unas grabaciones es el video editado completo: voz, corte base, gráficos,
  capturas, render y masterizado.
- Codificar con NVENC (`-rc constqp -qp 10/14`) en vez de libx264 bajó el render de unos 13 s a 1.5 s
  por segundo de video.
