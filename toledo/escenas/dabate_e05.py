"""Piezas 2D comunes de las escenas 5 y 6 (caso Dabate, Ellington, Connecticut).

- Paleta de Connecticut (`paletas.CONNECTICUT`), fondo de diagrama y acabado de cine.
- `Lienzo`: formas de cairo y textos de un cuadro, que se componen con sombra suave y brillo.
- Íconos de línea (auto, sobre, computadora, campana, llavero, video, pasos, nube…).
- `CasaDiagrama`: la casa en corte, con sus sensores y aparatos (5.0, 6.0, 6.2).
- `LineaTiempo`: la línea de tiempo de la mañana del 23 de diciembre de 2015, con la versión de
  Richard arriba y lo que registró cada aparato debajo (6.1, 6.3, 6.6).
- Fotos en marco (las de víctimas, sin tinte ni efectos) y efectos de sonido propios de estas escenas.
"""

from __future__ import annotations

import math

import cv2
import numpy as np
from PIL import Image

import dibujo as D
import sfx
from cine import sombra_suave
from escenas import diagramas as DG
from escenas.base import SR, aparece, texto
from graficos import H, W, caja_dentro, color, desenfoque, lim, suave
from paletas import CONNECTICUT, mezcla, rgb

TAU = math.tau
P = rgb(CONNECTICUT)
NEGRO = np.zeros(3, np.float32)
BEIGE = P["beige"]
CLARO = mezcla(P["beige"], np.ones(3, np.float32), 0.55)          # texto principal
TENUE = mezcla(P["beige"], P["azul"], 0.35)                       # texto secundario
AZUL = P["azul"]
REG = mezcla(P["azul_patrulla"], np.ones(3, np.float32), 0.38)   # lo que registraron los aparatos
ROJO = mezcla(P["rojo_patrulla"], np.ones(3, np.float32), 0.08)  # contradicciones, alarma
OSCURO = mezcla(P["azul"], NEGRO, 0.84)

# El 3D trae su curva de color (AgX): el acabado encima es leve. Sombras hacia el azul de la bandera,
# luces hacia el beige de casa suburbana.
CINE = dict(sombras=mezcla(P["azul"], NEGRO, 0.45), luces=P["beige"], mezcla=0.12, saturacion=0.95,
            contraste=0.06, halo=0.10, grano=0.012, vineta=0.32)
CRUCE = 0.9


def fondo() -> np.ndarray:
    return DG.fondo(mezcla(P["azul"], NEGRO, 0.86), mezcla(P["azul"], P["beige"], 0.25), 0.05)


def hm(cadena: str) -> float:
    """«9:23» -> minutos desde la medianoche."""
    h, m = cadena.split(":")
    return int(h) * 60 + int(m)


# =========================================================================== lienzo


class Lienzo:
    """Las formas de un cuadro (cairo) y sus textos, que se escriben después de componer."""

    def __init__(self):
        self.tr = DG.Trazo()
        self.c = self.tr.c
        self.textos: list = []

    def tinta(self, col, a: float = 1.0) -> None:
        D.tinta(self.c, color(col), a)

    def texto(self, cadena, x, y, tam, col, a=1.0, alinear="izq", nombre="Inter-SemiBold.ttf", interletra=0.0):
        if a > 0.003 and cadena:
            self.textos.append((cadena, x, y, tam, col, a, alinear, nombre, interletra))

    def componer(self, img: np.ndarray, brillo: float = 0.35, sombra: float = 0.5, sigma: float = 9.0) -> np.ndarray:
        capa = D.a_rgba(self.tr.s)
        if capa[..., 3].max() > 0:
            if sombra > 0:
                img *= 1 - sombra_suave(capa[..., 3], 8, 12, 14, sombra)[..., None]
            if brillo > 0:
                img += desenfoque(capa[..., :3], sigma) * brillo
            img = img * (1 - capa[..., 3:]) + capa[..., :3]
        for (cad, x, y, tam, col, a, al, nom, il) in self.textos:
            texto(img, cad, x, y, tam, col, nombre=nom, alinear=al, opacidad=a, interletra=il, sombra=0.45)
        return img


def caja_suave(L: Lienzo, x, y, w, h, a, borde=REG, relleno=OSCURO, r=12, punteada=False, grosor=2.5):
    """Tarjeta: relleno oscuro casi opaco y borde fino (punteado para lo que solo dijo Richard)."""
    if a <= 0:
        return
    c = L.c
    L.tinta(relleno, 0.86 * a)
    D.rect_redondeado(c, x, y, w, h, r)
    c.fill()
    L.tinta(borde, a)
    c.set_line_width(grosor)
    if punteada:
        c.set_dash([10, 8])
    D.rect_redondeado(c, x, y, w, h, r)
    c.stroke()
    c.set_dash([])


def punteada(L: Lienzo, pts, col, a, grosor=2.5, guion=(10, 8)):
    if a <= 0:
        return
    L.tinta(col, a)
    L.c.set_dash(list(guion))
    DG.linea(L.c, pts, 1.0, grosor)
    L.c.set_dash([])


def panel_esmerilado(img, x0, y0, x1, y1, a, oscuro=0.45):
    """Vidrio esmerilado sobre el 3D: lo de atrás se desenfoca y oscurece; un filo de luz arriba."""
    if a <= 0:
        return
    x0, y0, x1, y1 = (int(round(v)) for v in (x0, y0, x1, y1))
    zona = img[y0:y1, x0:x1]
    borrosa = cv2.GaussianBlur(zona, (0, 0), 16) * (1 - oscuro)
    img[y0:y1, x0:x1] = zona * (1 - a) + borrosa * a
    img[y0 : y0 + 2, x0:x1] = img[y0 : y0 + 2, x0:x1] * (1 - 0.35 * a) + BEIGE * 0.35 * a


# =========================================================================== íconos (línea, centro y alto s)


def icono(c, nombre: str, cx: float, cy: float, s: float, g: float = 3.0) -> None:
    c.save()
    c.set_line_width(g)
    getattr(_Iconos, nombre)(c, cx, cy, s)
    c.restore()


class _Iconos:
    @staticmethod
    def auto(c, cx, cy, s):
        w = s * 1.6
        x0, y0 = cx - w / 2, cy - s * 0.15
        c.move_to(x0, y0 + s * 0.42)
        c.line_to(x0, y0 + s * 0.05)
        c.line_to(x0 + w * 0.2, y0 - s * 0.05)
        c.line_to(x0 + w * 0.32, y0 - s * 0.38)
        c.line_to(x0 + w * 0.7, y0 - s * 0.38)
        c.line_to(x0 + w * 0.84, y0 - s * 0.05)
        c.line_to(x0 + w, y0 + s * 0.05)
        c.line_to(x0 + w, y0 + s * 0.42)
        c.close_path()
        c.stroke()
        for u in (0.24, 0.76):
            c.new_sub_path()
            c.arc(x0 + w * u, y0 + s * 0.45, s * 0.17, 0, TAU)
            c.stroke()

    @staticmethod
    def sobre(c, cx, cy, s):
        w, h = s * 1.3, s * 0.85
        D.rect_redondeado(c, cx - w / 2, cy - h / 2, w, h, s * 0.06)
        c.stroke()
        c.move_to(cx - w / 2, cy - h / 2 + 2)
        c.line_to(cx, cy + h * 0.12)
        c.line_to(cx + w / 2, cy - h / 2 + 2)
        c.stroke()

    @staticmethod
    def laptop(c, cx, cy, s):
        w, h = s * 1.3, s * 0.8
        D.rect_redondeado(c, cx - w / 2, cy - h / 2 - s * 0.1, w, h, s * 0.05)
        c.stroke()
        c.move_to(cx - w * 0.62, cy + h / 2 + s * 0.02)
        c.line_to(cx + w * 0.62, cy + h / 2 + s * 0.02)
        c.stroke()

    @staticmethod
    def telefono(c, cx, cy, s):
        w = s * 0.55
        D.rect_redondeado(c, cx - w / 2, cy - s / 2, w, s, s * 0.08)
        c.stroke()
        c.move_to(cx - s * 0.06, cy - s * 0.4)
        c.line_to(cx + s * 0.06, cy - s * 0.4)
        c.stroke()

    @staticmethod
    def campana(c, cx, cy, s):
        c.move_to(cx - s * 0.42, cy + s * 0.25)
        c.curve_to(cx - s * 0.3, cy + s * 0.1, cx - s * 0.32, cy - s * 0.42, cx, cy - s * 0.42)
        c.curve_to(cx + s * 0.32, cy - s * 0.42, cx + s * 0.3, cy + s * 0.1, cx + s * 0.42, cy + s * 0.25)
        c.close_path()
        c.stroke()
        c.new_sub_path()
        c.arc(cx, cy + s * 0.36, s * 0.08, 0, TAU)
        c.fill()

    @staticmethod
    def llavero(c, cx, cy, s):
        D.rect_redondeado(c, cx - s * 0.25, cy - s * 0.2, s * 0.5, s * 0.7, s * 0.2)
        c.stroke()
        c.new_sub_path()
        c.arc(cx, cy - s * 0.38, s * 0.16, 0, TAU)
        c.stroke()
        c.new_sub_path()
        c.arc(cx, cy + s * 0.12, s * 0.09, 0, TAU)
        c.fill()

    @staticmethod
    def video(c, cx, cy, s):
        w, h = s * 1.2, s * 0.85
        D.rect_redondeado(c, cx - w / 2, cy - h / 2, w, h, s * 0.1)
        c.stroke()
        c.move_to(cx - s * 0.12, cy - s * 0.2)
        c.line_to(cx + s * 0.22, cy)
        c.line_to(cx - s * 0.12, cy + s * 0.2)
        c.close_path()
        c.fill()

    @staticmethod
    def mensaje(c, cx, cy, s):
        w, h = s * 1.2, s * 0.8
        D.rect_redondeado(c, cx - w / 2, cy - h / 2 - s * 0.06, w, h, s * 0.2)
        c.stroke()
        c.move_to(cx - w * 0.25, cy + h / 2 - s * 0.08)
        c.line_to(cx - w * 0.35, cy + h / 2 + s * 0.16)
        c.line_to(cx - w * 0.05, cy + h / 2 - s * 0.06)
        c.stroke()

    @staticmethod
    def casa(c, cx, cy, s):
        w = s * 1.1
        c.move_to(cx - w / 2, cy + s * 0.45)
        c.line_to(cx - w / 2, cy - s * 0.05)
        c.line_to(cx, cy - s * 0.48)
        c.line_to(cx + w / 2, cy - s * 0.05)
        c.line_to(cx + w / 2, cy + s * 0.45)
        c.close_path()
        c.stroke()
        c.rectangle(cx - s * 0.12, cy + s * 0.12, s * 0.24, s * 0.33)
        c.stroke()

    @staticmethod
    def silueta(c, cx, cy, s):
        c.new_sub_path()
        c.arc(cx, cy - s * 0.28, s * 0.17, 0, TAU)
        c.fill()
        c.move_to(cx - s * 0.36, cy + s * 0.5)
        c.curve_to(cx - s * 0.36, cy - s * 0.05, cx + s * 0.36, cy - s * 0.05, cx + s * 0.36, cy + s * 0.5)
        c.close_path()
        c.fill()

    @staticmethod
    def autobus(c, cx, cy, s):
        w, h = s * 1.5, s * 0.8
        D.rect_redondeado(c, cx - w / 2, cy - h / 2, w, h, s * 0.1)
        c.stroke()
        for k in range(3):
            c.rectangle(cx - w / 2 + s * 0.12 + k * s * 0.42, cy - h / 2 + s * 0.12, s * 0.32, s * 0.25)
            c.stroke()
        for u in (0.22, 0.78):
            c.new_sub_path()
            c.arc(cx - w / 2 + w * u, cy + h / 2, s * 0.12, 0, TAU)
            c.fill()

    @staticmethod
    def edificio(c, cx, cy, s):
        w, h = s * 0.9, s
        c.rectangle(cx - w / 2, cy - h / 2, w, h)
        c.stroke()
        for i in range(3):
            for j in range(2):
                c.rectangle(cx - w / 2 + s * 0.16 + j * s * 0.36, cy - h / 2 + s * 0.14 + i * s * 0.25, s * 0.2, s * 0.13)
                c.fill()

    @staticmethod
    def pasos(c, cx, cy, s):
        for k, (dx, dy) in enumerate(((-0.18, 0.1), (0.18, -0.15))):
            x, y = cx + dx * s, cy + dy * s
            D.elipse(c, x, y, s * 0.13, s * 0.22)
            c.fill()
            D.elipse(c, x, y + s * 0.34, s * 0.1, s * 0.09)
            c.fill()

    @staticmethod
    def nube(c, cx, cy, s):
        c.new_sub_path()
        c.move_to(cx - s * 0.6, cy + s * 0.25)
        c.curve_to(cx - s * 0.85, cy + s * 0.25, cx - s * 0.85, cy - s * 0.15, cx - s * 0.55, cy - s * 0.12)
        c.curve_to(cx - s * 0.5, cy - s * 0.5, cx + s * 0.05, cy - s * 0.55, cx + s * 0.15, cy - s * 0.25)
        c.curve_to(cx + s * 0.35, cy - s * 0.45, cx + s * 0.7, cy - s * 0.25, cx + s * 0.6, cy + s * 0.0)
        c.curve_to(cx + s * 0.9, cy + s * 0.05, cx + s * 0.85, cy + s * 0.25, cx + s * 0.6, cy + s * 0.25)
        c.close_path()
        c.stroke()

    @staticmethod
    def bluetooth(c, cx, cy, s):
        c.move_to(cx - s * 0.25, cy - s * 0.22)
        c.line_to(cx + s * 0.22, cy + s * 0.2)
        c.line_to(cx, cy + s * 0.42)
        c.line_to(cx, cy - s * 0.42)
        c.line_to(cx + s * 0.22, cy - s * 0.2)
        c.line_to(cx - s * 0.25, cy + s * 0.22)
        c.stroke()

    @staticmethod
    def reloj(c, cx, cy, s):
        c.new_sub_path()
        c.arc(cx, cy, s * 0.42, 0, TAU)
        c.stroke()
        c.move_to(cx, cy - s * 0.26)
        c.line_to(cx, cy)
        c.line_to(cx + s * 0.18, cy + s * 0.1)
        c.stroke()

    @staticmethod
    def escudo(c, cx, cy, s):
        c.move_to(cx, cy - s * 0.48)
        c.line_to(cx + s * 0.38, cy - s * 0.34)
        c.curve_to(cx + s * 0.38, cy + s * 0.1, cx + s * 0.2, cy + s * 0.36, cx, cy + s * 0.48)
        c.curve_to(cx - s * 0.2, cy + s * 0.36, cx - s * 0.38, cy + s * 0.1, cx - s * 0.38, cy - s * 0.34)
        c.close_path()
        c.stroke()

    @staticmethod
    def modem(c, cx, cy, s):
        w, h = s * 1.3, s * 0.42
        D.rect_redondeado(c, cx - w / 2, cy - h / 2 + s * 0.15, w, h, s * 0.08)
        c.stroke()
        for k in range(4):
            c.new_sub_path()
            c.arc(cx - w * 0.3 + k * w * 0.16, cy + s * 0.15, s * 0.035, 0, TAU)
            c.fill()
        for dx in (-0.35, 0.35):
            c.move_to(cx + dx * w, cy - h / 2 + s * 0.15)
            c.line_to(cx + dx * w * 1.1, cy - s * 0.42)
            c.stroke()

    @staticmethod
    def documento(c, cx, cy, s):
        DG.archivo(c, cx - s * 0.36, cy - s * 0.48, s * 0.96, c.get_line_width())
        for k in range(3):
            c.move_to(cx - s * 0.2, cy - s * 0.05 + k * s * 0.17)
            c.line_to(cx + s * 0.22, cy - s * 0.05 + k * s * 0.17)
        c.stroke()

    @staticmethod
    def puerta(c, cx, cy, s):
        c.rectangle(cx - s * 0.3, cy - s * 0.5, s * 0.6, s)
        c.stroke()
        c.new_sub_path()
        c.arc(cx + s * 0.17, cy + s * 0.04, s * 0.05, 0, TAU)
        c.fill()

    @staticmethod
    def escalera(c, cx, cy, s):
        x, y = cx - s * 0.5, cy + s * 0.45
        c.move_to(x, y)
        for k in range(4):
            y -= s * 0.22
            c.line_to(x, y)
            x += s * 0.25
            c.line_to(x, y)
        c.stroke()

    @staticmethod
    def chip(c, cx, cy, s):
        DG.chip(c, cx, cy, s * 0.7, c.get_line_width(), 4)


# =========================================================================== fotos


def foto_en_marco(img, foto, x0, y0, fw, fh, zoom=1.0, cx=0.5, cy=0.4, borde=0.45, a=1.0):
    """Foto recortada a un marco con un filo claro. Sin tinte ni efectos (vale para las víctimas)."""
    if a <= 0 or not foto.existe:
        return
    im = foto.im
    cubre = max(fw / im.width, fh / im.height) * zoom
    bw, bh = fw / cubre, fh / cubre
    bx = min(max(cx * im.width - bw / 2, 0), im.width - bw)
    by = min(max(cy * im.height - bh / 2, 0), im.height - bh)
    x0, y0, fw, fh = int(x0), int(y0), int(fw), int(fh)
    sub = np.asarray(im.resize((fw, fh), Image.BICUBIC, box=caja_dentro((bx, by, bx + bw, by + bh), im.width, im.height)), np.float32) / 255
    zona = img[y0 : y0 + fh, x0 : x0 + fw]
    img[y0 : y0 + fh, x0 : x0 + fw] = zona * (1 - a) + sub * a
    if borde > 0:
        b = CLARO * borde * a
        img[y0 - 2 : y0, x0 - 2 : x0 + fw + 2] = img[y0 - 2 : y0, x0 - 2 : x0 + fw + 2] * (1 - borde * a) + b
        img[y0 + fh : y0 + fh + 2, x0 - 2 : x0 + fw + 2] = img[y0 + fh : y0 + fh + 2, x0 - 2 : x0 + fw + 2] * (1 - borde * a) + b
        img[y0 : y0 + fh, x0 - 2 : x0] = img[y0 : y0 + fh, x0 - 2 : x0] * (1 - borde * a) + b
        img[y0 : y0 + fh, x0 + fw : x0 + fw + 2] = img[y0 : y0 + fh, x0 + fw : x0 + fw + 2] * (1 - borde * a) + b


def sombra_marco(img, x0, y0, fw, fh, a, fuerza=0.55):
    """Sombra suave debajo de un marco de foto (para que flote sobre el fondo)."""
    if a <= 0:
        return
    m = np.zeros((H, W), np.float32)
    m[int(y0) : int(y0 + fh), int(x0) : int(x0 + fw)] = 1.0
    img *= 1 - sombra_suave(m, 14, 20, 22, fuerza * a)[..., None]


# =========================================================================== la casa en corte


class CasaDiagrama:
    """La casa vista en corte: dos pisos, sótano y cochera, dibujada con líneas. Las coordenadas son
    de diseño (1920×1080); `escala` y `centro` la mueven sin redibujar a mano. Cada aparato tiene
    su lugar en `PUNTOS` para unir líneas o encender sensores."""

    PUNTOS = {
        "panel": (1085, 668), "puerta_cochera": (1158, 712), "puerta_principal": (630, 712),
        "ventana_1": (720, 655), "ventana_2": (990, 655), "ventana_3": (720, 500), "ventana_4": (1000, 500),
        "ventana_5": (1300, 670), "movimiento": (880, 618),
        "laptop": (820, 728), "telefono": (925, 715), "modem": (1010, 742), "tableta": (760, 565),
    }
    SENSORES = ("puerta_principal", "puerta_cochera", "ventana_1", "ventana_2", "ventana_3", "ventana_4",
                "ventana_5", "movimiento")

    def __init__(self, centro=(960, 600), escala=1.0):
        self.centro, self.escala = centro, escala

    def p(self, nombre_o_xy):
        x, y = self.PUNTOS[nombre_o_xy] if isinstance(nombre_o_xy, str) else nombre_o_xy
        return (self.centro[0] + (x - 960) * self.escala, self.centro[1] + (y - 600) * self.escala)

    def _transformar(self, c):
        c.translate(self.centro[0], self.centro[1])
        c.scale(self.escala, self.escala)
        c.translate(-960, -600)

    def dibujar(self, L: Lienzo, p: float, col=BEIGE, a: float = 1.0, grosor=3.0) -> None:
        """La casa se traza con el avance `p` (0..1): primero el contorno, luego pisos y ventanas."""
        if p <= 0 or a <= 0:
            return
        c = L.c
        c.save()
        self._transformar(c)
        L.tinta(col, a)
        g = grosor / self.escala
        contorno = [(600, 760), (600, 440), (560, 440), (880, 300), (1200, 440), (1160, 440), (1160, 600),
                    (1400, 600), (1400, 760), (600, 760)]
        DG.linea(c, contorno, suave(lim(p / 0.55)), g)
        q = suave(lim((p - 0.35) / 0.5))
        if q > 0:
            L.tinta(col, a * q)
            DG.linea(c, [(600, 600), (1160, 600)], 1.0, g * 0.8)                       # entrepiso
            DG.linea(c, [(1160, 760), (1160, 600)], 1.0, g * 0.8)                      # pared de la cochera
            DG.linea(c, [(1160, 600), (1290, 545), (1400, 600)], 1.0, g * 0.8)         # tejado de la cochera
            # sótano
            c.set_dash([12 / self.escala, 9 / self.escala])
            DG.linea(c, [(600, 760), (600, 880), (1160, 880), (1160, 760)], 1.0, g * 0.8)
            c.set_dash([])
            DG.linea(c, [(1040, 760), (1120, 880)], 1.0, g * 0.6)                      # escalera al sótano
            for k in range(5):
                x, y = 1040 + k * 16, 760 + k * 24
                DG.linea(c, [(x, y), (x + 16, y)], 1.0, g * 0.5)
            DG.linea(c, [(860, 600), (860, 760)], 1.0, g * 0.5)                        # muro interior
            DG.linea(c, [(880, 440), (880, 600)], 1.0, g * 0.5)
            # ventanas
            for (x, y, w, h) in ((690, 470, 60, 60), (970, 470, 60, 60), (690, 630, 60, 55), (960, 630, 60, 55),
                                 (1270, 650, 60, 40)):
                c.rectangle(x, y, w, h)
                c.stroke()
                DG.linea(c, [(x + w / 2, y), (x + w / 2, y + h)], 1.0, g * 0.4)
            # puertas
            c.rectangle(615, 668, 30, 92)
            c.stroke()
            c.rectangle(1150, 668, 16, 92)
            c.stroke()
            for k in range(2):                                                         # puertas de la cochera
                c.rectangle(1185 + k * 108, 690, 92, 70)
                c.stroke()
        c.restore()

    def sensor(self, L: Lienzo, nombre: str, t: float, inicio: float, col=REG, a: float = 1.0, tam: float = 9.0):
        """Un sensor que aparece con un anillo que se expande y luego queda latiendo suave."""
        v = aparece(t, inicio, 0.35) * a
        if v <= 0:
            return
        x, y = self.p(nombre)
        c = L.c
        L.tinta(col, v)
        c.new_sub_path()
        c.arc(x, y, tam * self.escala ** 0.5, 0, TAU)
        c.fill()
        u = ((t - inicio) * 0.8) % 1.0
        L.tinta(col, v * (1 - u) * 0.7)
        c.set_line_width(2.5)
        c.new_sub_path()
        c.arc(x, y, (tam + 34 * u) * self.escala ** 0.5, 0, TAU)
        c.stroke()

    def aparato(self, L: Lienzo, nombre: str, icono_nombre: str, a: float, col=CLARO, s: float = 40.0, g: float = 3.0):
        if a <= 0:
            return
        x, y = self.p(nombre)
        L.tinta(col, a)
        icono(L.c, icono_nombre, x, y, s * self.escala, g)


# =========================================================================== línea de tiempo


class LineaTiempo:
    """La mañana del 23 de diciembre de 2015 en una línea: una fila por fuente. Arriba, punteada, lo
    que dijo Richard; abajo, en líneas firmes, lo que registró cada aparato. El rango visible
    (`t0`, `t1`, en minutos) puede cambiar para acercarse a un tramo; las filas se acomodan según
    cuántas hay en pantalla."""

    X0, X1 = 430, 1800
    NOMBRES = {"richard": ("SEGÚN RICHARD", "lo que declaró"), "computadora": ("COMPUTADORA", "de la casa"),
               "alarma": ("ALARMA", "empresa de seguridad"), "facebook": ("FACEBOOK", "iPhone de Connie"),
               "fitbit": ("FITBIT", "de Connie")}

    def __init__(self, t0="8:30", t1="10:30", filas=None, eje=930):
        self.t0, self.t1 = hm(t0), hm(t1)
        self.filas = dict(filas or {"richard": 250, "computadora": 400, "alarma": 535, "facebook": 670, "fitbit": 805})
        self.eje_y = eje

    def rango(self, t0: float, t1: float) -> None:
        self.t0, self.t1 = t0, t1

    def x(self, m) -> float:
        if isinstance(m, str):
            m = hm(m)
        return self.X0 + (m - self.t0) / (self.t1 - self.t0) * (self.X1 - self.X0)

    def y(self, clave: str) -> float:
        return self.filas[clave]

    def eje(self, L: Lienzo, a: float, paso: int = 30, arriba: float = 170) -> None:
        if a <= 0:
            return
        c = L.c
        L.tinta(BEIGE, 0.55 * a)
        DG.linea(c, [(self.X0 - 20, self.eje_y), (self.X1 + 20, self.eje_y)], 1.0, 2.0)
        m = math.ceil(self.t0 / 5) * 5
        while m <= self.t1:
            x = self.x(m)
            if self.X0 - 25 <= x <= self.X1 + 25:
                mayor = m % paso == 0
                L.tinta(BEIGE, (0.7 if mayor else 0.3) * a)
                DG.linea(c, [(x, self.eje_y), (x, self.eje_y + (14 if mayor else 7))], 1.0, 2.0 if mayor else 1.2)
                if mayor:
                    L.texto(f"{m // 60}:{m % 60:02d}", x, self.eje_y + 52, 28, BEIGE, 0.8 * a, "centro", "Inter-Regular.ttf")
                    L.tinta(BEIGE, 0.06 * a)
                    DG.linea(c, [(x, arriba), (x, self.eje_y)], 1.0, 1.2)
            m += 5

    def fila(self, L: Lienzo, clave: str, a: float, col=None, punteada_=False, p: float = 1.0) -> None:
        if a <= 0:
            return
        y = self.filas[clave]
        col = col if col is not None else (BEIGE if clave == "richard" else REG)
        nombre, sub = self.NOMBRES[clave]
        L.texto(nombre, self.X0 - 40, y + 2, 24, col, a, "der", "Inter-SemiBold.ttf", 0.12)
        if sub:
            L.texto(sub, self.X0 - 40, y + 34, 22, TENUE, a * 0.9, "der", "Inter-Regular.ttf")
        x1 = self.X0 + (self.X1 - self.X0) * suave(lim(p))
        if punteada_:
            punteada(L, [(self.X0, y), (x1, y)], col, 0.4 * a, 2.0, (8, 10))
        else:
            L.tinta(col, 0.28 * a)
            DG.linea(L.c, [(self.X0, y), (x1, y)], 1.0, 2.0)

    def punto(self, L: Lienzo, clave: str, m, a: float, col=None, punteada_=False, r: float = 8.0) -> tuple:
        x, y = self.x(m), self.filas[clave]
        if a <= 0:
            return x, y
        col = col if col is not None else (BEIGE if clave == "richard" else REG)
        c = L.c
        L.tinta(col, a)
        c.new_sub_path()
        if punteada_:
            c.set_line_width(2.5)
            c.arc(x, y, r + 1, 0, TAU)
            c.set_dash([4, 4])
            c.stroke()
            c.set_dash([])
        else:
            c.arc(x, y, r * suave(lim(a * 1.6)) + 1, 0, TAU)
            c.fill()
        return x, y

    def marca(self, L: Lienzo, clave: str, m, a: float, rotulo: str = "", detalle: str = "", col=None,
              arriba: bool = True, alto: float = 0.0, ic: str | None = None, punteada_=False, tam=30,
              hora: bool = True) -> tuple:
        """Un evento: punto en su fila, una línea corta y, en renglones, la hora (con su ícono), qué
        pasó y un detalle. Devuelve (x, y) del punto."""
        x, y = self.punto(L, clave, m, a, col, punteada_)
        if a <= 0:
            return x, y
        col = col if col is not None else (BEIGE if clave == "richard" else REG)
        c = L.c
        s = -1 if arriba else 1
        largo = 30 + alto
        L.tinta(col, a)
        if punteada_:
            c.set_dash([4, 4])
        DG.linea(c, [(x, y + s * 12), (x, y + s * (12 + largo * suave(lim(a * 1.6))))], 1.0, 2.0)
        c.set_dash([])
        renglones = []
        if hora:
            renglones.append(("hora", m if isinstance(m, str) else f"{int(m) // 60}:{int(m) % 60:02d}", tam + 10))
        elif ic:
            renglones.append(("icono", "", 46))
        if rotulo:
            renglones.append(("rotulo", rotulo, 34))
        if detalle:
            renglones.append(("detalle", detalle, 30))
        if arriba:
            renglones = renglones[::-1]
        yy = y + s * (12 + largo) + (-10 if arriba else 0)
        for tipo, cad, paso in renglones:
            if not arriba:
                yy += paso
            if tipo == "hora":
                if ic:
                    L.tinta(col, a)
                    icono(c, ic, x + 32, yy - tam * 0.36, 30, 2.5)
                    L.texto(cad, x + 8, yy, tam, CLARO, a, "der")
                else:
                    L.texto(cad, x, yy, tam, CLARO, a, "centro")
            elif tipo == "icono":
                L.tinta(col, a)
                icono(c, ic, x, yy - 16, 34, 2.5)
            elif tipo == "rotulo":
                L.texto(cad, x, yy, 26, CLARO if col is BEIGE else col, a, "centro", "Inter-Regular.ttf")
            else:
                L.texto(cad, x, yy, 22, TENUE, a, "centro", "Inter-Regular.ttf")
            if arriba:
                yy -= paso
        return x, y

    def grupo(self, L: Lienzo, clave: str, eventos: list, a: float, col=None, arriba=False, alto=0.0,
              ancla: float | None = None) -> None:
        """Varios eventos muy juntos: un punto por evento y un solo bloque de texto «hora  qué pasó»."""
        if a <= 0:
            return
        col = col if col is not None else REG
        xs = [self.punto(L, clave, e[0], a, col)[0] for e in eventos]
        y = self.filas[clave]
        s = -1 if arriba else 1
        xm = sum(xs) / len(xs)
        L.tinta(col, a)
        for x in xs:
            DG.linea(L.c, [(x, y + s * 12), (x, y + s * 22), (xm, y + s * 34)], 1.0, 2.0)
        DG.linea(L.c, [(xm, y + s * 34), (xm, y + s * (40 + alto))], 1.0, 2.0)
        x0 = ancla if ancla is not None else xm
        yy = y + s * (40 + alto) + (-14 if arriba else 38)
        filas = eventos[::-1] if arriba else eventos
        for evento in filas:                         # (hora, texto) o (hora, texto, lo que se escribe en vez de la hora)
            m, cad = evento[0], evento[1]
            hora = evento[2] if len(evento) > 2 else (m if isinstance(m, str) else f"{int(m) // 60}:{int(m) % 60:02d}")
            L.texto(hora, x0 - 10, yy, 28, CLARO, a, "der")
            L.texto(cad, x0 + 8, yy, 26, col, a, "izq", "Inter-Regular.ttf")
            yy += 40 if not arriba else -40

    def tramo(self, L: Lienzo, clave: str, m0, m1, a: float, col=None, alto=26, rayado=False, punteada_=False,
              p: float = 1.0) -> None:
        """Una franja de tiempo en una fila (rayada: «sin actividad»)."""
        if a <= 0:
            return
        x0, x1 = self.x(m0), self.x(m1)
        x1 = x0 + (x1 - x0) * lim(p)
        y = self.filas[clave]
        col = col if col is not None else REG
        c = L.c
        c.save()
        c.rectangle(x0, y - alto / 2, max(1.0, x1 - x0), alto)
        c.clip()
        if rayado:
            L.tinta(col, 0.35 * a)
            c.set_line_width(2)
            k = x0 - alto
            while k < x1 + alto:
                c.move_to(k, y + alto / 2)
                c.line_to(k + alto, y - alto / 2)
                k += 14
            c.stroke()
        else:
            L.tinta(col, 0.5 * a)
            c.paint()
        c.restore()
        L.tinta(col, a)
        if punteada_:
            c.set_dash([8, 6])
        c.set_line_width(2)
        c.rectangle(x0, y - alto / 2, max(1.0, x1 - x0), alto)
        c.stroke()
        c.set_dash([])


# =========================================================================== sonido


def _n(seg: float) -> int:
    return int(round(seg * SR))


def _rng(semilla):
    return np.random.default_rng(semilla)


def alarma_casa(dur: float = 3.0, semilla: int = 501, lejos: float = 0.6) -> np.ndarray:
    """Sirena de alarma casera (piezo): un tono agudo que sube y baja rápido; `lejos` la apaga, como
    oída desde la calle."""
    n = _n(dur)
    t = np.arange(n) / SR
    f = 2600 + 700 * (0.5 + 0.5 * np.sign(np.sin(TAU * 3.2 * t)) * np.abs(np.sin(TAU * 3.2 * t)) ** 0.3)
    tono = np.sign(np.sin(TAU * np.cumsum(f) / SR)) * 0.6 + np.sin(TAU * np.cumsum(f) / SR) * 0.4
    tono = sfx.filtro(tono, "lowpass", 5000 - 3800 * lejos, 2)
    y = sfx.estereo(tono * np.clip(t / 0.05, 0, 1), 0.15)
    return sfx.normalizar_pico(sfx.reverberacion(y, 1.0, 0.25 + 0.3 * lejos, 3000, semilla)[:n], 0.5)


def sirena_americana(dur: float, semilla: int = 502) -> np.ndarray:
    """Sirena de patrulla estadounidense (el «wail»: sube y baja lento), lejos y acercándose."""
    rng = _rng(semilla)
    n = _n(dur)
    t = np.arange(n) / SR
    f = 700 + 650 * (0.5 - 0.5 * np.cos(TAU * t / 4.2))
    fase = TAU * np.cumsum(f) / SR
    tono = np.sin(fase) + 0.3 * np.sin(2 * fase) + 0.12 * np.sin(3 * fase)
    cerca = np.clip(t / max(dur, 1e-3), 0, 1)
    y = sfx.filtro(tono, "lowpass", 1400, 2) * (0.25 + 0.75 * cerca) * (0.85 + 0.15 * sfx.lfo_suave(n, rng, 0.4))
    return sfx.fundidos(sfx.normalizar_pico(sfx.reverberacion(sfx.estereo(y, -0.3), 2.0, 0.5, 1800, semilla)[:n]), 1.5, 1.0)


def tono_grave(dur: float, semilla: int = 503) -> np.ndarray:
    """Tono inquietante grave: dos senos casi iguales que baten despacio y un soplo oscuro que crece."""
    rng = _rng(semilla)
    n = _n(dur)
    t = np.arange(n) / SR
    x = np.sin(TAU * 49 * t) + np.sin(TAU * 51.3 * t) + 0.4 * np.sin(TAU * 98.5 * t)
    soplo = sfx.filtro(sfx.ruido_rosa(n, rng), "lowpass", 300, 2) * (0.3 + 0.7 * np.clip(t / max(dur, 1), 0, 1))
    y = x * 0.35 + soplo * 0.8
    return sfx.fundidos(sfx.normalizar_pico(sfx.estereo(y)), 2.0, 2.0)


def soplete(dur: float = 4.0, semilla: int = 504) -> np.ndarray:
    """Soplete que se enciende: el chasquido del encendedor, el «pof» del gas y un siseo que tiembla."""
    rng = _rng(semilla)
    n = _n(dur)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for t0 in (0.0, 0.09):
        i = _n(t0)
        k = _n(0.02)
        x[i : i + k] += rng.standard_normal(k) * np.exp(-np.arange(k) / (SR * 0.003)) * 0.8
    on = _n(0.18)
    env = np.clip((t - 0.18) / 0.12, 0, 1) * np.clip((dur - t) / 0.4, 0, 1)
    pof = np.zeros(n)
    pof[on : on + _n(0.25)] = np.exp(-np.arange(_n(0.25)) / (SR * 0.05))
    pof = sfx.filtro(rng.standard_normal(n) * pof, "lowpass", 400, 2) * 1.5
    sise = sfx.filtro(rng.standard_normal(n), "bandpass", (1500, 7000), 2) * (0.75 + 0.25 * sfx.lfo_suave(n, rng, 9.0))
    rugido = sfx.filtro(sfx.ruido_rosa(n, rng), "bandpass", (150, 700), 2) * 0.5
    y = sfx.estereo(x + pof + (sise * 0.5 + rugido) * env, -0.1)
    return sfx.normalizar_pico(sfx.reverberacion(y, 0.8, 0.3, 4000, semilla)[:n], 0.5)


def papel(dur: float = 1.2, semilla: int = 505) -> np.ndarray:
    """Hojas de papel que se acomodan sobre la mesa."""
    rng = _rng(semilla)
    n = _n(dur)
    x = np.zeros(n)
    for _ in range(int(dur * 40)):
        i = int(rng.uniform(0, n - _n(0.06)))
        k = _n(rng.uniform(0.01, 0.06))
        x[i : i + k] += rng.standard_normal(k) * np.hanning(k) * rng.uniform(0.2, 1)
    x = sfx.filtro(x, "bandpass", (900, 8000), 2) * np.sin(np.pi * np.linspace(0, 1, n)) ** 0.5
    return sfx.normalizar_pico(sfx.reverberacion(sfx.estereo(x, 0.1), 0.4, 0.12, 6000, semilla)[:n], 0.5)


def clic_mouse(semilla: int = 506) -> np.ndarray:
    rng = _rng(semilla)
    n = _n(0.12)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for t0, amp in ((0.0, 1.0), (0.055, 0.6)):
        i = _n(t0)
        tt = t[: n - i]
        x[i:] += sfx.filtro(rng.standard_normal(len(tt)) * np.exp(-tt / 0.0015), "bandpass", (2000, 8000), 2) * amp
    return sfx.normalizar_pico(sfx.estereo(x, 0.1), 0.5)


def clic_magnetico(semilla: int = 507) -> np.ndarray:
    """El contacto magnético que cambia: un clic seco de plástico con un tic metálico."""
    rng = _rng(semilla)
    n = _n(0.3)
    t = np.arange(n) / SR
    golpe = sfx.filtro(rng.standard_normal(n) * np.exp(-t / 0.002), "bandpass", (1200, 6000), 2)
    tic = np.sin(TAU * 4300 * t) * np.exp(-t / 0.012) * 0.3
    return sfx.normalizar_pico(sfx.reverberacion(sfx.estereo(golpe + tic), 0.3, 0.12, 6000, semilla)[:n], 0.5)


def pitido(f: float = 2900.0, dur: float = 0.09) -> np.ndarray:
    n = _n(dur + 0.1)
    t = np.arange(n) / SR
    x = np.sin(TAU * f * t) * (t < dur) * np.clip(t / 0.003, 0, 1)
    return sfx.normalizar_pico(sfx.estereo(sfx.filtro(x, "lowpass", 6000, 2)), 0.4)


def notificacion(semilla: int = 508) -> np.ndarray:
    n = _n(0.8)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for t0, f in ((0.0, 1318.5), (0.11, 1975.5)):
        i = _n(t0)
        tt = t[: n - i]
        x[i:] += np.sin(TAU * f * tt) * np.clip(tt / 0.005, 0, 1) * np.exp(-tt / 0.18)
    return sfx.normalizar_pico(sfx.reverberacion(sfx.estereo(x), 0.6, 0.2, 6000, semilla)[:n], 0.4)


def sincronizacion(dur: float = 1.6, semilla: int = 509) -> np.ndarray:
    """Datos que viajan: una escala corta de pitidos suaves que sube."""
    n = _n(dur)
    t = np.arange(n) / SR
    x = np.zeros(n)
    notas = (880, 1108.7, 1318.5, 1760)
    for k, f in enumerate(notas):
        i = _n(k * dur / 5)
        tt = t[: n - i]
        x[i:] += np.sin(TAU * f * tt) * np.clip(tt / 0.004, 0, 1) * np.exp(-tt / 0.09) * 0.7
    return sfx.normalizar_pico(sfx.reverberacion(sfx.estereo(x), 0.5, 0.2, 7000, semilla)[:n], 0.4)


def pasos_madera(tiempos: list[float], dur: float, semilla: int = 510) -> np.ndarray:
    """Pasos sobre piso de duela: golpe sordo del talón y roce; cada uno algo distinto."""
    rng = _rng(semilla)
    salida = np.zeros((_n(dur), 2), np.float32)
    k = _n(0.25)
    tt = np.arange(k) / SR
    for j, t0 in enumerate(tiempos):
        golpe = np.sin(TAU * rng.uniform(70, 95) * tt) * np.exp(-tt / 0.035)
        roce = sfx.filtro(rng.standard_normal(k) * np.exp(-tt / 0.03), "bandpass", (400, 3000), 2) * 0.35
        x = sfx.estereo((golpe + roce) * rng.uniform(0.6, 1.0), 0.2 * math.sin(j))
        i = _n(t0)
        if 0 <= i < len(salida):
            trozo = x[: len(salida) - i]
            salida[i : i + len(trozo)] += trozo
    return sfx.normalizar_pico(sfx.reverberacion(salida, 0.7, 0.2, 3500, semilla)[: len(salida)], 0.5)


def mazo(semilla: int = 511) -> np.ndarray:
    """Mazo de juez: dos golpes de madera con la resonancia de la sala."""
    rng = _rng(semilla)
    n = _n(2.5)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for t0, amp in ((0.0, 1.0), (0.32, 0.8)):
        i = _n(t0)
        tt = t[: n - i]
        madera = sum(a * np.sin(TAU * f * tt) * np.exp(-tt / d) for f, a, d in ((180, 1.0, 0.05), (410, 0.6, 0.03), (930, 0.3, 0.015)))
        chas = sfx.filtro(rng.standard_normal(len(tt)) * np.exp(-tt / 0.004), "bandpass", (800, 5000), 2) * 0.6
        x[i:] += (madera + chas) * amp
    return sfx.normalizar_pico(sfx.reverberacion(sfx.estereo(x), 1.8, 0.35, 3000, semilla)[:n], 0.7)


def cuarto(dur: float, semilla: int = 512) -> np.ndarray:
    """Tono de cuarto de una casa vacía: el zumbido del refrigerador y aire muy bajo."""
    rng = _rng(semilla)
    n = _n(dur)
    t = np.arange(n) / SR
    zumbido = (np.sin(TAU * 60 * t) + 0.4 * np.sin(TAU * 120 * t)) * (0.8 + 0.2 * sfx.lfo_suave(n, rng, 0.1))
    aire = sfx.filtro(sfx.ruido_rosa(n, rng), "bandpass", (120, 1200), 2)
    return sfx.fundidos(sfx.normalizar_pico(sfx.estereo(zumbido * 0.15 + aire * 0.6)), 1.0, 1.0)


def manana_afuera(dur: float, semilla: int = 513) -> np.ndarray:
    """Mañana de suburbio en diciembre: viento suave, un cuervo lejos y un auto que pasa a lo lejos."""
    rng = _rng(semilla)
    n = _n(dur)
    base = sfx.viento(dur, semilla, 0.6)
    salida = base * 0.8
    t = np.arange(n) / SR
    for t0 in rng.uniform(1.0, max(1.5, dur - 2.0), max(1, int(dur / 9))):
        for k in range(rng.integers(2, 4)):
            i = _n(t0 + k * 0.42)
            m = _n(0.28)
            if i + m >= n:
                continue
            tt = np.arange(m) / SR
            f = 520 * (1 - 0.25 * tt / 0.28)
            graz = np.sign(np.sin(TAU * np.cumsum(f) / SR)) * np.sin(np.pi * tt / 0.28) ** 0.5
            graz = sfx.filtro(graz + rng.standard_normal(m) * 0.6, "bandpass", (500, 2500), 2) * 0.12
            salida[i : i + m] += sfx.estereo(graz, -0.5)
    auto = sfx.filtro(sfx.ruido_rosa(n, rng), "lowpass", 500, 2) * np.exp(-((t - dur * 0.55) / 3.0) ** 2) * 0.4
    salida += sfx.estereo(auto, 0.3)
    return sfx.fundidos(sfx.normalizar_pico(salida), 1.2, 1.2)
