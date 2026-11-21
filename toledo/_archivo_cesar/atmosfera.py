"""Atmósfera reutilizable: estrellas, niebla y humo, partículas (brasas, polvo, astillas) y llamas.

Todo es determinista: el estado en el tiempo t se calcula de forma analítica a partir de una
semilla, así cualquier cuadro se puede renderizar suelto y en cualquier orden (procesos en
paralelo, fotogramas de revisión).
"""

from __future__ import annotations

import functools
import math

import cairo
import numpy as np

import siluetas as S
from graficos import H, W, Campo, ampliar, color

# --------------------------------------------------------------------------- puntos de luz


@functools.lru_cache(maxsize=64)
def _nucleo(radio_q: int, sub: int) -> np.ndarray:
    """Núcleo gaussiano de radio radio_q/4 px con desplazamiento subpíxel (sub = 0..15)."""
    r = radio_q / 4.0
    ox, oy = (sub % 4) / 4.0, (sub // 4) / 4.0
    m = int(math.ceil(r * 3)) + 1
    yy, xx = np.mgrid[-m : m + 1, -m : m + 1].astype(np.float32)
    k = np.exp(-((xx - ox) ** 2 + (yy - oy) ** 2) / (2 * r * r))
    return k


def salpicar(img: np.ndarray, x: float, y: float, radio: float, col, intensidad: float,
             modo: str = "suma") -> None:
    """Punto difuso en (x, y). modo 'suma' (luz) o 'sobre' (polvo opaco)."""
    if intensidad <= 0.002:
        return
    radio = max(0.35, radio)
    xi, yi = int(math.floor(x)), int(math.floor(y))
    sub = int((x - xi) * 4) + 4 * int((y - yi) * 4)
    k = _nucleo(max(1, int(round(radio * 4))), sub)
    m = k.shape[0] // 2
    y0, x0 = yi - m, xi - m
    h, w = img.shape[:2]
    a0, b0 = max(0, y0), max(0, x0)
    a1, b1 = min(h, y0 + k.shape[0]), min(w, x0 + k.shape[1])
    if a0 >= a1 or b0 >= b1:
        return
    kk = k[a0 - y0 : a1 - y0, b0 - x0 : b1 - x0, None] * intensidad
    c = color(col)
    if modo == "suma":
        img[a0:a1, b0:b1] += kk * c
    else:
        kk = np.minimum(kk, 1.0)
        img[a0:a1, b0:b1] = img[a0:a1, b0:b1] * (1 - kk) + kk * c


# --------------------------------------------------------------------------- estrellas


class Estrellas:
    def __init__(self, n: int, semilla: int, zona=(0, 0, W, H * 0.55)):
        r = np.random.default_rng(semilla)
        x0, y0, x1, y1 = zona
        self.x = r.uniform(x0, x1, n)
        self.y = r.uniform(y0, y1, n) ** 1.0
        self.b = r.pareto(2.2, n) * 0.25 + 0.15
        self.f = r.uniform(0.6, 2.5, n)
        self.ph = r.uniform(0, math.tau, n)
        self.tam = r.uniform(0.45, 0.9, n)

    def dibujar(self, img, t: float, opacidad: float = 1.0, dx: float = 0.0, dy: float = 0.0,
                zoom: float = 1.0, col="#DDE6FF", mascara: np.ndarray | None = None) -> None:
        if opacidad <= 0.01:
            return
        brillo = self.b * (0.7 + 0.3 * np.sin(t * self.f * 2 + self.ph)) * opacidad
        xs = (self.x - W / 2) * zoom + W / 2 - dx
        ys = (self.y - H / 2) * zoom + H / 2 - dy
        for x, y, b, s in zip(xs, ys, brillo, self.tam):
            if 0 <= x < W and 0 <= y < H:
                if mascara is not None:
                    b *= mascara[int(y), int(x)]
                salpicar(img, x, y, s, col, min(b, 1.2))


# --------------------------------------------------------------------------- niebla y humo


class Niebla:
    """Niebla en bandas: ruido periódico que se desplaza, calculado a 1/4 de resolución."""

    def __init__(self, semilla: int, celda: int = 128):
        self.campo = Campo(semilla, 512, celda, 5, 0.55)
        self.campo2 = Campo(semilla + 77, 512, celda // 2, 4, 0.5)

    def alfa(self, t: float, *, y0: float, y1: float, densidad: float = 0.6, vel=(14.0, 0.0),
             escala: float = 1.0, umbral: float = 0.35, dx: float = 0.0, dy: float = 0.0,
             suavidad: float = 0.25, f: int = 4) -> np.ndarray:
        """Alfa (H, W). La banda va de y0 a y1 (px de pantalla) con bordes suaves.

        `vel`: deriva de la niebla en px/s de pantalla; (dx, dy): movimiento de cámara.
        `escala`: píxeles de textura por píxel reducido (mayor = jirones más pequeños).
        """
        h, w = H // f, W // f
        e = escala
        xo = (dx - vel[0] * t) / f * e
        yo = (dy - vel[1] * t) / f * e
        a = self.campo.muestra(h, w, xo, yo, e)
        b = self.campo2.muestra(h, w, xo * 1.7 + 91, yo * 1.3 + 33, e * 1.6)
        n = a * 0.65 + b * 0.35
        n = np.clip((n - umbral) / max(1e-3, suavidad), 0, 1)
        n = n * n * (3 - 2 * n)
        ys = (np.arange(h, dtype=np.float32) + 0.5) * f
        banda = np.clip((ys - y0) / max(1, (y1 - y0) * 0.35), 0, 1) * np.clip((y1 - ys) / max(1, (y1 - y0) * 0.35), 0, 1)
        banda = banda * banda * (3 - 2 * banda)
        return ampliar(n * banda[:, None] * densidad)


def componer_niebla(img: np.ndarray, alfa: np.ndarray, col, luz: np.ndarray | None = None,
                    peso_luz: float = 0.8) -> np.ndarray:
    """Niebla de color `col`; si hay mapa de luz, la niebla se ilumina donde hay resplandor."""
    c = color(col)
    a = alfa[..., None]
    if luz is not None:
        img *= 1 - a
        img += a * (c + luz * peso_luz)
    else:
        img *= 1 - a
        img += a * c
    return img


# --------------------------------------------------------------------------- partículas


class Brasas:
    """Chispas que suben desde emisores, con temblor lateral y vida limitada."""

    def __init__(self, emisores: list[tuple[float, float]], por_emisor: int, semilla: int,
                 vida=(1.2, 2.6), subida=(40, 110), deriva: float = 22.0, tam=(0.6, 1.5),
                 dispersion: float = 8.0):
        r = np.random.default_rng(semilla)
        self.p = []
        for ex, ey in emisores:
            for _ in range(por_emisor):
                self.p.append(dict(ex=ex + r.normal(0, dispersion), ey=ey + r.normal(0, dispersion * 0.4),
                                   vida=r.uniform(*vida), off=r.uniform(0, 10), v=r.uniform(*subida),
                                   f=r.uniform(1.0, 3.0), ph=r.uniform(0, 6.28), amp=r.uniform(0.3, 1.0) * deriva,
                                   tam=r.uniform(*tam), viento=r.uniform(8, 26)))

    def dibujar(self, img, t: float, transformar=None, col="#FFB347", intensidad: float = 1.0,
                viento: float = 1.0) -> None:
        for q in self.p:
            edad = (t + q["off"]) % q["vida"]
            u = edad / q["vida"]
            x = q["ex"] + math.sin(edad * q["f"] * 2 + q["ph"]) * q["amp"] * u + q["viento"] * viento * edad
            y = q["ey"] - q["v"] * edad - 6 * edad * edad
            if transformar is not None:
                x, y, esc = transformar(x, y)
            else:
                esc = 1.0
            b = (1 - u) ** 1.5 * min(1.0, u * 8) * (0.6 + 0.4 * math.sin(t * 17 + q["ph"]))
            salpicar(img, x, y, q["tam"] * esc, col, b * intensidad * 1.4)


class Polvo:
    """Motas suspendidas que derivan despacio (polvo en la luz, ceniza, nieve fina)."""

    def __init__(self, n: int, semilla: int, zona=(0, 0, W, H), vel=(6.0, -3.0), tam=(0.8, 3.0)):
        r = np.random.default_rng(semilla)
        x0, y0, x1, y1 = zona
        self.zona = zona
        self.x = r.uniform(x0, x1, n)
        self.y = r.uniform(y0, y1, n)
        self.vx = vel[0] * r.uniform(0.4, 1.6, n)
        self.vy = vel[1] * r.uniform(0.4, 1.6, n)
        self.tam = r.uniform(*tam, n)
        self.b = r.uniform(0.2, 1.0, n)
        self.ph = r.uniform(0, 6.28, n)

    def dibujar(self, img, t: float, col, intensidad: float = 0.5, luz: np.ndarray | None = None,
                modo: str = "suma") -> None:
        x0, y0, x1, y1 = self.zona
        xs = x0 + (self.x - x0 + self.vx * t + 9 * np.sin(t * 0.7 + self.ph)) % (x1 - x0)
        ys = y0 + (self.y - y0 + self.vy * t + 6 * np.cos(t * 0.5 + self.ph)) % (y1 - y0)
        for x, y, s, b, ph in zip(xs, ys, self.tam, self.b, self.ph):
            k = b * intensidad * (0.6 + 0.4 * math.sin(t * 1.3 + ph))
            if luz is not None and 0 <= y < H and 0 <= x < W:
                k *= float(luz[int(y), int(x)])
            salpicar(img, x, y, s, col, k, modo)


# --------------------------------------------------------------------------- llamas


def llama(img: np.ndarray, x: float, y: float, alto: float, ancho: float, t: float,
          semilla: int = 0, intensidad: float = 1.0, nucleo="#FFF2C6", borde="#E08A2E") -> None:
    """Llama aditiva (punta hacia arriba) con núcleo claro y borde ámbar."""
    w = int(ancho * 3 + 12)
    h = int(alto * 1.6 + 12)
    ox, oy = int(x - w / 2), int(y - alto * 1.35 - 6)
    s, c = S.lienzo(w, h)
    lx, ly = x - ox, y - oy
    pts = S.llama_contorno(lx, ly, alto, ancho, t, semilla)
    grad = cairo.RadialGradient(lx, ly - alto * 0.25, 1, lx, ly - alto * 0.3, alto * 0.9)
    b = color(borde)
    n = color(nucleo)
    grad.add_color_stop_rgba(0.0, n[0], n[1], n[2], 1.0)
    grad.add_color_stop_rgba(0.35, b[0], b[1], b[2], 0.95)
    grad.add_color_stop_rgba(1.0, b[0] * 0.6, b[1] * 0.3, b[2] * 0.1, 0.0)
    c.set_source(grad)
    S.camino(c, pts)
    c.fill()
    pts_n = S.llama_contorno(lx, ly, alto * 0.55, ancho * 0.45, t + 0.05, semilla + 1)
    c.set_source_rgba(n[0], n[1], n[2], 0.9)
    S.camino(c, pts_n)
    c.fill()
    capa = S.a_rgba(s)
    x0, y0 = max(0, ox), max(0, oy)
    x1, y1 = min(img.shape[1], ox + w), min(img.shape[0], oy + h)
    if x0 < x1 and y0 < y1:
        img[y0:y1, x0:x1] += capa[y0 - oy : y1 - oy, x0 - ox : x1 - ox, :3] * intensidad


def parpadeo(t: float, semilla: int = 0) -> float:
    """Intensidad 0.8..1.1 de una llama que titila (suma de senos inconmensurables)."""
    a = semilla * 1.618
    return 0.94 + 0.06 * math.sin(t * 11.0 + a) + 0.04 * math.sin(t * 23.3 + a * 2) + 0.03 * math.sin(t * 5.1 + a * 3)


class Humo:
    """Columnas de humo que suben y se deshilachan (ruido que se desplaza hacia arriba)."""

    def __init__(self, semilla: int):
        self.campo = Campo(semilla, 512, 64, 5, 0.55)

    def alfa(self, t: float, columnas: list[tuple[float, float, float, float]], *, vel: float = 28.0,
             viento: float = 18.0, densidad: float = 0.5, f: int = 4) -> np.ndarray:
        """columnas: [(x_base, y_base, ancho, alto)] en px de pantalla."""
        h, w = H // f, W // f
        ys = (np.arange(h, dtype=np.float32) + 0.5) * f
        xs = (np.arange(w, dtype=np.float32) + 0.5) * f
        n = self.campo.muestra(h, w, 0.0, vel * t / f, 1.4, 1.0)
        total = np.zeros((h, w), np.float32)
        for k, (xb, yb, ancho, alto) in enumerate(columnas):
            subida = np.clip((yb - ys) / alto, 0, 1)[:, None]
            centro = xb + viento * subida * alto / 120.0 + 14 * np.sin(subida * 5 + t * 0.7 + k)
            abre = ancho * (0.35 + 1.4 * subida)
            perfil = np.exp(-((xs[None, :] - centro) / abre) ** 2)
            vida = np.clip(np.sin(np.pi * np.clip(subida, 0, 1)), 0, 1) ** 0.7 * (ys[:, None] < yb)
            total += perfil * vida
        total = np.clip(total, 0, 1) * np.clip((n - 0.25) * 1.8, 0, 1)
        return ampliar(total * densidad)
