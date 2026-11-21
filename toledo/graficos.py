"""Motor gráfico común a todas las escenas.

Todo trabaja con imágenes float32 en 0..1 (alto, ancho, canales). Las capas con transparencia
son RGBA *premultiplicadas* (el color ya viene multiplicado por la opacidad), igual que en cairo.

Piezas:
- curvas de tiempo (suave, tramo...)
- ruido y texturas (papel, niebla periódica)
- cámara: recorte con zoom y paralaje sobre capas grandes ya dibujadas
- luces a baja resolución (resplandores de antorchas, velas, luna)
- composición y acabado (resplandor, viñeta, grano, papel, fundido)
- texto con Cinzel o EB Garamond (con interletraje)
"""

from __future__ import annotations

import functools
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

W, H, FPS = 1920, 1080, 30
RAIZ = Path(__file__).resolve().parent
FUENTES = RAIZ / "fuentes"

# --------------------------------------------------------------------------- curvas de tiempo


def lim(x: float, a: float = 0.0, b: float = 1.0) -> float:
    return a if x < a else b if x > b else x


def tramo(t: float, a: float, b: float) -> float:
    """0 antes de a, 1 después de b, lineal entre ambos."""
    if b == a:
        return 1.0 if t >= b else 0.0
    return lim((t - a) / (b - a))


def suave(x: float) -> float:
    x = lim(x)
    return x * x * (3 - 2 * x)


def suave5(x: float) -> float:
    x = lim(x)
    return x * x * x * (x * (6 * x - 15) + 10)


def sale(x: float, p: float = 3.0) -> float:
    """Arranca rápido y frena (ease-out)."""
    return 1 - (1 - lim(x)) ** p


def entra(x: float, p: float = 3.0) -> float:
    """Arranca lento y acelera (ease-in)."""
    return lim(x) ** p


def mezclar(a, b, x):
    return a + (b - a) * x


def campana(t: float, a: float, b: float, rampa: float) -> float:
    """1 entre a y b con rampas suaves de `rampa` segundos a cada lado."""
    return suave(tramo(t, a - rampa, a)) * (1 - suave(tramo(t, b, b + rampa)))


# --------------------------------------------------------------------------- ruido y texturas


def caja_dentro(caja, w: float, h: float) -> tuple[float, float, float, float]:
    """Una caja de recorte (x0, y0, x1, y1) metida dentro de una imagen de w×h. PIL rechaza la caja
    que se sale aunque sea por redondeo (una esquina en -1e-13) o por truncar con int(); pasó en el
    mapa de la escena 1, la foto del puerto de la 3 y el titular de la 6. Toda caja de `resize` pasa
    por aquí; dentro de la imagen no cambia nada."""
    x0, y0, x1, y1 = caja
    x0, y0 = min(max(x0, 0.0), float(w)), min(max(y0, 0.0), float(h))
    return x0, y0, max(min(x1, float(w)), x0), max(min(y1, float(h)), y0)


def _ampliar_canal(a: np.ndarray, w: int, h: int, filtro=Image.BILINEAR, caja=None) -> np.ndarray:
    img = Image.fromarray(np.ascontiguousarray(a, dtype=np.float32), "F")
    caja = caja_dentro(caja, img.width, img.height) if caja is not None else None
    return np.array(img.resize((w, h), filtro, box=caja), dtype=np.float32)  # copia escribible


def ampliar(a: np.ndarray, w: int = W, h: int = H, filtro=Image.BILINEAR) -> np.ndarray:
    """Redimensiona un arreglo float32 2D o 3D (un canal a la vez, en C vía Pillow)."""
    if a.ndim == 2:
        return _ampliar_canal(a, w, h, filtro)
    return np.stack([_ampliar_canal(a[..., k], w, h, filtro) for k in range(a.shape[2])], axis=-1)


def reducir(a: np.ndarray, f: int) -> np.ndarray:
    """Promedio por bloques f×f (las dimensiones deben ser múltiplos de f)."""
    h, w = a.shape[:2]
    if a.ndim == 2:
        return a.reshape(h // f, f, w // f, f).mean(axis=(1, 3))
    return a.reshape(h // f, f, w // f, f, a.shape[2]).mean(axis=(1, 3))


def ruido_suave(h: int, w: int, celda: int, semilla: int, periodico: bool = False) -> np.ndarray:
    """Ruido de valor interpolado (bicúbico), 0..1. Si `periodico`, celda debe dividir h y w."""
    r = np.random.default_rng(semilla)
    if periodico:
        gh, gw = h // celda, w // celda
        g = r.random((gh, gw), dtype=np.float32)
        pad = 3
        gp = np.pad(g, pad, mode="wrap")
        grande = _ampliar_canal(gp, (gw + 2 * pad) * celda, (gh + 2 * pad) * celda, Image.BICUBIC)
        return grande[pad * celda : pad * celda + h, pad * celda : pad * celda + w].copy()
    gh, gw = math.ceil(h / celda) + 3, math.ceil(w / celda) + 3
    g = r.random((gh, gw), dtype=np.float32)
    grande = _ampliar_canal(g, gw * celda, gh * celda, Image.BICUBIC)
    return grande[celda : celda + h, celda : celda + w].copy()


def fbm(h, w, celda, octavas=4, persistencia=0.5, semilla=0, periodico=False) -> np.ndarray:
    """Suma de octavas de ruido; resultado aproximadamente en 0..1 con media 0.5."""
    total = np.zeros((h, w), np.float32)
    amp, suma = 1.0, 0.0
    for o in range(octavas):
        c = max(1, celda >> o)
        total += amp * ruido_suave(h, w, c, semilla * 7919 + o * 104729, periodico)
        suma += amp
        amp *= persistencia
    total /= suma
    # Normalizar a media 0.5 y desviación 0.18: mismo contraste sin importar las octavas.
    return np.clip((total - total.mean()) / (total.std() + 1e-6) * 0.18 + 0.5, 0, 1)


@functools.lru_cache(maxsize=8)
def textura_papel(semilla: int = 3, w: int = W, h: int = H) -> np.ndarray:
    """Textura multiplicativa de papel (≈1.0): manchas, fibras y grano fino."""
    r = np.random.default_rng(semilla)
    manchas = fbm(h, w, 256, 3, 0.5, semilla) - 0.5
    medio = fbm(h, w, 32, 3, 0.5, semilla + 1) - 0.5
    fino = ndimage.gaussian_filter(r.standard_normal((h, w)).astype(np.float32), 0.7)
    fib_h = ndimage.gaussian_filter(r.standard_normal((h, w)).astype(np.float32), (0.5, 7))
    fib_v = ndimage.gaussian_filter(r.standard_normal((h, w)).astype(np.float32), (7, 0.5))
    tex = 1.0 + 0.12 * manchas + 0.07 * medio + 0.02 * fino + 0.05 * fib_h + 0.035 * fib_v
    return tex.astype(np.float32)


class Campo:
    """Textura periódica de ruido que se muestrea con desplazamiento (niebla, humo, nubes)."""

    def __init__(self, semilla: int, tam: int = 512, celda: int = 128, octavas: int = 4,
                 persistencia: float = 0.55):
        self.tam = tam
        self.t = fbm(tam, tam, celda, octavas, persistencia, semilla, periodico=True)

    def muestra(self, h: int, w: int, x0: float, y0: float, escala: float,
                escala_y: float | None = None) -> np.ndarray:
        ey = escala if escala_y is None else escala_y
        yy = (y0 + np.arange(h, dtype=np.float32) * ey)[:, None]
        xx = (x0 + np.arange(w, dtype=np.float32) * escala)[None, :]
        yy, xx = np.broadcast_arrays(yy, xx)
        return ndimage.map_coordinates(self.t, [yy, xx], order=1, mode="grid-wrap").astype(np.float32)


# --------------------------------------------------------------------------- color y gradientes


def color(hex_o_rgb) -> np.ndarray:
    if isinstance(hex_o_rgb, str):
        v = hex_o_rgb.lstrip("#")
        return np.array([int(v[i : i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)
    return np.asarray(hex_o_rgb, np.float32)


def lienzo_color(c, w: int = W, h: int = H) -> np.ndarray:
    return np.broadcast_to(color(c), (h, w, 3)).copy()


def gradiente_vertical(paradas: list[tuple[float, object]], w: int = W, h: int = H,
                       y0: float = 0.0, escala: float = 1.0) -> np.ndarray:
    """paradas: [(posición 0..1, color), ...] de arriba abajo. y0/escala permiten moverlo con cámara."""
    pos = np.array([p for p, _ in paradas], np.float32)
    cols = np.stack([color(c) for _, c in paradas])
    y = (np.arange(h, dtype=np.float32) / (h - 1) - 0.5) / escala + 0.5 + y0
    filas = np.stack([np.interp(y, pos, cols[:, k]) for k in range(3)], axis=-1).astype(np.float32)
    return np.broadcast_to(filas[:, None, :], (h, w, 3)).copy()


@functools.lru_cache(maxsize=4)
def _malla(f: int):
    h, w = H // f, W // f
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return (yy + 0.5) * f, (xx + 0.5) * f


class Luces:
    """Acumula resplandores a 1/f de resolución y los amplía al final (son suaves de todos modos)."""

    def __init__(self, f: int = 4):
        self.f = f
        self.yy, self.xx = _malla(f)
        self.a = np.zeros(self.yy.shape + (3,), np.float32)

    def punto(self, x: float, y: float, radio: float, c, intensidad: float = 1.0,
              forma: str = "suave", achatado: float = 1.0) -> None:
        if intensidad <= 0 or radio <= 0:
            return
        alcance = radio * (3.2 if forma == "gauss" else 6.0)
        f = self.f
        h, w = self.yy.shape
        y0, y1 = int(max(0, (y - alcance * achatado) // f)), int(min(h, (y + alcance * achatado) // f + 2))
        x0, x1 = int(max(0, (x - alcance) // f)), int(min(w, (x + alcance) // f + 2))
        if y0 >= y1 or x0 >= x1:
            return
        dy = (self.yy[y0:y1, x0:x1] - y) / achatado
        dx = self.xx[y0:y1, x0:x1] - x
        d2 = (dx * dx + dy * dy) / (radio * radio)
        if forma == "gauss":
            v = np.exp(-d2)
        else:  # caída lenta, como luz en niebla
            v = 1.0 / (1.0 + d2) ** 1.6
        self.a[y0:y1, x0:x1] += v[..., None] * (color(c) * intensidad)

    def resultado(self) -> np.ndarray:
        return ampliar(self.a)


def rayos_de_luz(fuente: np.ndarray, cx: float, cy: float, muestras: int = 32, alcance: float = 0.85,
                 decae: float = 0.97, f: int = 4) -> np.ndarray:
    """Rayos crepusculares: la luz de `fuente` (h×w) se arrastra en línea recta hacia (cx, cy).

    Donde una silueta tapa la fuente quedan franjas de sombra que salen del sol; es el mismo
    desenfoque radial que usan los motores de juego, hecho a 1/f de resolución.
    """
    p = reducir(fuente, f)
    h, w = p.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cxs, cys = cx / f, cy / f
    acc = np.zeros_like(p)
    peso, total = 1.0, 0.0
    for i in range(muestras):
        s = 1.0 - alcance * i / muestras
        acc += ndimage.map_coordinates(p, [cys + (yy - cys) * s, cxs + (xx - cxs) * s],
                                       order=1, mode="nearest") * peso
        total += peso
        peso *= decae
    return ampliar(acc / total)


# --------------------------------------------------------------------------- cámara y capas


def a_pil(rgba: np.ndarray) -> Image.Image:
    """float32 RGBA premultiplicado -> imagen Pillow 'RGBa' (8 bits)."""
    u8 = np.clip(rgba * 255 + 0.5, 0, 255).astype(np.uint8)
    return Image.frombytes("RGBa", (u8.shape[1], u8.shape[0]), u8.tobytes())


def de_pil(img: Image.Image) -> np.ndarray:
    return np.asarray(img, dtype=np.float32) * (1.0 / 255.0)


class Capa:
    """Imagen grande ya dibujada que la cámara recorre.

    `densidad`: píxeles de la capa por píxel de pantalla a zoom 1 (p. ej. 1.3 permite acercar
    hasta 1.3× sin perder nitidez). `paralaje`: cuánto la afecta el movimiento de cámara
    (0 = fija como el cielo lejano, 1 = se mueve con la cámara completa).
    """

    def __init__(self, rgba: np.ndarray | Image.Image, densidad: float = 1.0, paralaje: float = 1.0):
        self.img = rgba if isinstance(rgba, Image.Image) else a_pil(rgba)
        self.densidad = densidad
        self.paralaje = paralaje

    def ver(self, cx: float = 0.0, cy: float = 0.0, zoom: float = 1.0) -> np.ndarray:
        """Recorte de pantalla: (cx, cy) desplazamiento en px de pantalla, zoom ≥ ~1."""
        k = self.paralaje
        z = 1.0 + (zoom - 1.0) * k
        lw, lh = self.img.size
        d = self.densidad
        bw, bh = W * d / z, H * d / z
        x0 = lw / 2 + cx * k * d - bw / 2
        y0 = lh / 2 + cy * k * d - bh / 2
        x0 = min(max(x0, 0), lw - bw)
        y0 = min(max(y0, 0), lh - bh)
        return de_pil(self.img.resize((W, H), Image.BILINEAR, box=caja_dentro((x0, y0, x0 + bw, y0 + bh), lw, lh)))


def sobre(base: np.ndarray, capa: np.ndarray, opacidad: float = 1.0) -> np.ndarray:
    """Compone una capa RGBA premultiplicada sobre una base RGB (en el lugar)."""
    if opacidad <= 0:
        return base
    a = capa[..., 3:4] * opacidad
    base *= 1.0 - a
    base += capa[..., :3] * opacidad
    return base


def sobre_en(base: np.ndarray, capa: np.ndarray, x: int, y: int, opacidad: float = 1.0) -> np.ndarray:
    """Como `sobre`, pero la capa es más chica y se coloca con su esquina en (x, y)."""
    h, w = capa.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(base.shape[1], x + w), min(base.shape[0], y + h)
    if x0 >= x1 or y0 >= y1:
        return base
    trozo = capa[y0 - y : y1 - y, x0 - x : x1 - x]
    sobre(base[y0:y1, x0:x1], trozo, opacidad)
    return base


def tenir(alfa: np.ndarray, c, opacidad: float = 1.0) -> np.ndarray:
    """Máscara (h, w) -> capa RGBA premultiplicada de un solo color."""
    a = alfa[..., None] * opacidad
    return np.concatenate([a * color(c), a], axis=-1).astype(np.float32)


def desenfoque(a: np.ndarray, sigma: float) -> np.ndarray:
    """Desenfoque gaussiano rápido: reduce, desenfoca y vuelve a ampliar."""
    if sigma <= 0:
        return a
    h, w = a.shape[:2]
    f = 1
    while sigma / f > 6 and h % (f * 2) == 0 and w % (f * 2) == 0:
        f *= 2
    peq = reducir(a, f) if f > 1 else a
    s = sigma / f
    peq = ndimage.gaussian_filter(peq, (s, s, 0) if a.ndim == 3 else s)
    return ampliar(peq, w, h) if f > 1 else peq


def contraluz(alfa: np.ndarray, dx: int, dy: int, suavizado: float = 1.5) -> np.ndarray:
    """Borde de la silueta que mira hacia la luz (dx, dy apuntan hacia la fuente)."""
    vecino = np.roll(np.roll(alfa, -dy, axis=0), -dx, axis=1)
    borde = np.clip(alfa - vecino, 0, 1)
    if suavizado > 0:
        borde = ndimage.gaussian_filter(borde, suavizado)
    return borde * alfa


def sombra_proyectada(alfa: np.ndarray, dx: int, dy: int, sigma: float) -> np.ndarray:
    """Sombra suave desplazada (efecto de recorte de papel separado del fondo)."""
    s = np.roll(np.roll(alfa, dy, axis=0), dx, axis=1)
    return ndimage.gaussian_filter(s, sigma)


# --------------------------------------------------------------------------- acabado


@functools.lru_cache(maxsize=4)
def mascara_vineta(fuerza: float, forma: float = 2.2) -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx = (xx - W / 2) / (W / 2)
    ny = (yy - H / 2) / (H / 2)
    r = np.sqrt(nx * nx * 0.85 + ny * ny)
    return np.clip(1.0 - fuerza * r ** forma, 0, 1)[..., None].astype(np.float32)


@functools.lru_cache(maxsize=2)
def banco_grano(n: int = 8, semilla: int = 11) -> np.ndarray:
    r = np.random.default_rng(semilla)
    banco = []
    for _ in range(n):
        g = r.standard_normal((H // 2, W // 2)).astype(np.float32)
        g = ndimage.gaussian_filter(g, 0.55)
        g = ampliar(g, W, H, Image.BILINEAR)
        g /= g.std() + 1e-6
        banco.append(g.astype(np.float16))
    return np.stack(banco)


def resplandor(img: np.ndarray, umbral: float = 0.6, fuerza: float = 0.35, sigma: float = 28) -> np.ndarray:
    """Bloom: lo más brillante se difumina y se suma (luz que 'sangra' en la niebla)."""
    peq = reducir(img, 4)
    lum = peq.max(axis=-1, keepdims=True)
    brillo = peq * np.clip((lum - umbral) / (1 - umbral + 1e-6), 0, 1)
    a = ndimage.gaussian_filter(brillo, (sigma / 4, sigma / 4, 0))
    b = ndimage.gaussian_filter(brillo, (sigma, sigma, 0))
    img += ampliar(a * 0.6 + b * 0.8) * fuerza
    return img


def acabado(img: np.ndarray, cuadro: int, *, vineta: float = 0.45, grano: float = 0.015,
            papel: float = 0.0, bloom: float = 0.3, umbral_bloom: float = 0.62,
            opacidad: float = 1.0, semilla_papel: int = 3) -> np.ndarray:
    """Pasos finales comunes: resplandor, papel, viñeta, grano y fundido a negro."""
    if bloom > 0:
        resplandor(img, umbral_bloom, bloom)
    if papel > 0:
        img *= (1.0 + (textura_papel(semilla_papel) - 1.0) * papel)[..., None]
    if vineta > 0:
        img *= mascara_vineta(round(vineta, 3))
    if grano > 0:
        g = banco_grano()[cuadro % 8].astype(np.float32)
        lum = img.mean(axis=-1, keepdims=True)
        peso = 0.35 + 0.65 * np.clip(1.0 - np.abs(lum - 0.35) * 1.4, 0, 1)
        img += g[..., None] * (grano * peso)
    if opacidad < 1.0:
        img *= opacidad
    return img


def a_bytes(img: np.ndarray) -> bytes:
    return np.clip(img * 255.0 + 0.5, 0, 255).astype(np.uint8).tobytes()


def a_imagen(img: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(img * 255.0 + 0.5, 0, 255).astype(np.uint8), "RGB")


# --------------------------------------------------------------------------- texto


@functools.lru_cache(maxsize=32)
def fuente(nombre: str, tam: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FUENTES / nombre), tam)


def texto_alfa(texto: str, nombre: str, tam: int, interletra: float = 0.0,
               margen: int | None = None) -> np.ndarray:
    """Máscara float32 del texto. `interletra` en fracción del tamaño (0.1 = 10 %)."""
    f = fuente(nombre, tam)
    asc, desc = f.getmetrics()
    margen = int(tam * 0.4) if margen is None else margen
    if interletra == 0:
        ancho = f.getlength(texto)
        img = Image.new("L", (int(math.ceil(ancho)) + 2 * margen, asc + desc + 2 * margen), 0)
        ImageDraw.Draw(img).text((margen, margen), texto, font=f, fill=255)
        return np.asarray(img, np.float32) / 255.0
    avances = [f.getlength(c) for c in texto]
    ancho = sum(avances) + interletra * tam * (len(texto) - 1)
    img = Image.new("L", (int(math.ceil(ancho)) + 2 * margen, asc + desc + 2 * margen), 0)
    d = ImageDraw.Draw(img)
    x = float(margen)
    for c, a in zip(texto, avances):
        d.text((x, margen), c, font=f, fill=255)
        x += a + interletra * tam
    return np.asarray(img, np.float32) / 255.0


def escalar_alfa(alfa: np.ndarray, escala: float) -> np.ndarray:
    h, w = alfa.shape
    return _ampliar_canal(alfa, max(1, int(round(w * escala))), max(1, int(round(h * escala))),
                          Image.BICUBIC).clip(0, 1)


def colocar(rgba, cx: float, cy: float, escala: float = 1.0, angulo: float = 0.0,
            w: int = W, h: int = H) -> np.ndarray:
    """Coloca una imagen RGBA premultiplicada en pantalla con centro, escala y giro (radianes).

    Se usa la transformación inversa de Pillow: para cada píxel de salida se busca su punto
    en la imagen original. Conviene que la escala no baje mucho de 0.7 (no promedia al reducir).
    """
    img = rgba if isinstance(rgba, Image.Image) else a_pil(rgba)
    iw, ih = img.size
    ca, sa = math.cos(angulo), math.sin(angulo)
    a, b = ca / escala, sa / escala
    d, e = -sa / escala, ca / escala
    c0 = iw / 2 - (a * cx + b * cy)
    f0 = ih / 2 - (d * cx + e * cy)
    salida = img.transform((w, h), Image.AFFINE, (a, b, c0, d, e, f0), resample=Image.BILINEAR)
    return de_pil(salida)
