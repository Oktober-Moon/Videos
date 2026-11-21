"""Primitivas de dibujo vectorial con cairo: lienzo, curvas suaves, rellenos y conversión a numpy.

Convenciones: coordenadas de pantalla con y hacia abajo; las capas salen como RGBA float32
premultiplicado (lo que esperan `graficos.sobre` y compañía).
"""

from __future__ import annotations

import math

import cairo
import numpy as np

TAU = math.tau


def lienzo(w: int, h: int) -> tuple[cairo.ImageSurface, cairo.Context]:
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(w), int(h))
    c = cairo.Context(s)
    c.set_antialias(cairo.ANTIALIAS_GOOD)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    return s, c


def _datos(s: cairo.ImageSurface) -> np.ndarray:
    s.flush()
    h, w, st = s.get_height(), s.get_width(), s.get_stride()
    return np.ndarray((h, st // 4, 4), np.uint8, s.get_data())[:, :w]


def a_rgba(s: cairo.ImageSurface) -> np.ndarray:
    """Superficie cairo -> float32 RGBA premultiplicado."""
    return _datos(s)[..., [2, 1, 0, 3]].astype(np.float32) * (1.0 / 255.0)


def a_alfa(s: cairo.ImageSurface) -> np.ndarray:
    return _datos(s)[..., 3].astype(np.float32) * (1.0 / 255.0)


def tinta(c: cairo.Context, col, a: float = 1.0) -> None:
    c.set_source_rgba(float(col[0]), float(col[1]), float(col[2]), a)


def camino(c: cairo.Context, pts, cerrado: bool = True, tension: float = 1.0) -> None:
    """Curva Catmull-Rom que pasa por todos los puntos (convertida a Bézier)."""
    p = [np.asarray(q, float) for q in pts]
    n = len(p)
    if n < 2:
        return
    c.move_to(*p[0])
    tramos = n if cerrado else n - 1
    for i in range(tramos):
        p0 = p[i - 1] if (i > 0 or cerrado) else p[i]
        p1, p2 = p[i], p[(i + 1) % n]
        p3 = p[(i + 2) % n] if (i + 2 < n or cerrado) else p2
        c1 = p1 + (p2 - p0) / 6.0 * tension
        c2 = p2 - (p3 - p1) / 6.0 * tension
        c.curve_to(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    if cerrado:
        c.close_path()


def rellenar(c: cairo.Context, pts, suave: bool = True, tension: float = 1.0) -> None:
    if suave:
        camino(c, pts, True, tension)
    else:
        c.move_to(*pts[0])
        for q in pts[1:]:
            c.line_to(*q)
        c.close_path()
    c.fill()


def capsula(c: cairo.Context, p1, p2, r1: float, r2: float) -> None:
    """Segmento redondeado de grosor variable."""
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    largo = math.hypot(dx, dy) or 1e-6
    nx, ny = -dy / largo, dx / largo
    c.move_to(x1 + nx * r1, y1 + ny * r1)
    c.line_to(x2 + nx * r2, y2 + ny * r2)
    c.line_to(x2 - nx * r2, y2 - ny * r2)
    c.line_to(x1 - nx * r1, y1 - ny * r1)
    c.close_path()
    c.fill()
    c.arc(x1, y1, r1, 0, TAU)
    c.fill()
    c.arc(x2, y2, r2, 0, TAU)
    c.fill()


def rect_redondeado(c: cairo.Context, x: float, y: float, w: float, h: float, r: float) -> None:
    r = min(r, w / 2, h / 2)
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -TAU / 4, 0)
    c.arc(x + w - r, y + h - r, r, 0, TAU / 4)
    c.arc(x + r, y + h - r, r, TAU / 4, TAU / 2)
    c.arc(x + r, y + r, r, TAU / 2, 3 * TAU / 4)
    c.close_path()


def elipse(c: cairo.Context, x: float, y: float, rx: float, ry: float, ang: float = 0.0) -> None:
    c.save()
    c.translate(x, y)
    c.rotate(ang)
    c.scale(max(rx, 1e-6), max(ry, 1e-6))
    c.arc(0, 0, 1, 0, TAU)
    c.restore()
    c.fill()
