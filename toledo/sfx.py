"""Efectos de sonido sintetizados con numpy/scipy (sin bancos de sonido).

Cada función devuelve un arreglo float32 estéreo (muestras, 2) a 48 kHz con picos cerca de
0.5; la ganancia final se decide al mezclar. `Mezcla` coloca los efectos en el tiempo y
normaliza la pista; `bajo_la_voz` la deja unos 15 dB por debajo de la voz y la baja más
mientras se habla (en las pausas sube un poco).
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
from scipy import ndimage, signal

SR = 48_000


# --------------------------------------------------------------------------- utilidades


def _rng(semilla: int) -> np.random.Generator:
    return np.random.default_rng(semilla)


def _n(seg: float) -> int:
    return int(round(seg * SR))


def ruido_rosa(n: int, rng: np.random.Generator) -> np.ndarray:
    """Ruido 1/f por filtrado espectral."""
    blanco = rng.standard_normal(n)
    espectro = np.fft.rfft(blanco)
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = f[1]
    espectro /= np.sqrt(f)
    x = np.fft.irfft(espectro, n)
    return (x / (np.abs(x).max() + 1e-9)).astype(np.float32)


def ruido_marron(n: int, rng: np.random.Generator) -> np.ndarray:
    x = np.cumsum(rng.standard_normal(n))
    x = signal.sosfilt(signal.butter(1, 20, "highpass", fs=SR, output="sos"), x)
    return (x / (np.abs(x).max() + 1e-9)).astype(np.float32)


def filtro(x: np.ndarray, tipo: str, corte, orden: int = 4) -> np.ndarray:
    sos = signal.butter(orden, corte, tipo, fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0).astype(np.float32)


def lfo_suave(n: int, rng: np.random.Generator, puntos_por_seg: float, minimo=0.0, maximo=1.0) -> np.ndarray:
    """Curva lenta y aleatoria (para variar volumen o frecuencia sin que se note un patrón)."""
    from scipy.interpolate import PchipInterpolator

    k = max(4, int(n / SR * puntos_por_seg) + 4)
    valores = rng.uniform(minimo, maximo, k)
    xs = np.linspace(0, n, k)
    # Interpolación monótona por tramos: suave y sin salirse de [minimo, maximo]. Se evita
    # convolucionar a 48 kHz con núcleos de cientos de miles de muestras.
    return PchipInterpolator(xs, valores)(np.arange(n)).astype(np.float32)


def a_control(n: int, fn_control, tasa: int = 100) -> np.ndarray:
    """Calcula una curva a `tasa` Hz con `fn_control(m)` y la lleva a 48 kHz por interpolación."""
    m = max(2, int(n / SR * tasa) + 2)
    curva = fn_control(m)
    return np.interp(np.arange(n), np.linspace(0, n, m), curva).astype(np.float32)


def envolvente(n: int, ataque: float, caida: float, curva: float = 1.0) -> np.ndarray:
    t = np.arange(n) / SR
    a = np.clip(t / max(ataque, 1e-4), 0, 1)
    d = np.exp(-np.maximum(t - ataque, 0) / max(caida, 1e-4))
    return (a * d ** curva).astype(np.float32)


def fundidos(x: np.ndarray, entrada: float, salida: float) -> np.ndarray:
    n = len(x)
    e = np.ones(n, np.float32)
    ni, no = min(n, _n(entrada)), min(n, _n(salida))
    if ni:
        e[:ni] = np.sin(np.linspace(0, math.pi / 2, ni)) ** 2
    if no:
        e[-no:] *= np.cos(np.linspace(0, math.pi / 2, no)) ** 2
    return x * (e[:, None] if x.ndim == 2 else e)


def estereo(mono: np.ndarray, pan: float | np.ndarray = 0.0) -> np.ndarray:
    """Paneo de potencia constante: pan -1 izquierda, +1 derecha."""
    ang = (np.asarray(pan) + 1) * math.pi / 4
    return np.stack([mono * np.cos(ang), mono * np.sin(ang)], axis=1).astype(np.float32)


def normalizar_pico(x: np.ndarray, pico: float = 0.5) -> np.ndarray:
    return (x * (pico / (np.abs(x).max() + 1e-9))).astype(np.float32)


def filtro_variable(x: np.ndarray, centro: np.ndarray, ancho_oct: float | np.ndarray = 1.0,
                    tipo: str = "banda") -> np.ndarray:
    """Filtro que cambia en el tiempo, aplicado en el dominio de la frecuencia (STFT).

    `centro`: frecuencia central (Hz) por muestra. tipo: 'banda' o 'graves' (pasa bajos).
    """
    nper = 2048
    f, t, Z = signal.stft(x, SR, nperseg=nper, noverlap=nper * 3 // 4, boundary="even")
    idx = np.clip((t * SR).astype(int), 0, len(centro) - 1)
    c = np.maximum(centro[idx], 20.0)[None, :]
    ff = np.maximum(f, 1.0)[:, None]
    if tipo == "banda":
        aw = ancho_oct if np.isscalar(ancho_oct) else np.asarray(ancho_oct)[idx][None, :]
        mascara = np.exp(-0.5 * (np.log2(ff / c) / (aw / 2)) ** 2)
    else:
        mascara = 1.0 / np.sqrt(1.0 + (ff / c) ** 6)
    _, y = signal.istft(Z * mascara, SR, nperseg=nper, noverlap=nper * 3 // 4, boundary=True)
    y = y[: len(x)]
    if len(y) < len(x):
        y = np.pad(y, (0, len(x) - len(y)))
    return y.astype(np.float32)


def reverberacion(x: np.ndarray, segundos: float = 1.2, mezcla: float = 0.3, brillo: float = 4000,
                  semilla: int = 0, predemora: float = 0.012) -> np.ndarray:
    """Convolución con una respuesta sintética (ruido que decae), distinta en cada canal."""
    rng = _rng(semilla)
    n = _n(segundos)
    t = np.arange(n) / SR
    decaimiento = np.exp(-6.9 * t / segundos)
    ir = rng.standard_normal((n, 2)) * decaimiento[:, None]
    ir = filtro(ir, "lowpass", brillo, 2)
    ir = np.vstack([np.zeros((_n(predemora), 2)), ir])
    ir /= np.sqrt((ir ** 2).sum(axis=0, keepdims=True)) + 1e-9
    if x.ndim == 1:
        x = estereo(x)
    cola = np.zeros((len(x) + len(ir) - 1, 2), np.float32)
    for k in range(2):
        cola[:, k] = signal.fftconvolve(x[:, k], ir[:, k])
    seco = np.vstack([x, np.zeros((len(ir) - 1, 2), np.float32)])
    return (seco * (1 - mezcla) + cola * mezcla * 1.6).astype(np.float32)


def eco(x: np.ndarray, demora: float, retroalim: float, repeticiones: int = 4) -> np.ndarray:
    d = _n(demora)
    salida = np.vstack([x, np.zeros((d * repeticiones, x.shape[1]), np.float32)])
    g = 1.0
    for k in range(1, repeticiones + 1):
        g *= retroalim
        trozo = x[:, ::-1] if k % 2 else x       # rebota de un lado a otro
        salida[k * d : k * d + len(x)] += trozo * g
    return salida


# --------------------------------------------------------------------------- efectos


def viento(dur: float, semilla: int = 1, intensidad: float = 1.0) -> np.ndarray:
    """Viento nocturno: ruido rosa filtrado con banda y volumen que cambian despacio."""
    rng = _rng(semilla)
    n = _n(dur)
    canales = []
    rafaga = lfo_suave(n, rng, 0.25, 0.25, 1.0) ** 1.6
    for k in range(2):
        base = ruido_rosa(n, rng)
        centro = 260 + 520 * lfo_suave(n, rng, 0.3) * (0.6 + 0.4 * rafaga)
        cuerpo = filtro_variable(base, centro, 1.6)
        silbido = filtro_variable(ruido_rosa(n, rng), 700 + 600 * lfo_suave(n, rng, 0.2), 0.25) * 0.35
        graves = filtro(ruido_marron(n, rng), "lowpass", 140, 2) * 0.5
        canales.append((cuerpo + silbido * rafaga + graves) * (0.35 + 0.65 * rafaga))
    x = np.stack(canales, axis=1) * intensidad
    return fundidos(normalizar_pico(x), 1.5, 1.5)














def whoosh(dur: float = 0.7, semilla: int = 7, f0: float = 160, f1: float = 3200,
           pan0: float = -0.5, pan1: float = 0.6) -> np.ndarray:
    """Barrido de ruido de grave a agudo, con crescendo y paso de izquierda a derecha."""
    rng = _rng(semilla)
    n = _n(dur)
    u = np.linspace(0, 1, n)
    centro = f0 * (f1 / f0) ** (u ** 1.3)
    x = filtro_variable(ruido_rosa(n, rng), centro, 1.4)
    env = np.sin(np.pi * np.clip(u / 0.9, 0, 1)) ** 2 * (0.3 + 0.7 * u)
    y = estereo(x * env, pan0 + (pan1 - pan0) * u)
    return normalizar_pico(reverberacion(y, 0.5, 0.15, 6000, semilla)[:n])






def golpe_sordo(semilla: int = 10) -> np.ndarray:
    """Golpe grave y apagado para la tarjeta de título, con cola oscura."""
    rng = _rng(semilla)
    n = _n(3.0)
    t = np.arange(n) / SR
    f = 30 * np.exp(-t * 4) + 40
    sub = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t / 0.55)
    golpe = filtro(rng.standard_normal(n) * np.exp(-t / 0.05), "lowpass", 280, 2) * 0.8
    y = estereo(sub + golpe)
    return normalizar_pico(reverberacion(y, 2.6, 0.35, 900, semilla)[:n], 0.9)


def agua_rio(dur: float, semilla: int = 11, caudal: float = 1.0) -> np.ndarray:
    """Río angosto: rumor grave continuo y gorgoteos agudos que aparecen y se van."""
    rng = _rng(semilla)
    n = _n(dur)
    canales = []
    for k in range(2):
        rumor = filtro_variable(ruido_rosa(n, rng), 380 + 160 * lfo_suave(n, rng, 0.4), 1.8)
        burbujas = rng.standard_normal(n) * (rng.random(n) < 0.004 * caudal)
        burbujas = ndimage.gaussian_filter1d(burbujas, 6)
        gorgoteo = filtro_variable(burbujas * 12, 900 + 1400 * lfo_suave(n, rng, 2.0), 0.6)
        brillo = filtro(ruido_rosa(n, rng), "bandpass", (2500, 7000), 2) * 0.12
        canales.append(rumor * 0.8 + gorgoteo * 0.5 + brillo * (0.6 + 0.4 * lfo_suave(n, rng, 0.8)))
    return fundidos(normalizar_pico(np.stack(canales, axis=1)), 1.2, 1.2)


def rueda_bici(dur: float, semilla: int = 12, vueltas_por_seg: float = 2.2) -> np.ndarray:
    """Rueda libre de bicicleta: el tic-tic del trinquete y el roce de la llanta sobre el asfalto."""
    rng = _rng(semilla)
    n = _n(dur)
    t = np.arange(n) / SR
    x = np.zeros(n)
    dientes = 24
    paso = 1.0 / (vueltas_por_seg * dientes)
    clic = np.exp(-np.arange(_n(0.006)) / (SR * 0.0009)) * rng.standard_normal(_n(0.006))
    clic = filtro(clic, "bandpass", (3000, 9000), 2)
    for k, tk in enumerate(np.arange(0.0, dur - 0.01, paso)):
        i = _n(tk + rng.normal(0, paso * 0.06))
        if 0 <= i < n - len(clic):
            x[i : i + len(clic)] += clic * (0.6 + 0.4 * rng.random())
    roce = filtro_variable(ruido_rosa(n, rng), 600 + 300 * lfo_suave(n, rng, 0.5), 1.2) * 0.35
    y = estereo(x * 0.8 + roce, 0.2 * np.sin(2 * math.pi * t / max(dur, 1)))
    return fundidos(normalizar_pico(reverberacion(y, 0.6, 0.12, 6000, semilla)[:n]), 0.6, 0.8)


def sirena_lejana(dur: float, semilla: int = 13) -> np.ndarray:
    """Sirena europea de dos tonos (la-re) muy lejos: filtrada, con eco de calles y sin agudos."""
    rng = _rng(semilla)
    n = _n(dur)
    t = np.arange(n) / SR
    ciclo = 1.4                                            # dos tonos por ciclo
    f = np.where((t % ciclo) < ciclo / 2, 440.0, 587.0) * (1 + 0.003 * np.sin(2 * math.pi * 0.3 * t))
    f = ndimage.gaussian_filter1d(f, SR * 0.01)
    fase = 2 * math.pi * np.cumsum(f) / SR
    tono = np.sin(fase) + 0.35 * np.sin(2 * fase) + 0.15 * np.sin(3 * fase)
    lejos = filtro(tono, "lowpass", 1200, 2) * (0.5 + 0.5 * lfo_suave(n, rng, 0.25))
    y = estereo(lejos, -0.35)
    return fundidos(normalizar_pico(reverberacion(y, 2.4, 0.55, 1500, semilla)[:n]), 2.0, 2.0)


def tiempos_latido(dur: float, ppm: float = 52.0, semilla: int = 14, desde: float = 0.3) -> list[float]:
    """Instantes de cada latido (el «lub»); la imagen usa los mismos para que la luz lata a la par."""
    rng = _rng(semilla)
    periodo = 60.0 / ppm
    return [float(t + rng.normal(0, 0.01)) for t in np.arange(desde, dur - 0.5, periodo)]


def latido(dur: float, semilla: int = 14, ppm: float = 52.0, tiempos: list[float] | None = None) -> np.ndarray:
    """Latido grave y suave: dos golpes (lub-dub) muy apagados, más sentidos que oídos."""
    n = _n(dur)
    x = np.zeros(n)
    golpe_n = _n(0.25)
    tt = np.arange(golpe_n) / SR

    def golpe(f0, dec, amp):
        f = f0 * (1 + 0.6 * np.exp(-tt * 30))
        return amp * np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-tt / dec)

    lub, dub = golpe(52, 0.07, 1.0), golpe(64, 0.05, 0.6)
    for tk in (tiempos if tiempos is not None else tiempos_latido(dur, ppm, semilla)):
        i = _n(tk)
        j = i + _n(0.28)
        if j + golpe_n < n:
            x[i : i + golpe_n] += lub
            x[j : j + golpe_n] += dub
    x = filtro(x, "lowpass", 160, 2)
    return fundidos(normalizar_pico(estereo(x)), 0.8, 0.8)


def clic_contador(semilla: int = 15) -> np.ndarray:
    """Clic seco y pequeño de un contador mecánico (un paso)."""
    rng = _rng(semilla)
    n = _n(0.08)
    t = np.arange(n) / SR
    x = rng.standard_normal(n) * np.exp(-t / 0.0025)
    x = filtro(x, "bandpass", (1800, 6500), 2) + 0.4 * np.sin(2 * math.pi * 2300 * t) * np.exp(-t / 0.006)
    return normalizar_pico(estereo(x), 0.5)


def clics(tiempos: list[float], dur: float, semilla: int = 16) -> np.ndarray:
    """Varios clics de contador en los tiempos dados, cada uno algo distinto."""
    salida = np.zeros((_n(dur), 2), np.float32)
    for k, tk in enumerate(tiempos):
        c = clic_contador(semilla + k) * (0.75 + 0.25 * ((k * 7) % 5) / 4)
        i = _n(tk)
        if 0 <= i < len(salida):
            trozo = c[: len(salida) - i]
            salida[i : i + len(trozo)] += trozo
    return salida


def bajo_la_voz(efectos: np.ndarray, voz: np.ndarray | None, *, debajo_db: float = 15.0,
                extra_al_hablar_db: float = 6.0, ataque: float = 0.08, liberacion: float = 0.6) -> np.ndarray:
    """Coloca los efectos debajo de la voz y los baja más mientras se habla.

    Los efectos (ya mezclados) se ajustan para que su sonoridad quede `debajo_db` por debajo de
    la de la voz; además, una envolvente de la voz (con ataque rápido y liberación lenta) los
    baja `extra_al_hablar_db` mientras hay voz, así en las pausas suben solos. Sin voz grabada
    se usa una voz de referencia a -16 LUFS.
    """
    import pyloudnorm as pyln

    medidor = pyln.Meter(SR)
    lufs_e = medidor.integrated_loudness(efectos.astype(np.float64))
    if voz is None or not np.any(voz):
        lufs_v = -16.0
        hablando = np.zeros(len(efectos))
    else:
        lufs_v = medidor.integrated_loudness(voz.astype(np.float64))
        nivel = ndimage.uniform_filter1d(np.abs(voz).mean(axis=1), _n(0.05))
        umbral = np.percentile(nivel[nivel > 1e-5], 35) if np.any(nivel > 1e-5) else 1.0
        hablando = (nivel > umbral).astype(np.float64)
        # ataque rápido, liberación lenta: un máximo móvil seguido de un suavizado
        hablando = ndimage.maximum_filter1d(hablando, _n(liberacion))
        hablando = ndimage.uniform_filter1d(hablando, _n(ataque * 2))
    if not np.isfinite(lufs_e):
        return efectos
    base = 10 ** ((lufs_v - debajo_db - lufs_e) / 20)
    ganancia = base * 10 ** (-extra_al_hablar_db * hablando / 20)
    return (efectos * ganancia[:, None]).astype(np.float32)


# --------------------------------------------------------------------------- escena 2: laboratorio y chips


def _en(salida: np.ndarray, t: float, x: np.ndarray, g: float = 1.0) -> None:
    i = _n(t)
    if 0 <= i < len(salida):
        trozo = x[: len(salida) - i]
        salida[i : i + len(trozo)] += trozo * g


def zumbido_cctv(dur: float, semilla: int = 21) -> np.ndarray:
    """Cámara de seguridad: zumbido de red de 50 Hz con armónicos, un silbido agudo débil y soplido."""
    rng = _rng(semilla)
    n = _n(dur)
    t = np.arange(n) / SR
    red = sum(a * np.sin(2 * math.pi * 50 * k * t + rng.uniform(0, 6)) for k, a in ((1, 1.0), (2, 0.5), (3, 0.35), (5, 0.2)))
    silbido = 0.04 * np.sin(2 * math.pi * 7800 * t) * (0.6 + 0.4 * lfo_suave(n, rng, 0.5))
    soplo = filtro(ruido_rosa(n, rng), "bandpass", (800, 6000), 2) * 0.12
    return fundidos(normalizar_pico(estereo((red * 0.5 + silbido + soplo) * (0.85 + 0.15 * lfo_suave(n, rng, 0.3)))), 0.8, 0.8)


def bolsa_evidencia(dur: float = 1.6, semilla: int = 22) -> np.ndarray:
    """Bolsa de plástico que se acomoda: crujidos cortos y agudos en ráfagas."""
    rng = _rng(semilla)
    n = _n(dur)
    x = np.zeros(n)
    for _ in range(int(dur * 70)):
        i = int(rng.uniform(0, n - _n(0.03)))
        largo = _n(rng.uniform(0.003, 0.02))
        x[i : i + largo] += rng.standard_normal(largo) * np.exp(-np.arange(largo) / (largo * 0.3)) * rng.uniform(0.2, 1)
    x = filtro(x, "highpass", 1500, 2) * (0.4 + 0.6 * np.sin(np.pi * np.linspace(0, 1, n)) ** 0.6)
    return normalizar_pico(reverberacion(estereo(x, 0.1), 0.4, 0.15, 7000, semilla)[:n])


def zumbido_electronico(dur: float, semilla: int = 23) -> np.ndarray:
    """Zumbido suave de aparato encendido: graves estables con un brillo que respira."""
    rng = _rng(semilla)
    n = _n(dur)
    t = np.arange(n) / SR
    base = np.sin(2 * math.pi * 110 * t) + 0.5 * np.sin(2 * math.pi * 220.7 * t) + 0.25 * np.sin(2 * math.pi * 331 * t)
    brillo = filtro_variable(ruido_rosa(n, rng), 1200 + 600 * lfo_suave(n, rng, 0.2), 0.5) * 0.25
    x = base * (0.7 + 0.3 * lfo_suave(n, rng, 0.15)) * 0.4 + brillo
    return fundidos(normalizar_pico(estereo(x)), 1.5, 1.5)


def datos(dur: float, semilla: int = 24, densidad: float = 28.0) -> np.ndarray:
    """Transferencia de datos: pitidos breves de tono al azar sobre un soplido digital."""
    rng = _rng(semilla)
    n = _n(dur)
    salida = np.zeros((n, 2), np.float32)
    for tk in np.sort(rng.uniform(0, dur - 0.05, int(dur * densidad))):
        largo = rng.uniform(0.012, 0.04)
        tt = np.arange(_n(largo)) / SR
        f = rng.choice([1200, 1600, 2000, 2400, 3200])
        pit = np.sin(2 * math.pi * f * tt) * np.sin(np.pi * tt / largo) ** 2
        _en(salida, tk, estereo(pit * rng.uniform(0.3, 1), rng.uniform(-0.4, 0.4)))
    soplo = filtro(ruido_rosa(n, rng), "bandpass", (2000, 9000), 2) * 0.08
    salida += estereo(soplo)
    return fundidos(normalizar_pico(salida), 0.3, 0.5)


def teclado(dur: float, semilla: int = 25, rapido: float = 1.0) -> np.ndarray:
    """Tecleo: cada tecla un clic con un golpe sordo; `rapido` sube la frecuencia."""
    rng = _rng(semilla)
    n = _n(dur)
    salida = np.zeros((n, 2), np.float32)
    t = 0.05
    while t < dur - 0.1:
        largo = _n(0.05)
        tt = np.arange(largo) / SR
        clic = filtro(rng.standard_normal(largo) * np.exp(-tt / 0.004), "bandpass", (1500, 6000), 2)
        golpe = np.sin(2 * math.pi * rng.uniform(140, 220) * tt) * np.exp(-tt / 0.012) * 0.6
        _en(salida, t, estereo((clic + golpe) * rng.uniform(0.5, 1), rng.uniform(-0.3, 0.3)))
        t += rng.uniform(0.05, 0.14) / rapido
    return fundidos(normalizar_pico(reverberacion(salida, 0.3, 0.08, 6000, semilla)[:n]), 0.05, 0.3)


def candado(semilla: int = 26) -> np.ndarray:
    """Candado que se cierra: golpe metálico, el pestillo y un brillo de resonancia."""
    rng = _rng(semilla)
    n = _n(0.9)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for t0, amp in ((0.0, 1.0), (0.07, 0.7)):
        i = _n(t0)
        tt = t[: n - i]
        golpe = filtro(rng.standard_normal(len(tt)) * np.exp(-tt / 0.003), "bandpass", (1500, 7000), 2)
        timbre = sum(a * np.sin(2 * math.pi * f * tt) * np.exp(-tt / d) for f, a, d in ((2150, 0.5, 0.08), (3420, 0.35, 0.05), (5100, 0.2, 0.03)))
        x[i:] += (golpe + timbre) * amp
    return normalizar_pico(reverberacion(estereo(x), 0.5, 0.15, 6000, semilla)[:n], 0.6)


def laser(dur: float = 1.8, semilla: int = 27) -> np.ndarray:
    """Grabado láser: un tono agudo que tiembla, con chisporroteo fino, y un timbre metálico al final."""
    rng = _rng(semilla)
    n = _n(dur)
    t = np.arange(n) / SR
    f = 2600 + 400 * np.sin(2 * math.pi * 7 * t) + 300 * lfo_suave(n, rng, 3)
    tono = np.sin(2 * math.pi * np.cumsum(f) / SR) * 0.35
    chispa = filtro(rng.standard_normal(n) * (rng.random(n) < 0.03), "highpass", 4000, 2) * 0.8
    env = np.clip(t / 0.1, 0, 1) * np.clip((dur - 0.25 - t) / 0.1, 0, 1)
    x = (tono + chispa) * env
    timbre = tono_metalico(semilla)[: n - _n(dur - 0.25)]
    y = estereo(x, 0.1)
    y[_n(dur - 0.25) : _n(dur - 0.25) + len(timbre)] += timbre * 0.8
    return normalizar_pico(y)


def tono_metalico(semilla: int = 28) -> np.ndarray:
    """Timbre metálico: parciales no armónicos que se apagan a distinto ritmo."""
    n = _n(1.6)
    t = np.arange(n) / SR
    x = sum(a * np.sin(2 * math.pi * f * t) * np.exp(-t / d) for f, a, d in
            ((880, 1.0, 0.9), (1997, 0.55, 0.5), (3150, 0.35, 0.3), (4420, 0.2, 0.2)))
    x[: _n(0.003)] *= np.linspace(0, 1, _n(0.003))
    return normalizar_pico(reverberacion(estereo(x), 1.2, 0.25, 6000, semilla)[:n], 0.5)


def estatica(dur: float, semilla: int = 29) -> np.ndarray:
    """Estática de radio: ruido de banda media que tartamudea."""
    rng = _rng(semilla)
    n = _n(dur)
    x = filtro(rng.standard_normal(n), "bandpass", (600, 5000), 2)
    corte = ndimage.uniform_filter1d((rng.random(n // 400 + 1) > 0.25).astype(float).repeat(400)[:n], 200)
    return fundidos(normalizar_pico(estereo(x * corte * (0.6 + 0.4 * lfo_suave(n, rng, 4)))), 0.05, 0.2)


def tics(tiempos: list[float], dur: float, semilla: int = 30) -> np.ndarray:
    """Tic de reloj en cada instante: golpecito de madera seco."""
    rng = _rng(semilla)
    salida = np.zeros((_n(dur), 2), np.float32)
    largo = _n(0.04)
    tt = np.arange(largo) / SR
    for k, tk in enumerate(tiempos):
        f = 2400 if k % 2 else 2000
        x = np.sin(2 * math.pi * f * tt) * np.exp(-tt / 0.006) + filtro(rng.standard_normal(largo) * np.exp(-tt / 0.002), "highpass", 3000, 2) * 0.4
        _en(salida, tk, estereo(x, 0.15 if k % 2 else -0.15), 0.8)
    return salida


def error_suave(semilla: int = 31) -> np.ndarray:
    """Aviso de error discreto: dos notas que bajan, redondas y suaves."""
    n = _n(0.9)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for t0, f in ((0.0, 659.3), (0.18, 440.0)):
        i = _n(t0)
        tt = t[: n - i]
        x[i:] += (np.sin(2 * math.pi * f * tt) + 0.2 * np.sin(4 * math.pi * f * tt)) * np.clip(tt / 0.01, 0, 1) * np.exp(-tt / 0.22)
    return normalizar_pico(reverberacion(estereo(x), 0.8, 0.2, 5000, semilla)[:n], 0.5)


def vibracion(semilla: int = 32) -> np.ndarray:
    """Teléfono que vibra por un error: dos zumbidos cortos de motor."""
    rng = _rng(semilla)
    n = _n(0.75)
    t = np.arange(n) / SR
    motor = np.sin(2 * math.pi * 165 * t + 0.4 * np.sin(2 * math.pi * 23 * t)) + 0.4 * np.sin(2 * math.pi * 330 * t)
    roce = filtro(rng.standard_normal(n), "bandpass", (300, 1500), 2) * 0.3
    env = ((t > 0.0) & (t < 0.22)) * 1.0 + ((t > 0.36) & (t < 0.58)) * 1.0
    env = ndimage.uniform_filter1d(env, _n(0.01))
    return normalizar_pico(estereo((motor + roce) * env))


def alarma_cortada(sonando: float = 1.1, semilla: int = 33) -> np.ndarray:
    """Alarma de teléfono que empieza a sonar y se corta en seco: el silencio es el efecto."""
    n = _n(sonando + 0.05)
    t = np.arange(n) / SR
    x = np.zeros(n)
    notas = (1046.5, 1318.5, 1568.0, 1318.5, 1046.5, 1318.5, 1568.0, 2093.0)
    for k, f in enumerate(notas):
        i = _n(k * 0.14)
        if i >= n:
            break
        tt = t[: n - i]
        x[i:] += np.sin(2 * math.pi * f * tt) * np.exp(-tt / 0.12) * np.clip(tt / 0.004, 0, 1)
    x[_n(sonando) :] = 0                                           # corte seco
    return normalizar_pico(estereo(x), 0.5)


# --------------------------------------------------------------------------- mezcla


class Mezcla:
    def __init__(self, duracion: float):
        self.n = _n(duracion)
        self.x = np.zeros((self.n, 2), np.float32)
        self.registro: list[tuple[str, float, float]] = []

    def agregar(self, nombre: str, t: float, efecto: np.ndarray, db: float = 0.0,
                fundido_entrada: float = 0.0, fundido_salida: float = 0.0) -> None:
        if fundido_entrada or fundido_salida:
            efecto = fundidos(efecto, fundido_entrada, fundido_salida)
        i = _n(t)
        if i >= self.n:
            return
        trozo = efecto[: self.n - i] * (10 ** (db / 20))
        self.x[i : i + len(trozo)] += trozo
        self.registro.append((nombre, t, db))

    def sonoridad(self) -> float:
        import pyloudnorm as pyln

        return float(pyln.Meter(SR).integrated_loudness(self.x.astype(np.float64)))

    def pico_real_db(self) -> float:
        sobre = signal.resample_poly(self.x, 4, 1, axis=0)
        return float(20 * np.log10(np.abs(sobre).max() + 1e-12))

    def normalizar(self, lufs_objetivo: float, pico_max_db: float = -6.0) -> dict:
        antes = self.sonoridad()
        self.x *= 10 ** ((lufs_objetivo - antes) / 20)
        pico = self.pico_real_db()
        if pico > pico_max_db:
            self._limitar(10 ** (pico_max_db / 20))
        return {"lufs_antes": antes, "lufs": self.sonoridad(), "pico_real_db": self.pico_real_db()}

    def _limitar(self, techo: float) -> None:
        """Limitador con anticipación: baja la ganancia solo alrededor de los picos.

        El mínimo móvil (ventana 2w) seguido de un promedio móvil (ventana w) garantiza que en
        cada pico la ganancia no supere la necesaria, y que la bajada empiece antes del pico.
        """
        nivel = np.abs(signal.resample_poly(self.x, 4, 1, axis=0)).max(axis=1)[::4]
        ganancia = np.minimum(1.0, techo * 0.97 / (nivel + 1e-9))
        w = _n(0.01)
        g = ndimage.minimum_filter1d(ganancia, 2 * w)
        g = ndimage.uniform_filter1d(g, w)
        self.x *= g[:, None].astype(np.float32)

    def escribir_wav(self, ruta: Path) -> None:
        """WAV PCM de 24 bits, 48 kHz, estéreo (escrito con nombre temporal)."""
        from scipy.io import wavfile

        ruta = Path(ruta)
        flotante = ruta.with_suffix(".float.tmp.wav")
        temporal = ruta.with_suffix(".tmp.wav")
        wavfile.write(flotante, SR, self.x.astype(np.float32))
        resultado = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(flotante), "-c:a", "pcm_s24le", str(temporal)],
            capture_output=True, text=True,
        )
        flotante.unlink(missing_ok=True)
        if resultado.returncode != 0:
            temporal.unlink(missing_ok=True)
            raise RuntimeError(f"ffmpeg no pudo escribir el WAV:\n{resultado.stderr}")
        temporal.replace(ruta)
