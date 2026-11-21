"""Efectos de sonido de la escena 4 sintetizados con las piezas de `sfx.py` (numpy y scipy): pájaros en
la orilla, pasos en asfalto y en tierra, el murmullo de una sala, el escáner de huellas, el mazo del
juez y un tono que sube. Todo sale normalizado; la mezcla lo deja 15 dB debajo de la voz."""

from __future__ import annotations

import math

import numpy as np

from sfx import SR, estereo, filtro, fundidos, lfo_suave, normalizar_pico, reverberacion, ruido_rosa


def _rng(semilla: int) -> np.random.Generator:
    return np.random.default_rng(semilla)


def _n(seg: float) -> int:
    return int(round(seg * SR))


def _en(salida: np.ndarray, t: float, x: np.ndarray, g: float = 1.0) -> None:
    i = _n(t)
    if 0 <= i < len(salida):
        trozo = x[: len(salida) - i]
        salida[i : i + len(trozo)] += trozo * g


def pajaros(dur: float, semilla: int = 401, densidad: float = 0.8) -> np.ndarray:
    """Pájaros lejanos en los árboles de la orilla: trinos cortos (glisandos agudos con vibrato), en
    grupos, a izquierda y derecha."""
    rng = _rng(semilla)
    salida = np.zeros((_n(dur), 2), np.float32)
    t = rng.uniform(0.2, 1.0)
    while t < dur - 0.5:
        pan = rng.uniform(-0.8, 0.8)
        lejos = rng.uniform(0.25, 1.0)
        for _ in range(rng.integers(2, 6)):                       # una frase de varias notas
            largo = rng.uniform(0.04, 0.14)
            tt = np.arange(_n(largo)) / SR
            f0, f1 = rng.uniform(2800, 5200), rng.uniform(2600, 6200)
            f = f0 + (f1 - f0) * tt / largo + 180 * np.sin(2 * math.pi * rng.uniform(25, 60) * tt)
            nota = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / largo) ** 1.5
            _en(salida, t, estereo(nota * lejos, pan))
            t += largo + rng.uniform(0.02, 0.09)
        t += rng.exponential(1.4 / densidad)
    salida = reverberacion(salida, 1.6, 0.35, 7000, semilla)[: len(salida)]
    return fundidos(normalizar_pico(salida), 0.5, 0.8)


def pasos(tiempos: list[float], dur: float, semilla: int = 402, suelo: str = "asfalto") -> np.ndarray:
    """Pasos en cada instante: un golpe sordo del talón y el roce de la suela; en tierra, con
    crujido de grava."""
    rng = _rng(semilla)
    salida = np.zeros((_n(dur), 2), np.float32)
    largo = _n(0.22)
    tt = np.arange(largo) / SR
    for k, tp in enumerate(tiempos):
        talon = np.sin(2 * math.pi * rng.uniform(70, 95) * tt) * np.exp(-tt / 0.03)
        roce = filtro(rng.standard_normal(largo), "bandpass", (500, 3500) if suelo == "asfalto" else (900, 6000), 2)
        roce *= np.exp(-tt / (0.05 if suelo == "asfalto" else 0.09))
        x = talon * 0.7 + roce * (0.35 if suelo == "asfalto" else 0.6)
        if suelo == "tierra":
            for _ in range(rng.integers(3, 8)):                       # piedritas
                i = rng.integers(0, largo - _n(0.01))
                x[i : i + _n(0.004)] += rng.standard_normal(_n(0.004)) * rng.uniform(0.2, 0.6)
        _en(salida, tp, estereo(x * rng.uniform(0.7, 1.0), 0.15 if k % 2 else -0.15))
    return normalizar_pico(reverberacion(salida, 0.5, 0.1, 5000, semilla)[: len(salida)])


def murmullo(dur: float, semilla: int = 403) -> np.ndarray:
    """Murmullo de una sala llena antes de empezar: voces sin palabras (ruido con formantes que
    cambian), alguna tos lejana, todo con eco de sala grande."""
    rng = _rng(semilla)
    n = _n(dur)
    x = np.zeros(n)
    for k in range(9):                                                # nueve voces de fondo
        base = filtro(ruido_rosa(n, rng), "bandpass", (rng.uniform(250, 450), rng.uniform(1200, 2400)), 2)
        silabas = lfo_suave(n, rng, rng.uniform(3.0, 5.0), 0.0, 1.0) ** 2
        frases = lfo_suave(n, rng, 0.3, 0.0, 1.0)
        x += base * silabas * (frases > 0.45)
    y = estereo(x * 0.3, 0.0)
    y[:, 0] *= 0.9
    for _ in range(int(dur / 4)):
        tt = np.arange(_n(0.25)) / SR
        tos = filtro(rng.standard_normal(len(tt)), "bandpass", (300, 2000), 2) * np.exp(-tt / 0.06)
        _en(y, rng.uniform(0.5, max(0.6, dur - 0.5)), estereo(tos * 0.4, rng.uniform(-0.7, 0.7)))
    return fundidos(normalizar_pico(reverberacion(y, 2.2, 0.45, 4000, semilla)[:n]), 1.0, 1.0)


def escaner(semilla: int = 404, dur: float = 1.6) -> np.ndarray:
    """Escáner de huellas: un barrido de luz con zumbido que sube y un pitido corto de lectura."""
    n = _n(dur)
    t = np.arange(n) / SR
    zumbido = np.sin(2 * math.pi * (180 + 260 * t / dur) * t) * 0.35
    rng = _rng(semilla)
    aire = filtro(rng.standard_normal(n), "bandpass", (1500, 5000), 2) * 0.08
    env = np.clip(t / 0.05, 0, 1) * np.clip((dur - 0.35 - t) / 0.1, 0, 1)
    x = (zumbido + aire) * env
    i = _n(dur - 0.3)
    tt = t[: n - i]
    x[i:] += np.sin(2 * math.pi * 2093 * tt) * np.exp(-tt / 0.08) * np.clip(tt / 0.005, 0, 1) * 0.6
    return normalizar_pico(reverberacion(estereo(x), 0.5, 0.12, 6000, semilla)[:n])


def mazo(semilla: int = 405) -> np.ndarray:
    """Mazo de juez sobre su base de madera: dos golpes secos con cuerpo de madera y eco de sala."""
    rng = _rng(semilla)
    n = _n(1.8)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for t0, amp in ((0.0, 1.0), (0.32, 0.8)):
        i = _n(t0)
        tt = t[: n - i]
        golpe = filtro(rng.standard_normal(len(tt)) * np.exp(-tt / 0.004), "bandpass", (600, 4000), 2)
        cuerpo = sum(a * np.sin(2 * math.pi * f * tt) * np.exp(-tt / d) for f, a, d in ((180, 1.0, 0.05), (410, 0.5, 0.03), (930, 0.3, 0.02)))
        x[i:] += (golpe * 0.8 + cuerpo) * amp
    return normalizar_pico(reverberacion(estereo(x), 1.4, 0.3, 4000, semilla)[:n], 0.6)


def tono_sube(dur: float = 2.2, semilla: int = 406) -> np.ndarray:
    """Tono suave que sube (cada piso que se sube), redondo y sin ataque."""
    n = _n(dur)
    t = np.arange(n) / SR
    f = 330 * 2 ** (t / dur)
    x = np.sin(2 * math.pi * np.cumsum(f) / SR) + 0.25 * np.sin(4 * math.pi * np.cumsum(f) / SR)
    x *= np.sin(np.pi * t / dur) ** 1.2
    return normalizar_pico(reverberacion(estereo(x * 0.6), 1.0, 0.3, 5000, semilla)[:n], 0.5)


def silbido_aire(dur: float, semilla: int = 407) -> np.ndarray:
    """Aire que pasa: viento muy suave y agudo (la columna de aire sobre la persona)."""
    rng = _rng(semilla)
    n = _n(dur)
    x = filtro(ruido_rosa(n, rng), "bandpass", (300, 2500), 2) * (0.5 + 0.5 * lfo_suave(n, rng, 0.2))
    return fundidos(normalizar_pico(estereo(x)), 1.0, 1.0)
