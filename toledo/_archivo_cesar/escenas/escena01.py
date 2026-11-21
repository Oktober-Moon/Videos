"""Escena 1 — El sitio del campamento de Quinto Cicerón (54 a. C.) y la carta en letras griegas.

Mundos y paletas:
- Galia belga (exterior, noche, guerreros nervios): azul glasto, verde bosque, gris niebla,
  ámbar de antorcha, negro noche.
- Roma (la carta, César, el campamento por dentro): púrpura de Tiro, rojo de las legiones,
  oro del águila, terracota, mármol, tinta.

Cada plano es una clase con `preparar()` y `cuadro(t)`. Los tiempos y las marcas de
sincronía vienen de `escena01.json`; aquí solo hay posiciones, formas y colores.
"""

from __future__ import annotations

import functools
import math
from pathlib import Path

import cairo
import numpy as np
from PIL import Image

import anatomia as AN
import atmosfera as A
import sfx
import siluetas as S
from escenas.base import FPS, Plano, TiempoPlano, cargar_tiempos
from graficos import (H, W, Capa, Luces, acabado, ampliar, campana, colocar, color, contraluz, desenfoque,
                      fuente, rayos_de_luz, reducir, sombra_proyectada,
                      entra, escalar_alfa, fbm, gradiente_vertical, mezclar, sale, sobre,
                      sobre_en, suave, suave5, tenir, texto_alfa, textura_papel, tramo)
from paletas import GALIA, ROMA

RUTA_TIEMPOS = Path(__file__).with_suffix(".json")

# Colores como arreglos float (0..1)
R = {k: color(v) for k, v in ROMA.items()}
G = {k: color(v) for k, v in GALIA.items()}
NEGRO = np.zeros(3, np.float32)
BLANCO = np.ones(3, np.float32)


def mez(a, b, x):
    return (np.asarray(a, np.float32) * (1 - x) + np.asarray(b, np.float32) * x).astype(np.float32)


# --------------------------------------------------------------------------- utilidades de escena


def dibujo(w: int, h: int, fn, col=None) -> np.ndarray:
    """Ejecuta `fn(ctx)` en un lienzo cairo nuevo y devuelve RGBA premultiplicado."""
    s, c = S.lienzo(w, h)
    if col is not None:
        S.tinta(c, col)
    fn(c)
    return S.a_rgba(s)


def alfa_de(w: int, h: int, fn) -> np.ndarray:
    s, c = S.lienzo(w, h)
    c.set_source_rgb(1, 1, 1)
    fn(c)
    return S.a_alfa(s)


class Vista:
    """Cámara 2D: lleva coordenadas de una capa (px de capa) a la pantalla.

    Equivale a `Capa.ver`: con densidad d y zoom z, un punto de la capa en (lx, ly) cae en
    pantalla en ((lx - lw/2 - cx·k·d)·z'/d + W/2, ...), con z' = 1 + (z-1)·k.
    """

    def __init__(self, lw: int, lh: int, densidad: float, cx: float, cy: float, z: float,
                 paralaje: float = 1.0):
        self.lw, self.lh, self.d = lw, lh, densidad
        k = paralaje
        self.z = 1.0 + (z - 1.0) * k
        self.ox = lw / 2 + cx * k * densidad
        self.oy = lh / 2 + cy * k * densidad

    def p(self, x: float, y: float) -> tuple[float, float]:
        f = self.z / self.d
        return (x - self.ox) * f + W / 2, (y - self.oy) * f + H / 2

    @property
    def escala(self) -> float:
        return self.z / self.d

    def aplicar(self, c: cairo.Context) -> None:
        c.translate(W / 2, H / 2)
        c.scale(self.escala, self.escala)
        c.translate(-self.ox, -self.oy)


class PlanoBase(Plano):
    """Agrega el acabado común (grano, viñeta, resplandor) y el índice de cuadro absoluto."""

    ajustes_acabado: dict = {}

    def indice(self, t: float) -> int:
        return int(round((self.tiempo.inicio + t) * FPS))

    def acabar(self, img: np.ndarray, t: float, **kw) -> np.ndarray:
        opciones = dict(self.ajustes_acabado)
        opciones.update(kw)
        return acabado(img, self.indice(t), opacidad=self.opacidad(t), **opciones)


def fundir(a: np.ndarray, b: np.ndarray, x: float) -> np.ndarray:
    """Encadenado (cross-dissolve) entre dos imágenes dentro de un mismo plano."""
    if x <= 0:
        return a
    if x >= 1:
        return b
    return a * (1 - x) + b * x


# =========================================================================== PLANO 1
# Mapa nocturno de la Galia que se acerca hasta el territorio de los nervios; "54 a. C.";
# la niebla cubre el mapa y descubre el campamento romano de invierno.

LAT0, LON0 = 47.5, 2.5
COS_LAT = math.cos(math.radians(47.0))


def proy(lon: float, lat: float) -> tuple[float, float]:
    return (lon - LON0) * COS_LAT, -(lat - LAT0)


def proy_lista(pts):
    return [proy(lon, lat) for lon, lat in pts]


CONTINENTE = [
    (-9.5, 38.5), (-9.4, 40.5), (-8.9, 41.8), (-8.9, 42.5), (-9.3, 42.9), (-8.3, 43.4), (-7.7, 43.75),
    (-6.5, 43.55), (-5.7, 43.58), (-4.5, 43.4), (-3.8, 43.47), (-2.9, 43.4), (-2.0, 43.32),
    (-1.75, 43.38), (-1.5, 43.55), (-1.3, 44.3), (-1.25, 44.65), (-1.15, 45.3), (-1.05, 45.6),
    (-1.2, 45.9), (-1.2, 46.15), (-1.8, 46.5), (-2.15, 46.9), (-2.2, 47.25), (-2.55, 47.3),
    (-2.9, 47.5), (-3.5, 47.7), (-4.1, 47.85), (-4.37, 47.8), (-4.7, 48.03), (-4.4, 48.25),
    (-4.77, 48.35), (-4.6, 48.6), (-4.0, 48.72), (-3.5, 48.83), (-2.7, 48.55), (-2.3, 48.66),
    (-2.0, 48.65), (-1.5, 48.63), (-1.58, 48.85), (-1.6, 49.2), (-1.85, 49.55), (-1.95, 49.72),
    (-1.6, 49.66), (-1.25, 49.7), (-1.15, 49.4), (-0.6, 49.35), (-0.1, 49.3), (0.15, 49.45),
    (0.2, 49.7), (0.6, 49.85), (1.1, 49.93), (1.5, 50.15), (1.6, 50.4), (1.58, 50.73),
    (1.85, 50.95), (2.37, 51.05), (2.9, 51.23), (3.35, 51.38), (3.6, 51.45), (3.95, 51.55),
    (4.05, 51.85), (4.15, 51.98), (4.4, 52.2), (4.6, 52.5), (4.75, 52.95), (5.4, 53.25),
    (6.2, 53.45), (7.1, 53.6), (7.3, 53.3), (8.0, 53.55), (8.6, 53.55), (8.7, 53.9), (8.9, 54.3),
    (8.6, 54.9), (8.6, 56.0), (8.3, 57.5), (25.0, 57.5), (25.0, 40.5), (19.4, 40.5), (19.0, 42.0),
    (17.5, 43.0), (16.4, 43.5), (15.2, 44.2), (14.5, 45.25), (13.6, 45.0), (13.7, 45.65),
    (12.3, 45.4), (12.5, 44.9), (12.57, 44.06), (13.5, 43.6), (14.2, 42.5), (15.0, 42.0),
    (16.2, 41.9), (17.0, 41.1), (18.5, 40.2), (18.4, 39.8), (17.2, 40.5), (16.6, 39.0),
    (16.0, 38.0), (15.6, 40.0), (15.0, 40.25), (14.25, 40.8), (13.7, 41.2), (13.0, 41.25),
    (12.4, 41.65), (11.8, 42.05), (11.1, 42.4), (10.5, 42.95), (10.25, 43.6), (9.85, 44.05),
    (9.5, 44.15), (8.9, 44.4), (8.2, 43.9), (7.7, 43.78), (7.3, 43.7), (6.9, 43.45), (6.4, 43.15),
    (5.95, 43.1), (5.6, 43.15), (5.3, 43.3), (4.85, 43.35), (4.4, 43.45), (3.9, 43.55),
    (3.3, 43.3), (3.05, 43.0), (3.05, 42.55), (3.3, 42.3), (3.2, 41.9), (2.2, 41.4), (1.25, 41.1),
    (0.85, 40.7), (0.0, 40.0), (-0.3, 39.45), (-0.2, 38.5),
]
BRITANIA = [
    (-5.7, 50.06), (-5.2, 49.96), (-4.1, 50.35), (-3.64, 50.22), (-3.4, 50.6), (-2.45, 50.58),
    (-1.95, 50.68), (-1.3, 50.75), (-0.79, 50.72), (0.25, 50.73), (0.97, 50.91), (1.32, 51.13),
    (1.44, 51.38), (0.6, 51.5), (0.95, 51.62), (1.2, 51.8), (1.3, 51.95), (1.75, 52.48),
    (1.6, 52.9), (1.0, 52.96), (0.3, 52.85), (0.35, 53.2), (0.1, 53.6), (-0.08, 54.1),
    (-0.6, 54.5), (-1.2, 54.65), (-1.6, 55.6), (-2.0, 56.0), (-2.6, 56.05), (-3.0, 56.3),
    (-2.5, 56.6), (-2.0, 57.1), (-1.8, 57.6), (-4.0, 57.9), (-5.6, 57.6), (-5.6, 56.3),
    (-5.7, 55.3), (-4.8, 55.7), (-4.9, 55.0), (-5.0, 54.65), (-3.6, 54.95), (-3.3, 54.4),
    (-3.0, 54.0), (-2.9, 53.4), (-3.4, 53.35), (-4.3, 53.4), (-4.7, 52.8), (-4.1, 52.4),
    (-4.7, 52.1), (-5.3, 51.88), (-4.9, 51.65), (-4.0, 51.6), (-3.2, 51.45), (-2.7, 51.5),
    (-3.2, 51.2), (-4.2, 51.2), (-4.53, 51.0), (-4.95, 50.55),
]
HIBERNIA = [(-6.0, 52.0), (-6.4, 52.2), (-6.0, 53.0), (-6.2, 53.6), (-6.0, 54.0), (-5.5, 54.6),
            (-6.0, 55.2), (-7.5, 55.3), (-8.5, 54.8), (-10.0, 54.2), (-9.9, 53.4), (-10.3, 52.1),
            (-9.5, 51.5), (-8.0, 51.7), (-6.4, 52.15)]
CORCEGA = [(8.6, 41.4), (9.2, 41.4), (9.55, 42.1), (9.45, 43.0), (9.35, 42.95), (8.7, 42.6), (8.55, 42.2)]
CERDENA = [(8.4, 39.0), (9.0, 38.9), (9.65, 39.5), (9.8, 40.5), (9.5, 41.1), (9.2, 41.25),
           (8.2, 40.9), (8.4, 40.3), (8.45, 39.5)]

RIN = [(4.15, 51.98), (5.0, 51.9), (5.85, 51.85), (6.6, 51.65), (6.75, 51.2), (6.95, 50.94),
       (7.1, 50.73), (7.6, 50.36), (8.27, 50.0), (8.4, 49.6), (8.2, 49.0), (7.75, 48.58),
       (7.55, 48.0), (7.6, 47.56), (8.4, 47.6), (9.2, 47.6), (9.6, 47.25), (9.5, 46.6)]
GALIA_POL = (
    [p for p in CONTINENTE[CONTINENTE.index((-1.75, 43.38)) : CONTINENTE.index((4.15, 51.98)) + 1]]
    + RIN[1:16]
    + [(9.6, 47.2), (9.5, 46.5), (8.4, 46.0), (7.0, 45.9), (7.0, 45.2), (6.9, 44.4), (7.4, 43.75)]
    + [p for p in CONTINENTE[CONTINENTE.index((7.3, 43.7)) : CONTINENTE.index((3.05, 42.55)) + 1]]
    + [(2.6, 42.4), (1.8, 42.45), (1.0, 42.7), (0.0, 42.75), (-0.8, 42.95), (-1.4, 43.05)]
)
BELGAS_POL = (
    [p for p in CONTINENTE[CONTINENTE.index((0.15, 49.45)) : CONTINENTE.index((4.15, 51.98)) + 1]]
    + RIN[1:12]
    + [(6.5, 48.3), (5.3, 47.9), (4.9, 48.6), (4.4, 48.95), (3.6, 49.0), (3.0, 48.95), (2.4, 48.82),
       (2.0, 48.95), (1.4, 49.1), (0.9, 49.35), (0.5, 49.4)]
)
RIOS = {
    "Sequana": [(0.2, 49.45), (0.5, 49.4), (0.9, 49.35), (1.4, 49.1), (2.0, 48.95), (2.35, 48.85),
                (2.8, 48.6), (3.5, 48.45), (4.1, 48.3), (4.6, 47.9)],
    "Matrona": [(2.4, 48.82), (3.0, 48.95), (3.6, 49.0), (4.4, 48.95), (4.9, 48.6), (5.3, 47.95)],
    "Liger": [(-2.2, 47.25), (-1.55, 47.2), (-0.55, 47.4), (0.7, 47.4), (1.9, 47.9), (2.9, 47.6),
              (3.1, 47.0), (3.9, 46.0), (4.1, 45.3), (4.1, 44.8)],
    "Garumna": [(-1.05, 45.6), (-0.6, 45.1), (-0.2, 44.6), (0.6, 44.2), (1.45, 43.6), (1.0, 43.1), (0.6, 42.9)],
    "Duranius": [(-0.6, 45.1), (0.5, 44.85), (1.5, 44.9), (2.4, 45.4)],
    "Rhodanus": [(4.85, 43.4), (4.8, 43.95), (4.75, 44.6), (4.85, 45.2), (4.85, 45.75), (5.4, 45.9),
                 (5.9, 46.1), (6.15, 46.2), (6.5, 46.4)],
    "Arar": [(4.85, 45.75), (4.85, 46.3), (5.0, 46.9), (5.6, 47.5), (6.0, 47.9)],
    "Rhenus": RIN,
    "Mosa": [(4.2, 51.75), (5.2, 51.75), (5.75, 51.2), (5.7, 50.7), (5.55, 50.62), (4.9, 50.47),
             (4.85, 50.0), (4.75, 49.75), (5.1, 49.4), (5.4, 48.9), (5.6, 48.1)],
    "Sabis": [(4.9, 50.47), (4.45, 50.4), (4.1, 50.28), (3.8, 50.2), (3.6, 50.05)],
    "Scaldis": [(4.0, 51.45), (4.4, 51.22), (4.2, 51.1), (3.73, 51.05), (3.5, 50.8), (3.4, 50.6),
                (3.3, 50.3), (3.25, 50.0)],
    "Mosella": [(7.6, 50.36), (7.2, 50.1), (6.65, 49.75), (6.3, 49.45), (6.15, 49.1), (6.2, 48.7), (6.4, 48.3)],
    "Tamesis": [(1.0, 51.5), (0.3, 51.48), (-0.1, 51.5), (-0.6, 51.45), (-1.2, 51.7), (-1.8, 51.7)],
    "Padus": [(12.5, 44.95), (11.6, 45.0), (10.5, 45.05), (9.6, 45.1), (8.7, 45.15), (7.7, 45.05)],
    "Iberus": [(0.85, 40.7), (0.4, 41.0), (-0.9, 41.65), (-1.6, 42.1), (-2.4, 42.45)],
}
MONTES = [  # (lon0, lat0, lon1, lat1, cantidad, tamaño en grados)
    (5.9, 44.4, 7.0, 45.9, 9, 0.38), (7.0, 45.9, 10.5, 46.5, 10, 0.4), (10.5, 46.5, 13.5, 46.6, 8, 0.4),
    (-1.4, 43.0, 3.0, 42.5, 11, 0.32), (2.4, 44.8, 3.6, 45.8, 5, 0.3), (5.7, 46.4, 7.3, 47.4, 5, 0.22),
    (6.9, 47.9, 7.3, 48.7, 3, 0.2),
]
BOSQUES = [  # (lon, lat, radio en grados, cantidad): Arduenna Silva y la selva Carbonaria
    (5.5, 50.1, 0.55, 46), (4.3, 50.65, 0.32, 20), (6.6, 49.9, 0.35, 14),
]
CAMPAMENTO_LONLAT = (4.25, 50.42)
ETIQUETAS = [  # texto, lon, lat, tamaño (grados de latitud), tipo
    ("OCEANVS", -6.6, 47.2, 0.55, "mar"), ("GALLIA", 2.2, 46.9, 0.9, "tierra"),
    ("BELGAE", 3.75, 49.95, 0.42, "tierra"), ("BRITANNIA", -2.4, 52.35, 0.42, "tierra"),
    ("GERMANIA", 10.6, 51.3, 0.5, "tierra"), ("AQVITANI", 0.0, 44.1, 0.3, "tierra"),
    ("HISPANIA", -4.6, 41.9, 0.38, "tierra"), ("ITALIA", 11.6, 43.25, 0.34, "tierra"),
    ("MARE NOSTRVM", 5.2, 41.7, 0.3, "mar"), ("RHENVS", 8.75, 50.45, 0.18, "rio"),
    ("NERVII", 3.95, 50.62, 0.075, "nervios"), ("SABIS", 4.55, 50.33, 0.04, "rio"),
]


class Plano1(PlanoBase):
    fundido_entrada = 1.2
    fundido_salida = 0.45

    def preparar(self) -> None:
        self.tierras = [proy_lista(p) for p in (CONTINENTE, BRITANIA, HIBERNIA, CORCEGA, CERDENA)]
        self.galia = proy_lista(GALIA_POL)
        self.belgas = proy_lista(BELGAS_POL)
        self.rios = {k: proy_lista(v) for k, v in RIOS.items()}
        r = np.random.default_rng(5)
        self.montes = []
        for lon0, lat0, lon1, lat1, n, tam in MONTES:
            for k in range(n):
                u = (k + r.uniform(-0.3, 0.3)) / max(1, n - 1)
                lon = lon0 + (lon1 - lon0) * u + r.normal(0, 0.12)
                lat = lat0 + (lat1 - lat0) * u + r.normal(0, 0.12)
                self.montes.append((proy(lon, lat), tam * r.uniform(0.75, 1.2)))
        self.arboles = []
        for lon, lat, rad, n in BOSQUES:
            for _ in range(n):
                a, d = r.uniform(0, math.tau), rad * math.sqrt(r.uniform(0, 1))
                self.arboles.append((proy(lon + d * math.cos(a) / COS_LAT * 0.8, lat + d * math.sin(a) * 0.6),
                                     r.uniform(0.045, 0.075)))
        self.etiquetas = []
        for texto, lon, lat, tam, tipo in ETIQUETAS:
            px = 160 if tipo in ("tierra", "mar") else 90
            alfa = texto_alfa(texto, "Cinzel-Regular.ttf" if tipo != "tierra" else "Cinzel-Bold.ttf",
                              px, interletra=0.28 if tipo in ("tierra", "mar") else 0.15)
            self.etiquetas.append((alfa, proy(lon, lat), tam, tipo, px))
        self.fecha = texto_alfa("54 a. C.", "Cinzel-Bold.ttf", 156, interletra=0.12)
        self.niebla = A.Niebla(101)
        self.velo = A.Niebla(202, celda=64)
        self.polvo = A.Polvo(70, 9, vel=(4.0, 2.0), tam=(0.8, 2.2))
        self.campamento = CampamentoNoche(semilla=11)

    # ---- cámara del mapa: zoom logarítmico hacia el campamento
    def camara_mapa(self, t: float):
        s0 = H / 11.5
        s1 = H / 1.05
        c0 = np.array(proy(1.6, 47.2))
        c1 = np.array(proy(*CAMPAMENTO_LONLAT))
        u = suave5(tramo(t, 0.2, self.m("niebla") + 0.9))
        u = 0.6 * u + 0.4 * u * u
        s = math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * u)
        w = (1 / s0 - 1 / s) / (1 / s0 - 1 / s1)
        return c0 + (c1 - c0) * w, s, s / s0

    def mapa(self, t: float) -> np.ndarray:
        centro, s, zoom = self.camara_mapa(t)
        mar = gradiente_vertical([(0.0, mez(G["noche"], G["glasto"], 0.18)),
                                  (1.0, mez(G["noche"], G["glasto"], 0.42))])
        sup, c = S.lienzo(W, H)
        c.translate(W / 2, H / 2)
        c.scale(s, s)
        c.translate(-centro[0], -centro[1])

        def poligonos(lista):
            for pol in lista:
                S.camino(c, pol, True, 0.6)

        # Anillos de grabado alrededor de las costas (ancho constante en pantalla)
        anillo = mez(G["glasto"], G["niebla"], 0.55)
        for k in range(7, 0, -1):
            c.set_operator(cairo.OPERATOR_OVER)
            S.tinta(c, anillo, 0.30 * (1 - k / 8.5))
            c.set_line_width(2 * k * 7.0 / s)
            poligonos(self.tierras)
            c.stroke()
            c.set_operator(cairo.OPERATOR_CLEAR)
            c.set_line_width((2 * k * 7.0 - 1.4) / s)
            poligonos(self.tierras)
            c.stroke()
        c.set_operator(cairo.OPERATOR_OVER)
        # Tierras: lo que no es Galia más oscuro
        S.tinta(c, mez(G["noche"], G["bosque"], 0.42))
        poligonos(self.tierras)
        c.fill()
        S.tinta(c, mez(mez(G["bosque"], G["noche"], 0.3), G["niebla"], 0.16))
        S.camino(c, self.galia, True, 0.6)
        c.fill()
        brillo_belgas = 0.12 + 0.28 * suave(tramo(t, 1.5, 4.5))
        S.tinta(c, mez(mez(G["bosque"], G["glasto"], 0.55), G["niebla"], brillo_belgas), 0.95)
        S.camino(c, self.belgas, True, 0.6)
        c.fill()
        # Montes y bosques (en unidades de mapa: crecen con el zoom)
        S.tinta(c, mez(G["noche"], G["bosque"], 0.25), 0.85)
        c.set_line_width(max(1.2, 0.045 * s) / s)
        for (x, y), tam in self.montes:
            h = tam * 0.6
            c.move_to(x - tam * 0.5, y + h * 0.35)
            c.line_to(x, y - h * 0.65)
            c.line_to(x + tam * 0.5, y + h * 0.35)
            c.stroke()
            c.move_to(x - tam * 0.12, y - h * 0.2)
            c.line_to(x + tam * 0.05, y + h * 0.3)
            c.stroke()
        for (x, y), tam in self.arboles:
            c.arc(x, y - tam * 0.6, tam * 0.42, 0, math.tau)
            c.fill()
            c.rectangle(x - tam * 0.06, y - tam * 0.3, tam * 0.12, tam * 0.45)
            c.fill()
        # Ríos
        S.tinta(c, mez(G["glasto"], G["niebla"], 0.65), 0.9)
        for nombre, pts in self.rios.items():
            ancho = (2.6 if nombre == "Rhenus" else 1.5) + 0.006 * s
            c.set_line_width(min(ancho, 9.0) / s)
            S.camino(c, pts, False, 0.8)
            c.stroke()
        # Costa
        S.tinta(c, mez(G["niebla"], BLANCO, 0.25), 0.9)
        c.set_line_width(1.8 / s)
        poligonos(self.tierras)
        c.stroke()
        # Campamento de Quinto Cicerón: cuadrado con cuatro puertas
        x, y = proy(*CAMPAMENTO_LONLAT)
        aparece = suave(tramo(t, 3.4, 4.6))
        if aparece > 0:
            lado = 0.035
            S.tinta(c, G["antorcha"], aparece)
            c.set_line_width(max(1.5, 0.006 * s) / s)
            c.rectangle(x - lado, y - lado, 2 * lado, 2 * lado)
            c.stroke()
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                c.arc(x + dx * lado, y + dy * lado, lado * 0.18, 0, math.tau)
                c.fill()
        capa = S.a_rgba(sup)
        img = mar
        sobre(img, capa)
        # Etiquetas
        for alfa, (lx, ly), tam, tipo, px in self.etiquetas:
            alto_px = tam * s
            if tipo == "nervios":
                op = suave(tramo(zoom, 3.0, 4.5))
            elif tipo == "rio":
                op = suave(tramo(zoom, 1.6, 2.5)) * (1 - suave(tramo(zoom, 7.0, 8.5)))
            else:
                op = 1 - suave(tramo(zoom, 1.5, 2.3)) if tam >= 0.5 else 1 - suave(tramo(zoom, 2.4, 3.4))
            if op <= 0.01 or alto_px < 6 or alto_px > 420:
                continue
            esc = alto_px / px
            a = escalar_alfa(alfa, esc)
            sx = (lx - centro[0]) * s + W / 2 - a.shape[1] / 2
            sy = (ly - centro[1]) * s + H / 2 - a.shape[0] / 2
            col = G["antorcha"] if tipo == "nervios" else mez(G["niebla"], BLANCO, 0.45 if tipo != "rio" else 0.2)
            sobre_en(img, tenir(a, col, 0.85 * op), int(sx), int(sy))
        # Resplandor de antorchas sobre el campamento
        luces = Luces()
        cx_, cy_ = (x - centro[0]) * s + W / 2, (y - centro[1]) * s + H / 2
        luces.punto(cx_, cy_, 26 + 22 * zoom ** 0.6, G["antorcha"], 0.55 * aparece * A.parpadeo(t, 3))
        img += luces.resultado()
        return img

    def cuadro(self, t: float) -> np.ndarray:
        pico = (self.m("niebla") + self.m("campamento")) / 2
        sube = suave(tramo(t, self.m("niebla"), pico))
        baja = 1 - suave(tramo(t, pico, self.m("campamento") + 0.8))
        cubre = min(sube, baja) if t >= pico else sube
        if t < pico:
            img = self.mapa(t)
            fina = self.niebla.alfa(t, y0=-100, y1=H + 100, densidad=0.35, vel=(26, -4), umbral=0.42)
            A.componer_niebla(img, fina, mez(G["niebla"], G["glasto"], 0.35) * 0.8)
            papel = 0.8
        else:
            img = self.campamento.cuadro(t - pico, self.duracion - pico)
            papel = 0.25
        # Fecha
        op = suave(tramo(t, self.m("fecha"), self.m("fecha") + 1.1)) * (1 - suave(tramo(t, self.m("niebla") - 1.3, self.m("niebla") - 0.2)))
        if op > 0:
            esc = 1.0 + 0.035 * tramo(t, self.m("fecha"), self.m("niebla"))
            a = escalar_alfa(self.fecha, esc)
            x, y = (W - a.shape[1]) // 2, int(H * 0.60 - a.shape[0] / 2)
            sombra = desenfoque(np.pad(a, 30), 12)
            sobre_en(img, tenir(sombra, G["noche"], 0.85 * op), x - 30, y - 30 + 6)
            sobre_en(img, tenir(a, mez(G["antorcha"], BLANCO, 0.12), op), x, y)
        # Velo de niebla que cubre el cambio de lugar
        if cubre > 0.001:
            n = self.velo.alfa(t, y0=-200, y1=H + 200, densidad=1.0, vel=(60, -8), umbral=0.18, suavidad=0.5)
            velo = np.clip(cubre * (0.75 + 0.5 * n) * 1.15, 0, 1)
            niebla_col = mez(G["niebla"], G["glasto"], 0.25) * (0.85 + 0.25 * n[..., None])
            img = img * (1 - velo[..., None]) + niebla_col * velo[..., None]
        self.polvo.dibujar(img, t, mez(G["niebla"], BLANCO, 0.3), 0.18)
        return self.acabar(img, t, papel=papel, vineta=0.55, bloom=0.35, grano=0.014)


class CampamentoNoche:
    """Campamento romano de invierno visto desde el foso, de noche (paleta de la Galia)."""

    D = 1.12

    def __init__(self, semilla: int = 11):
        d = self.D
        # margen para que el paneo nunca toque el borde (si no, las capas se desalinean)
        self.lw, self.lh = int((W + 200) * d), int((H + 100) * d)
        lw, lh = self.lw, self.lh
        r = np.random.default_rng(semilla)
        hor = lh * 0.565
        base_muro = lh * 0.70

        def lejano(c):
            pts = [(0, lh)] + [(lw * u, hor - 24 - 34 * math.sin(u * 5.3) - 20 * math.sin(u * 13 + 1))
                               for u in np.linspace(0, 1, 30)] + [(lw, lh)]
            S.rellenar(c, pts)
            for k in range(70):
                S.arbol_desnudo(c, r.uniform(0, lw), hor - 18 + r.uniform(-12, 22), r.uniform(70, 150),
                                semilla=k, niveles=5, apertura=0.45)
        self.lejano = Capa(dibujo(lw, lh, lejano, mez(G["noche"], G["niebla"], 0.30)), d, 0.3)

        def tiendas(c):
            for k in range(9):
                x = lw * (0.08 + 0.1 * k + r.uniform(-0.03, 0.03))
                S.tienda(c, x, lh * 0.62, r.uniform(80, 120), r.uniform(70, 95))
            S.tienda(c, lw * 0.5, lh * 0.625, 230, 165)  # pretorio
            for x in (0.455, 0.545, 0.36, 0.66):
                c.rectangle(lw * x - 2, lh * 0.625 - 230, 4, 230)
                c.fill()
                S.elipse(c, lw * x, lh * 0.625 - 220, 9, 9)
        self.tiendas = Capa(dibujo(lw, lh, tiendas, mez(G["noche"], G["glasto"], 0.14)), d, 0.6)
        self.luces_lejanas = [(lw * x, lh * y) for x, y in ((0.31, 0.585), (0.44, 0.59), (0.58, 0.585),
                                                             (0.69, 0.592), (0.86, 0.588), (0.13, 0.592))]
        self.antorchas = []
        torres = []

        def muralla(c):
            S.empalizada(c, -10, lw + 10, base_muro + 4, 150, semilla=3)
            for tx, alto in ((0.2, 400), (0.76, 370)):
                torres.append(S.torre_madera(c, lw * tx, base_muro + 6, 160, alto, semilla=int(tx * 100)))
        muro = dibujo(lw, lh, muralla, G["noche"] * 0.55)
        for j in torres:
            self.antorchas.append(j["esquina_izq"] + np.array([4, -18]))
            self.antorchas.append(j["esquina_der"] + np.array([-4, -18]))
        self.bandera_base = torres[0]["tope"] + np.array([0, -40])
        borde = contraluz(muro[..., 3], 0, -3, 1.2)
        muro[..., :3] += tenir(borde, mez(G["glasto"], G["niebla"], 0.7), 0.5)[..., :3]

        # Cara del terraplén (tierra con pasto, apenas iluminada); debajo, el foso
        def terraplen(c):
            pts = [(-10, base_muro + 2)] + [(lw * u, base_muro + r.uniform(-3, 3)) for u in np.linspace(0, 1, 50)]
            pts += [(lw + 10, base_muro), (lw + 10, lh + 10), (-10, lh + 10)]
            S.rellenar(c, pts, suave_=False)
        cara = dibujo(lw, lh, terraplen, mez(G["noche"], G["bosque"], 0.32))
        vetas = fbm(lh, lw, 64, 3, 0.5, 7)
        cara[..., :3] *= (0.9 + 0.2 * desenfoque(vetas[..., None], 6)[..., 0])[..., None]
        grad = np.clip((np.arange(lh) - base_muro) / (lh * 0.22), 0, 1)[:, None, None]
        cara[..., :3] *= (1.15 - 0.8 * grad ** 0.8)

        def pasto(c):
            for k in range(420):
                x = r.uniform(0, lw)
                y = base_muro + r.uniform(-2, 4)
                ang = r.uniform(-0.6, 0.6)
                S.capsula(c, (x, y), (x + math.sin(ang) * 20, y - math.cos(ang) * r.uniform(8, 26)), 1.6, 0.4)
        hierba = dibujo(lw, lh, pasto, mez(G["noche"], G["bosque"], 0.25))
        sobre(cara[..., :3], hierba)
        cara[..., 3] = np.maximum(cara[..., 3], hierba[..., 3])
        total = cara.copy()
        sobre(total[..., :3], muro)
        total[..., 3] = np.maximum(total[..., 3], muro[..., 3])
        self.muralla = Capa(np.clip(total, 0, 1), d, 1.0)

        def frente(c):
            pts = [(-20, lh)] + [(lw * u, lh * 0.9 + 26 * math.sin(u * 7) + r.uniform(-5, 5))
                                 for u in np.linspace(-0.02, 1.02, 40)] + [(lw + 20, lh)]
            S.rellenar(c, pts)
            for k in range(70):
                x = r.uniform(0, lw)
                y = lh * 0.9 + 26 * math.sin(x / lw * 7) + 6
                for h in range(5):
                    ang = r.uniform(-0.5, 0.5)
                    S.capsula(c, (x, y), (x + math.sin(ang) * 45, y - math.cos(ang) * r.uniform(25, 70)), 2.2, 0.5)
        self.frente = Capa(desenfoque(dibujo(lw, lh, frente, G["noche"] * 0.45), 2.5), d, 1.25)
        self.niebla = A.Niebla(303)
        self.humo = A.Humo(505)
        self.niebla_baja = A.Niebla(404, celda=64)
        self.estrellas = A.Estrellas(260, 21, (0, 0, W, H * 0.5))
        self.brasas = A.Brasas([tuple(p) for p in self.antorchas], 10, 31, subida=(30, 80))
        self.ceniza = A.Polvo(90, 41, vel=(10.0, 14.0), tam=(0.7, 1.8))

    def cuadro(self, t: float, dur: float) -> np.ndarray:
        u = suave(t / max(dur, 1e-3))
        z = 1.02 + 0.07 * u
        cx, cy = -30 + 70 * u, 6 * u
        cielo = gradiente_vertical([(0.0, G["noche"] * 0.85), (0.36, mez(G["noche"], G["glasto"], 0.45)),
                                    (0.54, mez(G["glasto"], G["niebla"], 0.45)), (0.72, mez(G["noche"], G["glasto"], 0.3))],
                                   y0=-cy / H * 0.3)
        luces = Luces()
        luces.punto(W * 0.68 - cx * 0.1, H * 0.20, 360, mez(G["niebla"], BLANCO, 0.35), 0.40)
        luces.punto(W * 0.68 - cx * 0.1, H * 0.20, 60, BLANCO, 0.25, forma="gauss")
        for k, hx in enumerate((0.2, 0.42, 0.6, 0.83)):
            luces.punto(W * hx - cx * 0.5, H * 0.58, 260, G["antorcha"], 0.10 + 0.02 * A.parpadeo(t, k), achatado=0.45)
        img = cielo
        self.estrellas.dibujar(img, t, 0.7, dx=cx * 0.1, zoom=1.0)
        img += luces.resultado()
        sobre(img, self.lejano.ver(cx, cy, z))
        n = self.niebla.alfa(t, y0=H * 0.46, y1=H * 0.66, densidad=0.5, vel=(16, 0), dx=cx * 0.4)
        A.componer_niebla(img, n, mez(G["niebla"], G["glasto"], 0.3))
        sobre(img, self.tiendas.ver(cx, cy, z))
        v6 = Vista(self.lw, self.lh, self.D, cx, cy, z, 0.6)
        v1 = Vista(self.lw, self.lh, self.D, cx, cy, z, 1.0)
        lejanas = Luces()
        for k, (x, y) in enumerate(self.luces_lejanas):
            sx, sy = v6.p(x, y)
            lejanas.punto(sx, sy, 16, G["antorcha"], 0.7 * A.parpadeo(t, k), forma="gauss")
            lejanas.punto(sx, sy, 80, G["antorcha"], 0.16 * A.parpadeo(t, k))
        img += lejanas.resultado()
        humo = self.humo.alfa(t, [(*v6.p(x, y), 18, 260) for x, y in self.luces_lejanas[:4]], densidad=0.35)
        A.componer_niebla(img, humo, mez(G["niebla"], G["antorcha"], 0.18) * 0.55)
        brillo = Luces()
        for k, (x, y) in enumerate(self.antorchas):
            sx, sy = v1.p(x, y)
            brillo.punto(sx, sy, 170, G["antorcha"], 0.20 * A.parpadeo(t, k + 10))
        luz = brillo.resultado()
        sobre(img, self.muralla.ver(cx, cy, z))
        # neblina que se junta en el foso
        n2 = self.niebla_baja.alfa(t, y0=H * 0.70, y1=H * 0.93, densidad=0.55, vel=(-22, 0), dx=cx * 0.8, escala=1.4)
        A.componer_niebla(img, n2, mez(G["niebla"], G["glasto"], 0.4) * 0.6, luz, 0.8)
        s, c = S.lienzo(W, H)
        v1.aplicar(c)
        S.tinta(c, G["noche"] * 0.55)
        pano = S.estandarte(c, self.bandera_base + np.array([0, 150]), 150, t, 0.24)
        S.tinta(c, mez(R["rojo_legion"], G["noche"], 0.6))
        S.rellenar(c, pano)
        sobre(img, S.a_rgba(s))
        halo = Luces()
        for k, (x, y) in enumerate(self.antorchas):
            sx, sy = v1.p(x, y)
            halo.punto(sx, sy - 8, 40, G["antorcha"], 0.32 * A.parpadeo(t, k + 10))
            halo.punto(sx, sy, 150, G["antorcha"], 0.08 * A.parpadeo(t, k + 10))
        img += halo.resultado()
        for k, (x, y) in enumerate(self.antorchas):
            sx, sy = v1.p(x, y)
            A.llama(img, sx, sy, 26 * v1.escala, 13 * v1.escala, t, k, 1.2)
        self.brasas.dibujar(img, t, transformar=lambda x, y: (*v1.p(x, y), v1.escala), col=G["antorcha"], intensidad=0.9)
        sobre(img, self.frente.ver(cx, cy, z))
        self.ceniza.dibujar(img, t, mez(G["niebla"], BLANCO, 0.4), 0.25)
        return img


# =========================================================================== PLANO 2
# La colina de los nervios: miles de fuegos, guerreros en la cresta y, a la izquierda, las
# torres y el terraplén que levantan copiando a los romanos. Paleta de la Galia.


def guerrero(c, x: float, y: float, alto: float, tipo: str, semilla: int, mira_izq: bool = True):
    """Guerrero nervio en silueta (pelo largo o erizado con cal, bigote, capa, armas celtas).

    Devuelve la punta de la antorcha si la lleva (para dibujar la llama aparte).
    """
    r = np.random.default_rng(semilla)
    sx = -1.0 if mira_izq else 1.0
    pelo = "erizado" if r.random() < 0.45 else "largo"
    frente = tipo == "lanza"
    at = S.Atavio(vista="frente" if frente else "perfil", pelo=pelo, bigote=True,
                  capa=r.uniform(0.45, 0.9), viento=r.uniform(0.2, 0.7), corpulencia=r.uniform(0.95, 1.15))
    punta = None
    if tipo == "lanza":
        p = S.Pose(hombro_c=25, codo_c=70, hombro_l=18, codo_l=40, cadera_c=6, cadera_l=6)
        j = S.figura(c, x, y, alto, p, at)
        m = j["mano_c"]
        S.lanza(c, (m[0], m[1] + alto * 0.42), -math.pi / 2 + r.uniform(-0.07, 0.07), alto * 1.3, alto * 0.016)
        S.escudo_oval(c, j["mano_l"][0] - alto * 0.03, j["mano_l"][1] + alto * 0.02, alto * 0.30, alto * 0.52)
    elif tipo == "antorcha":
        p = S.Pose(torso=r.uniform(-4, 6), hombro_c=152, codo_c=12, hombro_l=-12, codo_l=25,
                   cadera_c=14, cadera_l=-10, rodilla_c=8)
        j = S.figura(c, x, y, alto, p, at, espejo=mira_izq)
        m = j["mano_c"]
        punta = np.array([m[0] + sx * alto * 0.02, m[1] - alto * 0.17])
        S.capsula(c, (m[0] - sx * alto * 0.01, m[1] + alto * 0.05), punta, alto * 0.012, alto * 0.018)
    elif tipo == "escudo":
        p = S.Pose(hombro_c=35, codo_c=55, hombro_l=55, codo_l=35, cadera_c=16, cadera_l=-12, rodilla_c=8)
        j = S.figura(c, x, y, alto, p, at, espejo=mira_izq)
        ml = j["mano_l"]
        S.escudo_oval(c, ml[0] + sx * alto * 0.05, ml[1] - alto * 0.02, alto * 0.13, alto * 0.5)
        m = j["mano_c"]
        ang = math.radians(-70) if not mira_izq else math.radians(-110)
        S.lanza(c, (m[0] - math.cos(ang) * alto * 0.45, m[1] - math.sin(ang) * alto * 0.45), ang, alto * 1.25, alto * 0.016)
    elif tipo == "carnyx":
        p = S.Pose(hombro_c=125, codo_c=35, hombro_l=115, codo_l=40, cadera_c=8, cadera_l=-6)
        j = S.figura(c, x, y, alto, p, at, espejo=mira_izq)
        m = j["mano_c"]
        S.carnyx(c, (m[0], m[1] + alto * 0.45), alto * 1.15, -sx * 0.06)
    else:  # "grito": lanza alzada en el puño
        p = S.Pose(torso=-4, cabeza=12, hombro_c=165, codo_c=5, hombro_l=-20, codo_l=30,
                   cadera_c=12, cadera_l=-12)
        j = S.figura(c, x, y, alto, p, at, espejo=mira_izq)
        m = j["mano_c"]
        S.lanza(c, (m[0] - sx * alto * 0.05, m[1] + alto * 0.5), -math.pi / 2 + sx * 0.12, alto * 1.25, alto * 0.016)
    return punta


def estandarte_jabali(c, x, y, alto):
    """Asta con un jabalí en lo alto, emblema celta."""
    S.capsula(c, (x, y), (x, y - alto), alto * 0.01, alto * 0.01)
    s = alto * 0.12
    cx, cy = x, y - alto - s * 0.3
    S.rellenar(c, [(cx - s * 1.2, cy), (cx - s * 0.9, cy - s * 0.55), (cx - s * 0.2, cy - s * 0.75),
                   (cx + s * 0.6, cy - s * 0.6), (cx + s * 1.25, cy - s * 0.2), (cx + s * 1.3, cy + s * 0.1),
                   (cx + s * 0.6, cy + s * 0.25), (cx - s * 0.8, cy + s * 0.3)])
    for k in range(5):  # cerdas del lomo
        bx = cx - s * 0.7 + k * s * 0.35
        S.rellenar(c, [(bx - s * 0.12, cy - s * 0.6), (bx, cy - s * 1.05), (bx + s * 0.12, cy - s * 0.6)], suave_=False)
    for px in (-0.7, -0.4, 0.4, 0.75):
        S.capsula(c, (cx + px * s, cy + s * 0.2), (cx + px * s, cy + s * 0.65), s * 0.08, s * 0.06)


class Plano2(PlanoBase):
    D = 1.15
    fundido_entrada = 0.45
    fundido_salida = 0.45
    CRESTA = [(0.26, 0.72), (0.36, 0.63), (0.46, 0.565), (0.56, 0.53), (0.68, 0.512), (0.80, 0.52),
              (0.90, 0.535), (1.02, 0.55)]

    def y_cresta(self, u: float) -> float:
        xs, ys = zip(*self.CRESTA)
        return float(np.interp(u, xs, ys)) * self.lh

    def preparar(self) -> None:
        d = self.D
        self.lw, self.lh = int((W + 420) * d), int((H + 140) * d)
        lw, lh = self.lw, self.lh
        r = np.random.default_rng(22)

        def loma(u):
            return lh * (0.528 - 0.028 * math.sin(u * 4.1 + 0.5) - 0.012 * math.sin(u * 11.0))

        def lejana(c):
            S.rellenar(c, [(0, lh)] + [(lw * u, loma(u)) for u in np.linspace(0, 1, 40)] + [(lw, lh)])
            for k in range(90):
                u = r.uniform(0, 1)
                S.arbol_desnudo(c, lw * u, loma(u) + 6, r.uniform(40, 90), semilla=500 + k, niveles=4, apertura=0.5)
        self.lejana = Capa(dibujo(lw, lh, lejana, mez(G["noche"], G["glasto"], 0.25)), d, 0.35)
        # Fogatas del ejército sitiador: grupos sobre la ladera lejana
        self.fuegos = []
        for _ in range(70):
            u0 = r.uniform(0.0, 1.0)
            prof = r.uniform(10, 80)
            for _ in range(int(r.integers(3, 9))):
                u = u0 + r.normal(0, 0.012)
                self.fuegos.append((lw * u, loma(u) + prof + r.normal(0, 6), r.uniform(1.0, 2.2), r.uniform(0, 6.28)))
        self.llamas: list[np.ndarray] = []
        tipos = ["lanza", "antorcha", "escudo", "grito", "lanza", "escudo", "carnyx", "antorcha", "lanza", "grito"]

        def colina(c):
            S.rellenar(c, [(lw * 0.18, lh)] + [(lw * u, lh * v) for u, v in self.CRESTA] + [(lw * 1.02, lh)])
            us, u = [], 0.47
            while u < 0.99:
                us.append(u)
                u += r.uniform(0.012, 0.03)
            for k, u in enumerate(us):
                x, y = lw * u, self.y_cresta(u) + 5
                alto = r.uniform(120, 160)
                punta = guerrero(c, x, y, alto, tipos[k % len(tipos)], 100 + k, mira_izq=r.random() < 0.75)
                if punta is not None:
                    self.llamas.append(punta)
            for u in (0.55, 0.77, 0.93):
                estandarte_jabali(c, lw * u, self.y_cresta(u) + 4, 230)
        col = dibujo(lw, lh, colina, G["noche"] * 0.6)
        borde = contraluz(col[..., 3], 0, -3, 1.0)
        col[..., :3] += tenir(borde, mez(G["antorcha"], G["niebla"], 0.35), 0.55)[..., :3]
        self.colina = Capa(col, d, 0.7)

        def suelo(c):
            pts = [(-10, lh * 0.75)] + [(lw * u, lh * (0.75 + 0.008 * math.sin(u * 9))) for u in np.linspace(0, 0.62, 14)]
            pts += [(lw * 0.8, lh * 0.83), (lw * 0.8, lh + 10), (-10, lh + 10)]
            S.rellenar(c, pts)
            # obreros que tiran de cuerdas al pie de las torres
            for k, (u, esp) in enumerate(((0.06, False), (0.17, True), (0.23, False), (0.35, True), (0.40, True))):
                p = S.Pose(torso=-18 if esp else -18, hombro_c=70, codo_c=20, hombro_l=60, codo_l=25,
                           cadera_c=25, rodilla_c=10, cadera_l=-20, rodilla_l=5)
                S.figura(c, lw * u, lh * 0.752, 95, p, S.Atavio(pelo="largo", capa=0.3), espejo=esp)
        self.suelo = Capa(dibujo(lw, lh, suelo, mez(G["noche"], G["bosque"], 0.15)), d, 0.85)
        self.torres = [(0.11, 440, 150), (0.29, 380, 130)]

        def frente(c):
            S.empalizada(c, lw * 0.0, lw * 1.0, lh * 1.03, lh * 0.17, semilla=5, ancho_estaca=62, travesano=False)
            p = S.Pose(cabeza=4, hombro_c=30, codo_c=70, hombro_l=-5, codo_l=15)
            j = S.figura(c, lw * 0.19, lh * 1.15, 900, p, S.Atavio(pelo="casco", capa=0.8, viento=0.2, tunica=0.8))
            m = j["mano_c"]
            S.lanza(c, (m[0] - 14, m[1] + 420), -math.pi / 2 + 0.05, 1150, 15, punta=0.08)
            S.escudo_romano(c, j["mano_l"][0] - 28, j["mano_l"][1] + 40, 100, 420)
        fr = dibujo(lw, lh, frente, G["noche"] * 0.3)
        borde = contraluz(fr[..., 3], 4, -2, 2.0)
        fr[..., :3] += tenir(borde, mez(G["antorcha"], G["niebla"], 0.5), 0.45)[..., :3]
        self.frente = Capa(desenfoque(fr, 2.2), d, 1.0)
        self.niebla = A.Niebla(212)
        self.niebla_baja = A.Niebla(313, celda=64)
        self.humo = A.Humo(414)
        self.brasas = A.Brasas([tuple(p) for p in self.llamas], 9, 61, subida=(35, 85), deriva=16)
        self.estrellas = A.Estrellas(200, 71, (0, 0, W, H * 0.4))

    def obras(self, c, t: float) -> None:
        """Torres y terraplén que se levantan desde la marca 'torres'."""
        lw, lh = self.lw, self.lh
        t0 = self.m("torres")
        S.tinta(c, mez(G["noche"], G["bosque"], 0.1) * 0.8)
        for k, (u, alto, ancho) in enumerate(self.torres):
            p = sale(tramo(t, t0 + 0.5 * k, t0 + 0.5 * k + 4.2), 2.2)
            if p > 0.01:
                S.torre_madera(c, lw * u, lh * 0.755, ancho, alto, semilla=40 + k, progreso=p, tejado=k == 0)
        fin = sale(tramo(t, t0 - 0.3, t0 + 4.8), 2.0)
        if fin > 0.01:
            x1 = lw * 0.46 * fin
            alto = 46
            pts = [(-10, lh * 0.76), (-10, lh * 0.755 - alto)]
            for u in np.linspace(0, 1, 16):
                pts.append((x1 * u, lh * 0.755 - alto * (1 - 0.15 * math.sin(u * 13))))
            pts += [(x1 + 30, lh * 0.76)]
            S.rellenar(c, pts, suave_=False)
            S.empalizada(c, -10, x1, lh * 0.755 - alto + 6, 48, semilla=8, ancho_estaca=9, travesano=False)

    def cuadro(self, t: float) -> np.ndarray:
        u = suave(t / self.duracion)
        cx, cy, z = 150 - 300 * u, 0.0, 1.03 + 0.06 * u
        v35 = Vista(self.lw, self.lh, self.D, cx, cy, z, 0.35)
        v7 = Vista(self.lw, self.lh, self.D, cx, cy, z, 0.7)
        v85 = Vista(self.lw, self.lh, self.D, cx, cy, z, 0.85)
        img = gradiente_vertical([(0.0, G["noche"] * 0.8), (0.30, mez(G["noche"], G["glasto"], 0.5)),
                                  (0.47, mez(G["glasto"], G["antorcha"], 0.18)), (0.60, mez(G["glasto"], G["niebla"], 0.35))])
        self.estrellas.dibujar(img, t, 0.35, dx=cx * 0.1)
        cielo = Luces()
        for k, uu in enumerate((0.5, 0.62, 0.74, 0.86, 0.97)):
            sx, sy = v7.p(self.lw * uu, self.y_cresta(uu) + 20)
            cielo.punto(sx, sy, 380, G["antorcha"], 0.24 + 0.03 * A.parpadeo(t, k), achatado=0.55)
        sx, sy = v35.p(self.lw * 0.2, self.lh * 0.42)
        cielo.punto(sx, sy, 520, mez(G["glasto"], G["niebla"], 0.6), 0.16)
        img += cielo.resultado()
        sobre(img, self.lejana.ver(cx, cy, z))
        resplandor_fuegos = Luces()
        for k, (x, y, tam, ph) in enumerate(self.fuegos):
            sx, sy = v35.p(x, y)
            if -5 < sx < W + 5:
                vivo = 0.75 + 0.25 * math.sin(t * 7 + ph)
                A.salpicar(img, sx, sy, tam, mez(G["antorcha"], BLANCO, 0.25), 0.9 * vivo)
                if k % 4 == 0:
                    resplandor_fuegos.punto(sx, sy, 34, G["antorcha"], 0.10 * vivo)
        img += resplandor_fuegos.resultado()
        humo = self.humo.alfa(t, [(*v35.p(self.lw * uu, self.lh * 0.53), 30, 320) for uu in (0.35, 0.6, 0.84)], densidad=0.3)
        A.componer_niebla(img, humo, mez(G["niebla"], G["antorcha"], 0.25) * 0.6)
        n = self.niebla.alfa(t, y0=H * 0.40, y1=H * 0.62, densidad=0.32, vel=(12, 0), dx=cx * 0.35)
        A.componer_niebla(img, n, mez(G["niebla"], G["glasto"], 0.35))
        sobre(img, self.colina.ver(cx, cy, z))
        luz = Luces()
        halo = Luces()
        for k, p in enumerate(self.llamas):
            sx, sy = v7.p(*p)
            luz.punto(sx, sy, 130, G["antorcha"], 0.2 * A.parpadeo(t, k))
            halo.punto(sx, sy - 6, 34, G["antorcha"], 0.3 * A.parpadeo(t, k))
        img += halo.resultado()
        for k, p in enumerate(self.llamas):
            sx, sy = v7.p(*p)
            A.llama(img, sx, sy, 24 * v7.escala, 12 * v7.escala, t, 200 + k, 1.15)
        self.brasas.dibujar(img, t, transformar=lambda x, y: (*v7.p(x, y), v7.escala), col=G["antorcha"], intensidad=0.85)
        luz_img = luz.resultado()
        n2 = self.niebla_baja.alfa(t, y0=H * 0.58, y1=H * 0.86, densidad=0.36, vel=(-18, 0), dx=cx * 0.75, escala=1.0, umbral=0.25, suavidad=0.6)
        A.componer_niebla(img, n2, mez(G["niebla"], G["glasto"], 0.4) * 0.65, luz_img, 0.9)
        sobre(img, self.suelo.ver(cx, cy, z))
        s, c = S.lienzo(W, H)
        v85.aplicar(c)
        self.obras(c, t)
        obras = S.a_rgba(s)
        borde = contraluz(obras[..., 3], 0, -2, 1.0)
        obras[..., :3] += tenir(borde, mez(G["glasto"], G["niebla"], 0.6), 0.35)[..., :3]
        sobre(img, obras)
        n3 = self.niebla.alfa(t, y0=H * 0.70, y1=H * 1.05, densidad=0.3, vel=(-10, 0), dx=cx, escala=1.8, umbral=0.45)
        A.componer_niebla(img, n3, mez(G["niebla"], G["glasto"], 0.4) * 0.45)
        sobre(img, self.frente.ver(cx, cy, z))
        return self.acabar(img, t, papel=0.25, vineta=0.5, bloom=0.4, grano=0.014)


# =========================================================================== objetos compartidos

# Latín escrito con letras griegas, como cuenta César (Graecis litteris): «César saluda a
# Cicerón. Salí con las legiones; llegaré pronto. Conserva tu valor de siempre.»
TEXTO_GRIEGO = ["ΚΑΙΣΑΡ ΚΙΚΕΡΩΝΙ ΣΑΛΟΥΤΕΜ", "ΚΟΥΜ ΛΕΓΙΩΝΙΒΟΥΣ ΠΡΟΦΕΚΤΟΥΣ",
                "ΚΕΛΕΡΙΤΕΡ ΑΔΕΡΩ", "ΠΡΙΣΤΙΝΑΜ ΟΥΙΡΤΟΥΤΕΜ ΡΕΤΙΝΕ"]
GRIEGAS = "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"


def glifo_tinta(ch: str, tam: int, semilla: int) -> np.ndarray:
    """Letra con borde de tinta que se corre un poco en el pergamino."""
    a = texto_alfa(ch, "EBGaramond-Regular.ttf", tam, margen=12)
    r = np.random.default_rng(semilla)
    g = desenfoque(a[..., None], 0.9)[..., 0]
    ruido = r.uniform(-1, 1, a.shape).astype(np.float32)
    ruido = desenfoque(ruido[..., None], 1.2)[..., 0]
    return np.clip((g - 0.42 + 0.35 * ruido) / 0.16, 0, 1)


class Carta:
    """Pergamino con el mensaje en letras griegas; puede escribirse, mostrarse o revolverse."""

    def __init__(self, ancho: int = 1500, alto: int = 900, tam: int = 74, semilla: int = 7):
        r = np.random.default_rng(semilla)
        self.w, self.h, self.tam = ancho, alto, tam
        m = 26
        contorno = S.rugoso([(m, m), (ancho - m, m), (ancho - m, alto - m), (m, alto - m)], 7, 5, semilla)
        self.alfa = alfa_de(ancho, alto, lambda c: S.rellenar(c, contorno, suave_=False))
        manchas = fbm(alto, ancho, 128, 4, 0.5, semilla)
        bordes = 1 - desenfoque(self.alfa[..., None], 34)[..., 0]
        base = mez(R["marmol"], R["terracota"], 0.10)
        mancha = mez(R["terracota"], R["tinta"], 0.35)
        k = np.clip((manchas - 0.55) * 1.6, 0, 1)[..., None] * 0.35 + np.clip(bordes * 1.6, 0, 1)[..., None] * 0.55
        self.base = (base * (1 - k) + mancha * k) * (0.94 + 0.06 * textura_papel(semilla, ancho, alto))[..., None]
        self.glifos = []
        y = alto * 0.15
        for li, linea in enumerate(TEXTO_GRIEGO):
            x = ancho * 0.075 + r.uniform(-6, 6)
            for ch in linea:
                adv = fuente("EBGaramond-Regular.ttf", tam).getlength(ch)
                if ch != " ":
                    self.glifos.append(dict(ch=ch, x=x + r.uniform(-2, 2), y=y + r.uniform(-3, 3),
                                            a=glifo_tinta(ch, tam, semilla * 1000 + len(self.glifos)),
                                            rot=r.uniform(-3, 3), adv=adv, linea=li))
                x += adv + tam * 0.07
            y += tam * 1.42
        self._otras = {ch: glifo_tinta(ch, tam, 999 + i) for i, ch in enumerate(GRIEGAS)}

    def punta(self, n: float) -> tuple[float, float]:
        """Punta de la pluma (px de la carta) cuando van escritas `n` letras."""
        i = int(min(max(n, 0), len(self.glifos) - 1))
        g = self.glifos[i]
        frac = min(1.0, max(0.0, n - i))
        return g["x"] + g["adv"] * frac, g["y"] + self.tam * 0.62

    def imagen(self, visibles: float | None = None, revuelto: float = 0.0, t: float = 0.0,
               ancho_visible: float = 1.0) -> np.ndarray:
        tinta_ = np.zeros((self.h, self.w), np.float32)
        mg = 12
        for i, g in enumerate(self.glifos):
            vis = 1.0 if visibles is None else min(1.0, max(0.0, visibles - i))
            if vis <= 0:
                continue
            a = g["a"]
            x, y = g["x"], g["y"]
            if revuelto > 0:
                rr = np.random.default_rng(i * 7919 + int(t * 7 * (1 + revuelto)))
                if rr.random() < 0.25 + 0.75 * revuelto:
                    a = self._otras[GRIEGAS[int(rr.integers(0, len(GRIEGAS)))]]
                ang = g["rot"] + revuelto * 55 * math.sin(t * 2.7 + i * 1.3)
                img = Image.fromarray(a).rotate(ang, resample=Image.BILINEAR, expand=False)
                if rr.random() < 0.3 * revuelto:
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
                a = np.asarray(img, np.float32)
                x += revuelto * 26 * math.sin(t * 2.1 + i * 1.7)
                y += revuelto * 20 * math.cos(t * 1.7 + i * 2.3)
            elif abs(g["rot"]) > 0.01:
                a = np.asarray(Image.fromarray(a).rotate(g["rot"], resample=Image.BILINEAR), np.float32)
            if vis < 1.0:
                xs = np.arange(a.shape[1], dtype=np.float32)
                corte = mg + g["adv"] * vis
                a = a * np.clip((corte - xs) / 6.0, 0, 1)[None, :]
            x0, y0 = int(x) - mg, int(y) - mg
            h, w = a.shape
            if x0 < 0 or y0 < 0 or x0 + w > self.w or y0 + h > self.h:
                continue
            zona = tinta_[y0 : y0 + h, x0 : x0 + w]
            np.maximum(zona, a, out=zona)
        tinta_ *= 0.92
        rgb = self.base * (1 - tinta_[..., None]) + R["tinta"] * tinta_[..., None]
        alfa = self.alfa
        if ancho_visible < 1.0:
            xs = np.arange(self.w, dtype=np.float32)
            alfa = alfa * np.clip((self.w * ancho_visible - xs) / 3.0, 0, 1)[None, :]
        return np.concatenate([rgb * alfa[..., None], alfa[..., None]], axis=-1).astype(np.float32)


def rodillo(c, x: float, y0: float, y1: float, diametro: float, col_claro, col_oscuro) -> None:
    """Pergamino enrollado visto de lado: cilindro con sombreado y la espiral en el extremo."""
    grad = cairo.LinearGradient(x - diametro / 2, 0, x + diametro / 2, 0)
    for pos, col in ((0.0, col_oscuro), (0.45, col_claro), (1.0, col_oscuro)):
        grad.add_color_stop_rgba(pos, float(col[0]), float(col[1]), float(col[2]), 1.0)
    c.set_source(grad)
    c.rectangle(x - diametro / 2, y0, diametro, y1 - y0)
    c.fill()
    S.tinta(c, col_oscuro)
    S.elipse(c, x, y0, diametro / 2, diametro * 0.18)
    S.tinta(c, mez(col_oscuro, NEGRO, 0.4))
    c.set_line_width(1.5)
    for k in range(3):
        c.arc(x, y0, diametro * (0.12 + 0.13 * k), math.pi * 0.1, math.pi * 1.6)
        c.stroke()


def luz_vela(x: float, y: float, t: float, intensidad: float = 1.0, radio: float = 520,
             col=None) -> np.ndarray:
    """Mapa de luz (H, W, 3) de una vela que titila."""
    col = mez(R["oro_aguila"], R["terracota"], 0.35) if col is None else col
    l = Luces()
    f = A.parpadeo(t, 5)
    l.punto(x, y, radio * (0.97 + 0.03 * f), col, 1.25 * intensidad * f)
    l.punto(x, y, radio * 0.25, mez(col, BLANCO, 0.4), 0.6 * intensidad * f, forma="gauss")
    return l.resultado()


class TiendaInterior:
    """Pared de cuero de una tienda romana: pliegues, costuras y suelo (albedo sin luz)."""

    def __init__(self, lw: int, lh: int, semilla: int = 31):
        r = np.random.default_rng(semilla)
        xs = np.arange(lw, dtype=np.float32)
        pliegues = np.zeros(lw, np.float32)
        for k in range(7):
            pliegues += np.sin(xs / lw * math.tau * r.uniform(2, 9) + r.uniform(0, 6)) * r.uniform(0.03, 0.08)
        base = mez(R["terracota"], R["purpura"], 0.35) * 0.55
        albedo = np.broadcast_to(base, (lh, lw, 3)).copy()
        albedo *= (1 + pliegues)[None, :, None]
        vetas = fbm(lh, lw, 96, 4, 0.5, semilla)
        albedo *= (0.85 + 0.3 * vetas)[..., None]
        for x in np.arange(lw * 0.08, lw, lw * 0.16):
            x = int(x + r.uniform(-20, 20))
            albedo[:, max(0, x - 2) : x + 2] *= 0.55
        suelo = int(lh * 0.83)
        albedo[suelo:] = mez(R["tinta"], R["terracota"], 0.25) * (0.8 + 0.3 * fbm(lh - suelo, lw, 32, 3, 0.5, semilla + 1))[..., None]
        self.albedo = Capa(np.concatenate([albedo, np.ones((lh, lw, 1), np.float32)], -1), 1.1, 1.0)
        self.suelo = suelo


# =========================================================================== PLANO 3
# Interior de la tienda: Quinto Cicerón solo junto a una vela. Paleta de Roma, muy oscura.


class Plano3(PlanoBase):
    D = 1.1
    fundido_entrada = 0.5
    fundido_salida = 0.8

    def preparar(self) -> None:
        d = self.D
        self.lw, self.lh = int((W + 160) * d), int((H + 100) * d)
        lw, lh = self.lw, self.lh
        self.tienda = TiendaInterior(lw, lh, 31)
        piso = self.tienda.suelo + 30
        self.vela_pos = None

        def figura(c):
            pose = S.Pose(torso=30, cabeza=-28, hombro_c=38, codo_c=110, hombro_l=30, codo_l=105,
                          cadera_c=82, rodilla_c=92, cadera_l=78, rodilla_l=88)
            j = S.figura(c, lw * 0.40, piso, 520, pose, S.Atavio(pelo="corto", capa=0.7, tunica=0.5))
            P = j["P"]
            # banco plegable de campaña bajo la cadera
            S.capsula(c, (P[0] - 70, P[1] + 20), (P[0] + 60, piso), 7, 7)
            S.capsula(c, (P[0] + 60, P[1] + 20), (P[0] - 70, piso), 7, 7)
            c.rectangle(P[0] - 85, P[1] + 10, 170, 16)
            c.fill()
            # cofre con la vela, una copa y un estuche de rollos
            c.rectangle(lw * 0.60, piso - 150, 230, 150)
            c.fill()
            c.rectangle(lw * 0.595, piso - 160, 240, 18)
            c.fill()
            S.capsula(c, (lw * 0.70, piso - 160), (lw * 0.70, piso - 205), 14, 20)
            S.elipse(c, lw * 0.70, piso - 210, 26, 8)
            c.rectangle(lw * 0.735, piso - 205, 44, 45)
            c.fill()
        self.capa_figura = Capa(dibujo(lw, lh, figura, R["tinta"] * 0.6), d)
        self.vela_base = (lw * 0.645, piso - 160)

        def vela(c):
            S.vela(c, self.vela_base[0], self.vela_base[1], 30, 120)
        self.capa_vela = Capa(dibujo(lw, lh, vela, mez(R["marmol"], R["terracota"], 0.25) * 0.85), d)
        self.mecha = (self.vela_base[0], self.vela_base[1] - 120 - 30 * 0.35)
        self.polvo = A.Polvo(110, 13, vel=(3.0, -2.0), tam=(0.8, 2.4))

    def cuadro(self, t: float) -> np.ndarray:
        u = suave(t / self.duracion)
        cx, cy, z = -10 - 40 * u, -10 * u, 1.02 + 0.07 * u
        v = Vista(self.lw, self.lh, self.D, cx, cy, z)
        mx, my = v.p(*self.mecha)
        luz = luz_vela(mx, my, t, 1.0, 560) + mez(R["purpura"], R["tinta"], 0.5) * 0.10
        pared = self.tienda.albedo.ver(cx, cy, z)[..., :3]
        figura = self.capa_figura.ver(cx, cy, z)
        # sombra del cuerpo proyectada en la pared, más grande y temblorosa
        f = A.parpadeo(t, 5)
        esc = 1.55 + 0.02 * (f - 1) * 10
        sombra_img = Image.fromarray(np.ascontiguousarray(figura[..., 3]), "F")
        a = 1 / esc
        sombra_img = sombra_img.transform((W, H), Image.AFFINE, (a, 0, mx - a * mx - 6, 0, a, my - a * my + 30),
                                          resample=Image.BILINEAR)
        sombra = desenfoque(np.array(sombra_img)[..., None], 9)[..., 0]
        img = pared * luz * (1 - 0.82 * np.clip(sombra, 0, 1))[..., None]
        borde = contraluz(figura[..., 3], 3, -1, 1.5)
        sobre(img, figura)
        img += borde[..., None] * luz * 0.6
        vela_ = self.capa_vela.ver(cx, cy, z)
        vela_[..., :3] *= np.clip(luz * 0.9, 0, 1.4)
        sobre(img, vela_)
        A.llama(img, mx, my, 34 * v.escala, 12 * v.escala, t, 5, 1.3)
        self.polvo.dibujar(img, t, mez(R["oro_aguila"], BLANCO, 0.4), 0.5, luz=np.clip(luz[..., 0], 0, 1))
        return self.acabar(img, t, papel=0.2, vineta=0.6, bloom=0.45, umbral_bloom=0.55, grano=0.016)


# =========================================================================== PLANO 4
# César escribe en letras griegas (Roma), entrega la carta al jinete galo al atardecer y le
# promete una recompensa: caen monedas de oro en la mano del jinete.


def _puntos(local, origen, ang, escala):
    ca, sa = math.cos(ang), math.sin(ang)
    ox, oy = origen
    return [(ox + (x * ca - y * sa) * escala, oy + (x * sa + y * ca) * escala) for x, y in local]


def mano_escribe(c, punta, escala: float, oscilar: float = 0.0, manga=None) -> None:
    """Mano derecha que sostiene una pluma de caña, vista desde arriba.

    El índice corre sobre la caña, el pulgar la pinza por un lado y los demás dedos van
    recogidos; el dorso y el antebrazo salen hacia abajo a la derecha. La punta toca `punta`.
    """
    e = escala
    p = np.array(punta, float)
    u = np.array([0.538, -0.843])            # eje de la caña (sube hacia la derecha)
    n = np.array([0.843, 0.538])             # perpendicular, hacia el dorso de la mano
    g = p + u * 58 * e + n * oscilar * 0.3   # punto de agarre
    S.capsula(c, p, p + u * 300 * e, 2.6 * e, 4.4 * e)                                   # caña
    k1 = g + u * 92 * e + n * 26 * e                                                     # nudillo del índice
    S.capsula(c, g + n * 3 * e, k1, 12 * e, 16 * e)                                      # índice sobre la caña
    S.capsula(c, g - n * 10 * e + u * 8 * e, g + u * 48 * e - n * 30 * e, 13 * e, 16 * e)  # pulgar
    S.capsula(c, g + u * 48 * e - n * 30 * e, g + u * 92 * e - n * 6 * e, 16 * e, 22 * e)
    S.capsula(c, g + n * 18 * e + u * 14 * e, g + n * 64 * e + u * 60 * e, 12 * e, 15 * e)  # medio recogido
    S.capsula(c, g + n * 40 * e + u * 22 * e, g + n * 92 * e + u * 62 * e, 11 * e, 14 * e)  # anular recogido
    muneca = g + u * 70 * e + n * 190 * e
    dorso = [k1 + n * 2 * e, k1 + n * 34 * e + u * 6 * e, k1 + n * 68 * e - u * 2 * e,
             k1 + n * 100 * e - u * 14 * e, muneca + u * 40 * e + n * 10 * e, muneca - u * 50 * e,
             g + n * 70 * e + u * 40 * e, g + u * 60 * e]
    S.rellenar(c, dorso)
    fin = muneca + np.array([520, 440]) * e
    S.capsula(c, muneca, fin, 60 * e, 92 * e)                                            # antebrazo
    if manga is not None:
        S.tinta(c, manga)
        S.capsula(c, muneca + (fin - muneca) * 0.28, fin + np.array([80, 60]) * e, 96 * e, 122 * e)


PALMA_LOCAL = [(-110, 12), (-40, 18), (40, 15), (110, 2)]


def mano_abierta(c, x: float, y: float, escala: float) -> list[tuple[float, float]]:
    """Mano ahuecada con la palma hacia arriba, de perfil; el antebrazo entra por la derecha.

    Devuelve la curva de la palma (en pantalla) donde se apoyan las monedas.
    """
    e = escala
    P = lambda pts: [(x + px * e, y + py * e) for px, py in pts]  # noqa: E731
    S.capsula(c, *P([(150, 45), (760, 250)]), 64 * e, 90 * e)                                 # antebrazo
    S.rellenar(c, P([(-120, 42), (-112, 10), (-40, 18), (40, 15), (110, 2), (150, -8), (178, 30),
                     (172, 85), (60, 100), (-60, 84)]))                                      # palma
    S.rellenar(c, P([(-120, 42), (-200, 26), (-242, -8), (-250, -46), (-228, -52), (-208, -22),
                     (-162, 0), (-112, 10)]))                                                # dedos
    S.capsula(c, *P([(112, 4), (66, -84)]), 25 * e, 18 * e)                                  # pulgar
    S.capsula(c, *P([(66, -84), (40, -96)]), 18 * e, 15 * e)
    return P(PALMA_LOCAL)


MANO_MONEDAS = (0.46, 0.66, 1.55)   # x, y relativos y escala de la mano en 4c


def simular_monedas(semilla: int = 17, n: int = 12, palma=None):
    """Caída de monedas sobre la palma. Devuelve trayectorias y golpes (para imagen y sonido).

    `palma`: borde superior de la mano en pantalla, de izquierda a derecha; sin él, la mano de
    recorte. Coordenadas de pantalla; tiempo relativo a la marca 'monedas'. Determinista.
    """
    r = np.random.default_rng(semilla)
    recorte = palma is None
    if recorte:
        mx, my, e = W * MANO_MONEDAS[0], H * MANO_MONEDAS[1], MANO_MONEDAS[2]
        palma = [(mx + x * e, my + y * e) for x, y in PALMA_LOCAL]
        abre = 90.0
    else:
        xs_, ys_ = np.array([q[0] for q in palma]), np.array([q[1] for q in palma])
        lo = ys_ > ys_.max() - 0.25 * (ys_.max() - ys_.min())       # fondo del hueco de la mano
        mx = float(xs_[lo].mean())
        abre = 0.35 * float(xs_[lo].max() - xs_[lo].min()) + 10
    px, py = zip(*palma)
    g, dt = 1500.0, 1 / 240
    monedas, golpes, pila = [], [], 0
    for k in range(n):
        t0 = 0.11 * k + r.uniform(0, 0.07)
        x, y = mx + r.uniform(-abre, abre), -60.0 - r.uniform(0, 80)
        vx, vy = r.uniform(-40, 40), r.uniform(0, 60)
        giro, vgiro = r.uniform(0, 6.28), r.uniform(7, 14)
        cae_fuera = k in (3, 8)
        tray, t, quieta, rebotes = [], t0, False, 0
        while t < t0 + 4.0:
            tray.append((t, x, y, giro))
            if not quieta:
                vy += g * dt
                x += vx * dt
                y += vy * dt
                giro += vgiro * dt
                suelo = np.interp(x, px, py) - 14 - pila * 6 if min(px) < x < max(px) else 1e9
                if not cae_fuera and y >= suelo and vy > 0:
                    golpes.append((t, min(1.0, vy / 1400.0)))
                    y = suelo
                    vy *= -0.3
                    vx = vx * 0.4 + r.uniform(-30, 30)
                    vgiro *= 0.35
                    rebotes += 1
                    if rebotes >= 2 or abs(vy) < 70:
                        quieta, pila = True, pila + 1
                        giro = math.pi / 2 * round(giro / (math.pi / 2)) + 0.25
                elif cae_fuera and y >= suelo and vy > 0 and rebotes == 0:
                    golpes.append((t, min(1.0, vy / 1400.0)))
                    vy *= -0.4
                    vx = (300 if x > mx else -300) if recorte else -260   # la que no cae, sale por las yemas
                    rebotes = 1
            t += dt
        monedas.append(np.array(tray))
    return monedas, sorted(golpes)


def dibujar_moneda(c, x, y, radio, giro, inclinacion=0.15):
    """Moneda de oro: elipse que se achata al girar, con borde y brillo."""
    ry = max(radio * abs(math.cos(giro)), radio * 0.12)
    oro = R["oro_aguila"]
    c.save()
    c.translate(x, y)
    c.rotate(inclinacion)
    grad = cairo.LinearGradient(-radio, -ry, radio, ry)
    claro, oscuro = mez(oro, BLANCO, 0.45), mez(oro, R["tinta"], 0.45)
    grad.add_color_stop_rgb(0, *map(float, claro))
    grad.add_color_stop_rgb(0.55, *map(float, oro))
    grad.add_color_stop_rgb(1, *map(float, oscuro))
    c.set_source(grad)
    c.scale(radio, ry)
    c.arc(0, 0, 1, 0, math.tau)
    c.restore()
    c.fill()
    c.save()
    c.translate(x, y)
    c.rotate(inclinacion)
    c.scale(radio * 0.72, ry * 0.72)
    c.arc(0, 0, 1, 0, math.tau)
    c.restore()
    c.set_source_rgba(*map(float, oscuro), 0.5)
    c.set_line_width(1.6)
    c.stroke()


def aguila(c, x: float, y_base: float, alto: float) -> None:
    """Águila legionaria sobre su asta: alas alzadas, corona de laurel debajo."""
    top = y_base - alto
    c.rectangle(x - 3, top, 6, alto)
    c.fill()
    c.rectangle(x - 26, top - 4, 52, 8)
    c.fill()
    c.set_line_width(6)
    c.arc(x, top + 34, 22, 0, math.tau)
    c.stroke()
    S.elipse(c, x, top - 26, 13, 24, 0.15)
    S.elipse(c, x + 12, top - 52, 9, 8)
    S.rellenar(c, [(x + 18, top - 55), (x + 30, top - 50), (x + 19, top - 47)], suave_=False)
    for lado in (-1, 1):
        S.rellenar(c, [(x + lado * 6, top - 36), (x + lado * 30, top - 62), (x + lado * 58, top - 112),
                       (x + lado * 44, top - 100), (x + lado * 50, top - 128), (x + lado * 30, top - 96),
                       (x + lado * 30, top - 120), (x + lado * 16, top - 76), (x + lado * 4, top - 50)],
                   suave_=False)
    S.rellenar(c, [(x - 8, top - 6), (x, top + 4), (x + 8, top - 6)], suave_=False)


class Plano4Recorte(PlanoBase):
    """Plano 4 en el estilo de recorte de papel (cápsulas de siluetas.py); queda como referencia."""

    fundido_entrada = 0.5
    fundido_salida = 0.35
    CRUCE = 0.45

    def preparar(self) -> None:
        self.carta = Carta(1500, 900, 74, 7)
        self.n_linea1 = sum(1 for g in self.carta.glifos if g["linea"] == 0)
        # mesa de madera oscura
        r = np.random.default_rng(4)
        lw, lh = int((W + 200) * 1.25), int((H + 200) * 1.25)
        vetas = ampliar(fbm(lh, lw // 16, 24, 3, 0.5, 4), lw, lh)
        madera = mez(R["tinta"], R["terracota"], 0.28) * (0.65 + 0.6 * vetas)[..., None]
        self.mesa = Capa(np.concatenate([madera, np.ones((lh, lw, 1), np.float32)], -1), 1.25)
        # atardecer en el campamento de César
        self.monedas, self.golpes = simular_monedas()
        dl, dh = int((W + 240) * 1.1), int((H + 120) * 1.1)
        self.dl, self.dh = dl, dh

        def fondo(c):
            for k in range(14):
                x = dl * (0.03 + 0.075 * k) + r.uniform(-20, 20)
                S.tienda(c, x, dh * 0.665, r.uniform(110, 160), r.uniform(70, 100))
            # águila de la legión sobre su asta
            aguila(c, dl * 0.30, dh * 0.665, 360)
        self.fondo = Capa(dibujo(dl, dh, fondo, mez(R["purpura"], R["tinta"], 0.55)), 1.1, 0.5)

        def suelo(c):
            S.rellenar(c, [(-10, dh * 0.70)] + [(dl * u, dh * (0.70 + 0.01 * math.sin(u * 7))) for u in np.linspace(0, 1, 12)]
                       + [(dl + 10, dh + 10), (-10, dh + 10)])
        self.suelo = Capa(dibujo(dl, dh, suelo, R["tinta"] * 0.8), 1.1, 0.8)
        self.polvo = A.Polvo(120, 19, vel=(9.0, -2.0), tam=(0.8, 2.6))
        # fondo de las monedas: bokeh cálido
        bok = np.zeros((H, W, 3), np.float32)
        for k in range(26):
            x, y = r.uniform(0, W), r.uniform(0, H * 0.8)
            A.salpicar(bok, x, y, r.uniform(25, 60), mez(R["oro_aguila"], R["terracota"], r.uniform(0, 1)), r.uniform(0.08, 0.25))
        self.bokeh = bok

    # ---- 4a: escribir
    def escribir(self, t: float) -> np.ndarray:
        u = suave(t / max(self.m("entrega"), 0.1))
        z = 1.08 + 0.06 * u
        img = self.mesa.ver(-60 + 80 * u, 20 - 30 * u, z)[..., :3]
        n = max(0.0, (t - 0.35) * 6.6)
        carta = self.carta.imagen(visibles=n)
        cx, cy = W * 0.52 - 120 * u, H * 0.56 - 20 * u
        esc, ang = 1.02 * z, math.radians(-3)
        sobre(img, colocar(carta, cx, cy, esc, ang))
        # pluma: del espacio de la carta a pantalla
        px, py = self.carta.punta(min(n, len(self.carta.glifos) - 0.01))
        dx, dy = (px - self.carta.w / 2) * esc, (py - self.carta.h / 2) * esc
        ca, sa = math.cos(ang), math.sin(ang)
        punta = (cx + dx * ca - dy * sa, cy + dx * sa + dy * ca + 4 * math.sin(t * 19))
        s, c = S.lienzo(W, H)
        S.tinta(c, R["tinta"] * 0.5)
        mano_escribe(c, punta, 1.15, 3 * math.sin(t * 9), manga=mez(R["purpura"], R["tinta"], 0.45))
        mano = S.a_rgba(s)
        borde = contraluz(mano[..., 3], -3, -3, 1.5)
        sobre(img, mano)
        # puño de la manga en púrpura de Tiro
        luz = Luces()
        luz.punto(W * 0.05, -H * 0.15, 1300, mez(R["oro_aguila"], R["terracota"], 0.3), 1.15)
        luz.punto(W * 0.3, H * 0.3, 500, R["oro_aguila"], 0.25)
        luz = luz.resultado() + 0.08
        img *= luz
        img += borde[..., None] * mez(R["oro_aguila"], BLANCO, 0.3) * 0.5
        return img

    # ---- 4b: la entrega al atardecer
    def entrega(self, t: float) -> np.ndarray:
        dur = self.m("monedas") - self.m("entrega")
        u = suave(t / max(dur, 0.1))
        cx, z = 30 - 50 * u, 1.03 + 0.05 * u
        img = gradiente_vertical([(0.0, R["purpura"] * 0.45), (0.42, mez(R["purpura"], R["terracota"], 0.55)),
                                  (0.62, mez(R["terracota"], R["oro_aguila"], 0.55)), (0.70, R["tinta"])])
        sol = Luces()
        sol.punto(W * 0.56 - cx * 0.3, H * 0.63, 280, R["oro_aguila"], 0.55)
        sol.punto(W * 0.56 - cx * 0.3, H * 0.63, 50, mez(R["oro_aguila"], BLANCO, 0.6), 0.8, forma="gauss")
        img += sol.resultado()
        sobre(img, self.fondo.ver(cx, 0, z))
        sobre(img, self.suelo.ver(cx, 0, z))
        v = Vista(self.dl, self.dh, 1.1, cx, 0, z)
        piso = self.dh * 0.86
        # tiempos del gesto
        brazo_cesar = suave(tramo(t, 0.0, 0.9)) * (1 - suave(tramo(t, 2.4, 3.4)))
        brazo_jinete = suave(tramo(t, 0.6, 1.5)) * (1 - 0.6 * suave(tramo(t, 1.9, 2.8)))
        en_jinete = t > 1.6
        viento = 0.35 + 0.2 * math.sin(t * 1.7)
        s, c = S.lienzo(W, H)
        v.aplicar(c)
        S.tinta(c, R["tinta"] * 0.7)
        S.caballo(c, self.dl * 0.80, piso, 500, espejo=True, cuello=-12, t=t, viento=0.3)
        # jinete galo: capa teñida de glasto, luego cuerpo
        pj = S.Pose(torso=-3, hombro_c=10 + 70 * brazo_jinete, codo_c=20 - 10 * brazo_jinete, hombro_l=-10, codo_l=25)
        aj = S.Atavio(pelo="largo", bigote=True, capa=0.8, viento=viento)
        S.tinta(c, mez(G["glasto"], R["tinta"], 0.55))
        S.figura(c, self.dl * 0.64, piso, 560, pj, aj, espejo=True)
        S.tinta(c, R["tinta"] * 0.7)
        aj.capa = 0.0
        jj = S.figura(c, self.dl * 0.64, piso, 560, pj, aj, espejo=True)
        # César: paludamento rojo, luego cuerpo
        pc = S.Pose(hombro_c=8 + 80 * brazo_cesar, codo_c=15 - 10 * brazo_cesar, hombro_l=-6, codo_l=20)
        ac = S.Atavio(pelo="calvo", capa=1.0, tunica=0.9, viento=viento * 0.6)
        S.tinta(c, mez(R["rojo_legion"], R["tinta"], 0.45))
        S.figura(c, self.dl * 0.41, piso, 575, pc, ac)
        S.tinta(c, R["tinta"] * 0.7)
        ac.capa = 0.0
        jc = S.figura(c, self.dl * 0.41, piso, 575, pc, ac)
        figuras = S.a_rgba(s)
        # el rollo: en la mano de César y luego en la del jinete
        s2, c2 = S.lienzo(W, H)
        v.aplicar(c2)
        mano = jj["mano_c"] if en_jinete else jc["mano_c"]
        S.tinta(c2, mez(R["marmol"], R["terracota"], 0.4) * 0.72)
        S.capsula(c2, (mano[0] - 6, mano[1] - 34), (mano[0] - 6, mano[1] + 34), 9, 9)
        rollo = S.a_rgba(s2)
        borde = contraluz(figuras[..., 3], 0, -2, 1.2)
        sobre(img, figuras)
        img += borde[..., None] * mez(R["oro_aguila"], BLANCO, 0.2) * 0.55
        sobre(img, rollo)
        self.polvo.dibujar(img, t, mez(R["oro_aguila"], BLANCO, 0.5), 0.35)
        return img

    # ---- 4c: monedas en la palma del jinete
    def monedas_(self, t: float) -> np.ndarray:
        img = gradiente_vertical([(0.0, mez(R["purpura"], R["tinta"], 0.65)), (1.0, R["tinta"] * 0.7)])
        img += self.bokeh
        s, c = S.lienzo(W, H)
        S.tinta(c, R["tinta"] * 0.55)
        mano_abierta(c, W * MANO_MONEDAS[0], H * MANO_MONEDAS[1], MANO_MONEDAS[2])
        palma = S.a_rgba(s)
        borde = contraluz(palma[..., 3], 0, -3, 1.4)
        sobre(img, palma)
        img += borde[..., None] * mez(R["oro_aguila"], BLANCO, 0.25) * 0.7
        s, c = S.lienzo(W, H)
        brillo = Luces()
        for tray in self.monedas:
            k = int(np.searchsorted(tray[:, 0], t))
            if k <= 0:
                continue
            _, x, y, giro = tray[min(k, len(tray) - 1)]
            if y > H + 60:
                continue
            dibujar_moneda(c, x, y, 36, giro)
            brillo.punto(x, y, 44, R["oro_aguila"], 0.10 + 0.16 * abs(math.sin(giro * 1.5)))
        sobre(img, S.a_rgba(s))
        img += brillo.resultado()
        return img

    def cuadro(self, t: float) -> np.ndarray:
        e, mo, x = self.m("entrega"), self.m("monedas"), self.CRUCE
        if t < e - x / 2:
            img = self.escribir(t)
        elif t < e + x / 2:
            img = fundir(self.escribir(t), self.entrega(t - e), tramo(t, e - x / 2, e + x / 2))
        elif t < mo - x / 2:
            img = self.entrega(t - e)
        elif t < mo + x / 2:
            img = fundir(self.entrega(t - e), self.monedas_(t - mo), tramo(t, mo - x / 2, mo + x / 2))
        else:
            img = self.monedas_(t - mo)
        return self.acabar(img, t, papel=0.35, vineta=0.55, bloom=0.4, umbral_bloom=0.6, grano=0.014)

    @staticmethod
    def trayectorias_monedas():
        return simular_monedas()


# --------------------------------------------------------------------------- plano 4, versión realista
# Las mismas tres partes con figuras anatómicas (anatomia.py): la mano que escribe proyecta su
# sombra sobre el pergamino; la entrega ocurre a contraluz, con rayos de sol entre las figuras;
# la mano ahuecada del jinete recibe las monedas. Fondo, carta y tiempos son los mismos.

TEZ = mez(R["terracota"], R["rojo_legion"], 0.45)       # luz que atraviesa la piel delgada
OSCURO = mez(R["tinta"], R["purpura"], 0.22) * 0.30      # cuerpos a contraluz
MANO_4C = (W * 0.640, H * 0.700, 430.0)                  # muñeca (x, y) y largo de la mano en 4c
POSE_RECIBE = AN.PoseMano(abd=(5, 0, -5, -11), mcp=(6, 8, 10, 13), pip=(16, 18, 20, 22),
                          dip=(9, 9, 10, 10), pulgar_abd=36, pulgar_opo=34, pulgar_flex=(8, 12))


def tienda_cuero(c, x: float, y_base: float, ancho: float, alto: float, giro: float,
                 grosor: float = 1.4) -> tuple[float, float]:
    """Tienda de cuero (papilio) en tres cuartos: frente a dos aguas, costado, cumbrera combada,
    palos que asoman y vientos tensos hasta las estacas. Devuelve la puerta (x, y)."""
    pared = alto * 0.38
    lado = 1 if giro >= 0 else -1
    frente = ancho * (0.38 + 0.25 * (1 - abs(giro)))
    costado = ancho - frente
    if lado > 0:
        f0, f1, fin = x - ancho / 2, x - ancho / 2 + frente, x + ancho / 2
    else:
        f0, f1, fin = x + ancho / 2, x + ancho / 2 - frente, x - ancho / 2
    cima = ((f0 + f1) / 2, y_base - alto)
    cima2 = (cima[0] + lado * costado, y_base - alto + costado * 0.05)
    pts = [(f0, y_base), (f0, y_base - pared), cima]
    for u in (0.3, 0.5, 0.7):
        pts.append((cima[0] + (cima2[0] - cima[0]) * u,
                    cima[1] + (cima2[1] - cima[1]) * u + alto * 0.035 * math.sin(math.pi * u)))
    pts += [cima2, (fin, y_base - pared - costado * 0.03), (fin, y_base)]
    S.rellenar(c, pts, suave_=False)
    c.set_line_width(grosor * 1.6)
    for px, py in (cima, cima2):  # palos
        c.move_to(px, py + 2)
        c.line_to(px, py - alto * 0.08)
    c.stroke()
    c.set_line_width(grosor)
    for (ax, ay), (bx, by) in (((f0, y_base - pared), (f0 - lado * ancho * 0.24, y_base + 1)),
                               ((fin, y_base - pared - costado * 0.03), (fin + lado * ancho * 0.22, y_base + 1)),
                               (cima, (cima[0] - lado * ancho * 0.30, y_base + alto * 0.04)),
                               (cima2, (cima2[0] + lado * ancho * 0.18, y_base + 1))):
        c.move_to(ax, ay)
        c.curve_to(ax + (bx - ax) * 0.4, ay + (by - ay) * 0.45, ax + (bx - ax) * 0.7, ay + (by - ay) * 0.75, bx, by)
    c.stroke()
    return cima[0], y_base - pared * 0.35


def aguila_legion(c, x: float, y_base: float, alto: float) -> None:
    """Águila de la legión: asta, tabla, corona de laurel; el ave con las alas alzadas y las
    primarias abiertas como dedos, cabeza de perfil con pico ganchudo, el rayo en las garras."""
    e = alto / 360.0
    top = y_base - alto

    def P(px, py):
        return (x + px * e, top + py * e)

    c.rectangle(x - 3.2 * e, top + 64 * e, 6.4 * e, alto - 64 * e)
    c.fill()
    S.rellenar(c, [P(-27, 126), P(27, 126), P(27, 150), P(-27, 150)], suave_=False)
    for k in range(24):  # corona de laurel
        a = k / 24 * math.tau
        S.elipse(c, *P(math.cos(a) * 19, 96 + math.sin(a) * 19), 7.5 * e, 3.2 * e, a + 0.9)
    S.rellenar(c, [P(-15, 62), P(15, 62), P(13, 70), P(-13, 70)], suave_=False)
    S.rellenar(c, [P(-34, 58), P(-10, 50), P(-13, 55), P(34, 47), P(10, 57), P(13, 52)], suave_=False)  # rayo
    for sx in (-1, 1):  # patas y garras
        S.capsula(c, P(sx * 6, 30), P(sx * 8, 52), 4.2 * e, 3.2 * e)
    S.rellenar(c, [P(-10, 28), P(10, 28), P(17, 56), P(6, 50), P(0, 57), P(-6, 50), P(-17, 56)])  # cola
    S.elipse(c, *P(0, 10), 15 * e, 26 * e, 0.10)                                  # cuerpo
    S.elipse(c, *P(7, -10), 10 * e, 13 * e, 0.5)                                  # cuello
    S.elipse(c, *P(12, -22), 9 * e, 8 * e)                                        # cabeza
    S.rellenar(c, [P(18, -27), P(30, -24), P(31, -17), P(26, -13), P(25, -19), P(18, -18)], suave_=False)
    for sx in (-1, 1):  # alas alzadas en V: borde de ataque por fuera, secundarias por dentro
        a0, a1 = np.array([sx * 9.0, -4.0]), np.array([sx * 78.0, -66.0])
        eje = (a1 - a0) / np.linalg.norm(a1 - a0)
        fuera = np.array([eje[1], -eje[0]]) * (-sx)          # perpendicular hacia afuera y abajo
        ataque, salida = [], []
        for u in np.linspace(0, 1, 6):
            q = a0 + (a1 - a0) * u
            h = 17 - 8 * u
            ataque.append(P(*(q + fuera * h)))
            salida.append(P(*(q - fuera * h)))
        S.rellenar(c, ataque + salida[::-1])
        for k in range(6):  # primarias abiertas como dedos
            g = math.atan2(eje[1], eje[0]) + sx * math.radians(-30 + k * 13)
            base = P(*(a1 - eje * 6 + fuera * (6 - 2.4 * k)))
            largo = (26 - k * 1.5) * e
            S.elipse(c, base[0] + math.cos(g) * largo * 0.5, base[1] + math.sin(g) * largo * 0.5,
                     largo * 0.55, 3.4 * e, g)
        for k in range(5):  # secundarias: borde de salida festoneado
            q = a0 + (a1 - a0) * (0.18 + 0.16 * k) - fuera * (13 - 6 * (0.18 + 0.16 * k))
            S.elipse(c, *P(*q), 7.5 * e, 4.2 * e, math.atan2(eje[1], eje[0]) + sx * 0.9)


def rollo_sdf(sil: AN.Silueta, centro, eje, largo: float, radio: float) -> None:
    """Rollo de papiro con sus varillas: cilindro y dos perillas en los extremos."""
    c = np.asarray(centro, float)
    u = np.asarray(eje, float) / (np.linalg.norm(eje) + 1e-9)
    a, b = c - u * largo / 2, c + u * largo / 2
    sil.cono(a, b, radio, radio)
    for q, s_ in ((a, -1), (b, 1)):
        sil.cono(q, q + u * s_ * radio * 0.9, radio * 0.42, radio * 0.6)


M_4C = AN.orientacion((-1.0, 0.06, 0.0), (0.0, 0.66, 0.75))   # palma arriba, algo hacia la cámara


def mano_receptora() -> AN.Silueta:
    """Mano ahuecada con la palma hacia arriba; el antebrazo sale por la derecha."""
    x, y, L = MANO_4C
    sil = AN.Silueta((x - 1.1 * L, y - 0.7 * L, W + 40, y + 0.6 * L))
    AN.mano(sil, (x, y), L, M_4C, POSE_RECIBE, antebrazo=1.6)
    return sil


@functools.lru_cache(maxsize=1)
def curva_palma() -> tuple:
    """Superficie de la palma de 4c en pantalla (de la yema del medio a la muñeca): ahí se
    apoyan las monedas. Sale del mismo esqueleto que dibuja la mano."""
    x, y, L = MANO_4C
    e = AN.esqueleto_mano(POSE_RECIBE)
    medio = e["dedos"][1]
    palma = -np.array([0.0, 0.0, 1.0]) * 0.055          # superficie de la palma, no el hueso
    pts3 = [medio[3], medio[2], medio[1], medio[0], np.array([0.30, 0.0, -0.02]), np.array([0.12, 0.0, -0.02])]
    pts = [np.array([x, y]) + L * (M_4C @ (q + palma))[:2] for q in pts3]
    pts.sort(key=lambda q: q[0])
    return tuple((float(q[0]), float(q[1])) for q in pts)


class Plano4(Plano4Recorte):
    """Plano 4 con figuras anatómicas a contraluz (véase anatomia.py)."""

    def preparar(self) -> None:
        super().preparar()
        r = np.random.default_rng(41)
        dl, dh = self.dl, self.dh
        hz = dh * 0.668
        self.monedas, self.golpes = self.trayectorias_monedas()

        def colinas(y0, amp, fase, frec):
            def fn(c):
                pts = [(-10, dh + 10)]
                for u in np.linspace(0, 1, 60):
                    yy = y0 - amp * (0.55 + 0.45 * math.sin(u * frec + fase)) * (0.7 + 0.3 * math.sin(u * frec * 2.7 + fase * 1.7))
                    pts.append((u * dl, yy))
                pts.append((dl + 10, dh + 10))
                S.rellenar(c, pts)
            return fn

        cielo_bajo = mez(R["terracota"], R["oro_aguila"], 0.35)
        self.lejos = Capa(dibujo(dl, dh, colinas(hz - 6, 46, 1.2, 6.0), mez(R["purpura"], cielo_bajo, 0.55) * 0.75), 1.1, 0.22)
        self.medio = Capa(dibujo(dl, dh, colinas(hz + 4, 30, 3.1, 9.0), mez(R["purpura"], R["tinta"], 0.45) * 0.9), 1.1, 0.36)

        # campamento: tiendas en hileras, empalizada al fondo, águila, soldados de guardia
        self.puertas = []

        def campamento(c):
            for k in range(40):  # estacas de la empalizada lejana
                xx = dl * (0.0 + k / 40) + r.uniform(-4, 4)
                c.rectangle(xx, hz - 18 - r.uniform(0, 4), 3.0, 22)
            c.rectangle(0, hz - 6, dl, 10)
            c.fill()
            filas = [(hz + 8, 0.62, 13, 0.0), (hz + 22, 0.82, 11, 0.04)]
            for y_f, esc, n, des in filas:
                for k in range(n):
                    xx = dl * (des + 0.02 + (k + r.uniform(-0.15, 0.15)) / n)
                    if 0.47 < xx / dl < 0.62:  # claro donde se pone el sol
                        continue
                    ancho, alto = r.uniform(118, 140) * esc, r.uniform(84, 96) * esc
                    puerta = tienda_cuero(c, xx, y_f, ancho, alto, r.uniform(-0.8, 0.8))
                    if r.uniform() < 0.35:
                        self.puertas.append((puerta, r.uniform(0, 6.28)))
            aguila_legion(c, dl * 0.27, hz + 30, 300)

        tono_campo = mez(mez(R["purpura"], R["tinta"], 0.62), mez(R["terracota"], R["oro_aguila"], 0.3), 0.18)
        capa_c = dibujo(dl, dh, campamento, tono_campo)
        for k, (xx, alto, esp) in enumerate(((0.12, 74, False), (0.205, 78, True), (0.355, 72, False), (0.70, 76, True), (0.86, 70, False))):
            pose = AN.Pose(hombro_c=14, codo_c=48, hombro_l=-4, codo_l=10, mano_c=AN.MANO_PUNO,
                           cadera_c=3 + k, cadera_l=-3)
            fig = AN.persona(pose, AN.Ropa("romano", pelo="casco", capa=False, semilla=k), dl * xx, hz + 30, alto, espejo=esp)
            m = fig.j["mano_c"]
            fig.cuerpo.cono(m + np.array([0, alto * 0.45]), m - np.array([0, alto * 0.75]), 1.2, 1.0)  # pilum
            AN.estampar(capa_c, fig.cuerpo, tono_campo)
        self.campo = Capa(capa_c, 1.1, 0.5)

        def suelo(c):
            pts = [(-10, dh * 0.70)] + [(dl * u, dh * (0.700 + 0.008 * math.sin(u * 7) + 0.004 * math.sin(u * 23)))
                                        for u in np.linspace(0, 1, 40)] + [(dl + 10, dh + 10), (-10, dh + 10)]
            S.rellenar(c, pts)
        self.suelo2 = Capa(dibujo(dl, dh, suelo, R["tinta"] * 0.75), 1.1, 0.8)
        self.humo = A.Humo(8)
        self.hierba = [(r.uniform(-0.05, 1.05), r.uniform(0.0, 1.0), r.uniform(12, 38), r.uniform(-0.4, 0.4),
                        r.uniform(0, 6.28)) for _ in range(420)]
        self.polvo2 = A.Polvo(160, 23, vel=(-7.0, -2.5), tam=(0.7, 2.4))
        # 4c: la mano receptora (estática) con su manga
        self.mano_4c = mano_receptora()
        self.manga_4c = manga_sobre(np.array(MANO_4C[:2]), -(M_4C @ np.array([1.0, 0, 0]))[:2], MANO_4C[2], 0.6)

    @staticmethod
    def trayectorias_monedas():
        return simular_monedas(palma=curva_palma())

    # ---- 4a: escribir
    def escribir(self, t: float) -> np.ndarray:
        u = suave(t / max(self.m("entrega"), 0.1))
        z = 1.08 + 0.06 * u
        img = self.mesa.ver(-60 + 80 * u, 20 - 30 * u, z)[..., :3]
        n = max(0.0, (t - 0.35) * 6.6)
        carta = self.carta.imagen(visibles=n)
        cx, cy = W * 0.52 - 120 * u, H * 0.56 - 20 * u
        esc, ang = 1.02 * z, math.radians(-3)
        sobre(img, colocar(carta, cx, cy, esc, ang))
        px, py = self.carta.punta(min(n, len(self.carta.glifos) - 0.01))
        dx, dy = (px - self.carta.w / 2) * esc, (py - self.carta.h / 2) * esc
        ca, sa = math.cos(ang), math.sin(ang)
        punta = np.array([cx + dx * ca - dy * sa, cy + dx * sa + dy * ca + 3 * math.sin(t * 19)])
        mano, manga, pluma = self.mano_escritora(punta, t)
        # sombra de mano, pluma y manga sobre el pergamino (la vela está arriba a la izquierda)
        alfa = np.zeros((H, W), np.float32)
        for sil in (mano, manga, pluma):
            _alfa_en(alfa, sil)
        sombra = ampliar(sombra_proyectada(reducir(alfa, 4), 8, 8, 3.5))   # a 1/4: es difusa de todos modos
        img *= (1.0 - 0.6 * sombra)[..., None]
        vela = (W * 0.05, -H * 0.15)
        borde = [dict(luz=vela, ancho=5, color=mez(R["oro_aguila"], BLANCO, 0.35), fuerza=0.9, potencia=1.2)]
        AN.pintar(img, pluma, mez(R["terracota"], R["tinta"], 0.55) * 0.6, bordes=borde)
        AN.pintar(img, manga, mez(R["purpura"], R["tinta"], 0.45) * 0.8,
                  bordes=[dict(luz=vela, ancho=9, color=mez(R["purpura"], R["oro_aguila"], 0.5), fuerza=0.6)])
        envuelve = dict(luz=vela, ancho=70, color=mez(R["terracota"], R["tinta"], 0.3), fuerza=0.30, potencia=1.0)
        AN.pintar(img, mano, R["tinta"] * 0.42, bordes=[envuelve] + [dict(borde[0], fuerza=1.3, ancho=6)],
                  trans=dict(radio=10, tau=4, color=TEZ, fuerza=0.35))
        luz = Luces()
        luz.punto(W * 0.05, -H * 0.15, 1300, mez(R["oro_aguila"], R["terracota"], 0.3), 1.15)
        luz.punto(W * 0.3, H * 0.3, 500, R["oro_aguila"], 0.25)
        img *= luz.resultado() + 0.08
        return img

    def mano_escritora(self, punta, t: float):
        """Mano derecha con pinza de tres dedos: la caña pasa entre pulgar e índice y descansa
        sobre el nudillo del índice; la punta toca `punta`."""
        L = 360.0
        M = AN.orientacion((-0.72, -0.42, 0.55), (0.40, 0.25, -0.88))
        e = AN.esqueleto_mano(AN.MANO_PLUMA)
        pinza = (e["dedos"][0][3] + e["pulgar"][3]) / 2 + np.array([0.0, 0.0, -0.01])
        ps = L * (M @ pinza)[:2]
        us = np.array([0.80, -0.56])          # la caña sube hacia la derecha, por encima del dorso
        us /= np.linalg.norm(us)
        muneca = punta - (ps - us * 0.34 * L) + np.array([1.5 * math.sin(t * 9), 0.0])
        mano = AN.Silueta((muneca[0] - 0.9 * L, muneca[1] - 0.9 * L, muneca[0] + 1.6 * L, muneca[1] + 1.4 * L))
        AN.mano(mano, muneca, L, M, AN.MANO_PLUMA, antebrazo=1.3)
        pluma = AN.Silueta((min(punta[0], punta[0] + us[0] * 360) - 10, min(punta[1], punta[1] + us[1] * 360) - 10,
                            max(punta[0], punta[0] + us[0] * 360) + 10, max(punta[1], punta[1] + us[1] * 360) + 10))
        pluma.cono(punta, punta + us * 22, 1.0, 2.6)
        pluma.cono(punta + us * 22, punta + us * 350, 2.6, 4.6)
        manga = manga_sobre(muneca, -(M @ np.array([1.0, 0.0, 0.0]))[:2], L, 0.7)
        return mano, manga, pluma

    # ---- 4b: la entrega al atardecer
    def entrega(self, t: float) -> np.ndarray:
        dur = self.m("monedas") - self.m("entrega")
        u = suave(t / max(dur, 0.1))
        cx, z = 30 - 50 * u, 1.03 + 0.05 * u
        img = gradiente_vertical([(0.0, R["purpura"] * 0.42), (0.40, mez(R["purpura"], R["terracota"], 0.55)),
                                  (0.60, mez(R["terracota"], R["oro_aguila"], 0.6)), (0.68, mez(R["oro_aguila"], BLANCO, 0.2)),
                                  (0.72, R["tinta"])])
        sx_, sy_ = W * 0.555 - cx * 0.3, H * 0.625
        sol = Luces()
        sol.punto(sx_, sy_, 300, R["oro_aguila"], 0.6)
        sol.punto(sx_, sy_, 46, mez(R["oro_aguila"], BLANCO, 0.7), 1.0, forma="gauss")
        resol = sol.resultado()
        img += resol
        ocl = np.zeros((H, W), np.float32)
        for capa_ in (self.lejos, self.medio):
            sobre(img, capa_.ver(cx, 0, z))
        # humo de los fuegos del campamento, que el viento tumba
        v5 = Vista(self.dl, self.dh, 1.1, cx, 0, z, 0.5)
        cols = []
        for (px, py), ph in self.puertas[:4]:
            qx, qy = v5.p(px, py - 30)
            cols.append((qx, qy, 18, 260))
        humo = self.humo.alfa(t, cols, vel=30, viento=-60, densidad=0.45)
        img = img * (1 - humo[..., None]) + humo[..., None] * mez(R["purpura"], R["terracota"], 0.5) * 0.8
        campo = self.campo.ver(cx, 0, z)
        sobre(img, campo)
        np.maximum(ocl, campo[..., 3], out=ocl)
        brillos = Luces()
        for (px, py), ph in self.puertas:
            qx, qy = v5.p(px, py)
            brillos.punto(qx, qy, 9, mez(R["oro_aguila"], R["terracota"], 0.4), 0.35 * A.parpadeo(t, int(ph * 10)))
        img += brillos.resultado()
        suelo = self.suelo2.ver(cx, 0, z)
        sobre(img, suelo)
        np.maximum(ocl, suelo[..., 3], out=ocl)

        v = Vista(self.dl, self.dh, 1.1, cx, 0, z)
        e = v.escala
        piso = self.dh * 0.86
        br_c = suave(tramo(t, 0.0, 0.9)) * (1 - suave(tramo(t, 2.4, 3.4)))
        br_j = suave(tramo(t, 0.6, 1.5))
        cierra = suave(tramo(t, 1.45, 1.75))
        lleva = suave(tramo(t, 1.9, 3.0))
        suelta = suave(tramo(t, 1.65, 2.3))
        en_jinete = t > 1.6
        viento = 0.36 + 0.18 * math.sin(t * 1.7)
        pj = AN.Pose(hombro_c=10 + 52 * br_j - 26 * lleva, codo_c=20 - 4 * br_j + 74 * lleva,
                     giro_c=95 * br_j * (1 - lleva), mano_c=AN.MANO_ABIERTA.mezcla(AN.MANO_SOSTIENE, cierra),
                     hombro_l=-8, codo_l=62, mano_l=AN.MANO_PUNO, cadera_c=5, cadera_l=-5, rodilla_l=8,
                     cabeza=3 + 5 * campana(t, 1.3, 2.6, 0.4), inclinacion=2.5)
        fj = AN.persona(pj, AN.Ropa("galo", pelo="largo", bigote=True, viento=viento, largo_capa=0.6, semilla=3),
                        *v.p(self.dl * 0.575, piso), 560 * e, espejo=True, t=t)
        pc = AN.Pose(hombro_c=6 + 74 * br_c, codo_c=14 - 6 * br_c,
                     mano_c=AN.MANO_SOSTIENE.mezcla(AN.MANO_RELAJADA, suelta),
                     hombro_l=-5, codo_l=14, cabeza=1 - 3 * br_c, cadera_c=4, cadera_l=-4, rodilla_l=6)
        fc = AN.persona(pc, AN.Ropa("romano", pelo="calvo", nariz=1.7, viento=viento * 0.8, largo_capa=0.8),
                        *v.p(self.dl * 0.375, piso), 575 * e, t=t)
        fh = AN.caballo(AN.PoseCaballo(cuello=7 + 3 * math.sin(t * 0.55), cabeza=4,
                                       orejas=8 * campana(t, 1.2, 2.4, 0.3), respira=math.sin(t * 1.3)),
                        *v.p(self.dl * 0.775, piso), 470 * e, espejo=True, t=t, viento=viento,
                        riendas_a=fj.j["mano_l"], semilla=2)
        oro = mez(R["oro_aguila"], BLANCO, 0.42)
        bordes = [dict(luz=(sx_, sy_), ancho=4.2 * e, color=oro, fuerza=1.3, potencia=1.3),
                  dict(luz=(0.0, -1.0), direccion=True, ancho=2.5 * e, color=mez(R["purpura"], R["terracota"], 0.5),
                       fuerza=0.22, potencia=1.0)]
        tez = dict(radio=6 * e, tau=2.4 * e, color=TEZ, fuerza=0.6)
        detras = np.zeros((H, W), np.float32)
        AN.pintar(img, fh.cuerpo, OSCURO, bordes=bordes, trans=tez, tapado=detras)
        for fig, tono, paso in ((fj, G["glasto"], 0.8), (fc, R["rojo_legion"], 1.25)):
            mapa = _pliegues(fig.capa, fig.escala, (sx_, sy_), t)
            AN.pintar(img, fig.capa, mez(tono, R["tinta"], 0.6) * 0.45, bordes=bordes,
                      luces=[(mapa, tono * paso)], tapado=detras)
            AN.pintar(img, fig.cuerpo, OSCURO, bordes=bordes, trans=tez, tapado=detras)
        # el rollo: en el puño de César y luego en la mano del jinete
        if en_jinete:
            m = fj.j["mano_c"]
            eje = (0.15 + 0.85 * lleva, 1.0 - 0.6 * lleva) if lleva > 0 else (0.15, 1.0)
        else:
            m = fc.j["mano_c"]
            eje = (0.05, 1.0)
        rollo = AN.Silueta((m[0] - 60 * e, m[1] - 60 * e, m[0] + 60 * e, m[1] + 60 * e))
        rollo_sdf(rollo, m, eje, 74 * e, 8.5 * e)
        AN.pintar(img, rollo, mez(R["terracota"], R["tinta"], 0.5) * 0.45, bordes=bordes[:1],
                  trans=dict(radio=4 * e, tau=3 * e, color=mez(R["oro_aguila"], R["marmol"], 0.4), fuerza=0.45))
        np.maximum(ocl, detras, out=ocl)
        # hierba del primer plano, mecida por el viento
        s, c = S.lienzo(W, H)
        v.aplicar(c)
        S.tinta(c, R["tinta"] * 0.5)
        for hx, hy, alto, curva, ph in self.hierba:
            bx, by = hx * self.dl, piso - 18 + hy * 70
            mece = (curva + 0.25 * viento * math.sin(t * 2.1 + ph)) * alto
            S.rellenar(c, [(bx - 1.6, by), (bx + mece * 0.45, by - alto * 0.55), (bx + mece, by - alto),
                           (bx + mece * 0.5, by - alto * 0.5), (bx + 1.6, by)], suave_=False)
        hierba = S.a_rgba(s)
        borde_h = contraluz(hierba[..., 3], -2, -2, 1.0)
        sobre(img, hierba)
        img += borde_h[..., None] * oro * 0.5
        np.maximum(ocl, hierba[..., 3], out=ocl)
        # rayos crepusculares: la luz del sol arrastrada entre las siluetas
        fuente_ = resol.mean(axis=-1) * (1.0 - ocl)
        rayos = rayos_de_luz(fuente_, sx_, sy_, muestras=36, alcance=0.9) * (1.0 - 0.75 * ocl)
        img += rayos[..., None] * mez(R["oro_aguila"], BLANCO, 0.3) * 0.32
        self.polvo2.dibujar(img, t, mez(R["oro_aguila"], BLANCO, 0.5), 0.35)
        return img

    # ---- 4c: monedas en la palma del jinete
    def monedas_(self, t: float) -> np.ndarray:
        img = gradiente_vertical([(0.0, mez(R["purpura"], R["tinta"], 0.65)), (1.0, R["tinta"] * 0.7)])
        img += self.bokeh
        luz = (W * 0.42, -H * 0.3)
        borde = [dict(luz=luz, ancho=7, color=mez(R["oro_aguila"], BLANCO, 0.3), fuerza=1.0, potencia=1.4)]
        AN.pintar(img, self.manga_4c, mez(G["glasto"], R["tinta"], 0.55) * 0.55,
                  bordes=[dict(luz=luz, ancho=10, color=mez(G["glasto"], R["oro_aguila"], 0.5), fuerza=0.7)])
        AN.pintar(img, self.mano_4c, R["tinta"] * 0.45, bordes=borde,
                  trans=dict(radio=16, tau=6, color=TEZ, fuerza=0.55))
        s, c = S.lienzo(W, H)
        brillo = Luces()
        for tray in self.monedas:
            k = int(np.searchsorted(tray[:, 0], t))
            if k <= 0:
                continue
            _, x, y, giro = tray[min(k, len(tray) - 1)]
            if y > H + 60:
                continue
            dibujar_moneda(c, x, y, 34, giro)
            brillo.punto(x, y, 44, R["oro_aguila"], 0.10 + 0.16 * abs(math.sin(giro * 1.5)))
        sobre(img, S.a_rgba(s))
        img += brillo.resultado()
        return img


def manga_sobre(muneca, antebrazo, L: float, desde: float) -> AN.Silueta:
    """Manga de lana sobre un antebrazo que sale de cuadro: más ancha que el brazo, con puño
    y bolsas de tela alternadas."""
    d = np.asarray(antebrazo, float)
    d /= np.linalg.norm(d)
    lado = np.array([-d[1], d[0]])
    a0 = np.asarray(muneca, float) + d * desde * L
    sil = AN.Silueta((min(a0[0] - 0.45 * L, a0[0] + d[0] * 3 * L), min(a0[1] - 0.45 * L, a0[1] + d[1] * 3 * L),
                      max(a0[0] + 0.45 * L, a0[0] + d[0] * 3 * L), max(a0[1] + 0.45 * L, a0[1] + d[1] * 3 * L)))
    sil.cono(a0, a0 + d * 3.0 * L, 0.205 * L, 0.27 * L, 0.04 * L)
    sil.cono(a0 - d * 0.03 * L, a0 + d * 0.07 * L, 0.218 * L, 0.222 * L, 0.03 * L)       # puño
    ang = math.degrees(math.atan2(d[1], d[0]))
    for k in range(6):
        q = a0 + d * (0.28 + 0.34 * k) * L + lado * (0.215 if k % 2 else -0.215) * L
        sil.elipse(q, 0.07 * L, 0.032 * L, ang + (14 if k % 2 else -14), 0.035 * L)
    return sil


def _alfa_en(alfa: np.ndarray, sil: AN.Silueta) -> None:
    """Pone el alfa de una silueta en un mapa a pantalla completa (máximo)."""
    j0, i0 = max(0, -sil.x0), max(0, -sil.y0)
    j1, i1 = min(sil.w, W - sil.x0), min(sil.h, H - sil.y0)
    if j0 < j1 and i0 < i1:
        zona = alfa[sil.y0 + i0 : sil.y0 + i1, sil.x0 + j0 : sil.x0 + j1]
        np.maximum(zona, sil.alfa()[i0:i1, j0:j1], out=zona)


def _pliegues(sil: AN.Silueta, alto: float, sol, t: float) -> np.ndarray:
    """Luz que atraviesa una capa de lana a contraluz: franjas de pliegues verticales, más
    claras cerca del sol y en la tela que cuelga lejos del cuerpo."""
    X, Y = sil.rejilla()
    lam = 0.03 * alto
    pl = 0.5 + 0.5 * np.sin((X - sil.x0) / lam * 2 * math.pi + 1.6 * np.sin(Y / (0.22 * alto) + t * 0.8))
    d2 = ((X - sol[0]) ** 2 + (Y - sol[1]) ** 2) / (0.9 * alto) ** 2
    cerca = 1.0 / (1.0 + d2)
    dentro = np.clip(-sil.d / (0.02 * alto), 0, 1)       # el borde mismo lo da el contraluz
    return (0.18 + 0.82 * pl ** 1.5) * cerca * dentro * sil.alfa()


# =========================================================================== PLANO 5
# La carta se enrolla y se amarra a una lanza, de noche, a la luz de una antorcha.


class Plano5(PlanoBase):
    fundido_entrada = 0.35
    fundido_salida = 0.4

    def preparar(self) -> None:
        r = np.random.default_rng(55)
        self.carta = Carta(1500, 900, 74, 7)
        lw, lh = int((W + 200) * 1.2), int((H + 200) * 1.2)
        tablas = ampliar(fbm(lh, lw // 14, 20, 3, 0.5, 9), lw, lh)
        base = mez(G["noche"], G["bosque"], 0.45) * (0.6 + 0.7 * tablas)[..., None]
        for y in np.arange(0, lh, lh / 5):
            base[int(y) : int(y) + 4] *= 0.35
        self.suelo = Capa(np.concatenate([base, np.ones((lh, lw, 1), np.float32)], -1), 1.2)
        self.p0 = np.array([W * -0.05, H * 0.92])
        self.p1 = np.array([W * 1.02, H * 0.20])
        d = self.p1 - self.p0
        self.ang_lanza = math.atan2(d[1], d[0])
        self.largo = float(np.hypot(*d))

    def cuadro(self, t: float) -> np.ndarray:
        u = suave(t / self.duracion)
        img = self.suelo.ver(20 - 40 * u, 0, 1.05 + 0.06 * u)[..., :3]
        luz = Luces()
        luz.punto(W * 0.08, H * 0.38, 1500, G["antorcha"], 1.7 * A.parpadeo(t, 8))
        luz.punto(W * 0.9, -H * 0.2, 1300, mez(G["glasto"], G["niebla"], 0.4), 0.6)
        luz = luz.resultado() + 0.07
        # lanza
        s, c = S.lienzo(W, H)
        S.tinta(c, mez(G["noche"], G["antorcha"], 0.5))
        punta = S.lanza(c, self.p0, self.ang_lanza, self.largo, 16, punta=0.13)
        lanza = S.a_rgba(s)
        sombra = sombra_proyectada(lanza[..., 3], 10, 14, 6)
        img *= (1 - 0.6 * sombra)[..., None]
        sobre(img, lanza)
        e0, e1 = self.m("enrollar"), self.m("amarrar")
        esc = 0.78
        centro = np.array([W * 0.48, H * 0.47])
        ang0 = math.radians(-4)
        # 1) enrollar de derecha a izquierda
        f = 1 - suave(tramo(t, e0, e1 - 0.7))
        mover = suave(tramo(t, e1 - 0.8, e1 + 0.2))
        diam_final = 64
        cerca = 0.62
        destino = self.p0 + (self.p1 - self.p0) * cerca
        if f > 0.02:
            carta = self.carta.imagen(ancho_visible=f)
            capa = colocar(carta, centro[0], centro[1], esc, ang0)
            sombra = sombra_proyectada(capa[..., 3], 12, 18, 10)
            img *= (1 - 0.5 * sombra)[..., None]
            sobre(img, capa)
        # posición del rodillo: en el borde derecho de lo que queda extendido
        borde_x = (self.carta.w * f - self.carta.w / 2) * esc
        diam = 18 + (diam_final - 18) * (1 - f) ** 0.6
        pos = centro + np.array([borde_x * math.cos(ang0), borde_x * math.sin(ang0)])
        pos = pos * (1 - mover) + destino * mover
        ang = ang0 + math.pi / 2
        ang = ang * (1 - mover) + self.ang_lanza * mover
        alto_rollo = self.carta.h * esc * (1 - 0.35 * mover) * 0.92
        if t >= e0 - 0.01:
            s, c = S.lienzo(W, H)
            c.translate(*pos)
            c.rotate(ang - math.pi / 2)
            rodillo(c, 0, -alto_rollo / 2, alto_rollo / 2, diam, mez(R["marmol"], R["terracota"], 0.15),
                    mez(R["marmol"], R["tinta"], 0.55))
            # 2) amarrar: vueltas de correa de cuero en dos lugares
            vueltas = int(tramo(t, e1, e1 + 2.6) * 12)
            S.tinta(c, mez(R["tinta"], R["terracota"], 0.3))
            for k in range(vueltas):
                grupo, i = divmod(k, 6)
                yv = (-0.32 if grupo == 0 else 0.32) * alto_rollo + (i - 2.5) * 9
                c.save()
                c.translate(0, yv)
                c.rotate(0.35)
                c.rectangle(-diam * 0.62, -3.2, diam * 1.24, 6.4)
                c.restore()
                c.fill()
            if vueltas >= 12:
                fin = tramo(t, e1 + 2.6, e1 + 3.4)
                S.capsula(c, (diam * 0.5, 0.32 * alto_rollo), (diam * 0.5 + 40 * fin, 0.32 * alto_rollo + 90 * fin), 3.5, 3)
                S.capsula(c, (diam * 0.5, 0.32 * alto_rollo), (diam * 0.5 + 10 * fin, 0.32 * alto_rollo + 110 * fin), 3.5, 3)
            rollo = S.a_rgba(s)
            sombra = sombra_proyectada(rollo[..., 3], 10, 14, 6)
            img *= (1 - 0.5 * sombra)[..., None]
            sobre(img, rollo)
        img *= luz
        return self.acabar(img, t, papel=0.3, vineta=0.6, bloom=0.35, grano=0.014)


# =========================================================================== PLANO 6
# El jinete galopa hasta la muralla, se detiene y lanza. Corte: la lanza se clava en lo alto de
# una torre (momento más fuerte). El cielo pasa de noche a día dos veces. Al tercer día, un
# soldado levanta la cabeza. Exterior: paleta de la Galia; el soldado lleva acento romano.


def cielo_ciclo(d: float, alba: float, f: int = 1) -> np.ndarray:
    """Gradiente del cielo según la luz del día d (0 noche, 1 día) y el tinte de alba/ocaso."""
    noche = [G["noche"] * 0.85, mez(G["noche"], G["glasto"], 0.5), mez(G["glasto"], G["niebla"], 0.4), mez(G["noche"], G["glasto"], 0.35)]
    dia = [mez(G["niebla"], G["glasto"], 0.35) * 1.05, G["niebla"] * 1.3, mez(G["niebla"], BLANCO, 0.4), mez(G["niebla"], G["bosque"], 0.3)]
    cols = [mez(n, dd, d) for n, dd in zip(noche, dia)]
    cols[2] = mez(cols[2], mez(G["antorcha"], BLANCO, 0.15), 0.65 * alba)
    cols[1] = mez(cols[1], mez(G["antorcha"], G["glasto"], 0.5), 0.35 * alba)
    return gradiente_vertical([(0.0, cols[0]), (0.45, cols[1]), (0.70, cols[2]), (0.85, cols[3])])


def soldado_busto(c, x: float, y: float, e: float, cabeza: float) -> None:
    """Legionario de medio cuerpo, de perfil hacia la derecha, con casco de botón y pilo.

    (x, y) = base del cuello; e = escala (px por unidad); cabeza en grados (+ mira arriba).
    """
    P = lambda pts: [(x + px * e, y + py * e) for px, py in pts]  # noqa: E731
    S.rellenar(c, P([(-60, -12), (-150, 30), (-205, 120), (-225, 300), (-240, 700), (240, 700),
                     (215, 380), (190, 220), (160, 90), (110, 30), (40, -12)]))              # hombros y torso
    S.rellenar(c, P([(-150, 30), (-215, 60), (-250, 150), (-255, 330), (-190, 300), (-170, 140)]))  # capa
    # pilo vertical sostenido por delante
    S.capsula(c, *P([(250, 700), (300, -520)]), 9 * e, 7 * e)
    S.rellenar(c, P([(292, -520), (306, -620), (318, -520)]), suave_=False)
    S.capsula(c, *P([(170, 300), (262, 330)]), 34 * e, 28 * e)                                  # brazo
    # cabeza y casco, girando sobre el cuello
    c.save()
    c.translate(x, y - 20 * e)
    c.rotate(-math.radians(cabeza))
    c.translate(-x, -(y - 20 * e))
    S.capsula(c, *P([(0, 0), (10, -70)]), 46 * e, 44 * e)                                       # cuello
    S.elipse(c, x + 12 * e, y - 118 * e, 78 * e, 92 * e)                                        # cabeza
    S.rellenar(c, P([(84, -112), (101, -88), (84, -80)]), suave_=False)                         # nariz
    S.rellenar(c, P([(66, -58), (80, -42), (64, -24), (30, -28)]))                              # mentón
    S.elipse(c, x - 14 * e, y - 186 * e, 84 * e, 64 * e)                                        # casco
    S.rellenar(c, P([(-96, -176), (60, -176), (64, -168), (-100, -166)]), suave_=False)         # reborde
    S.capsula(c, *P([(-14, -248), (-14, -270)]), 9 * e, 14 * e)                                 # botón
    S.rellenar(c, P([(-86, -162), (-110, -130), (-98, -124), (-72, -138)]), suave_=False)       # cubrenuca
    c.restore()


class Plano6(PlanoBase):
    fundido_entrada = 0.3
    fundido_salida = 0.6
    D = 2.4

    # ------------------------------------------------------------------ preparación
    def preparar(self) -> None:
        r = np.random.default_rng(66)
        self.corte = self.m("lanzamiento") + 0.32
        # A) campo abierto y muralla (panorama ancho)
        da = 1.1
        aw, ah = int((W + 1300) * da), int((H + 120) * da)
        self.aw, self.ah, self.da = aw, ah, da
        self.suelo_y = ah * 0.80

        def lejos(c):
            hor = ah * 0.64
            S.rellenar(c, [(0, ah)] + [(aw * u, hor - 30 * math.sin(u * 9) - 18 * math.sin(u * 23)) for u in np.linspace(0, 1, 60)] + [(aw, ah)])
            for k in range(140):
                S.arbol_desnudo(c, r.uniform(0, aw), hor - 10 + r.uniform(-8, 20), r.uniform(60, 130), semilla=900 + k, niveles=5)
        self.lejos = Capa(dibujo(aw, ah, lejos, mez(G["noche"], G["niebla"], 0.28)), da, 0.3)
        self.antorchas_a = []

        def mundo(c):
            pts = [(-10, self.suelo_y)] + [(aw * u, self.suelo_y + 6 * math.sin(u * 31)) for u in np.linspace(0, 1, 80)] + [(aw + 10, ah + 10), (-10, ah + 10)]
            S.rellenar(c, pts)
            for k in range(260):
                x = r.uniform(0, aw)
                for h in range(3):
                    ang = r.uniform(-0.5, 0.5)
                    S.capsula(c, (x, self.suelo_y + 2), (x + math.sin(ang) * 24, self.suelo_y - r.uniform(10, 34)), 1.8, 0.5)
            x0 = aw * 0.745
            S.terraplen(c, x0, aw + 10, self.suelo_y - 70, self.suelo_y + 10, semilla=3, rugosidad=4)
            S.empalizada(c, x0 + 10, aw + 10, self.suelo_y - 68, 150, semilla=4)
            j = S.torre_madera(c, aw * 0.80, self.suelo_y - 60, 170, 470, semilla=12)
            self.antorchas_a += [j["esquina_izq"] + np.array([4, -18]), j["esquina_der"] + np.array([-4, -18])]
        mu = dibujo(aw, ah, mundo, G["noche"] * 0.55)
        borde = contraluz(mu[..., 3], 0, -3, 1.2)
        mu[..., :3] += tenir(borde, mez(G["glasto"], G["niebla"], 0.6), 0.45)[..., :3]
        self.mundo = Capa(mu, da, 1.0)
        self.x_ini, self.x_alto = aw * 0.30, aw * 0.665
        # B/C) torre de cerca, en alta resolución para el acercamiento
        D = self.D
        tw, th = int((W + 120) * D), int((H + 80) * D)
        self.tw, self.th = tw, th
        L = lambda x, y: ((x - W / 2) * D + tw / 2, (y - H / 2) * D + th / 2)  # noqa: E731
        self.L = L
        sup, c = S.lienzo(tw, th)
        S.tinta(c, mez(G["noche"], G["antorcha"], 0.12))
        c.save()
        c.translate(tw / 2 - W / 2 * D, th / 2 - H / 2 * D)
        c.scale(D, D)
        S.terraplen(c, -80, W + 80, H * 0.84, H + 60, semilla=6, rugosidad=3)
        S.empalizada(c, -80, W + 80, H * 0.845, 110, semilla=7)
        jt = S.torre_madera(c, W * 0.60, H * 0.85, 190, 650, semilla=21, tablas=True)
        c.restore()
        self.torre_j = {k: np.array(L(*v)) for k, v in jt.items()}
        silueta = S.a_pil(sup)
        del sup
        # vetas de madera horneadas en la torre (se ven de cerca con la luz de la antorcha)
        vetas = ampliar(fbm(th // 4, tw // 64, 4, 3, 0.5, 31), tw, th)
        factor = np.clip((0.55 + 0.9 * vetas) * 128, 0, 255).astype(np.uint16)
        del vetas
        arr = np.array(silueta, np.uint8)
        for k in range(3):   # canal por canal en enteros: la imagen es enorme
            arr[..., k] = np.minimum(arr[..., k].astype(np.uint16) * factor >> 7, 255).astype(np.uint8)
        self.torre = Capa(Image.frombytes("RGBa", (tw, th), arr.tobytes()), D, 1.0)
        del arr, factor
        izq = self.torre_j["esquina_izq"]
        plataforma = self.torre_j["plataforma"]
        self.impacto_L = np.array([izq[0] + 4 * D, izq[1] + (plataforma[1] - izq[1]) * 0.42])
        self.antorcha_L = self.torre_j["esquina_der"] + np.array([-6 * D, -22 * D])
        self.dir_lanza = math.radians(22)
        self.largo_L = 270 * D
        # astillas del impacto
        self.astillas = [dict(v=np.array([r.uniform(-1500, -250), r.uniform(-1100, 250)]) * D,
                              giro=r.uniform(-25, 25), largo=r.uniform(3, 9) * D, ph=r.uniform(0, 6))
                         for _ in range(34)]
        # lejanía para el lapso: bosque y loma
        def horizonte(c):
            hor = th * 0.71
            S.rellenar(c, [(0, th)] + [(tw * u, hor - 25 * D * math.sin(u * 6) - 10 * D * math.sin(u * 17)) for u in np.linspace(0, 1, 50)] + [(tw, th)])
            for k in range(90):
                S.arbol_desnudo(c, r.uniform(0, tw), hor + r.uniform(-10, 30), r.uniform(60, 140) * D, semilla=700 + k, niveles=5)
        hs, hc = S.lienzo(tw, th)
        S.tinta(hc, BLANCO)
        horizonte(hc)
        self.horizonte = Capa(S.a_pil(hs), D, 0.4)
        del hs
        # D) amanecer del tercer día, con la torre lejana y desenfocada
        def fondo_d(c):
            S.terraplen(c, -20, W + 20, H * 0.78, H + 20, semilla=9, rugosidad=3)
            S.empalizada(c, -20, W + 20, H * 0.785, 60, semilla=10)
            j = S.torre_madera(c, W * 0.74, H * 0.79, 80, 300, semilla=21)
            self.lanza_d = j["esquina_izq"] + np.array([2, 14])
        self.fondo_d = desenfoque(dibujo(W, H, fondo_d, G["noche"] * 0.7), 2.5)
        self.niebla = A.Niebla(616)
        self.nubes = A.Niebla(717, celda=128)
        self.estrellas = A.Estrellas(320, 81, (0, 0, W, H * 0.62))
        self.brasas = A.Brasas([tuple(self.antorcha_L)], 14, 91, subida=(40, 90))

    # ------------------------------------------------------------------ A: galope y lanzamiento
    def jinete(self, c, t: float) -> None:
        alto_t, lanz = self.m("alto"), self.m("lanzamiento")
        u = min(t / alto_t, 1.0)
        prog = 1 - (1 - u) ** 1.7
        x = self.x_ini + (self.x_alto - self.x_ini) * prog
        cuerpo = 270
        if t < alto_t:
            fase = ((x - self.x_ini) / (cuerpo * 1.15)) % 1.0
            cab = 0.0
        else:
            fase = None
            cab = 0.55 * math.sin(math.pi * tramo(t, alto_t, alto_t + 0.9))
        jc = S.caballo(c, x, self.suelo_y + 4, cuerpo, fase=fase, t=t, viento=0.8, cabriola=cab)
        m = jc["montura"]
        h = 300
        armar = suave(tramo(t, alto_t + 0.15, lanz - 0.12))
        tirar = sale(tramo(t, lanz - 0.12, lanz + 0.05), 2.0)
        if t < alto_t:
            pose = S.Pose(torso=24, cabeza=-6, hombro_c=40, codo_c=50, hombro_l=60, codo_l=40,
                          cadera_c=55, rodilla_c=75, cadera_l=50, rodilla_l=70)
        else:
            base = S.Pose(torso=14, hombro_c=40, codo_c=50, hombro_l=60, codo_l=40,
                          cadera_c=55, rodilla_c=75, cadera_l=50, rodilla_l=70)
            armado = S.Pose(torso=-12, cabeza=10, hombro_c=205, codo_c=-30, hombro_l=70, codo_l=30,
                            cadera_c=50, rodilla_c=75, cadera_l=45, rodilla_l=70)
            lanzado = S.Pose(torso=26, cabeza=0, hombro_c=95, codo_c=10, hombro_l=40, codo_l=40,
                             cadera_c=58, rodilla_c=75, cadera_l=50, rodilla_l=70)
            pose = base.mezcla(armado, armar).mezcla(lanzado, tirar)
        j = S.figura(c, m[0], m[1] + 0.5 * h, h, pose, S.Atavio(pelo="largo", bigote=True, capa=0.7, viento=0.9), apoyar=False)
        mano = j["mano_c"]
        if t < lanz:
            ang = math.radians(-60 if t < alto_t else -60 + 30 * armar)
            S.lanza(c, (mano[0] - math.cos(ang) * 120, mano[1] - math.sin(ang) * 120), ang, 290, 6)
        else:
            dt_ = t - lanz
            p0 = np.array(mano) + np.array([10, -30])
            v = np.array([2100.0, -1700.0])
            pos = p0 + v * dt_ + np.array([0, 900]) * dt_ * dt_
            vel = v + np.array([0, 1800]) * dt_
            ang = math.atan2(vel[1], vel[0])
            S.lanza(c, (pos[0] - math.cos(ang) * 145, pos[1] - math.sin(ang) * 145), ang, 290, 6)

    def toma_a(self, t: float) -> np.ndarray:
        alto_t = self.m("alto")
        seg = sale(tramo(t, 0, alto_t + 0.3), 2.2)
        cx = -560 + 960 * seg
        z = 1.0 + 0.05 * tramo(t, alto_t, self.corte)
        img = cielo_ciclo(0.0, 0.0)
        luz = Luces()
        luz.punto(W * 0.22 - cx * 0.05, H * 0.18, 380, mez(G["niebla"], BLANCO, 0.3), 0.35)
        img += luz.resultado()
        self.estrellas.dibujar(img, t, 0.5, dx=cx * 0.05)
        sobre(img, self.lejos.ver(cx, 0, z))
        n = self.niebla.alfa(t, y0=H * 0.55, y1=H * 0.8, densidad=0.4, vel=(20, 0), dx=cx * 0.5)
        A.componer_niebla(img, n, mez(G["niebla"], G["glasto"], 0.35) * 0.9)
        sobre(img, self.mundo.ver(cx, 0, z))
        v = Vista(self.aw, self.ah, self.da, cx, 0, z)
        halo = Luces()
        for k, p in enumerate(self.antorchas_a):
            sx, sy = v.p(*p)
            halo.punto(sx, sy - 8, 40, G["antorcha"], 0.3 * A.parpadeo(t, k))
            halo.punto(sx, sy, 170, G["antorcha"], 0.1)
        img += halo.resultado()
        for k, p in enumerate(self.antorchas_a):
            sx, sy = v.p(*p)
            A.llama(img, sx, sy, 26 * v.escala, 13 * v.escala, t, 40 + k, 1.2)
        # jinete con desenfoque de movimiento (promedio de tres instantes)
        capas = []
        for dt_ in (-1 / 90, 0.0, 1 / 90):
            s, c = S.lienzo(W, H)
            v.aplicar(c)
            S.tinta(c, G["noche"] * 0.45)
            self.jinete(c, max(0.0, t + dt_))
            capas.append(S.a_rgba(s))
        jin = sum(capas) / 3
        borde = contraluz(jin[..., 3], 0, -2, 1.0)
        sobre(img, jin)
        img += borde[..., None] * mez(G["glasto"], G["niebla"], 0.6) * 0.4
        n2 = self.niebla.alfa(t, y0=H * 0.72, y1=H * 1.0, densidad=0.3, vel=(-30, 0), dx=cx, escala=1.5)
        A.componer_niebla(img, n2, mez(G["niebla"], G["glasto"], 0.4) * 0.6)
        return img

    # ------------------------------------------------------------------ B y C: la torre
    def camara_torre(self, t: float):
        ti, lap = self.m("impacto"), self.m("lapso")
        cerca = np.array([1010.0, 330.0])
        lejos = np.array([W / 2 + 40, H / 2 - 20])
        a = suave5(tramo(t, ti + 0.7, lap - 0.2))
        z = math.exp(math.log(2.25) * (1 - a))
        centro = cerca * (1 - a) + lejos * a
        if t >= ti:
            k = t - ti
            amp = 26 * math.exp(-k / 0.16)
            centro = centro + np.array([amp * math.sin(k * 2 * math.pi * 13), amp * 0.7 * math.cos(k * 2 * math.pi * 11)]) / z
            z *= 1 + 0.045 * math.exp(-k / 0.22)
        return centro[0] - W / 2, centro[1] - H / 2, z

    def luz_del_dia(self, t: float) -> tuple[float, float, float]:
        """(d, alba, progreso del día) durante el lapso; de noche fuera de él."""
        lap, sol = self.m("lapso"), self.m("soldado")
        p = tramo(t, lap, sol - 0.25)
        if p <= 0 or p >= 1:
            return 0.0, 0.0, 0.0
        d = 0.5 - 0.5 * math.cos(2 * math.pi * 2 * p)
        alba = math.sin(math.pi * d) ** 2 * 0.9
        return d, alba, (2 * p) % 1.0

    def toma_torre(self, t: float) -> np.ndarray:
        ti = self.m("impacto")
        cx, cy, z = self.camara_torre(t)
        d, alba, dia = self.luz_del_dia(t)
        noche = 1 - d
        img = cielo_ciclo(d, alba)
        v = Vista(self.tw, self.th, self.D, cx, cy, z)
        vh = Vista(self.tw, self.th, self.D, cx, cy, z, 0.4)
        astros = Luces()
        if d > 0.02:   # el sol cruza el cielo detrás de las nubes
            sx, sy = W * (0.1 + 0.8 * dia), H * (0.62 - 0.42 * math.sin(math.pi * dia))
            astros.punto(sx, sy, 300, mez(G["antorcha"], BLANCO, 0.6), 0.55 * d)
        astros.punto(W * 0.25, H * 0.2, 330, mez(G["niebla"], BLANCO, 0.35), 0.32 * noche)
        img += astros.resultado()
        self.estrellas.dibujar(img, t, 0.6 * noche ** 2, dx=cx * 0.1)
        # tiempo acelerado durante el lapso, continuo en sus bordes
        tl = t + 22 * max(0.0, min(t, self.m("soldado") - 0.25) - self.m("lapso"))
        nub = self.nubes.alfa(tl, y0=-H * 0.1, y1=H * 0.72, densidad=0.55, vel=(30, 0),
                              dx=cx * 0.1, escala=0.8, umbral=0.4)
        col_nube = mez(mez(G["noche"], G["glasto"], 0.4), mez(G["niebla"], BLANCO, 0.25), d)
        col_nube = mez(col_nube, G["antorcha"], 0.3 * alba)
        A.componer_niebla(img, nub, col_nube)
        hz = self.horizonte.ver(cx, cy, z)
        sobre(img, tenir(hz[..., 3], mez(mez(G["noche"], G["niebla"], 0.3), G["niebla"] * 0.8, d)))
        # torre iluminada: ambiente + antorcha de noche
        tor = self.torre.ver(cx, cy, z)
        ax, ay = v.p(*self.antorcha_L)
        luz = Luces()
        f = A.parpadeo(t, 3)
        luz.punto(ax, ay, 210 * v.escala * 2.4, G["antorcha"], 1.6 * noche * f)
        mapa = luz.resultado() + mez(mez(G["glasto"], G["niebla"], 0.3) * 0.35, G["niebla"] * 0.75, d)[None, None, :]
        tor[..., :3] *= np.clip(mapa, 0, 2.0) * 1.4
        borde = contraluz(tor[..., 3], 0, -2, 1.0)
        sobre(img, tor)
        img += borde[..., None] * mez(mez(G["glasto"], G["niebla"], 0.6), BLANCO, 0.3 * d) * 0.35
        # la lanza: vuela hasta el impacto y luego queda clavada y vibra
        s, c = S.lienzo(W, H)
        v.aplicar(c)
        S.tinta(c, mez(G["noche"], G["antorcha"], 0.35) * (0.6 + 0.6 * d))
        dirv = np.array([math.cos(self.dir_lanza), math.sin(self.dir_lanza)])
        if t < ti:
            capas = []
            for dt_ in (-1 / 60, -1 / 120, 0.0):
                s2, c2 = S.lienzo(W, H)
                v.aplicar(c2)
                S.tinta(c2, mez(G["noche"], G["antorcha"], 0.35))
                faltan = ti - (t + dt_)
                punta = self.impacto_L - dirv * 2600 * self.D * faltan
                S.lanza(c2, punta - dirv * self.largo_L, self.dir_lanza, self.largo_L + 30 * self.D, 7 * self.D)
                capas.append(S.a_rgba(s2))
            lanza = sum(capas) / 3
        else:
            k = t - ti
            temblor = math.radians(5.0) * math.exp(-k / 0.32) * math.sin(2 * math.pi * 7.5 * k)
            ang = self.dir_lanza + temblor
            dv = np.array([math.cos(ang), math.sin(ang)])
            hundida = 24 * self.D
            punta = self.impacto_L + dirv * hundida
            base = punta - dv * (self.largo_L + 30 * self.D)
            S.lanza(c, base, ang, self.largo_L + 30 * self.D, 7 * self.D)
            # el rollo atado cerca de la punta
            centro = punta - dv * (self.largo_L * 0.36)
            c.save()
            c.translate(*centro)
            c.rotate(ang + math.pi / 2)
            luzp = 0.35 + 0.45 * d + 0.2 * noche
            rodillo(c, 0, -40 * self.D, 40 * self.D, 15 * self.D,
                    mez(R["marmol"], R["terracota"], 0.2) * luzp, mez(R["marmol"], R["tinta"], 0.6) * luzp)
            S.tinta(c, mez(R["tinta"], R["terracota"], 0.3) * 0.8)
            for yy in (-27, -21, 21, 27):
                c.save()
                c.translate(0, yy * self.D)
                c.rotate(0.3)
                c.rectangle(-9.5 * self.D, -1.4 * self.D, 19 * self.D, 2.8 * self.D)
                c.restore()
                c.fill()
            c.restore()
            lanza = S.a_rgba(s)
        sobre(img, lanza)
        # antorcha de la torre (solo de noche)
        if noche > 0.05:
            halo = Luces()
            halo.punto(ax, ay - 8, 45 * v.escala * 2.4, G["antorcha"], 0.35 * noche * f)
            img += halo.resultado()
            A.llama(img, ax, ay, 30 * v.escala * 2.4, 15 * v.escala * 2.4, t, 77, 1.25 * noche)
            self.brasas.dibujar(img, t, transformar=lambda x, y: (*v.p(x, y), v.escala * 2.4), col=G["antorcha"],
                                intensidad=noche)
        # astillas y polvo del impacto
        if ti <= t < ti + 1.2:
            k = t - ti
            s, c = S.lienzo(W, H)
            v.aplicar(c)
            S.tinta(c, mez(G["noche"], G["antorcha"], 0.22))
            for a_ in self.astillas:
                kk = k + 0.035                     # ya salieron despedidas en el cuadro del golpe
                p = self.impacto_L + a_["v"] * kk + np.array([0, 1400 * self.D]) * kk * kk
                g = a_["giro"] * k + a_["ph"]
                dd = np.array([math.cos(g), math.sin(g)]) * a_["largo"]
                S.capsula(c, p - dd, p + dd, 1.1 * self.D, 0.6 * self.D)
            ast = S.a_rgba(s)
            sobre(img, ast, 1 - tramo(k, 0.7, 1.2))
            polvo = Luces()
            px_, py_ = v.p(*self.impacto_L)
            polvo.punto(px_ - 30 * k * v.escala * 2.4, py_, (40 + 220 * k) * v.escala, mez(G["niebla"], G["antorcha"], 0.25),
                        0.35 * math.exp(-k / 0.35))
            polvo.punto(px_, py_, 70 * v.escala * 2.4, mez(G["antorcha"], BLANCO, 0.5), 0.9 * math.exp(-k / 0.06), forma="gauss")
            img += polvo.resultado()
        n = self.niebla.alfa(tl * 0.5, y0=H * 0.70, y1=H * 1.0, densidad=0.35, vel=(-25, 0),
                             dx=cx, escala=1.3)
        A.componer_niebla(img, n, mez(mez(G["niebla"], G["glasto"], 0.4) * 0.6, G["niebla"] * 1.1, d))
        return img

    # ------------------------------------------------------------------ D: el soldado
    def toma_soldado(self, t: float) -> np.ndarray:
        c0 = self.m("cabeza")
        img = cielo_ciclo(0.55, 1.0)
        sol = Luces()
        sol.punto(W * 0.88, H * 0.74, 420, mez(G["antorcha"], BLANCO, 0.25), 0.55)
        img += sol.resultado()
        sobre(img, self.fondo_d)
        lx, ly = self.lanza_d
        s, c = S.lienzo(W, H)
        S.tinta(c, G["noche"] * 0.8)
        S.lanza(c, (lx - 70, ly - 26), math.radians(22), 75, 3)
        sobre(img, desenfoque(S.a_rgba(s), 1.5))
        n = self.niebla.alfa(t, y0=H * 0.6, y1=H * 0.9, densidad=0.35, vel=(12, 0))
        A.componer_niebla(img, n, mez(G["niebla"], G["antorcha"], 0.2))
        cab = -16 + 40 * suave(tramo(t, c0, c0 + 0.9))   # baja la vista y luego la levanta
        s, c = S.lienzo(W, H)
        S.tinta(c, G["noche"] * 0.55)
        soldado_busto(c, W * 0.34 + 6 * math.sin(t * 0.8), H * 0.62, 1.05, cab)
        bus = S.a_rgba(s)
        borde = contraluz(bus[..., 3], 4, -1, 2.0)
        sobre(img, bus)
        img += borde[..., None] * mez(G["antorcha"], BLANCO, 0.2) * 0.6
        # acento romano: la capa roja de la legión, apenas visible a contraluz
        s, c = S.lienzo(W, H)
        S.tinta(c, mez(R["rojo_legion"], G["noche"], 0.72))
        x, y, e = W * 0.34 + 6 * math.sin(t * 0.8), H * 0.62, 1.05
        S.rellenar(c, [(x + px * e, y + py * e) for px, py in
                       [(-70, -8), (-150, 26), (-205, 110), (-232, 300), (-246, 700), (-160, 700),
                        (-150, 420), (-120, 200), (-60, 60)]])
        sobre(img, S.a_rgba(s))
        return img

    def cuadro(self, t: float) -> np.ndarray:
        sol = self.m("soldado")
        if t < self.corte:
            img = self.toma_a(t)
        elif t < sol - 0.25:
            img = self.toma_torre(t)
        elif t < sol + 0.25:
            img = fundir(self.toma_torre(t), self.toma_soldado(t), tramo(t, sol - 0.25, sol + 0.25))
        else:
            img = self.toma_soldado(t)
        return self.acabar(img, t, papel=0.25, vineta=0.5, bloom=0.4, grano=0.014)


# =========================================================================== PLANO 7
# Cicerón despliega la carta a la luz de la vela. Paleta de Roma; la luz se entibia.


def cabeza_perfil(c, x: float, y: float, e: float, mira_izq: bool = True) -> None:
    """Cabeza y hombro de perfil, sin rasgos (silueta en primer plano)."""
    sx = -1 if mira_izq else 1
    P = lambda pts: [(x + sx * px * e, y + py * e) for px, py in pts]  # noqa: E731
    S.elipse(c, x + sx * 10 * e, y, 82 * e, 98 * e)
    S.rellenar(c, P([(82, -10), (106, 16), (84, 26)]), suave_=False)
    S.rellenar(c, P([(66, 60), (80, 76), (62, 96), (26, 90)]))
    S.capsula(c, *P([(0, 60), (-20, 200)]), 50 * e, 56 * e)
    S.rellenar(c, P([(-40, 150), (-260, 230), (-330, 700), (220, 700), (160, 260), (40, 170)]))


def mano_sostiene(c, x: float, y: float, e: float = 1.0, lado: int = -1) -> None:
    """Mano que sujeta el borde de una hoja en (x, y). lado -1: borde izquierdo; +1: derecho."""
    sx = lado
    S.elipse(c, x + sx * 48 * e, y + 52 * e, 56 * e, 78 * e, sx * 0.25)          # palma detrás del borde
    S.capsula(c, (x + sx * 40 * e, y + 30 * e), (x - sx * 36 * e, y + 4 * e), 17 * e, 13 * e)   # pulgar al frente
    S.capsula(c, (x + sx * 60 * e, y + 110 * e), (x + sx * 150 * e, y + 700 * e), 52 * e, 74 * e)  # antebrazo


class Plano7(PlanoBase):
    fundido_entrada = 0.45
    fundido_salida = 0.5

    def preparar(self) -> None:
        self.lw, self.lh = int((W + 160) * 1.1), int((H + 100) * 1.1)
        self.tienda = TiendaInterior(self.lw, self.lh, 37)
        self.carta = Carta(1500, 900, 74, 7)

        def candelero(c):
            S.capsula(c, (W * 0.15, H * 0.62), (W * 0.15, H * 1.05), 10, 14)
            S.elipse(c, W * 0.15, H * 0.62, 46, 10)
            S.elipse(c, W * 0.15, H * 0.98, 90, 22)
        self.mesa = dibujo(W, H, candelero, R["tinta"] * 0.5)
        s, c = S.lienzo(W, H)
        S.tinta(c, mez(R["marmol"], R["terracota"], 0.25) * 0.85)
        self.mecha = S.vela(c, W * 0.15, H * 0.615, 40, 170)
        self.vela = S.a_rgba(s)
        s, c = S.lienzo(W, H)
        S.tinta(c, R["tinta"] * 0.45)
        cabeza_perfil(c, W * 0.93, H * 0.30, 1.3)
        cab = S.a_rgba(s)
        self.cabeza_borde = contraluz(cab[..., 3], -5, -1, 2.5)
        self.cabeza = desenfoque(cab, 6)
        self.polvo = A.Polvo(90, 77, vel=(3.0, -3.0), tam=(0.8, 2.4))

    def cuadro(self, t: float) -> np.ndarray:
        u = suave(t / self.duracion)
        cx, z = -20 * u, 1.02 + 0.05 * u
        mx, my = self.mecha
        calidez = 1.0 + 0.18 * suave(tramo(t, self.m("desplegar") + 1.0, self.duracion))
        luz = luz_vela(mx, my, t, calidez, 760, mez(R["oro_aguila"], R["terracota"], 0.3)) + R["purpura"] * 0.05
        img = self.tienda.albedo.ver(cx, 0, z)[..., :3] * luz * 0.8
        sobre(img, self.mesa)
        v = self.vela.copy()
        v[..., :3] *= np.clip(luz, 0, 1.4)
        sobre(img, v)
        # la carta se despliega hacia la derecha
        d0 = self.m("desplegar")
        f = 0.1 + 0.9 * sale(tramo(t, d0, d0 + 1.9), 2.2)
        esc = 0.66 * z
        centro = np.array([W * 0.56, H * 0.50])
        ang = math.radians(2.5)
        carta = self.carta.imagen(ancho_visible=f)
        capa = colocar(carta, centro[0] - cx, centro[1], esc, ang)
        capa[..., :3] *= np.clip(luz * 1.15, 0, 1.6)
        sombra = sombra_proyectada(capa[..., 3], 14, 18, 10)
        img *= (1 - 0.55 * sombra)[..., None]
        sobre(img, capa)
        # manos y rodillo
        borde = (self.carta.w * f - self.carta.w / 2) * esc
        ca, sa = math.cos(ang), math.sin(ang)
        bx, by = centro[0] - cx + borde * ca, centro[1] + borde * sa
        izq = centro + np.array([-self.carta.w / 2 * esc - cx, 0])
        s, c = S.lienzo(W, H)
        c.save()
        c.translate(bx, by)
        c.rotate(ang)
        rodillo(c, 0, -self.carta.h * esc * 0.47, self.carta.h * esc * 0.47, 30 + 30 * (1 - f),
                mez(R["marmol"], R["terracota"], 0.2), mez(R["marmol"], R["tinta"], 0.55))
        c.restore()
        rod = S.a_rgba(s)
        rod[..., :3] *= np.clip(luz, 0, 1.4)
        sobre(img, rod)
        s, c = S.lienzo(W, H)
        S.tinta(c, R["tinta"] * 0.5)
        yb = centro[1] + self.carta.h * esc * 0.18
        mano_sostiene(c, izq[0] + 10, yb, 1.0, -1)
        mano_sostiene(c, bx + 8, yb + 10, 1.0, +1)
        manos = S.a_rgba(s)
        borde_m = contraluz(manos[..., 3], -3, -2, 1.5)
        sobre(img, manos)
        img += borde_m[..., None] * luz * 0.5
        A.llama(img, mx, my, 58, 20, t, 9, 1.35)
        sobre(img, self.cabeza)
        img += desenfoque(self.cabeza_borde[..., None], 3)[..., 0][..., None] * luz * 0.9
        self.polvo.dibujar(img, t, mez(R["oro_aguila"], BLANCO, 0.4), 0.5, luz=np.clip(luz[..., 0], 0, 1))
        return self.acabar(img, t, papel=0.25, vineta=0.6, bloom=0.45, umbral_bloom=0.6, grano=0.015)


# =========================================================================== PLANO 8
# El libro de César; la carta en letras griegas; y la misma carta vista por un guerrero
# enemigo: las letras se revuelven y no significan nada. Termina en negro.


def libro_portada(w: int = 980, h: int = 1280) -> tuple[np.ndarray, np.ndarray]:
    """Portada de cuero púrpura con filetes y título dorados. Devuelve (RGBA, máscara del oro)."""
    r = np.random.default_rng(88)
    grosor = 26
    s, c = S.lienzo(w + grosor + 20, h + grosor + 20)
    # canto de las hojas (abajo y a la derecha)
    S.tinta(c, mez(R["marmol"], R["terracota"], 0.25) * 0.75)
    c.rectangle(grosor, grosor, w, h)
    c.fill()
    S.tinta(c, mez(R["marmol"], R["tinta"], 0.5))
    c.set_line_width(1)
    for k in range(1, grosor, 3):
        c.move_to(w + k * 0.95, grosor + k)
        c.line_to(w + k * 0.95, h + k * 0.95)
        c.stroke()
        c.move_to(grosor + k, h + k * 0.95)
        c.line_to(w + k * 0.95, h + k * 0.95)
        c.stroke()
    S.tinta(c, R["purpura"] * 0.5)
    c.rectangle(0, 0, w, h)
    c.fill()
    base = S.a_rgba(s)
    textura = fbm(base.shape[0], base.shape[1], 48, 4, 0.5, 8)
    cuero = (base[..., 3] > 0) & (np.arange(base.shape[1])[None, :] < w) & (np.arange(base.shape[0])[:, None] < h)
    base[..., :3] *= np.where(cuero, 0.75 + 0.5 * textura, 1.0)[..., None]
    lomo = np.clip(1 - np.arange(base.shape[1]) / 90.0, 0, 1)[None, :, None]
    base[..., :3] *= 1 - 0.45 * lomo
    # filetes, florones y título
    oro = np.zeros(base.shape[:2], np.float32)

    def filetes(c):
        c.set_line_width(5)
        c.rectangle(60, 60, w - 120, h - 120)
        c.stroke()
        c.set_line_width(2)
        c.rectangle(80, 80, w - 160, h - 160)
        c.stroke()
        for x, y in ((80, 80), (w - 80, 80), (80, h - 80), (w - 80, h - 80)):
            S.rellenar(c, [(x, y - 26), (x + 18, y), (x, y + 26), (x - 18, y)], suave_=False)
        for y in (h * 0.36, h * 0.67):
            c.set_line_width(3)
            c.move_to(w * 0.25, y)
            c.line_to(w * 0.75, y)
            c.stroke()
            S.rellenar(c, [(w / 2, y - 14), (w / 2 + 14, y), (w / 2, y + 14), (w / 2 - 14, y)], suave_=False)
    oro_c = alfa_de(base.shape[1], base.shape[0], filetes)
    oro = np.maximum(oro, oro_c)
    for texto, nombre, tam, y, inter in (("CAYO JULIO CÉSAR", "Cinzel-Regular.ttf", 38, 0.27, 0.2),
                                         ("LA GUERRA", "Cinzel-Bold.ttf", 92, 0.43, 0.08),
                                         ("DE LAS GALIAS", "Cinzel-Bold.ttf", 92, 0.53, 0.08)):
        a = texto_alfa(texto, nombre, tam, interletra=inter)
        x0 = int((w - a.shape[1]) / 2)
        y0 = int(h * y - a.shape[0] / 2)
        zona = oro[y0 : y0 + a.shape[0], x0 : x0 + a.shape[1]]
        np.maximum(zona, a, out=zona)
    # relieve: luz arriba a la izquierda
    alto = desenfoque(oro[..., None], 1.2)[..., 0]
    gy, gx = np.gradient(alto)
    relieve = np.clip(0.5 - (gx + gy) * 2.5, 0, 1)
    dorado = R["oro_aguila"][None, None, :] * (0.55 + 0.9 * relieve[..., None])
    base[..., :3] = base[..., :3] * (1 - oro[..., None]) + dorado * oro[..., None]
    sombra = np.roll(np.roll(desenfoque(oro[..., None], 2.0)[..., 0], 3, 0), 3, 1)
    base[..., :3] *= (1 - 0.5 * np.clip(sombra - oro, 0, 1))[..., None]
    return base, oro


class Plano8(PlanoBase):
    fundido_entrada = 0.45
    fundido_salida = 1.3
    CRUCE = 0.5

    def preparar(self) -> None:
        self.libro, self.oro = libro_portada()
        self.oro_rgba = np.concatenate([np.repeat(self.oro[..., None], 3, -1), self.oro[..., None]], -1)
        self.carta = Carta(1500, 900, 74, 7)
        r = np.random.default_rng(8)
        mesa = mez(R["tinta"], R["terracota"], 0.2) * (0.7 + 0.5 * ampliar(fbm(H, W // 12, 18, 3, 0.5, 18), W, H))[..., None]
        self.mesa = mesa
        self.polvo = A.Polvo(110, 88, vel=(4.0, -2.0), tam=(0.8, 2.6))
        s, c = S.lienzo(W, H)
        S.tinta(c, G["noche"] * 0.6)
        cabeza_perfil(c, W * 0.07, H * 0.42, 1.5, mira_izq=False)
        at_pelo = [(W * 0.07 + 150 * math.cos(a), H * 0.42 - 120 + 150 * math.sin(a)) for a in np.linspace(-2.6, -0.4, 9)]
        for k, (x, y) in enumerate(at_pelo):
            S.rellenar(c, [(W * 0.07 + (x - W * 0.07) * 0.55, H * 0.42 - 120 + (y - H * 0.42 + 120) * 0.55),
                           (x, y), (W * 0.07 + (x - W * 0.07) * 0.6 + 12, H * 0.42 - 120 + (y - H * 0.42 + 120) * 0.6)],
                       suave_=False)
        cab = S.a_rgba(s)
        self.guerrero_borde = desenfoque(contraluz(cab[..., 3], 5, -2, 2.5)[..., None], 3)[..., 0]
        self.guerrero = desenfoque(cab, 6)
        s, c = S.lienzo(W, H)
        S.tinta(c, G["noche"] * 0.55)
        mano_sostiene(c, W * 0.215, H * 0.62, 1.15, -1)
        self.mano_g = S.a_rgba(s)

    def toma_libro(self, t: float) -> np.ndarray:
        u = suave(t / max(self.m("carta"), 0.1))
        img = self.mesa.copy()
        esc = 0.70 + 0.06 * u
        ang = math.radians(-2.5 + 1.5 * u)
        cx, cy = W * 0.5 + 20 - 40 * u, H * 0.52
        luz = luz_vela(W * 0.1, H * 0.05, t, 1.1, 1100)
        img *= np.clip(luz * 0.7, 0, 1.2) + 0.03
        lib = colocar(self.libro, cx, cy, esc, ang)
        lib[..., :3] *= np.clip(luz * 0.85 + 0.1, 0, 1.5)
        sombra = sombra_proyectada(lib[..., 3], 18, 24, 14)
        img *= (1 - 0.6 * sombra)[..., None]
        sobre(img, lib)
        # brillo que recorre el dorado
        oro = colocar(self.oro_rgba, cx, cy, esc, ang)[..., 3]
        yy, xx = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
        banda = np.exp(-(((xx + yy) - (W * 0.2 + 900 * u)) / 140) ** 2)
        img += ampliar(banda)[..., None] * oro[..., None] * mez(R["oro_aguila"], BLANCO, 0.5) * 0.35
        self.polvo.dibujar(img, t, mez(R["oro_aguila"], BLANCO, 0.4), 0.45, luz=np.clip(luz[..., 0], 0, 1))
        return img

    def toma_carta(self, t: float, revuelto: float, galia: float) -> np.ndarray:
        dur = self.duracion
        u = suave(t / dur)
        if galia < 0.5:
            img = self.mesa.copy()
            luz = luz_vela(W * 0.15, H * 0.1, t, 1.05, 1200)
        else:
            img = mez(G["noche"], G["bosque"], 0.3) * np.ones((H, W, 3), np.float32)
            l = Luces()
            l.punto(W * 0.95, H * 0.35, 1100, G["antorcha"], 1.5 * A.parpadeo(t, 4))
            l.punto(W * 0.3, -H * 0.3, 1000, G["glasto"], 0.35)
            luz = l.resultado() + 0.05
        img *= np.clip(luz * 0.6, 0, 1.2)
        esc = 0.86 + 0.08 * u
        sacudida = (6 * math.sin(t * 5.1), 4 * math.cos(t * 4.3)) if galia >= 0.5 else (0, 0)
        cx = W * 0.55 - 160 * u + sacudida[0]
        cy = H * 0.50 + sacudida[1]
        carta = self.carta.imagen(revuelto=revuelto, t=t)
        capa = colocar(carta, cx, cy, esc, math.radians(-3 if galia < 0.5 else 4))
        capa[..., :3] *= np.clip(luz * 1.1, 0, 1.6)
        sombra = sombra_proyectada(capa[..., 3], 14, 18, 10)
        img *= (1 - 0.55 * sombra)[..., None]
        sobre(img, capa)
        if galia >= 0.5:
            mano = self.mano_g.copy()
            borde = contraluz(mano[..., 3], 3, -1, 1.5)
            sobre(img, mano)
            img += borde[..., None] * G["antorcha"] * 0.5
            sobre(img, self.guerrero)
            img += self.guerrero_borde[..., None] * G["antorcha"] * 0.8
        return img

    def cuadro(self, t: float) -> np.ndarray:
        ca, en, x = self.m("carta"), self.m("enemigo"), self.CRUCE
        rev = suave(tramo(t, self.m("revuelto"), self.m("revuelto") + 2.6))
        if t < ca - x / 2:
            img = self.toma_libro(t)
        elif t < ca + x / 2:
            img = fundir(self.toma_libro(t), self.toma_carta(t, 0, 0), tramo(t, ca - x / 2, ca + x / 2))
        elif t < en - x / 2:
            img = self.toma_carta(t, 0, 0)
        elif t < en + x / 2:
            img = fundir(self.toma_carta(t, 0, 0), self.toma_carta(t, rev, 1), tramo(t, en - x / 2, en + x / 2))
        else:
            img = self.toma_carta(t, rev, 1)
        return self.acabar(img, t, papel=0.3, vineta=0.6, bloom=0.4, umbral_bloom=0.6, grano=0.015)


# =========================================================================== PLANO 9
# Tarjeta de título sobre negro, en Cinzel con oro romano.


class Plano9(PlanoBase):
    fundido_entrada = 0.0
    fundido_salida = 1.0

    def preparar(self) -> None:
        self.titulo = texto_alfa("EL CIFRADO CÉSAR", "Cinzel-Bold.ttf", 132, interletra=0.08)
        self.sub = texto_alfa("y la ingeniería social", "Cinzel-Regular.ttf", 62, interletra=0.06)
        h, w = self.titulo.shape
        grad = np.linspace(1.15, 0.7, h, dtype=np.float32)[:, None, None]
        self.oro = np.clip(R["oro_aguila"][None, None, :] * grad, 0, 1)
        self.humo = A.Niebla(909, celda=128)
        self.polvo = A.Polvo(70, 99, vel=(5.0, -6.0), tam=(0.8, 2.2))

    def cuadro(self, t: float) -> np.ndarray:
        t0 = self.m("titulo")
        img = np.zeros((H, W, 3), np.float32) + R["tinta"] * 0.35
        n = self.humo.alfa(t, y0=-100, y1=H + 100, densidad=0.22, vel=(10, -6), umbral=0.4)
        A.componer_niebla(img, n, mez(R["tinta"], R["oro_aguila"], 0.12))
        a = suave(tramo(t, t0, t0 + 0.28))
        if a > 0:
            esc = 1.0 + 0.05 * (1 - sale(tramo(t, t0, t0 + 0.9), 3))
            tit = escalar_alfa(self.titulo, esc)
            h, w = tit.shape
            x, y = (W - w) // 2, int(H * 0.45 - h / 2)
            brillo = desenfoque(np.pad(tit, 40)[..., None], 14)[..., 0]
            fulgor = 0.35 + 0.6 * math.exp(-max(0.0, t - t0) / 0.5)
            luz = tenir(brillo, R["oro_aguila"], a * fulgor * 0.6)
            img_ = img[max(0, y - 40) : y - 40 + brillo.shape[0], max(0, x - 40) : x - 40 + brillo.shape[1]]
            img_ += luz[: img_.shape[0], : img_.shape[1], :3]
            gy = np.linspace(1.18, 0.72, h, dtype=np.float32)[:, None, None]
            capa = np.concatenate([np.clip(R["oro_aguila"] * gy, 0, 1) * tit[..., None] * a, tit[..., None] * a], -1)
            sobre_en(img, capa, x, y)
        b = suave(tramo(t, t0 + 0.55, t0 + 1.35))
        if b > 0:
            h, w = self.sub.shape
            col = mez(R["oro_aguila"], R["marmol"], 0.3)
            sobre_en(img, tenir(self.sub, col, 0.92 * b), (W - w) // 2, int(H * 0.60 - h / 2))
        self.polvo.dibujar(img, t, mez(R["oro_aguila"], BLANCO, 0.3), 0.35 * a)
        return self.acabar(img, t, papel=0.2, vineta=0.5, bloom=0.5, umbral_bloom=0.5, grano=0.014)


PLANOS = {1: Plano1, 2: Plano2, 3: Plano3, 4: Plano4, 5: Plano5, 6: Plano6, 7: Plano7, 8: Plano8, 9: Plano9}


# =========================================================================== SONIDO


def pista_sonido(tiempos) -> sfx.Mezcla:
    """Efectos de la escena colocados con las mismas marcas que mueven la imagen."""
    m = sfx.Mezcla(tiempos.duracion)
    P = {p.numero: p for p in tiempos.planos}

    def inicio(n):
        return P[n].inicio

    def marca(n, nombre):
        return P[n].inicio + P[n].marcas[nombre]

    def dur(n):
        return P[n].duracion

    # Plano 1: viento sobre el mapa; antorchas cuando aparece el campamento
    m.agregar("viento", 0.0, sfx.viento(dur(1) + 0.5, 1), -4, 2.0, 1.0)
    t_camp = marca(1, "campamento") - 0.8
    m.agregar("antorchas", t_camp, sfx.antorchas(P[1].fin - t_camp + 0.3, 2, 6.0), -9, 1.0, 0.5)
    # Plano 2: murmullo del ejército y viento
    m.agregar("murmullo", inicio(2) - 0.3, sfx.murmullo(dur(2) + 0.6, 3), -6, 1.2, 1.0)
    m.agregar("viento", inicio(2), sfx.viento(dur(2) + 0.4, 11, 0.8), -9, 1.0, 1.0)
    m.agregar("antorchas", inicio(2), sfx.antorchas(dur(2), 12, 4.0, 0.6), -15, 1.0, 1.0)
    # Plano 3: silencio de la tienda: viento lejano y murmullo apenas audible
    m.agregar("viento", inicio(3), sfx.viento(dur(3) + 0.3, 21, 0.6), -18, 0.8, 1.0)
    m.agregar("murmullo", inicio(3), sfx.murmullo(dur(3), 22, 10), -22, 0.8, 1.0)
    # Plano 4: pluma, murmullo del campamento de César, monedas
    m.agregar("pluma", inicio(4) + 0.35, sfx.pluma(P[4].marcas["entrega"] - 0.35, 4), -7, 0.05, 0.3)
    m.agregar("murmullo", marca(4, "entrega"), sfx.murmullo(P[4].marcas["monedas"] - P[4].marcas["entrega"] + 0.8, 31, 14), -20, 0.6, 0.8)
    _, golpes = PLANOS[4].trayectorias_monedas()
    if golpes:
        tg = [g for g, _ in golpes]
        fz = [0.35 + 0.65 * f for _, f in golpes]
        t0 = tg[0]
        m.agregar("monedas", marca(4, "monedas") + t0, sfx.monedas([g - t0 for g in tg], fz, semilla=5), -7)
    # Plano 5: viento y antorcha
    m.agregar("viento", inicio(5), sfx.viento(dur(5) + 0.3, 41, 0.8), -12, 0.6, 0.8)
    m.agregar("antorchas", inicio(5), sfx.antorchas(dur(5), 42, 7.0, 1.0), -11, 0.5, 0.8)
    # Plano 6: galope, whoosh, impacto, paso del tiempo (dos días)
    alto, lanz, imp = P[6].marcas["alto"], P[6].marcas["lanzamiento"], P[6].marcas["impacto"]
    m.agregar("galope", inicio(6), sfx.galope(alto + 0.25, 6), -3, 0.1, 0.4)
    m.agregar("whoosh", marca(6, "lanzamiento") - 0.04, sfx.whoosh(imp - lanz + 0.12, 7), -5)
    m.agregar("impacto", marca(6, "impacto"), sfx.impacto_lanza(8), 0)
    lap, sol = P[6].marcas["lapso"], P[6].marcas["soldado"]
    dia = (sol - 0.25 - lap) / 2
    for k in range(2):
        m.agregar("paso del tiempo", inicio(6) + lap + k * dia, sfx.paso_del_tiempo(dia + 0.3, 9 + k), -6)
    m.agregar("viento", inicio(6), sfx.viento(dur(6) + 0.3, 51, 0.9), -12, 0.5, 1.0)
    m.agregar("antorchas", inicio(6) + imp - 0.3, sfx.antorchas(lap - imp + 0.6, 52, 6.0, 0.8), -14, 0.3, 0.8)
    # Plano 7: tienda: viento lejano
    m.agregar("viento", inicio(7), sfx.viento(dur(7) + 0.3, 61, 0.6), -19, 0.8, 1.0)
    # Plano 8: viento bajo; antorcha y un barrido suave cuando se revuelven las letras
    m.agregar("viento", inicio(8), sfx.viento(dur(8) + 0.3, 71, 0.6), -17, 0.8, 1.2)
    t_en = marca(8, "enemigo") - 0.3
    m.agregar("antorchas", t_en, sfx.antorchas(P[8].fin - t_en, 72, 6.0, 1.0), -12, 0.5, 1.2)
    m.agregar("whoosh", marca(8, "revuelto"), sfx.whoosh(1.6, 73, 900, 260, 0.4, -0.4), -14)
    # Plano 9: golpe sordo con el título
    m.agregar("golpe sordo", marca(9, "titulo"), sfx.golpe_sordo(10), 0)
    return m
