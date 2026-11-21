"""Efectos de sonido sintetizados con numpy/scipy (sin bancos de sonido).

Cada función devuelve un arreglo float32 estéreo (muestras, 2) a 48 kHz con picos cerca de
0.5; la ganancia final se decide al mezclar. `Mezcla` coloca los efectos en el tiempo y
normaliza toda la pista a una sonoridad integrada objetivo (LUFS), pensada para quedar unos
12 dB por debajo de la voz que se grabará encima.
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


def antorchas(dur: float, semilla: int = 2, densidad: float = 7.0, cerca: float = 1.0) -> np.ndarray:
    """Crepitar: chasquidos aleatorios sobre un ruido grave de llama."""
    rng = _rng(semilla)
    n = _n(dur)
    llama = filtro(ruido_marron(n, rng), "lowpass", 380, 2)
    parpadeo = 0.55 + 0.45 * lfo_suave(n, rng, 9.0)
    base = estereo(llama * parpadeo * 0.55, 0.0)
    eventos = rng.poisson(densidad * dur)
    for _ in range(eventos):
        i = rng.integers(0, max(1, n - _n(0.05)))
        largo = _n(rng.uniform(0.002, 0.018))
        chasquido = rng.standard_normal(largo) * envolvente(largo, 0.0004, rng.uniform(0.002, 0.008))
        corte = rng.uniform(1800, 6500)
        chasquido = filtro(chasquido, "highpass", corte, 2)
        amp = rng.lognormal(-1.6, 0.7) * cerca
        if rng.random() < 0.08:          # algún estallido más grave
            chasquido = filtro(rng.standard_normal(_n(0.03)) * envolvente(_n(0.03), 0.001, 0.01), "bandpass", (300, 1500), 2)
            amp *= 2.2
        base[i : i + len(chasquido)] += estereo(chasquido * amp, rng.uniform(-0.6, 0.6))
    return fundidos(normalizar_pico(reverberacion(base, 0.6, 0.18, 5000, semilla)[:n]), 0.6, 0.8)


def murmullo(dur: float, semilla: int = 3, voces: int = 22) -> np.ndarray:
    """Murmullo lejano de campamento: muchas 'voces' de ruido con ritmo silábico, todo grave."""
    rng = _rng(semilla)
    n = _n(dur)
    mezcla_ = np.zeros((n, 2), np.float32)
    t = np.arange(n) / SR
    for v in range(voces):
        formante = rng.uniform(380, 1100)
        voz = filtro(rng.standard_normal(n), "bandpass", (formante * 0.6, formante * 1.6), 2)
        silabas = 0.5 + 0.5 * np.sin(2 * math.pi * rng.uniform(3, 5.5) * t + rng.uniform(0, 6))
        umbral = rng.uniform(0.35, 0.6)
        frases = a_control(n, lambda m: ndimage.gaussian_filter1d(
            (lfo_suave(m * 480, rng, 0.6)[::480] > umbral).astype(np.float32), 2.0))
        mezcla_ += estereo(voz * silabas ** 2 * frases * rng.uniform(0.4, 1.0), rng.uniform(-0.8, 0.8))
    mezcla_ = filtro(mezcla_, "lowpass", 900, 4)
    rumor = estereo(filtro(ruido_marron(n, rng), "lowpass", 160, 2) * 0.6)
    x = reverberacion(mezcla_ + rumor, 2.2, 0.55, 2500, semilla)[:n]
    return fundidos(normalizar_pico(x), 1.5, 1.5)


def pluma(dur: float, semilla: int = 4) -> np.ndarray:
    """Pluma de caña sobre pergamino: trazos cortos de ruido agudo con pausas."""
    rng = _rng(semilla)
    n = _n(dur)
    x = np.zeros(n, np.float32)
    i = _n(0.05)
    while i < n - _n(0.3):
        largo = _n(rng.uniform(0.06, 0.22))
        trazo = rng.standard_normal(largo)
        aspereza = 0.6 + 0.4 * np.sin(2 * math.pi * rng.uniform(35, 80) * np.arange(largo) / SR) ** 2
        env = np.minimum(1, np.arange(largo) / _n(0.008)) * np.minimum(1, (largo - np.arange(largo)) / _n(0.025))
        centro = rng.uniform(2800, 5200)
        trazo = filtro(trazo * aspereza * env, "bandpass", (centro * 0.7, min(centro * 1.8, 16000)), 2)
        x[i : i + largo] += trazo * rng.uniform(0.6, 1.0)
        i += largo + _n(rng.uniform(0.03, 0.12) if rng.random() > 0.15 else rng.uniform(0.25, 0.45))
    cuerpo = filtro(x, "lowpass", 900, 2) * 0.6
    y = estereo(x + cuerpo, 0.05)
    return normalizar_pico(reverberacion(y, 0.35, 0.12, 6000, semilla)[:n])


def moneda(semilla: int, fuerza: float = 1.0) -> np.ndarray:
    """Un golpe metálico: parciales inarmónicos que decaen rápido, más el clic del choque."""
    rng = _rng(semilla)
    n = _n(0.6)
    t = np.arange(n) / SR
    f0 = rng.uniform(2100, 3300)
    x = np.zeros(n)
    for razon, amp, dec in ((1.0, 1.0, 0.22), (2.32, 0.6, 0.15), (4.25, 0.35, 0.09), (6.63, 0.2, 0.06)):
        f = f0 * razon * rng.uniform(0.98, 1.02)
        if f < SR / 2.2:
            x += amp * np.sin(2 * math.pi * f * t + rng.uniform(0, 6)) * np.exp(-t / (dec * rng.uniform(0.7, 1.3)))
    clic = rng.standard_normal(_n(0.004)) * envolvente(_n(0.004), 0.0002, 0.0012)
    x[: len(clic)] += filtro(clic, "highpass", 3000, 2) * 1.5
    return (x * fuerza).astype(np.float32)


def monedas(tiempos: list[float], fuerzas: list[float] | None = None, dur: float | None = None,
            semilla: int = 5, pans: list[float] | None = None) -> np.ndarray:
    """Varias monedas en los instantes dados (segundos desde el inicio del efecto), con eco."""
    rng = _rng(semilla)
    fuerzas = fuerzas or [1.0] * len(tiempos)
    pans = pans or [rng.uniform(-0.4, 0.4) for _ in tiempos]
    dur = dur or (max(tiempos) + 1.0)
    x = np.zeros((_n(dur) + _n(0.7), 2), np.float32)
    for k, (t0, fz, pn) in enumerate(zip(tiempos, fuerzas, pans)):
        m = estereo(moneda(semilla * 100 + k, fz), pn)
        i = _n(t0)
        x[i : i + len(m)] += m[: len(x) - i]
    x = eco(x, 0.13, 0.32, 4)
    x = reverberacion(x, 1.1, 0.28, 7000, semilla)
    return normalizar_pico(x[: _n(dur) + _n(1.0)])


def galope(dur: float, semilla: int = 6, frenar: float = 0.6, zancada: float = 0.43) -> np.ndarray:
    """Galope que se acerca: golpes graves en patrón de cuatro tiempos; frena al final."""
    rng = _rng(semilla)
    n = _n(dur + 0.6)
    x = np.zeros(n, np.float32)
    tiempos_golpe = []
    t = 0.0
    while t < dur:
        progreso = t / dur
        z = zancada * (1 + 0.9 * max(0.0, (t - (dur - frenar)) / frenar))
        for k, desfase in enumerate((0.0, 0.07, 0.15, 0.21)):
            tiempos_golpe.append((t + desfase * z / zancada, progreso, k))
        t += z
    for tg, progreso, k in tiempos_golpe:
        if tg >= dur:
            continue
        m = _n(0.16)
        tt = np.arange(m) / SR
        f = 85 * rng.uniform(0.85, 1.15) * np.exp(-tt * 18) + 45
        golpe = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.045)
        tierra = filtro(rng.standard_normal(m) * np.exp(-tt / 0.025), "bandpass", (180, 1400), 2) * 0.6
        clic = filtro(rng.standard_normal(m) * np.exp(-tt / 0.004), "highpass", 2500, 2) * 0.25
        acento = 1.0 if k in (0, 3) else 0.8
        cerca_ = 0.12 + 0.88 * progreso ** 1.7
        i = _n(tg)
        x[i : i + m] += (golpe + tierra + clic * cerca_) * acento * cerca_
    # se abre el brillo a medida que se acerca
    brillo = 500 + 6000 * (np.arange(n) / n) ** 1.5
    x = filtro_variable(x, brillo, tipo="graves")
    pan = np.linspace(-0.7, 0.15, n)
    y = estereo(x, pan)
    return normalizar_pico(reverberacion(y, 0.9, 0.2, 3000, semilla)[:n])


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


def impacto_lanza(semilla: int = 8) -> np.ndarray:
    """Lanza que se clava en madera: golpe grave + clic seco + vibración corta del asta."""
    rng = _rng(semilla)
    n = _n(1.6)
    t = np.arange(n) / SR
    f = 62 * np.exp(-t * 6) + 38
    grave = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t / 0.18) * 1.0
    cuerpo = filtro(rng.standard_normal(n) * np.exp(-t / 0.05), "lowpass", 600, 2) * 0.7
    clic = filtro(rng.standard_normal(n) * np.exp(-t / 0.006), "bandpass", (1800, 5200), 2) * 1.4
    madera = np.zeros(n)
    for fm, dec, amp in ((640, 0.06, 0.6), (1370, 0.04, 0.45), (2150, 0.03, 0.3), (310, 0.08, 0.5)):
        madera += amp * np.sin(2 * math.pi * fm * t) * np.exp(-t / dec)
    flexion = np.abs(np.sin(2 * math.pi * 21 * t)) * np.exp(-t / 0.28)
    tono = np.sin(2 * math.pi * 168 * (1 - 0.04 * t) * t) + 0.4 * np.sin(2 * math.pi * 336 * t)
    vibra = filtro(tono * flexion, "bandpass", (100, 900), 2) * 0.5
    vibra[: _n(0.02)] *= np.linspace(0, 1, _n(0.02))
    x = grave + cuerpo + clic + madera + vibra
    y = estereo(x, 0.15)
    return normalizar_pico(reverberacion(y, 1.4, 0.22, 3500, semilla)[:n], 0.9)


def paso_del_tiempo(dur: float = 2.2, semilla: int = 9) -> np.ndarray:
    """'Reloj de arena': lluvia de granos finos que crece y se apaga, con un barrido suave."""
    rng = _rng(semilla)
    n = _n(dur)
    u = np.linspace(0, 1, n)
    granos = rng.standard_normal(n) * (rng.random(n) < 0.08)
    granos = filtro(granos, "highpass", 2500, 2)
    arena = filtro_variable(granos + 0.15 * rng.standard_normal(n), 2500 + 4500 * np.sin(np.pi * u), 1.2)
    aire = filtro_variable(ruido_rosa(n, rng), 300 * (12 ** np.sin(np.pi * u * 0.95)), 1.0) * 0.6
    env = np.sin(np.pi * u) ** 2
    pan = 0.5 * np.sin(np.pi * 2 * u)
    y = estereo((arena + aire) * env, pan)
    return normalizar_pico(reverberacion(y, 1.6, 0.4, 7000, semilla)[:n])


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
