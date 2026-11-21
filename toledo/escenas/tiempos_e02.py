"""Inicio de cada oración en la narración de las escenas 2 y 4, medido palabra por palabra.

`escenas/base.tiempos` busca para cada oración el silencio más cercano a donde caería por número de
palabras. Con la voz de ElevenLabs eso falla a veces por uno o dos segundos: al procesarla
(`voz_elevenlabs.espaciar`) los silencios largos no siempre quedan en los fines de oración, y dos
oraciones cortas seguidas pueden caer en el mismo silencio (en la 2.0, «Tiene un iPhone.» y «Y se
niega a dar la contraseña.» empezaban juntas). Como cada imagen entra cuando la voz la nombra, aquí se
usan los inicios medidos con Whisper (tiempos por palabra) sobre esos mismos audios.

Cada medición va con la huella del audio que se midió (sus muestras, no su fecha): si el audio cambia
(se vuelve a generar una subescena), la huella ya no coincide y se usan los tiempos de `base`, que se
reacomodan solos. Para medir de nuevo: `medir()` con Whisper y pegar el resultado en `MEDIDOS`.
"""

from __future__ import annotations

import dataclasses
import functools
import hashlib

import numpy as np

from escenas import base

# id: (huella del audio, inicio de cada oración en segundos)
MEDIDOS: dict[str, tuple[str, tuple[float, ...]]] = {
    "2.0": ("95f0a2b4e298", (0.0, 5.61, 9.55, 11.63, 17.77, 20.75, 25.99, 26.59)),
    "2.1": ("46cb4bc5f4fd", (0.0, 3.05, 7.69, 12.53, 16.51)),
    "2.2": ("c42788940865", (0.0, 3.69, 11.26, 18.08, 23.37, 26.23, 36.93, 44.29, 53.07)),
    "2.3": ("02e753c4c615", (0.0, 2.3, 10.97, 14.63, 18.24, 24.98, 28.04)),
    "2.4": ("0340c0193d58", (0.0, 6.75, 9.78, 12.85, 16.92)),
    "2.5": ("40473a0b580f", (0.0, 5.55, 6.85, 13.11, 16.68, 21.43)),
    "2.6": ("b33f8ebdd664", (0.0, 5.78, 9.28, 11.29, 15.33, 22.25, 26.79)),
    "2.7": ("1ce1f5501e53", (0.0, 1.69, 3.86, 7.33, 14.29)),
    "2.8": ("f5ef0921bd5b", (0.0, 3.19, 5.64, 8.96, 11.21, 13.76, 15.62, 16.75, 18.85, 21.73, 26.58)),
    "2.9": ("87625ac6b45d", (0.0, 8.76, 16.08, 19.83, 22.01)),
    "2.10": ("3fc2561a4a88", (0.0, 4.77, 10.92, 17.35, 19.75, 25.89, 28.9, 37.37)),
    "4.0": ("8b19b0555883", (0.0, 1.58, 6.28, 9.35, 11.41, 16.86)),
    "4.1": ("b093b3d6f946", (0.0, 4.99, 10.05, 14.09, 21.37)),
    "4.2": ("f0c1e5bfbea6", (0.0, 5.47, 9.63, 14.82, 18.35, 26.81, 29.43, 36.85)),
    "4.3": ("6f486cd37961", (0.0, 6.03, 12.02, 15.76)),
    "4.4": ("ee8550f76bea", (0.0, 2.61, 8.31, 10.53, 14.93)),
    "4.5": ("4dd0dcf7f905", (0.0, 5.03, 6.19, 8.57, 15.04)),
    "4.6": ("550e4665b639", (0.0, 1.85, 8.78, 11.35, 13.7, 22.15, 25.48, 37.01, 38.07)),
    "4.7": ("56ff5b67c401", (0.0, 1.87, 9.25, 11.29, 16.16, 22.87, 29.41)),
}


@functools.lru_cache(maxsize=None)
def huella(id_: str) -> str | None:
    ruta = base.ruta_audio(id_)
    if ruta is None:
        return None
    x = base.leer_audio(ruta)
    return hashlib.sha1(np.round(x[:, 0] * 32767).astype(np.int16).tobytes()).hexdigest()[:12]


def tiempos(id_: str) -> base.Tiempos:
    T = base.tiempos(id_)
    medido = MEDIDOS.get(id_)
    if medido is None or medido[0] != huella(id_) or len(medido[1]) != len(T.oraciones):
        return T
    return dataclasses.replace(T, oraciones=list(medido[1]))


def medir(ids, modelo="medium") -> dict:
    """Mide con Whisper (faster-whisper, en CPU) el inicio de cada oración de `ids`. Devuelve el
    diccionario para `MEDIDOS`. Tarda varios minutos por subescena."""
    import re
    import unicodedata

    from faster_whisper import WhisperModel

    import guion

    def norm(w):
        w = unicodedata.normalize("NFD", w.lower())
        return re.sub(r"[^a-z0-9]", "", "".join(c for c in w if unicodedata.category(c) != "Mn"))

    m = WhisperModel(modelo, device="cpu", compute_type="int8")
    salida = {}
    for id_ in ids:
        x = base.leer_audio(base.ruta_audio(id_))[:, 0][::3].copy()            # 48 kHz -> 16 kHz
        segs, _ = m.transcribe(x, language="es", word_timestamps=True, vad_filter=False,
                               condition_on_previous_text=False, beam_size=5)
        palabras = [(w.word, w.start) for s in segs for w in s.words]
        salida[id_] = (huella(id_), inicios(guion.subescena(id_, hablado=True).oraciones, palabras, norm))
    return salida


def inicios(oraciones, palabras, norm) -> tuple[float, ...]:
    """Inicio de cada oración: el de su primera palabra reconocida (alineando el texto del guion con
    lo que oyó Whisper)."""
    from difflib import SequenceMatcher

    toks, primero = [], []
    for o in oraciones:
        primero.append(len(toks))
        toks += [norm(x) for x in o.split() if norm(x)]
    oidas = [norm(w) for w, _ in palabras]
    mapa = {}
    for a, b, n in SequenceMatcher(None, toks, oidas, autojunk=False).get_matching_blocks():
        for i in range(n):
            mapa[a + i] = b + i
    res = []
    for k, p in enumerate(primero):
        fin = primero[k + 1] if k + 1 < len(primero) else len(toks)
        q = next((mapa[i] for i in range(p, fin) if i in mapa), None)
        if q is None:
            res.append(None)
            continue
        desfase = sum(1 for i in range(p, fin) if i not in mapa and i < next(j for j in range(p, fin) if j in mapa))
        res.append(max(0.0, palabras[q][1] - 0.35 * desfase - 0.05))
    for k in range(len(res)):                                               # huecos: a mitad de camino
        if res[k] is None:
            a = res[k - 1] if k else 0.0
            b = next((v for v in res[k + 1:] if v is not None), a + 2.0)
            res[k] = (a + b) / 2
    res[0] = 0.0 if res[0] < 0.5 else res[0]
    return tuple(round(float(v), 2) for v in res)
