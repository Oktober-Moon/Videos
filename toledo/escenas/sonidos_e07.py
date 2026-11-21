"""Efectos de sonido sintetizados de las escenas 7 y 8, hechos con las piezas de `sfx.py`: chispa
eléctrica suave, cautín sobre la soldadura, estación de aire caliente, clic de pinzas, programador
que lee, burbujas de la tina, tono de activación de la bocina, agua que corre por la tubería, mazo de
juez y el aire quieto de una noche fría.

Cada función devuelve float32 estéreo (muestras, 2) a 48 kHz con picos cerca de 0.5.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

import sfx
from sfx import SR, estereo, filtro, filtro_variable, fundidos, lfo_suave, normalizar_pico, reverberacion, ruido_rosa


def _n(seg: float) -> int:
    return int(round(seg * SR))


def chispa(semilla: int = 71) -> np.ndarray:
    """Chispa eléctrica suave: un chasquido corto con chisporroteo y un zumbido que se apaga."""
    rng = np.random.default_rng(semilla)
    n = _n(0.9)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for _ in range(14):
        i = int(rng.uniform(0, 0.18) * SR)
        largo = _n(rng.uniform(0.002, 0.008))
        x[i : i + largo] += rng.standard_normal(largo) * rng.uniform(0.3, 1.0)
    x = filtro(x, "highpass", 2500, 2)
    zumbido = np.sin(2 * math.pi * 120 * t) * 0.15 * np.exp(-t / 0.25) + np.sin(2 * math.pi * 1900 * t) * 0.05 * np.exp(-t / 0.1)
    return normalizar_pico(reverberacion(estereo(x + zumbido, 0.1), 0.4, 0.12, 7000, semilla)[:n], 0.5)


def cautin(dur: float = 2.2, semilla: int = 72) -> np.ndarray:
    """La punta del cautín sobre la soldadura: el siseo del fundente y sus chasquidos finos."""
    rng = np.random.default_rng(semilla)
    n = _n(dur)
    t = np.arange(n) / SR
    siseo = filtro_variable(ruido_rosa(n, rng), 4200 + 1500 * lfo_suave(n, rng, 3.0), 1.2)
    crep = rng.standard_normal(n) * (rng.random(n) < 0.0025)
    crep = filtro(ndimage.gaussian_filter1d(crep, 2), "highpass", 3000, 2) * 3
    env = np.clip(t / 0.05, 0, 1) * np.exp(-np.maximum(t - 0.4, 0) / 0.9)
    return fundidos(normalizar_pico(estereo((siseo * 0.7 + crep) * env, -0.1)), 0.02, 0.4)


def aire_caliente(dur: float = 4.0, semilla: int = 73) -> np.ndarray:
    """Estación de aire caliente: soplido parejo de ventilador, con un silbido leve de la boquilla."""
    rng = np.random.default_rng(semilla)
    n = _n(dur)
    t = np.arange(n) / SR
    soplo = filtro_variable(ruido_rosa(n, rng), 900 + 200 * lfo_suave(n, rng, 0.8), 2.2)
    silbo = filtro_variable(ruido_rosa(n, rng), 3200 + 300 * lfo_suave(n, rng, 0.5), 0.3) * 0.25
    motor = np.sin(2 * math.pi * 210 * t + 0.3 * np.sin(2 * math.pi * 3 * t)) * 0.06
    return fundidos(normalizar_pico(estereo(soplo + silbo + motor, 0.15)), 0.35, 0.6)


def clic_pinzas(semilla: int = 74) -> np.ndarray:
    """Pinzas de acero que se cierran sobre el chip: un clic metálico pequeño y seco."""
    rng = np.random.default_rng(semilla)
    n = _n(0.4)
    t = np.arange(n) / SR
    golpe = filtro(rng.standard_normal(n) * np.exp(-t / 0.0015), "bandpass", (2500, 9000), 2)
    timbre = sum(a * np.sin(2 * math.pi * f * t) * np.exp(-t / d) for f, a, d in ((4100, 0.4, 0.03), (6700, 0.25, 0.02)))
    return normalizar_pico(reverberacion(estereo(golpe + timbre, 0.2), 0.3, 0.1, 8000, semilla)[:n], 0.5)


def lectura(dur: float, semilla: int = 75) -> np.ndarray:
    """Programador que lee el chip: un tic electrónico regular y un zumbido muy bajo."""
    rng = np.random.default_rng(semilla)
    n = _n(dur)
    t = np.arange(n) / SR
    x = np.sin(2 * math.pi * 60 * t) * 0.05 + filtro(ruido_rosa(n, rng), "bandpass", (1500, 5000), 2) * 0.04
    tics = [k / 6.4 for k in range(int(dur * 6.4))]
    for tk in tics:
        i = _n(tk)
        largo = _n(0.012)
        if i + largo < n:
            tt = np.arange(largo) / SR
            x[i : i + largo] += np.sin(2 * math.pi * 2600 * tt) * np.exp(-tt / 0.003) * 0.4
    return fundidos(normalizar_pico(estereo(x)), 0.2, 0.3)


def burbujas(dur: float, semilla: int = 76, chorros: float = 1.0) -> np.ndarray:
    """Tina de hidromasaje: el rumor grave de los chorros y burbujas que revientan en la superficie."""
    rng = np.random.default_rng(semilla)
    n = _n(dur)
    canales = []
    for k in range(2):
        rumor = filtro_variable(ruido_rosa(n, rng), 260 + 80 * lfo_suave(n, rng, 0.5), 1.6) * 0.6 * chorros
        pops = np.zeros(n)
        for tk in np.sort(rng.uniform(0, dur, int(dur * 26))):
            i = _n(tk)
            largo = _n(rng.uniform(0.01, 0.04))
            if i + largo >= n:
                continue
            tt = np.arange(largo) / SR
            f0 = rng.uniform(500, 1600)
            f = f0 * (1 + 2.5 * tt / tt[-1])
            pops[i : i + largo] += np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-tt / (largo / SR * 0.35)) * rng.uniform(0.2, 1)
        canales.append(rumor + pops * 0.5)
    x = np.stack(canales, axis=1)
    return fundidos(normalizar_pico(reverberacion(x, 0.6, 0.15, 5000, semilla)[:n]), 0.8, 1.0)


def tono_alexa(semilla: int = 77) -> np.ndarray:
    """Tono corto al despertar la bocina: dos notas suaves que suben, redondas, con algo de sala."""
    n = _n(1.2)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for t0, f, a in ((0.0, 622.3, 0.8), (0.11, 932.3, 1.0)):
        i = _n(t0)
        tt = t[: n - i]
        x[i:] += a * (np.sin(2 * math.pi * f * tt) + 0.15 * np.sin(4 * math.pi * f * tt)) * np.clip(tt / 0.012, 0, 1) * np.exp(-tt / 0.28)
    return normalizar_pico(reverberacion(estereo(x), 0.9, 0.22, 6000, semilla)[:n], 0.5)


def agua_tuberia(dur: float, semilla: int = 78) -> np.ndarray:
    """Agua que corre por un tubo: un siseo lleno y gorgoteos sordos."""
    rng = np.random.default_rng(semilla)
    n = _n(dur)
    canales = []
    for k in range(2):
        flujo = filtro_variable(ruido_rosa(n, rng), 700 + 250 * lfo_suave(n, rng, 0.7), 1.8)
        gorgo = filtro_variable(ndimage.gaussian_filter1d(rng.standard_normal(n) * (rng.random(n) < 0.003), 8) * 10,
                                400 + 600 * lfo_suave(n, rng, 2.5), 0.7)
        canales.append(filtro(flujo * 0.8 + gorgo * 0.4, "lowpass", 3500, 2))
    return fundidos(normalizar_pico(np.stack(canales, axis=1)), 1.0, 1.2)


def mazo(semilla: int = 79) -> np.ndarray:
    """Mazo de juez: dos golpes de madera sobre su base, con la sala detrás."""
    rng = np.random.default_rng(semilla)
    n = _n(2.2)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for t0, a in ((0.0, 1.0), (0.32, 0.85)):
        i = _n(t0)
        tt = t[: n - i]
        cuerpo = sum(b * np.sin(2 * math.pi * f * tt) * np.exp(-tt / d) for f, b, d in ((190, 1.0, 0.05), (410, 0.6, 0.03), (930, 0.3, 0.012)))
        golpe = filtro(rng.standard_normal(len(tt)) * np.exp(-tt / 0.004), "bandpass", (800, 5000), 2) * 0.8
        x[i:] += (cuerpo + golpe) * a
    return normalizar_pico(reverberacion(estereo(x), 1.6, 0.3, 4000, semilla)[:n], 0.6)


def noche_fria(dur: float, semilla: int = 80) -> np.ndarray:
    """Aire quieto de una noche de noviembre en un patio: un rumor lejano de ciudad y algo de viento."""
    rng = np.random.default_rng(semilla)
    n = _n(dur)
    lejos = filtro(ruido_rosa(n, rng), "lowpass", 420, 2) * (0.6 + 0.4 * lfo_suave(n, rng, 0.2))
    x = np.stack([lejos, filtro(ruido_rosa(n, rng), "lowpass", 420, 2) * 0.9], axis=1)
    return fundidos(normalizar_pico(x * 0.6 + sfx.viento(dur, semilla, 0.4) * 0.5), 1.0, 1.0)


def zumbido_lab(dur: float, semilla: int = 81) -> np.ndarray:
    """El laboratorio: el zumbido de los aparatos encendidos y el soplido de la ventilación."""
    rng = np.random.default_rng(semilla)
    n = _n(dur)
    aire = filtro(ruido_rosa(n, rng), "lowpass", 900, 2) * 0.35
    return fundidos(normalizar_pico(sfx.zumbido_electronico(dur, semilla) * 0.8 + estereo(aire)), 1.0, 1.0)
