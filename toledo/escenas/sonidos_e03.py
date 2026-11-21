"""Efectos de sonido de la escena 3, sintetizados con las piezas de `sfx.py` (sin bancos de sonido).

Cada función devuelve float32 estéreo (muestras, 2) a 48 kHz con picos cerca de 0.5; el volumen
final se decide al mezclar, debajo de la voz.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

import sfx
from sfx import SR, envolvente, estereo, filtro, filtro_variable, fundidos, lfo_suave, normalizar_pico, reverberacion, ruido_rosa


def _n(seg: float) -> int:
    return int(round(seg * SR))


def sirena_eeuu(dur: float, semilla: int = 301) -> np.ndarray:
    """Sirena de patrulla de EE. UU. (el «wail» que sube y baja) muy lejos, con eco de edificios."""
    rng = np.random.default_rng(semilla)
    n = _n(dur)
    t = np.arange(n) / SR
    f = 950 + 420 * np.sin(2 * math.pi * t / 4.2 - math.pi / 2)
    fase = 2 * math.pi * np.cumsum(f) / SR
    tono = np.sin(fase) + 0.3 * np.sin(2 * fase) + 0.12 * np.sin(3 * fase)
    lejos = filtro(tono, "lowpass", 1400, 2) * (0.55 + 0.45 * lfo_suave(n, rng, 0.3))
    y = estereo(lejos, 0.3)
    return fundidos(normalizar_pico(reverberacion(y, 2.6, 0.6, 1600, semilla)[:n]), 2.5, 2.5)


def helicoptero(dur: float, semilla: int = 302) -> np.ndarray:
    """Helicóptero lejano: el golpeteo de las aspas (unos 11 por segundo) sobre un rumor grave."""
    rng = np.random.default_rng(semilla)
    n = _n(dur)
    t = np.arange(n) / SR
    golpe = (0.5 + 0.5 * np.cos(2 * math.pi * 11.2 * t)) ** 6
    cuerpo = filtro(ruido_rosa(n, rng), "bandpass", (60, 420), 2) * (0.25 + golpe)
    turbina = filtro(ruido_rosa(n, rng), "bandpass", (1800, 3200), 2) * 0.08
    pan = 0.6 * np.sin(2 * math.pi * t / max(dur * 1.6, 1.0)) - 0.2
    y = estereo((cuerpo + turbina) * (0.6 + 0.4 * lfo_suave(n, rng, 0.2)), pan)
    return fundidos(normalizar_pico(reverberacion(y, 1.8, 0.4, 1200, semilla)[:n]), 2.0, 2.5)


def notificacion(semilla: int = 303) -> np.ndarray:
    """Aviso suave de teléfono: dos notas cortas que suben."""
    n = _n(0.8)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for t0, f in ((0.0, 880.0), (0.11, 1318.5)):
        i = _n(t0)
        tt = t[: n - i]
        x[i:] += np.sin(2 * math.pi * f * tt) * np.clip(tt / 0.005, 0, 1) * np.exp(-tt / 0.16)
    return normalizar_pico(reverberacion(estereo(x), 0.6, 0.2, 6000, semilla)[:n], 0.5)


def papel(dur: float = 1.2, semilla: int = 304) -> np.ndarray:
    """Hoja de papel que se desliza y se acomoda: soplido agudo con crujidos."""
    rng = np.random.default_rng(semilla)
    n = _n(dur)
    roce = filtro(rng.standard_normal(n), "bandpass", (1500, 8000), 2) * np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
    crujido = rng.standard_normal(n) * (rng.random(n) < 0.002)
    crujido = filtro(ndimage.gaussian_filter1d(crujido, 3) * 8, "highpass", 2500, 2)
    return normalizar_pico(reverberacion(estereo(roce * 0.5 + crujido, 0.15), 0.4, 0.15, 7000, semilla)[:n])


def mazo(semilla: int = 305) -> np.ndarray:
    """Mazo de juez sobre madera: golpe seco con cuerpo y una cola corta de sala."""
    rng = np.random.default_rng(semilla)
    n = _n(1.6)
    t = np.arange(n) / SR
    madera = sum(a * np.sin(2 * math.pi * f * t) * np.exp(-t / d) for f, a, d in ((180, 1.0, 0.06), (410, 0.6, 0.03), (930, 0.3, 0.015)))
    ataque = filtro(rng.standard_normal(n) * np.exp(-t / 0.004), "bandpass", (800, 5000), 2) * 0.6
    return normalizar_pico(reverberacion(estereo(madera + ataque), 1.2, 0.3, 3500, semilla)[:n], 0.6)


def conector(semilla: int = 306) -> np.ndarray:
    """Conector que entra en su puerto: roce breve y un clic con resorte."""
    rng = np.random.default_rng(semilla)
    n = _n(0.5)
    t = np.arange(n) / SR
    roce = filtro(rng.standard_normal(n), "bandpass", (2000, 7000), 2) * np.clip((0.12 - t) / 0.12, 0, 1) * 0.25
    clic_t = t - 0.11
    clic = np.where(clic_t > 0, filtro(rng.standard_normal(n), "bandpass", (2500, 9000), 2) * np.exp(-np.clip(clic_t, 0, None) / 0.003), 0)
    resorte = np.where(clic_t > 0, np.sin(2 * math.pi * 3400 * clic_t) * np.exp(-np.clip(clic_t, 0, None) / 0.02) * 0.3, 0)
    return normalizar_pico(reverberacion(estereo(roce + clic + resorte), 0.3, 0.1, 8000, semilla)[:n], 0.5)


def hallazgo(semilla: int = 307) -> np.ndarray:
    """Tono de hallazgo: una nota limpia que se abre, con un brillo agudo."""
    n = _n(1.8)
    t = np.arange(n) / SR
    x = (np.sin(2 * math.pi * 587.3 * t) + 0.5 * np.sin(2 * math.pi * 880 * t) * np.clip((t - 0.12) / 0.05, 0, 1)) * envolvente(n, 0.02, 0.6)
    return normalizar_pico(reverberacion(estereo(x), 1.4, 0.35, 5000, semilla)[:n], 0.5)


def tono_grave(dur: float = 3.0, semilla: int = 308) -> np.ndarray:
    """Tono grave sostenido que crece y se apaga (un detalle que pesa)."""
    n = _n(dur)
    t = np.arange(n) / SR
    x = np.sin(2 * math.pi * 55 * t) + 0.4 * np.sin(2 * math.pi * 82.5 * t) + 0.2 * np.sin(2 * math.pi * 110.3 * t)
    env = np.clip(t / 0.6, 0, 1) * np.clip((dur - t) / 1.2, 0, 1)
    return normalizar_pico(reverberacion(estereo(filtro(x * env, "lowpass", 400, 2)), 2.0, 0.3, 900, semilla)[:n], 0.6)


def caja_registradora(semilla: int = 309) -> np.ndarray:
    """Caja registradora suave: el cajón que corre y una campanita."""
    rng = np.random.default_rng(semilla)
    n = _n(1.4)
    t = np.arange(n) / SR
    cajon = filtro(rng.standard_normal(n), "bandpass", (300, 2500), 2) * np.clip((0.25 - t) / 0.25, 0, 1) * 0.4
    tt = t - 0.22
    campana = np.where(tt > 0, sum(a * np.sin(2 * math.pi * f * tt) * np.exp(-np.clip(tt, 0, None) / d)
                                   for f, a, d in ((2093, 1.0, 0.45), (4186, 0.35, 0.25), (6280, 0.15, 0.12))), 0)
    return normalizar_pico(reverberacion(estereo(cajon + campana * 0.7), 0.8, 0.2, 7000, semilla)[:n], 0.5)


def desbloqueo(semilla: int = 310) -> np.ndarray:
    """Desbloqueo de teléfono: un clic hueco y suave."""
    rng = np.random.default_rng(semilla)
    n = _n(0.35)
    t = np.arange(n) / SR
    x = np.sin(2 * math.pi * 1200 * t * (1 - 0.3 * t)) * np.exp(-t / 0.02) + filtro(rng.standard_normal(n) * np.exp(-t / 0.002), "highpass", 3000, 2) * 0.3
    return normalizar_pico(reverberacion(estereo(x), 0.3, 0.12, 7000, semilla)[:n], 0.45)


def cierre_bolsa(dur: float = 1.0, semilla: int = 311) -> np.ndarray:
    """Velcro de la solapa que se cierra: ráfaga de rasgueos que se acelera."""
    rng = np.random.default_rng(semilla)
    n = _n(dur)
    x = np.zeros(n)
    t = 0.0
    while t < dur * 0.85:
        i = _n(t)
        largo = _n(rng.uniform(0.002, 0.006))
        x[i : i + largo] += rng.standard_normal(min(largo, n - i)) * rng.uniform(0.4, 1.0)
        t += rng.uniform(0.004, 0.012) * (1.2 - t / dur)
    x = filtro(x, "bandpass", (900, 7000), 2) * np.sin(np.pi * np.linspace(0, 1, n)) ** 0.5
    return normalizar_pico(reverberacion(estereo(x, -0.1), 0.4, 0.12, 7000, semilla)[:n])


def reinicio(semilla: int = 312) -> np.ndarray:
    """Teléfono que se reinicia solo: un golpecito grave de encendido y un zumbido que sube."""
    rng = np.random.default_rng(semilla)
    n = _n(1.6)
    t = np.arange(n) / SR
    golpe = np.sin(2 * math.pi * 70 * t) * np.exp(-t / 0.12)
    sube = filtro_variable(ruido_rosa(n, rng), 300 + 2500 * np.clip(t / 1.4, 0, 1) ** 2, 0.6) * np.clip(t / 0.4, 0, 1) * np.clip((1.6 - t) / 0.4, 0, 1) * 0.3
    return normalizar_pico(reverberacion(estereo(golpe + sube), 0.8, 0.2, 5000, semilla)[:n], 0.5)


def eslabones(veces: int = 3, semilla: int = 313) -> np.ndarray:
    """Eslabones de cadena que se enganchan: tintineos metálicos cortos."""
    rng = np.random.default_rng(semilla)
    n = _n(0.4 + 0.22 * veces)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(veces):
        i = _n(0.05 + 0.22 * k)
        tt = t[: n - i]
        f0 = rng.uniform(2200, 2800)
        x[i:] += sum(a * np.sin(2 * math.pi * f0 * r * tt) * np.exp(-tt / d) for r, a, d in ((1.0, 1.0, 0.05), (1.52, 0.5, 0.03), (2.4, 0.3, 0.02)))
    return normalizar_pico(reverberacion(estereo(x), 0.7, 0.25, 6000, semilla)[:n], 0.5)


def grieta(semilla: int = 314) -> np.ndarray:
    """Algo duro que se agrieta: chasquidos en cascada y un tintineo de cristal."""
    rng = np.random.default_rng(semilla)
    n = _n(1.5)
    t = np.arange(n) / SR
    x = np.zeros(n)
    tk = 0.0
    while tk < 0.35:
        i = _n(tk)
        largo = _n(0.004)
        x[i : i + largo] += rng.standard_normal(largo) * rng.uniform(0.5, 1.0)
        tk += rng.uniform(0.006, 0.03)
    x = filtro(x, "bandpass", (1200, 9000), 2)
    cristal = sum(a * np.sin(2 * math.pi * f * t) * np.exp(-t / d) for f, a, d in ((3150, 0.4, 0.3), (4720, 0.3, 0.2), (6230, 0.2, 0.12)))
    return normalizar_pico(reverberacion(estereo(x + cristal * 0.5), 0.9, 0.25, 7000, semilla)[:n], 0.6)


def zumbido(dur: float, semilla: int = 315) -> np.ndarray:
    return sfx.zumbido_electronico(dur, semilla)
