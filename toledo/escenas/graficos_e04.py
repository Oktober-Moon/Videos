"""Gráficos de la escena 4 dibujados con cairo: el mapa de Europa (Corfú, Friburgo, Múnich), los
pictogramas de caminar, correr y bicicleta, el acelerómetro con su masa y sus resortes, la columna de
aire sobre alguien que sube una escalera, la huella dactilar y la radiografía dental.

Los contornos de costa están simplificados a mano (unos cientos de puntos): bastan para ubicar a
Corfú y a Friburgo, no son un mapa de navegación.
"""

from __future__ import annotations

import functools
import math

import cv2
import numpy as np

import dibujo as D
from graficos import H, W, fbm, gradiente_vertical

TAU = math.tau

# --------------------------------------------------------------------------- mapa de Europa

# Tierra firme, en el sentido del reloj: de arriba a la izquierda, por arriba hacia la derecha, y de
# regreso por la costa del Egeo, Grecia, el Adriático, Italia, la Costa Azul y España.
CONTINENTE = [
    (-12.0, 60.0), (42.0, 60.0), (42.0, 36.4), (28.0, 36.8), (27.3, 37.3), (26.5, 38.5), (26.9, 39.2), (26.2, 40.0),
    (26.6, 40.6), (26.0, 40.9), (24.4, 40.85), (23.9, 40.4), (24.3, 40.15), (23.7, 40.0),
    (23.35, 40.25), (23.3, 39.95), (22.95, 40.6), (22.6, 40.3), (22.6, 39.9), (22.95, 39.35), (23.2, 39.1), (22.8, 38.9),
    (23.6, 38.3), (24.0, 38.0), (24.05, 37.65), (23.6, 37.95), (23.15, 37.9), (23.2, 37.4), (22.75, 37.0), (23.05, 36.45),
    (22.55, 36.75), (22.48, 36.38), (22.1, 36.9), (21.7, 36.8), (21.65, 37.4), (21.3, 37.65), (21.1, 38.1), (21.6, 38.2),
    (21.1, 38.5), (20.75, 38.95), (20.25, 39.45), (20.0, 39.7), (19.45, 40.35), (19.45, 40.9), (19.45, 41.3), (19.6, 41.8),
    (19.1, 42.1), (18.55, 42.4), (18.1, 42.65), (17.4, 43.0), (16.45, 43.5), (15.9, 43.65), (15.2, 44.2), (14.9, 44.7),
    (14.45, 45.3), (14.05, 44.95), (13.85, 44.85), (13.6, 45.15), (13.75, 45.6), (13.1, 45.75), (12.4, 45.45),
    (12.55, 44.95), (12.25, 44.5), (12.6, 44.05), (13.5, 43.6), (14.2, 42.45), (14.9, 42.0), (15.2, 41.95), (16.2, 41.9),
    (15.9, 41.55), (16.9, 41.12), (17.95, 40.65), (18.5, 40.15), (18.37, 39.8), (18.0, 40.05), (17.2, 40.45),
    (16.6, 40.1), (16.5, 39.75), (17.15, 39.1), (16.6, 38.45), (16.05, 37.95), (15.65, 38.0), (15.65, 38.3), (15.85, 38.7),
    (16.0, 39.4), (15.65, 40.0), (15.0, 40.25), (14.75, 40.65), (14.35, 40.6), (14.25, 40.83), (13.75, 41.25),
    (13.05, 41.22), (12.25, 41.75), (11.75, 42.1), (11.1, 42.4), (10.5, 42.95), (10.3, 43.55), (10.1, 44.0), (9.8, 44.1),
    (8.95, 44.4), (8.2, 43.9), (7.4, 43.7), (6.6, 43.15), (5.9, 43.1), (5.3, 43.3), (4.6, 43.4), (3.5, 43.3), (3.05, 42.8),
    (3.2, 42.3), (2.2, 41.4), (0.9, 41.0), (0.0, 39.9), (-0.4, 39.45), (0.2, 38.75), (-0.5, 38.3), (-1.0, 37.6),
    (-2.0, 36.8), (-5.5, 36.0), (-12.0, 36.0),
]
ISLAS = [
    [(9.4, 43.0), (9.55, 42.6), (9.55, 42.1), (9.25, 41.4), (8.9, 41.6), (8.6, 41.9), (8.65, 42.3), (8.55, 42.6), (9.0, 42.75)],
    [(9.15, 41.25), (9.7, 40.95), (9.65, 40.1), (9.6, 39.2), (9.0, 39.1), (8.55, 38.9), (8.4, 39.3), (8.4, 40.0), (8.15, 40.55),
     (8.3, 40.95), (8.9, 41.05)],
    [(12.45, 37.8), (12.6, 38.1), (13.3, 38.2), (14.3, 38.0), (15.1, 38.15), (15.65, 38.25), (15.3, 37.6), (15.1, 37.0),
     (15.1, 36.65), (14.4, 36.75), (13.4, 37.15), (12.6, 37.55)],
    [(19.65, 39.8), (19.95, 39.77), (19.9, 39.6), (20.1, 39.42), (20.02, 39.36), (19.82, 39.47), (19.66, 39.65)],      # Corfú
    [(20.4, 38.45), (20.65, 38.35), (20.8, 38.12), (20.55, 38.1), (20.35, 38.2)],
    [(23.0, 39.0), (23.6, 38.7), (24.6, 38.0), (24.3, 38.1), (23.6, 38.4), (22.85, 38.8)],
    [(2.35, 39.6), (3.1, 39.95), (3.45, 39.7), (3.2, 39.35), (2.7, 39.4)],
]
ALEMANIA = [
    (6.0, 50.75), (6.2, 51.4), (5.95, 51.85), (6.8, 52.1), (7.05, 52.25), (6.7, 52.5), (7.05, 52.65),
    (7.2, 53.25), (7.3, 53.7), (8.0, 53.7), (8.5, 53.55), (8.65, 53.9), (9.0, 54.0), (8.6, 54.4),
    (8.65, 54.9), (9.4, 54.85), (10.0, 54.6), (10.9, 54.4), (10.85, 53.95), (11.5, 54.05),
    (12.3, 54.3), (13.2, 54.6), (14.2, 53.9), (14.4, 53.3), (14.6, 52.6), (14.75, 52.1),
    (14.95, 51.4), (15.0, 51.0), (14.3, 50.9), (13.5, 50.65), (12.4, 50.3), (12.1, 50.25),
    (12.5, 49.75), (13.0, 49.3), (13.85, 48.75), (13.4, 48.35), (13.0, 47.8), (13.0, 47.47),
    (12.2, 47.6), (11.2, 47.4), (10.2, 47.3), (9.6, 47.55), (9.0, 47.7), (8.6, 47.65), (7.6, 47.58),
    (7.55, 48.0), (7.9, 48.6), (8.2, 48.98), (7.0, 49.15), (6.35, 49.45), (6.5, 49.8), (6.1, 50.1),
    (6.4, 50.3),
]
GRECIA = [(20.0, 39.7), (20.25, 39.45), (20.75, 38.95), (21.1, 38.5), (21.6, 38.2), (21.1, 38.1), (21.3, 37.65),
          (21.65, 37.4), (21.7, 36.8), (22.1, 36.9), (22.48, 36.38), (22.55, 36.75), (23.05, 36.45), (22.75, 37.0),
          (23.2, 37.4), (23.15, 37.9), (23.6, 37.95), (24.05, 37.65), (24.0, 38.0), (23.6, 38.3), (22.8, 38.9),
          (23.2, 39.1), (22.95, 39.35), (22.6, 39.9), (22.6, 40.3), (22.95, 40.6), (23.3, 39.95), (23.35, 40.25),
          (23.7, 40.0), (24.3, 40.15), (23.9, 40.4), (24.4, 40.85), (26.0, 40.9), (26.6, 41.6), (25.0, 41.35),
          (23.0, 41.4), (22.0, 41.1), (20.95, 40.9), (20.6, 40.1)]
FRIBURGO = (7.85, 47.99)
MUNICH = (11.58, 48.14)
CORFU = (19.92, 39.62)


class Mapa:
    """Mapa grande (3840 × 2160) de lon0..lon1 × lat0..lat1 que se recorre con zoom."""

    def __init__(self, P, centro=(14.0, 44.0), escala=180.0, resaltar=(), tinte=None):
        self.P, self.centro, self.k = P, centro, escala
        self.w, self.h = 3840, 2160
        self.img = self._dibujar(resaltar, tinte)

    def proy(self, lon, lat):
        lon0, lat0 = self.centro
        return (self.w / 2 + (lon - lon0) * self.k * math.cos(math.radians(lat0)), self.h / 2 - (lat - lat0) * self.k)

    def _dibujar(self, resaltar, tinte):
        P = self.P
        mar = gradiente_vertical([(0.0, P["rio"] * 0.20), (1.0, P["rio"] * 0.11)], self.w, self.h)
        mar *= (0.88 + 0.24 * fbm(self.h // 8, self.w // 8, 32, 4, 0.5, 41).repeat(8, 0).repeat(8, 1))[..., None]
        s, c = D.lienzo(self.w, self.h)
        tierra = P["verde"] * 0.85 + P["piedra"] * 0.14
        D.tinta(c, tierra)
        for poli in [CONTINENTE] + ISLAS:
            D.rellenar(c, [self.proy(*q) for q in poli], suave=False)
        for poli, col, a in resaltar:
            D.tinta(c, col, a)
            D.rellenar(c, [self.proy(*q) for q in poli], suave=False)
        D.tinta(c, P["piedra"] * 0.9 + P["blanco"] * 0.1, 0.55)
        c.set_line_width(3)
        for poli in [CONTINENTE] + ISLAS:
            pts = [self.proy(*q) for q in poli]
            c.move_to(*pts[0])
            for q in pts[1:]:
                c.line_to(*q)
            c.close_path()
            c.stroke()
        D.tinta(c, P["blanco"], 0.22)                                    # Alemania, con borde fino
        c.set_line_width(2.5)
        pts = [self.proy(*q) for q in ALEMANIA]
        c.move_to(*pts[0])
        for q in pts[1:]:
            c.line_to(*q)
        c.close_path()
        c.stroke()
        capa = D.a_rgba(s)
        alfa = capa[..., 3]
        sombra = cv2.GaussianBlur(np.roll(np.roll(alfa, 22, 0), 14, 1), (0, 0), 22) * 0.55
        img = mar * (1 - sombra)[..., None]
        img = img * (1 - capa[..., 3:]) + capa[..., :3]
        relieve = fbm(self.h // 4, self.w // 4, 24, 5, 0.55, 42).repeat(4, 0).repeat(4, 1)
        img *= (1 + (relieve - 0.5) * 0.18 * alfa)[..., None]
        return np.clip(img, 0, 1).astype(np.float32)

    def ver(self, cx, cy, zoom):
        """Encuadre de 1920 × 1080 centrado en (cx, cy) del mapa grande; devuelve (imagen, función que
        pasa un punto del mapa grande a la pantalla)."""
        bw, bh = self.w / 2 / zoom, self.h / 2 / zoom
        x0, y0 = cx - bw / 2, cy - bh / 2
        M = np.float32([[W / bw, 0, -x0 * W / bw], [0, H / bh, -y0 * H / bh]])
        img = cv2.warpAffine(self.img, M, (W, H), flags=cv2.INTER_LINEAR if zoom > 0.9 else cv2.INTER_AREA,
                             borderMode=cv2.BORDER_REFLECT)

        def pant(px, py):
            return ((px - x0) * W / bw, (py - y0) * H / bh)
        return img, pant


# --------------------------------------------------------------------------- pictogramas


def _miembro(c, pts, grosor):
    c.set_line_width(grosor)
    c.move_to(*pts[0])
    for q in pts[1:]:
        c.line_to(*q)
    c.stroke()


def pictograma(c, cx, cy, s, tipo: str, fase: float = 0.0):
    """Figura de señalética (cabeza redonda, miembros gruesos de punta redonda) de alto `s`, con
    `fase` (0..1) del paso: caminar, correr o bicicleta."""
    g = s * 0.11
    a = math.sin(fase * TAU)
    if tipo == "bici":
        r = s * 0.24
        rueda1, rueda2 = (cx - s * 0.33, cy + s * 0.26), (cx + s * 0.33, cy + s * 0.26)
        c.set_line_width(g * 0.55)
        for q in (rueda1, rueda2):
            c.new_sub_path()
            c.arc(q[0], q[1], r, 0, TAU)
        c.stroke()
        pedal = (cx - s * 0.02, cy + s * 0.24)
        _miembro(c, [rueda1, pedal, (cx + s * 0.20, cy - s * 0.06), rueda2], g * 0.5)
        _miembro(c, [pedal, (cx - s * 0.10, cy - s * 0.10)], g * 0.5)
        cadera = (cx - s * 0.10, cy - s * 0.16)
        hombro = (cx + s * 0.08, cy - s * 0.42)
        _miembro(c, [cadera, hombro], g)
        _miembro(c, [hombro, (cx + s * 0.20, cy - s * 0.22), (cx + s * 0.22, cy - s * 0.10)], g * 0.8)
        pie = (pedal[0] + s * 0.09 * math.cos(fase * TAU), pedal[1] + s * 0.09 * math.sin(fase * TAU))
        _miembro(c, [cadera, (cx + s * 0.06, cy + s * 0.02 + s * 0.04 * a), pie], g * 0.9)
        c.arc(hombro[0] + s * 0.06, hombro[1] - s * 0.13, s * 0.085, 0, TAU)
        c.fill()
        return
    corre = tipo == "correr"
    incl = s * (0.10 if corre else 0.03)
    cadera = (cx, cy + s * 0.05)
    hombro = (cx + incl, cy - s * 0.30)
    c.arc(hombro[0] + incl * 0.5, hombro[1] - s * 0.16, s * 0.09, 0, TAU)
    c.fill()
    _miembro(c, [cadera, hombro], g)
    ab = (0.55 if corre else 0.35) * a
    for lado in (1, -1):
        ang = lado * ab
        codo = (hombro[0] + s * 0.16 * math.sin(ang), hombro[1] + s * 0.16 * math.cos(ang))
        mano = (codo[0] + s * (0.14 if corre else 0.15) * math.sin(ang + (1.2 if corre else 0.2)),
                codo[1] + s * 0.14 * math.cos(ang + (1.2 if corre else 0.2)) * (0.6 if corre else 1))
        _miembro(c, [hombro, codo, mano], g * 0.8)
        pa = -lado * (0.6 if corre else 0.4) * a
        rodilla = (cadera[0] + s * 0.22 * math.sin(pa), cadera[1] + s * 0.22 * math.cos(pa))
        dob = 0.9 if (corre and lado * a < 0) else 0.15
        pie = (rodilla[0] + s * 0.22 * math.sin(pa - dob), rodilla[1] + s * 0.22 * math.cos(pa - dob))
        _miembro(c, [cadera, rodilla, pie], g)


# --------------------------------------------------------------------------- acelerómetro


def acelerometro(c, cx, cy, s, dx: float, col_fijo, col_masa, a: float = 1.0):
    """Acelerómetro MEMS visto desde arriba: una masa de prueba colgada de dos resortes, con dedos
    que se meten entre los dedos fijos del chip; `dx` corre la masa (en fracción de `s`)."""
    w, h = s * 0.62, s * 0.30
    mx = cx + dx * s
    D.tinta(c, col_fijo, 0.9 * a)
    c.set_line_width(s * 0.012)
    D.rect_redondeado(c, cx - s * 0.62, cy - s * 0.38, s * 1.24, s * 0.76, s * 0.04)
    c.stroke()
    for lado in (-1, 1):                                          # anclas
        c.rectangle(cx + lado * s * 0.56 - s * 0.03, cy - s * 0.06, s * 0.06, s * 0.12)
        c.fill()
    D.tinta(c, col_fijo, 0.85 * a)
    c.set_line_width(s * 0.008)
    for lado in (-1, 1):                                          # resortes en zigzag
        x0 = cx + lado * s * 0.53
        x1 = mx + lado * w / 2
        n = 9
        c.move_to(x0, cy)
        for i in range(1, n):
            u = i / n
            c.line_to(x0 + (x1 - x0) * u, cy + (s * 0.045 if i % 2 else -s * 0.045))
        c.line_to(x1, cy)
        c.stroke()
    D.tinta(c, col_masa, a)
    D.rect_redondeado(c, mx - w / 2, cy - h / 2, w, h, s * 0.015)
    c.fill()
    D.tinta(c, (0, 0, 0), 0.35 * a)                               # perforaciones de la masa
    for i in range(7):
        for j in range(3):
            c.rectangle(mx - w / 2 + w * (i + 0.5) / 7 - s * 0.012, cy - h / 2 + h * (j + 0.5) / 3 - s * 0.012, s * 0.024, s * 0.024)
    c.fill()
    for lado in (-1, 1):                                          # dedos de la masa y dedos fijos
        y_base = cy + lado * h / 2
        for i in range(8):
            x = mx - w / 2 + w * (i + 0.5) / 8
            D.tinta(c, col_masa, a)
            c.rectangle(x - s * 0.008, min(y_base, y_base + lado * s * 0.12), s * 0.016, s * 0.12)
            c.fill()
            xf = cx - w / 2 + w * (i + 1.0) / 8
            D.tinta(c, col_fijo, 0.85 * a)
            yb = cy + lado * s * 0.36
            c.rectangle(xf - s * 0.008, min(yb, yb - lado * s * 0.15), s * 0.016, s * 0.15)
            c.fill()


# --------------------------------------------------------------------------- huella y radiografía


@functools.lru_cache(maxsize=4)
def huella(tam: int = 420, semilla: int = 3) -> np.ndarray:
    """Huella dactilar (crestas en espiral con un poco de desorden), como máscara 0..1."""
    yy, xx = np.mgrid[0:tam, 0:tam].astype(np.float32)
    x = (xx - tam / 2) / (tam * 0.36)
    y = (yy - tam * 0.55) / (tam * 0.46)
    r = np.sqrt(x * x + (y * 1.15) ** 2)
    ang = np.arctan2(y, x)
    ruido = fbm(tam, tam, 64, 4, 0.5, semilla)
    fino = fbm(tam, tam, 16, 3, 0.5, semilla + 1)
    # un lazo: las crestas rodean un núcleo y abajo se abren hacia los lados (delta)
    lazo = np.sqrt(x * x * 1.3 + (y + 0.25) ** 2)
    fase = lazo * 62 + 2.2 * np.sin(ang + 0.4) + 6.0 * ruido + 3.0 * np.clip(y - 0.1, 0, None) * np.abs(x) * 8
    cresta = (np.sin(fase) > 0.05).astype(np.float32) * (fino > 0.32)
    forma = np.clip((1.0 - np.sqrt(x * x * 1.0 + (y * 0.92) ** 2)) * 6, 0, 1)
    m = cv2.GaussianBlur(cresta * forma, (0, 0), 0.9)
    return m


@functools.lru_cache(maxsize=2)
def radiografia_dental(ancho: int = 1100, alto: int = 520) -> np.ndarray:
    """Radiografía panorámica estilizada: los dos arcos de dientes claros sobre el hueso gris, con la
    textura borrosa de una placa (gris azulado)."""
    s, c = D.lienzo(ancho, alto)
    D.tinta(c, (0.30, 0.32, 0.36), 1.0)
    D.elipse(c, ancho / 2, alto * 0.52, ancho * 0.47, alto * 0.42)
    c.fill()
    for fila, (yc, sgn) in enumerate(((alto * 0.40, -1), (alto * 0.62, 1))):
        n = 16
        for i in range(n):
            u = (i + 0.5) / n
            x = ancho * (0.08 + 0.84 * u)
            curva = (u - 0.5) ** 2 * alto * 0.45
            y = yc - sgn * curva * 0.6
            ancho_d = ancho * 0.84 / n * (0.80 if 4 < i < 11 else 0.92)
            alto_d = alto * (0.15 if 4 < i < 11 else 0.13)
            D.tinta(c, (0.92, 0.93, 0.95), 0.95)
            D.rect_redondeado(c, x - ancho_d / 2, y - alto_d / 2, ancho_d, alto_d, ancho_d * 0.3)
            c.fill()
            D.tinta(c, (0.70, 0.72, 0.76), 0.85)                   # raíz
            c.move_to(x - ancho_d * 0.25, y + sgn * alto_d * 0.4)
            c.line_to(x, y + sgn * alto_d * 1.6)
            c.line_to(x + ancho_d * 0.25, y + sgn * alto_d * 0.4)
            c.close_path()
            c.fill()
            if i in (0, n - 1) and fila == 1:                       # muelas del juicio
                D.tinta(c, (0.95, 0.96, 0.98), 0.9)
                D.elipse(c, x, y + sgn * alto_d * 0.9, ancho_d * 0.35, alto_d * 0.4)
                c.fill()
    capa = D.a_rgba(s)
    img = capa[..., :3]
    img = cv2.GaussianBlur(img, (0, 0), 2.2)
    grano = fbm(alto, ancho, 6, 3, 0.5, 9)[..., None]
    img = img * (0.85 + 0.25 * grano)
    tinte = np.array([0.86, 0.94, 1.0], np.float32)
    return np.clip(img * tinte, 0, 1).astype(np.float32)
