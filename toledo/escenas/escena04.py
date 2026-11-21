"""Escena 4 — Escaleras donde no hay escaleras (Friburgo: la app Salud, el juicio y la sentencia).

Lugares en 3D (Blender, `tres_d/planos_e04.py`, sobre el Dreisam de `tres_d/rio.py`): el río de día,
la orilla en pendiente, vacía, y el investigador que camina por ella con un iPhone en el bolsillo.
Los sensores (acelerómetro y barómetro), la línea de tiempo de la madrugada, el mapa de Europa y la
huella de Eurodac son gráficos (`escenas/graficos_e04.py`); la app Salud, el tribunal, Corfú, Merkel,
el Tagesschau y la sentencia, fotos y capturas reales.

4.0  El Dreisam de día; una empresa de Múnich abre el iPhone; la app Salud.
4.1  El coprocesador de movimiento y el acelerómetro: una masa diminuta que se mueve con cada paso;
     caminar, correr, bicicleta.
4.2  El barómetro: la columna de aire se acorta al subir; tres metros = un piso; la app lo anota
     («Flights Climbed»); todo queda en una base de datos cifrada que la empresa pudo leer.
4.3  La madrugada del 16 de octubre en la línea de tiempo, con un tramo de «subir escaleras»; la
     orilla en pendiente, vacía (quieta en la pausa); bajar y subir.
4.4  Un investigador repite el recorrido con un iPhone en el bolsillo: la misma gráfica.
4.5  El tribunal de Friburgo; la edad: 16, por lo menos 22, unos 25 (radiografía dental).
4.6  Grecia: Corfú, la condena, la amnistía, el viaje a Alemania; las huellas en Eurodac.
4.7  El país dividido; el Tagesschau; la AfD; Merkel; la sentencia del 22 de marzo de 2018.

Paleta de Friburgo: verde de la Selva Negra, rojo y blanco del escudo, gris piedra, azul río.
"""

from __future__ import annotations

import math

import cv2
import numpy as np
from PIL import Image

import dibujo as D
import guion
import sfx
from escenas import diagramas as DG
from escenas import graficos_e04 as G
from escenas import sonidos_e04 as SN
from escenas.base import SR, Foto, Segmentos, Subescena, TarjetaTitulo, aparece, recorrido, texto
from escenas.plano3d import Plano3D
from escenas.tiempos_e02 import tiempos
from graficos import H, W, caja_dentro, lim, suave
from paletas import APPLE, FRIBURGO, mezcla, rgb

NUMERO = 4
P = rgb(FRIBURGO)
AP = rgb(APPLE)
NEGRO = np.zeros(3, np.float32)
BL = P["blanco"]
GRIS = mezcla(P["piedra"], P["blanco"], 0.45)
NARANJA = np.array([1.0, 0.584, 0.0], np.float32)          # el color de «pisos subidos» en la app Salud
CRUCE = 0.9

# Eevee: el río de día y la orilla nublada se ven casi iguales en los dos motores (direccion_visual §5).
MOTOR = {"e04_dreisam_dia": "eevee", "e04_orilla_pendiente": "eevee", "e04_policia_orilla": "eevee"}

CINE = dict(sombras=mezcla(P["verde"], NEGRO, 0.45), luces=P["blanco"], mezcla=0.12, saturacion=0.95,
            contraste=0.06, halo=0.12, grano=0.012, vineta=0.32)
CINE_DIAG = dict(sombras=mezcla(P["verde"], NEGRO, 0.55), luces=P["blanco"], mezcla=0.07, saturacion=1.0,
                 contraste=0.04, halo=0.2, grano=0.010, vineta=0.38)


# =========================================================================== utilidades


def fondo() -> np.ndarray:
    return DG.fondo_profundo(mezcla(P["verde"], NEGRO, 0.84), mezcla(P["verde"], P["blanco"], 0.10))


def rotulo(img, cadena, x, y, tam=34, col=BL, a=1.0, alinear="izq", nombre="Inter-SemiBold.ttf"):
    return texto(img, cadena, x, y, tam, col, nombre=nombre, alinear=alinear, opacidad=a, sombra=0.45)


def panel(img, x0, y0, x1, y1, a, tinte=BL):
    return DG.tarjeta(img, x0, y0, x1, y1, a, tinte=tinte)


def lento(img: np.ndarray, t: float, d: float, z0: float = 1.0, z1: float = 1.035, deriva=(0.0, 0.0)) -> np.ndarray:
    u = 0.5 - 0.5 * math.cos(math.pi * lim(t / max(d, 1e-6)))
    z = z0 + (z1 - z0) * u
    if abs(z - 1) < 1e-4 and not any(deriva):
        return img
    M = np.float32([[z, 0, W / 2 * (1 - z) + deriva[0] * u], [0, z, H / 2 * (1 - z) + deriva[1] * u]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def imagen_flotante(img, im: Image.Image, cx, cy, alto, a=1.0, zoom=1.0, sombra=0.6, borde=0.0):
    """Captura o foto (con su transparencia, si la tiene) puesta como tarjeta que flota con sombra."""
    if a <= 0.002:
        return img
    h = int(alto * zoom)
    w = int(im.width * h / im.height)
    rgba = np.asarray(im.convert("RGBA").resize((w, h), Image.LANCZOS), np.float32) / 255
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return img
    alfa = np.zeros((H, W), np.float32)
    alfa[ya:yb, xa:xb] = rgba[ya - y0 : yb - y0, xa - x0 : xb - x0, 3]
    s = cv2.GaussianBlur(np.roll(np.roll(alfa, 24, 0), 14, 1), (0, 0), 26)
    img *= (1 - sombra * a * s)[..., None]
    k = alfa[ya:yb, xa:xb, None] * a
    img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - k) + rgba[ya - y0 : yb - y0, xa - x0 : xb - x0, :3] * k
    if borde > 0:
        img[ya:yb, xa : xa + 2] += borde * a
        img[ya:yb, xb - 2 : xb] += borde * a
        img[ya : ya + 2, xa:xb] += borde * a
        img[yb - 2 : yb, xa:xb] += borde * a
    return img


def abrir(nombre: str) -> Image.Image | None:
    f = Foto(nombre)
    if not f.existe:
        return None
    return Image.open(f.ruta)


def por_segmentos(seg: Segmentos, partes, t):
    img = None
    for k, peso in seg.pesos(t):
        capa = partes[k](t)
        img = capa * peso if img is None else img + capa * peso
    return img


def leyenda(img, t, lineas, x=110, y=H - 250, ancho=760, tam=40, col=BL):
    """Rótulo en tarjeta de vidrio: [(texto, inicio, fin, es_sub)]."""
    alfa = max((aparece(t, a, 0.5, b, 0.5) for _, a, b, _ in lineas), default=0)
    if alfa <= 0:
        return img
    alto = 40 + sum(56 if not s else 44 for _, _, _, s in lineas)
    img = panel(img, x - 40, y - 64, x + ancho, y - 64 + alto, alfa)
    yy = y
    for cadena, a, b, sub in lineas:
        op = aparece(t, a, 0.5, b, 0.5)
        if sub:
            rotulo(img, cadena, x, yy - 8, int(tam * 0.7), GRIS, op, nombre="Inter-Regular.ttf")
            yy += 44
        else:
            rotulo(img, cadena, x, yy, tam, col, op)
            yy += 56
    return img


def tira_registro(img, x0, x1, y, a, mov, marca, texto_mov="movimiento", texto_marca="subir escaleras"):
    """Registro esquemático (sin escala ni horas): la franja del día, un tramo de movimiento que crece
    con `mov` y, adentro, el tramo marcado como «subir escaleras», que se enciende con `marca`."""
    if a <= 0:
        return img
    tr = DG.Trazo()
    tr.tinta(mezcla(P["piedra"], NEGRO, 0.4), 0.8 * a)
    D.rect_redondeado(tr.c, x0, y - 22, x1 - x0, 44, 22)
    tr.c.fill()
    m0, m1 = x0 + (x1 - x0) * 0.38, x0 + (x1 - x0) * 0.66
    if mov > 0:
        tr.tinta(mezcla(P["rio"], BL, 0.35), a)
        D.rect_redondeado(tr.c, m0, y - 22, max(44.0, (m1 - m0) * mov), 44, 22)
        tr.c.fill()
    e0, e1 = x0 + (x1 - x0) * 0.50, x0 + (x1 - x0) * 0.57
    if marca > 0:
        tr.tinta(NARANJA, a * marca)
        D.rect_redondeado(tr.c, e0, y - 22, e1 - e0, 44, 22)
        tr.c.fill()
    img = DG.componer_relieve(tr, img, sombra=0.25, brillo=0.3 * marca, col_brillo=NARANJA)
    rotulo(img, texto_mov, m0, y + 70, 28, GRIS, a * mov, nombre="Inter-Regular.ttf")
    rotulo(img, texto_marca, (e0 + e1) / 2, y - 50, 34, NARANJA, a * marca, alinear="centro")
    return img


def alemania_chica(c, x0, y0, escala, ciudades=()):
    """El contorno de Alemania pequeño, para una tarjeta; `ciudades` [(lon, lat)] -> sus puntos."""
    def pr(lon, lat):
        return x0 + (lon - 5.8) * escala * math.cos(math.radians(51)), y0 + (55.1 - lat) * escala
    pts = [pr(*q) for q in G.ALEMANIA]
    D.rellenar(c, pts, suave=False)
    return [pr(*q) for q in ciudades]


# =========================================================================== título


def titulo() -> TarjetaTitulo:
    t = TarjetaTitulo(NUMERO, guion.leer()[NUMERO].titulo, P["rojo"], BL)
    t.cine = CINE
    return t


# =========================================================================== 4.0


class Sub40(Subescena):
    """El Dreisam de día; la empresa de Múnich; la app Salud."""

    cine = CINE

    def preparar(self) -> None:
        s = self.T.oraciones
        self.seg = Segmentos([s[4] - 0.2], 1.1)
        self.rio = Plano3D("e04_dreisam_dia", s[4] + CRUCE / 2 + 0.4, motor=MOTOR["e04_dreisam_dia"])
        self.planos3d = [self.rio]
        self.salud = abrir("4.0_app_salud.png")
        self.fondo = fondo()

    def _rio(self, t: float) -> np.ndarray:
        img = self.rio.cuadro(t)
        m = self.m
        a = aparece(t, 0.4, 0.8, m(1) - 0.2)
        img = panel(img, 80, H - 270, 640, H - 90, a)
        rotulo(img, "DE VUELTA EN", 130, H - 196, 24, GRIS, a)
        rotulo(img, "Friburgo", 128, H - 132, 60, BL, a)
        b = aparece(t, m(1) + 0.2, 0.6, m(4) - 0.4)
        if b > 0:
            img = panel(img, 80, 120, 920, 520, b)
            tr = DG.Trazo()
            tr.tinta(P["verde"] * 0.8 + P["blanco"] * 0.2, 0.9 * b)
            fr, mu = alemania_chica(tr.c, 690, 150, 24.0, (G.FRIBURGO, G.MUNICH))
            tr.tinta(P["rojo"], b)
            for q in (fr, mu):
                tr.c.arc(q[0], q[1], 7, 0, math.tau)
                tr.c.fill()
            img = DG.componer_relieve(tr, img, sombra=0.3)
            rotulo(img, "Múnich", mu[0] + 14, mu[1] + 8, 22, BL, b, nombre="Inter-Regular.ttf")
            rotulo(img, "una empresa de Múnich", 130, 220, 40, BL, b)
            rotulo(img, "abre el iPhone de Khavari", 132, 270, 30, GRIS, b, nombre="Inter-Regular.ttf")
            rotulo(img, "su nombre nunca se hizo público", 132, 380, 30, BL, aparece(t, m(2) + 0.2, 0.6) * b,
                   nombre="Inter-Regular.ttf")
            rotulo(img, "lo logró", 132, 460, 44, P["rojo"] * 0.4 + BL * 0.6, aparece(t, m(3) + 0.2, 0.6) * b)
        return img

    def _salud(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        m = self.m
        # «no en los mensajes ni en las fotos»: dos íconos que se apagan
        b = aparece(t, m(4) + 0.4, 0.6, m(5) + 0.3)
        for k, (x, nombre) in enumerate(((560, "mensajes"), (900, "fotos"))):
            img = panel(img, x - 120, 380, x + 120, 620, b * 0.9)
            tr = DG.Trazo()
            tr.tinta(BL, 0.85 * b)
            if k == 0:
                D.rect_redondeado(tr.c, x - 60, 440, 120, 80, 18)
                tr.c.set_line_width(5)
                tr.c.stroke()
            else:
                tr.c.set_line_width(5)
                tr.c.rectangle(x - 60, 440, 120, 90)
                tr.c.stroke()
                tr.c.move_to(x - 50, 520)
                tr.c.line_to(x - 10, 470)
                tr.c.line_to(x + 20, 500)
                tr.c.line_to(x + 50, 520)
                tr.c.stroke()
            tr.tinta(P["rojo"], b * aparece(t, m(4) + 1.6, 0.4))
            DG.cruz(tr.c, x, 480, 90, 7)
            img = DG.componer_relieve(tr, img, sombra=0.3)
            rotulo(img, nombre, x, 590, 28, GRIS, b, alinear="centro", nombre="Inter-Regular.ttf")
        c = aparece(t, m(5) - 0.2, 0.8)
        if self.salud is not None and c > 0:
            z = 1.0 + 0.04 * lim((t - m(5)) / 6.0)
            img = imagen_flotante(img, self.salud, 1400, 540, 900, c, z, 0.6)
            img = panel(img, 120, 640, 900, 900, c)
            rotulo(img, "Salud", 170, 740, 72, BL, c)
            rotulo(img, "la app de Apple que cuenta pasos", 172, 810, 34, GRIS, c, nombre="Inter-Regular.ttf")
        return lento(img, t - m(4), self.d - m(4), 1.0, 1.03)

    def cuadro(self, t: float) -> np.ndarray:
        return por_segmentos(self.seg, (self._rio, self._salud), t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("río", 0.0, sfx.agua_rio(self.m(4) + 1.5, 401, 0.8), 0, 1.0, 1.5)
        m.agregar("pájaros", 0.3, SN.pajaros(self.m(4) + 1.0, 402), -4, 1.0, 1.5)
        m.agregar("zumbido", self.m(4) - 0.3, sfx.zumbido_electronico(d - self.m(4) + 0.3, 403), -14, 1.0, 1.0)
        return m.x[:n]


# =========================================================================== 4.1


class Sub41(Subescena):
    """El coprocesador de movimiento: lee el acelerómetro todo el día y cuenta los pasos."""

    cine = CINE_DIAG

    def preparar(self) -> None:
        self.fondo = fondo()
        m = self.m
        r = np.random.default_rng(41)
        self.pasos = []
        t = m(3) + 1.2
        while t < self.d - 0.3:
            self.pasos.append(t)
            t += 0.55 + r.normal(0, 0.02)

    def _sacudida(self, t: float) -> float:
        """Desplazamiento de la masa: un golpe amortiguado en cada paso."""
        v = 0.0
        for tp in self.pasos:
            x = t - tp
            if 0 <= x < 0.6:
                v += math.exp(-x / 0.12) * math.sin(x * 2 * math.pi * 4.0)
        return v

    def cuadro(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        m = self.m
        # el teléfono con el chip de movimiento
        a_tel = aparece(t, 0.3, 0.8, m(3) - 0.3)
        if a_tel > 0:
            img = panel(img, 260, 160, 700, 920, a_tel)
            tr = DG.Trazo()
            tr.tinta(BL, 0.85 * a_tel)
            DG.telefono(tr.c, 480, 540, 660, 4)
            p = aparece(t, m(1) + 0.2, 0.8)
            tr.tinta(P["rojo"], p * a_tel)
            DG.chip(tr.c, 480, 450, 110, 4, 5, p)
            bat = aparece(t, m(2) + 0.2, 0.6)
            tr.tinta(BL, 0.8 * bat * a_tel)
            D.rect_redondeado(tr.c, 420, 650, 110, 52, 10)
            tr.c.set_line_width(4)
            tr.c.stroke()
            tr.c.rectangle(532, 666, 10, 20)
            tr.c.fill()
            nivel = 0.92 - 0.03 * lim((t - m(2)) / 4.0)
            tr.tinta(mezcla(P["verde"], BL, 0.4), bat * a_tel)
            tr.c.rectangle(428, 658, 94 * nivel, 36)
            tr.c.fill()
            img = DG.componer_relieve(tr, img, brillo=0.3 * p, col_brillo=P["rojo"])
            rotulo(img, "coprocesador de movimiento", 800, 420, 44, BL, aparece(t, m(1) + 0.3, 0.6) * a_tel)
            rotulo(img, "desde el iPhone 5S", 802, 475, 30, GRIS, aparece(t, m(1) + 0.8, 0.6) * a_tel, nombre="Inter-Regular.ttf")
            rotulo(img, "todo el día, casi sin batería", 802, 690, 36, BL, aparece(t, m(2) + 0.3, 0.6) * a_tel)
        # el acelerómetro: la masa que se mueve con cada sacudida
        a_ac = aparece(t, m(3) - 0.2, 0.8)
        if a_ac > 0:
            dx = 0.035 * self._sacudida(t)
            img = panel(img, 140, 150, 1180, 760, a_ac)
            tr = DG.Trazo()
            G.acelerometro(tr.c, 660, 470, 600, dx, mezcla(P["piedra"], BL, 0.3), mezcla(P["rio"], BL, 0.35), a_ac)
            img = DG.componer_relieve(tr, img, brillo=0.25, col_brillo=P["rio"])
            rotulo(img, "acelerómetro", 190, 215, 38, BL, a_ac)
            rotulo(img, "una masa diminuta que se mueve con cada sacudida", 192, 735, 28, GRIS, a_ac, nombre="Inter-Regular.ttf")
            # la señal: una gráfica que corre a la derecha
            img = panel(img, 1240, 150, 1800, 760, a_ac)
            tr = DG.Trazo()
            tr.tinta(mezcla(P["rio"], BL, 0.4), a_ac)
            tr.c.set_line_width(4)
            ventana = 4.0
            for i in range(240):
                tt = t - ventana + ventana * i / 239
                y = 455 - 180 * self._sacudida(tt)
                x = 1280 + 480 * i / 239
                (tr.c.move_to if i == 0 else tr.c.line_to)(x, y)
            tr.c.stroke()
            img = DG.componer_relieve(tr, img, sombra=0.2, brillo=0.4, col_brillo=P["rio"])
            rotulo(img, "señal", 1280, 230, 30, GRIS, a_ac, nombre="Inter-Regular.ttf")
            # cada paso enciende una marca (sin contar: el número no sería un dato del caso)
            ultimo = max((tp for tp in self.pasos if tp <= t), default=-9.0)
            destello = math.exp(-(t - ultimo) / 0.15) if t >= ultimo else 0.0
            rotulo(img, "un paso", 1280, 700, 30, mezcla(GRIS, BL, destello), a_ac * (0.5 + 0.5 * destello))
        # caminar, correr, bicicleta
        a_ic = aparece(t, m(4) + 0.2, 0.7)
        if a_ic > 0:
            for k, (tipo, nombre, vel) in enumerate((("caminar", "caminar", 1.8), ("correr", "correr", 3.0), ("bici", "bicicleta", 1.2))):
                x = 420 + k * 540
                b = a_ic * aparece(t, m(4) + 0.3 + 0.9 * k, 0.5)
                img = panel(img, x - 200, 800, x + 200, 1040, b)
                tr = DG.Trazo()
                tr.tinta(BL, b)
                G.pictograma(tr.c, x - 90, 920, 150, tipo, (t * vel) % 1.0)
                img = DG.componer_relieve(tr, img, sombra=0.3)
                rotulo(img, nombre, x + 10, 935, 34, BL, b)
        return lento(img, t, self.d, 1.0, 1.03)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(d, 411), -14, 1.5, 1.5)
        m.agregar("pasos", 0.0, SN.pasos(self.pasos, d, 412), -4)
        return m.x[:n]


# =========================================================================== 4.2


class Sub42(Subescena):
    """El barómetro: el aire pesa; subir tres metros es un piso; todo queda en una base cifrada."""

    cine = CINE_DIAG

    def preparar(self) -> None:
        self.fondo = fondo()
        self.pisos = abrir("4.2_pisos_subidos.png")
        s = self.T.oraciones
        self.seg = Segmentos([s[6] - 0.2], 1.0)

    def _subida(self, t: float) -> float:
        """Altura (en escalones, 0..18) de la persona que sube la escalera, de [2] a [4]."""
        return 18 * suave(lim((t - self.m(2) + 0.3) / max(1.0, self.m(5) - self.m(2) - 0.8)))

    def _aire(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        m = self.m
        a = aparece(t, 0.3, 0.8)
        # escalera: 18 escalones de 17 cm (unos 3 m)
        x0, y0, paso_x, paso_y = 250, 960, 30, 26
        h = self._subida(t)
        tr = DG.Trazo()
        tr.tinta(mezcla(P["piedra"], BL, 0.2), 0.9 * a)
        tr.c.move_to(x0 - 120, y0)
        for k in range(18):
            tr.c.line_to(x0 + k * paso_x, y0 - k * paso_y)
            tr.c.line_to(x0 + (k + 1) * paso_x, y0 - k * paso_y)
        tr.c.line_to(x0 + 18 * paso_x + 120, y0 - 18 * paso_y)
        tr.c.set_line_width(5)
        tr.c.stroke()
        k = min(17.0, h)
        px = x0 + k * paso_x + 14
        py = y0 - k * paso_y
        tr.tinta(BL, a)
        G.pictograma(tr.c, px, py - 95, 150, "caminar", (t * 1.6) % 1.0 if 0 < h < 18 else 0.0)
        img = DG.componer_relieve(tr, img, sombra=0.35)
        # la columna de aire encima: puntos que se aclaran hacia arriba
        b = aparece(t, m(1) - 0.2, 0.8)
        if b > 0:
            alto = py - 175
            col = np.zeros((H, W), np.float32)
            rng = np.random.default_rng(42)
            n = 900
            xs = rng.uniform(px - 70, px + 70, n)
            ys = 60 + (alto - 60) * rng.random(n) ** 0.55
            for x, y in zip(xs.astype(int), ys.astype(int)):
                if 0 <= y < H and 0 <= x < W:
                    col[y, x] = 1
            col = cv2.GaussianBlur(cv2.dilate(col, np.ones((3, 3), np.uint8)), (0, 0), 1.0)
            caja = np.zeros((H, W), np.float32)
            caja[60:int(alto), int(px - 80):int(px + 80)] = 1
            caja = cv2.GaussianBlur(caja, (0, 0), 6)
            img += (caja[..., None] * 0.06 + col[..., None] * 0.55) * mezcla(P["rio"], BL, 0.5) * b
            rotulo(img, "el aire de encima", px + 110, 160, 30, GRIS, b, nombre="Inter-Regular.ttf")
        # lecturas del barómetro
        c = aparece(t, 0.4, 0.6)
        img = panel(img, 1060, 140, 1820, 320, c)
        rotulo(img, "barómetro", 1110, 220, 40, BL, c)
        rotulo(img, "mide la presión del aire", 1112, 268, 28, GRIS, c, nombre="Inter-Regular.ttf")
        d = aparece(t, m(2) + 0.2, 0.6)
        img = panel(img, 1060, 380, 1820, 580, d)
        rotulo(img, "1 metro más arriba", 1110, 460, 36, BL, d)
        rotulo(img, "≈ 12 pascales menos", 1110, 520, 36, mezcla(P["rio"], BL, 0.45), d)
        e = aparece(t, m(3) + 0.2, 0.6, m(4) - 0.2)
        rotulo(img, "una diferencia minúscula", 1110, 660, 36, BL, e)
        f = aparece(t, m(4) + 0.3, 0.6)
        if f > 0:
            tr = DG.Trazo()
            tr.tinta(NARANJA, f)
            xb = x0 + 18 * paso_x + 90
            DG.linea(tr.c, [(xb, y0), (xb, y0 - 18 * paso_y)], f, 4)
            for yy in (y0, y0 - 18 * paso_y):
                tr.c.move_to(xb - 14, yy)
                tr.c.line_to(xb + 14, yy)
                tr.c.stroke()
            img = DG.componer_relieve(tr, img, sombra=0.2, brillo=0.3, col_brillo=NARANJA)
            rotulo(img, "3 m", xb + 26, y0 - 9 * paso_y + 14, 34, NARANJA, f)
            img = panel(img, 1060, 760, 1820, 960, f)
            rotulo(img, "caminando + 3 m más arriba", 1110, 840, 34, BL, f)
            rotulo(img, "= 1 piso de escaleras", 1110, 900, 40, NARANJA, f)
        return lento(img, t, self.T.oraciones[6], 1.0, 1.03)

    def _base_datos(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        m = self.m
        a = aparece(t, m(6) - 0.3, 0.8)
        img = panel(img, 160, 170, 1160, 930, a)
        rotulo(img, "base de datos del teléfono", 210, 250, 36, BL, a)
        # renglones de ejemplo: el tipo de registro y barras en lugar de horas y cantidades (no hay datos del caso)
        filas = ("pasos", "pasos", "pasos", "pisos", "pasos", "pasos")
        abre = aparece(t, m(7) + 0.6, 0.8)
        for k, que in enumerate(filas):
            y = 340 + k * 86
            b = a * aparece(t, m(6) + 0.3 + 0.25 * k, 0.4)
            if abre < 1:
                bloque = DG.ruido_visual(52, 860, t + k, k)[..., None] * mezcla(P["piedra"], BL, 0.2) * 0.35
                img[y - 40 : y + 12, 210 : 1070] = img[y - 40 : y + 12, 210 : 1070] * (1 - b * (1 - abre)) + bloque * b * (1 - abre)
            col = NARANJA if que == "pisos" else BL
            tr = DG.Trazo()
            tr.tinta(GRIS, 0.55 * b * abre)
            D.rect_redondeado(tr.c, 230, y - 26, 120, 22, 11)                     # hora y minuto
            D.rect_redondeado(tr.c, 960, y - 26, 80, 22, 11)                      # cantidad
            tr.c.fill()
            img = tr.componer(img)
            rotulo(img, que, 420, y, 34, col, b * abre)
        tr = DG.Trazo()
        tr.tinta(BL, a)
        DG.candado(tr.c, 1080, 230, 60, cerrado=1 - abre)
        img = DG.componer_relieve(tr, img, sombra=0.3)
        rotulo(img, "cifrada", 1250, 400, 40, BL, a * (1 - abre))
        rotulo(img, "con hora y minuto", 1250, 460, 30, GRIS, a, nombre="Inter-Regular.ttf")
        rotulo(img, "la empresa de Múnich", 1250, 640, 40, BL, abre)
        rotulo(img, "la pudo leer", 1250, 696, 40, BL, abre)
        return lento(img, t - m(6), self.d - m(6), 1.0, 1.04)

    def cuadro(self, t: float) -> np.ndarray:
        img = por_segmentos(self.seg, (self._aire, self._base_datos), t)
        m = self.m
        g = aparece(t, m(4) + 1.6, 0.7, m(6) - 0.4)                       # la app lo anota
        if self.pisos is not None and g > 0:
            img = img * (1 - g) + cv2.GaussianBlur(img, (0, 0), 14) * 0.35 * g
            img = imagen_flotante(img, self.pisos, 960, 520, 640, g, 1.0 + 0.03 * lim((t - m(4)) / 6), 0.6)
            rotulo(img, "Pisos subidos", 960, 930, 44, BL, g, alinear="centro")
            rotulo(img, "nadie tiene que abrir la app", 960, 990, 30, GRIS, g * aparece(t, m(5), 0.6), alinear="centro",
                   nombre="Inter-Regular.ttf")
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("aire", 0.3, SN.silbido_aire(self.m(4), 421), -6, 1.0, 1.5)
        m.agregar("sube", self.m(4) + 0.3, SN.tono_sube(2.2, 422), -4)
        m.agregar("zumbido", self.m(6) - 0.3, sfx.zumbido_electronico(d - self.m(6) + 0.3, 423), -14, 1.0, 1.0)
        m.agregar("candado", self.m(7) + 0.6, sfx.candado(424), -8)
        return m.x[:n]


# =========================================================================== 4.3


class Sub43(Subescena):
    """La madrugada en la línea de tiempo, con un tramo de «subir escaleras»; la orilla vacía."""

    cine = CINE

    def preparar(self) -> None:
        s = self.T.oraciones
        self.fondo = fondo()
        self.seg = Segmentos([s[2] - 0.2], 1.2)
        self.ini_pend = s[2] - 0.2 - 0.6
        self.pend = Plano3D("e04_orilla_pendiente", self.quieto(self.d) - self.quieto(self.ini_pend) + 0.3,
                            motor=MOTOR["e04_orilla_pendiente"])
        self.planos3d = [self.pend]

    def _linea(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        m = self.m
        a = aparece(t, 0.3, 0.8)
        img = panel(img, 120, 180, 1800, 900, a)
        rotulo(img, "madrugada del 16 de octubre de 2016", 180, 270, 42, BL, a)
        rotulo(img, "lo que registró la app Salud (esquema)", 182, 320, 28, GRIS, a, nombre="Inter-Regular.ttf")
        crece = suave(lim((t - 0.8) / 2.0))
        marca = aparece(t, m(1) + 0.4, 0.6)
        img = tira_registro(img, 220, 1700, 620, a, crece, marca, "movimiento a la hora del crimen")
        return lento(img, t, self.m(2), 1.0, 1.04)

    def _orilla(self, t: float) -> np.ndarray:
        img = self.pend.cuadro(self.quieto(t) - self.quieto(self.ini_pend))
        m = self.m
        a = aparece(t, m(2) + 0.2, 0.7, m(3) - 0.2)
        img = panel(img, 80, H - 260, 900, H - 90, a)
        rotulo(img, "en esa orilla", 130, H - 190, 30, GRIS, a, nombre="Inter-Regular.ttf")
        rotulo(img, "no hay escaleras", 128, H - 130, 56, BL, a)
        b = aparece(t, m(3) + 0.3, 0.8)
        if b > 0:                                                           # el perfil: bajar y volver a subir
            img = panel(img, 80, 120, 820, 470, b)
            rotulo(img, "lo que interpretan", 130, 190, 30, GRIS, b, nombre="Inter-Regular.ttf")
            tr = DG.Trazo()
            u = suave(lim((t - m(3) - 0.6) / 3.0))
            pts = [(140, 260), (300, 262), (460, 410), (520, 412), (680, 262), (770, 260)]
            tr.tinta(BL, 0.35 * b)
            DG.linea(tr.c, pts, 1.0, 3)
            tr.tinta(NARANJA, b)
            DG.linea(tr.c, pts, u, 5)
            img = DG.componer_relieve(tr, img, sombra=0.2, brillo=0.3, col_brillo=NARANJA)
            rotulo(img, "orilla", 150, 248, 24, GRIS, b, nombre="Inter-Regular.ttf")
            rotulo(img, "agua", 470, 450, 24, GRIS, b, nombre="Inter-Regular.ttf")
            rotulo(img, "subir escaleras", 560, 330, 26, NARANJA, b * aparece(t, m(3) + 2.4, 0.5))
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return por_segmentos(self.seg, (self._linea, self._orilla), t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(self.m(2) + 0.5, 431), -16, 1.0, 1.0)
        m.agregar("agua", self.m(2) - 0.5, sfx.agua_rio(d - self.m(2) + 0.5, 432, 0.7), -2, 2.0, 2.0)
        m.agregar("viento", self.m(2) - 0.5, sfx.viento(d - self.m(2) + 0.5, 433, 0.5), -8, 2.0, 2.0)
        return m.x[:n]


# =========================================================================== 4.4


class Sub44(Subescena):
    """Un investigador repite el recorrido con un iPhone en el bolsillo: la app registra lo mismo."""

    cine = CINE

    def preparar(self) -> None:
        s = self.T.oraciones
        self.fondo = fondo()
        self.seg = Segmentos([s[3] - 0.2], 1.0)
        self.pol = Plano3D("e04_policia_orilla", s[3] + CRUCE / 2 + 0.3, motor=MOTOR["e04_policia_orilla"])
        self.planos3d = [self.pol]

    def _orilla(self, t: float) -> np.ndarray:
        img = self.pol.cuadro(t)
        m = self.m
        img = leyenda(img, t, [("una interpretación no basta", 0.3, m(1) - 0.1, False),
                               ("en un juicio", 0.7, m(1) - 0.1, True)])
        img = leyenda(img, t, [("un investigador de la policía", m(1) + 0.2, m(2) - 0.1, False),
                               ("la misma orilla, un iPhone en el bolsillo", m(1) + 0.8, m(2) - 0.1, True)])
        img = leyenda(img, t, [("baja la pendiente y vuelve a subir", m(2) + 0.2, self.d, False)])
        return img

    def _graficas(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        m = self.m
        filas = (("16 de octubre de 2016", "el teléfono de Khavari"), ("recreación", "el teléfono del investigador"))
        for k, (que, de) in enumerate(filas):
            y0 = 160 + k * 400
            a = aparece(t, m(3) - 0.2 + 0.6 * k, 0.7)
            img = panel(img, 120, y0, 1800, y0 + 340, a)
            rotulo(img, que, 170, y0 + 70, 36, BL, a)
            rotulo(img, de, 172, y0 + 116, 28, GRIS, a, nombre="Inter-Regular.ttf")
            mov = suave(lim((t - m(3) - 0.6 * k) / 1.2))
            marca = aparece(t, m(3) + 1.0 + 0.6 * k, 0.5)
            img = tira_registro(img, 700, 1740, y0 + 200, a, mov, marca, "")
        b = aparece(t, m(4) + 0.3, 0.6)
        img = panel(img, 460, 930, 1460, 1040, b)
        rotulo(img, "una prueba crucial", 960, 1002, 44, BL, b, alinear="centro")
        return lento(img, t - m(3), self.d - m(3), 1.0, 1.03)

    def cuadro(self, t: float) -> np.ndarray:
        return por_segmentos(self.seg, (self._orilla, self._graficas), t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        pasos = list(np.arange(0.3, self.m(3) + 0.6, 0.56))
        m.agregar("pasos", 0.0, SN.pasos(pasos, self.m(3) + 1.0, 441, "tierra"), -2, 0.5, 0.8)
        m.agregar("río", 0.0, sfx.agua_rio(self.m(3) + 1.0, 442, 0.6), -8, 1.0, 1.0)
        m.agregar("zumbido", self.m(3) - 0.3, sfx.zumbido_electronico(d - self.m(3) + 0.3, 443), -14, 1.0, 1.0)
        return m.x[:n]


# =========================================================================== 4.5


class Sub45(Subescena):
    """El juicio en el tribunal de Friburgo; la edad: dijo 16, el examen dio por lo menos 22 y el
    dentista forense, unos 25."""

    cine = CINE

    def preparar(self) -> None:
        s = self.T.oraciones
        self.tribunal = Foto("4.5_tribunal_friburgo.jpg", P["piedra"], 0.06)
        self.juicio = Foto("4.5_juicio_khavari.jpg")
        self.fondo = fondo()
        self.rx = G.radiografia_dental(660, 310)
        self.seg = Segmentos([s[1] - 0.2], 1.0)

    def _tribunal(self, t: float) -> np.ndarray:
        z, cx, cy = recorrido(t, self.m(1) + 0.6, 1.0, 1.06, (0.5, 0.62), (0.5, 0.42))
        img = self.tribunal.ver(z, cx, cy) * 0.92
        a = aparece(t, 0.4, 0.7)
        img = panel(img, 80, H - 270, 860, H - 90, a)
        rotulo(img, "TRIBUNAL DE FRIBURGO", 130, H - 196, 24, GRIS, a)
        rotulo(img, "septiembre de 2017", 128, H - 132, 56, BL, a)
        return img

    def _edad(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        m = self.m
        if self.juicio.existe:                                              # la foto del juicio, quieta
            x0, y0, fw, fh = 110, 250, 760, 474
            im = self.juicio.im
            z = 1.0 + 0.03 * lim((t - m(1)) / 10.0)
            cubre = max(fw / im.width, fh / im.height) * z
            bw, bh = fw / cubre, fh / cubre
            bx, by = (im.width - bw) * 0.55, (im.height - bh) * 0.35
            foto = np.asarray(im.resize((fw, fh), Image.LANCZOS, box=caja_dentro((bx, by, bx + bw, by + bh), im.width, im.height)), np.float32) / 255
            a = aparece(t, m(1) - 0.2, 0.7)
            sm = np.zeros((H, W), np.float32)
            sm[y0 : y0 + fh, x0 : x0 + fw] = 1
            img *= (1 - 0.55 * a * cv2.GaussianBlur(np.roll(np.roll(sm, 20, 0), 12, 1), (0, 0), 22))[..., None]
            img[y0 : y0 + fh, x0 : x0 + fw] = img[y0 : y0 + fh, x0 : x0 + fw] * (1 - a) + foto * a
            rotulo(img, "Hussein Khavari en el juicio", x0, y0 + fh + 60, 30, GRIS, a, nombre="Inter-Regular.ttf")
        # la radiografía dental, a la derecha de las cifras (se suma como luz: la placa es negra)
        r = aparece(t, m(4) + 0.6, 0.8)
        if r > 0:
            y0, x0 = 700, 990
            rx = self.rx
            img[y0 : y0 + rx.shape[0], x0 : x0 + rx.shape[1]] += rx * 0.9 * r
            rotulo(img, "radiografía", x0 + rx.shape[1] + 30, y0 + 150, 26, GRIS, r, nombre="Inter-Regular.ttf")
            rotulo(img, "dental", x0 + rx.shape[1] + 30, y0 + 186, 26, GRIS, r, nombre="Inter-Regular.ttf")
        filas = ((2, "dijo tener", "16"), (3, "examen médico, feb. 2017", "22 o más"), (4, "dentista forense", "unos 25"))
        for k, (o, que, cifra) in enumerate(filas):
            a = aparece(t, m(o) + 0.2, 0.6)
            y = 270 + k * 150
            tachada = k == 0 and t > m(o + 1) + 0.4
            col = GRIS if tachada else BL
            rotulo(img, que, 1000, y, 30, GRIS, a, nombre="Inter-Regular.ttf")
            w, _ = rotulo(img, cifra, 1000, y + 76, 76, col, a, nombre="Inter-Light.ttf")
            if tachada:
                img[y + 44 : y + 48, 1000 : 1000 + int(w * suave(lim((t - m(o + 1) - 0.4) / 0.5)))] = P["rojo"]
        return lento(img, t - m(1), self.d - m(1), 1.0, 1.03)

    def cuadro(self, t: float) -> np.ndarray:
        return por_segmentos(self.seg, (self._tribunal, self._edad), t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("murmullo", 0.0, SN.murmullo(self.m(1) + 1.5, 451), -2, 1.0, 1.5)
        m.agregar("zumbido", self.m(1) - 0.3, sfx.zumbido_electronico(d - self.m(1) + 0.3, 452), -16, 1.0, 1.0)
        return m.x[:n]


# =========================================================================== 4.6


class Sub46(Subescena):
    """Grecia: Corfú, diez años de condena y uno y medio de cárcel; el viaje a Alemania; las huellas
    en Eurodac, que nadie cruzó."""

    cine = CINE

    def preparar(self) -> None:
        s = self.T.oraciones
        gris_grecia = mezcla(P["piedra"], P["verde"], 0.3)
        self.mapa = G.Mapa(P, centro=(14.0, 45.0), escala=150.0, resaltar=[(G.GRECIA, gris_grecia, 0.6)])
        self.corfu = Foto("4.6_corfu.jpg", P["rio"], 0.05)
        self.fondo = fondo()
        self.huella = G.huella(420)
        self.seg = Segmentos([s[1] - 0.1, s[3] - 0.1, s[6] - 0.2], 1.0)

    def _ver_mapa(self, t: float, u: float) -> tuple[np.ndarray, callable]:
        """u = 0: Europa entera; u = 1: cerca de Grecia."""
        cx0, cy0 = self.mapa.proy(14.0, 45.0)
        cx1, cy1 = self.mapa.proy(20.5, 39.8)
        cx, cy = cx0 + (cx1 - cx0) * u, cy0 + (cy1 - cy0) * u
        return self.mapa.ver(cx, cy, 0.62 + 1.2 * u)

    def _grecia(self, t: float) -> np.ndarray:
        u = suave(lim(t / max(1.0, self.m(1))))
        img, pant = self._ver_mapa(t, u)
        x, y = pant(*self.mapa.proy(*G.CORFU))
        tr = DG.Trazo()
        tr.tinta(P["rojo"])
        tr.c.arc(x, y, 10, 0, math.tau)
        tr.c.fill()
        img = tr.componer(img, 0.6, P["rojo"], 10)
        rotulo(img, "Corfú", x - 30, y + 10, 40, BL, aparece(t, 0.6, 0.6), alinear="der")
        gx, gy = pant(*self.mapa.proy(22.2, 39.6))
        rotulo(img, "GRECIA", gx, gy, 44, mezcla(P["piedra"], BL, 0.3), aparece(t, 0.2, 0.8) * 0.8, alinear="centro")
        return img

    def _foto_corfu(self, t: float) -> np.ndarray:
        z, cx, cy = recorrido(t - self.m(1), self.m(3) - self.m(1) + 1.0, 1.0, 1.08, (0.45, 0.5), (0.55, 0.45))
        img = self.corfu.ver(z, cx, cy) * 0.9
        a = aparece(t, self.m(1) + 0.3, 0.6)
        img = panel(img, 80, H - 270, 900, H - 90, a)
        rotulo(img, "CORFÚ, GRECIA", 130, H - 196, 24, GRIS, a)
        rotulo(img, "2013", 128, H - 132, 56, BL, a)
        rotulo(img, "una estudiante de 20 años sobrevivió con heridas graves", 130, 120, 30, BL,
               aparece(t, self.m(2) + 0.2, 0.6), nombre="Inter-Regular.ttf")
        return img

    def _viaje(self, t: float) -> np.ndarray:
        m = self.m
        mx, my = self.mapa.proy(13.9, 43.8)                           # Corfú y Friburgo en el mismo cuadro
        img, pant = self.mapa.ver(mx, my, 0.7)
        a0 = pant(*self.mapa.proy(*G.CORFU))
        a1 = pant(*self.mapa.proy(*G.FRIBURGO))
        p = suave(lim((t - m(4) - 1.2) / 2.5))
        tr = DG.Trazo()
        tr.tinta(P["rojo"])
        for q in (a0, a1):
            tr.c.arc(q[0], q[1], 9, 0, math.tau)
            tr.c.fill()
        tr.c.set_dash([18, 12])
        DG.flecha(tr.c, a0, a1, p, 5, 22, curva=-120)
        img = tr.componer(img, 0.5, P["rojo"], 10)
        rotulo(img, "Corfú", a0[0] + 18, a0[1] + 40, 32, BL, 1.0)
        rotulo(img, "Friburgo", a1[0] - 20, a1[1] - 20, 32, BL, aparece(t, m(4) + 2.0, 0.6), alinear="der")
        img = panel(img, 1240, 140, 1840, 560, aparece(t, m(3), 0.6))
        rotulo(img, "condena", 1290, 220, 30, GRIS, aparece(t, m(3), 0.6), nombre="Inter-Regular.ttf")
        rotulo(img, "10 años", 1290, 300, 64, BL, aparece(t, m(3) + 0.2, 0.6), nombre="Inter-Light.ttf")
        rotulo(img, "libre al año y medio", 1290, 400, 40, BL, aparece(t, m(4) + 0.2, 0.6))
        rotulo(img, "amnistía para delincuentes juveniles", 1290, 450, 26, GRIS, aparece(t, m(4) + 0.6, 0.6), nombre="Inter-Regular.ttf")
        tr = DG.Trazo()
        largo = 480 * (1 - 0.85 * suave(lim((t - m(4) - 0.2) / 1.2)))
        tr.tinta(P["rojo"], aparece(t, m(3) + 0.4, 0.6))
        tr.c.rectangle(1290, 500, largo, 14)
        tr.c.fill()
        img = DG.componer_relieve(tr, img, sombra=0.2)
        b = aparece(t, m(5) + 0.2, 0.6)
        img = panel(img, 1240, 620, 1840, 760, b)
        rotulo(img, "Grecia nunca pidió", 1290, 680, 34, BL, b)
        rotulo(img, "su búsqueda internacional", 1290, 728, 30, GRIS, b, nombre="Inter-Regular.ttf")
        return img

    def _eurodac(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        m = self.m
        a = aparece(t, m(6) - 0.2, 0.8)
        img = panel(img, 160, 200, 760, 840, a)
        # la huella que se escanea: una línea de luz que la recorre
        y0, x0 = 300, 250
        barrido = lim((t - m(6) - 0.3) / 2.0)
        h = self.huella
        visible = np.zeros_like(h)
        corte = int(h.shape[0] * barrido)
        visible[:corte] = h[:corte]
        col = mezcla(P["rio"], BL, 0.45)
        img[y0 : y0 + 420, x0 : x0 + 420] += visible[..., None] * col * a * 0.9
        if 0 < barrido < 1:
            yb = y0 + corte
            img[max(0, yb - 3) : yb + 3, x0 - 20 : x0 + 440] += mezcla(P["rio"], BL, 0.6) * 0.8 * a
        rotulo(img, "huellas dactilares", 220, 790, 30, GRIS, a, nombre="Inter-Regular.ttf")
        # dos bases de datos sin cruzar
        b = aparece(t, m(6) + 1.6, 0.6)
        img = panel(img, 900, 220, 1780, 420, b)
        rotulo(img, "Eurodac", 950, 300, 52, BL, b)
        rotulo(img, "solicitantes de asilo de la UE · desde 2013", 952, 360, 28, GRIS, b, nombre="Inter-Regular.ttf")
        c = aparece(t, m(7) + 0.1, 0.6)
        rotulo(img, "el dato existía", 950, 520, 44, BL, c)
        d = aparece(t, m(8) + 0.1, 0.6)
        img = panel(img, 900, 640, 1780, 840, d)
        rotulo(img, "historial en Grecia", 950, 720, 44, BL, d)
        rotulo(img, "condena en Corfú", 952, 778, 28, GRIS, d, nombre="Inter-Regular.ttf")
        tr = DG.Trazo()
        tr.tinta(P["rojo"], d)
        tr.c.set_dash([10, 12])
        DG.linea(tr.c, [(1340, 425), (1340, 520)], d, 4)
        DG.linea(tr.c, [(1340, 560), (1340, 635)], d, 4)
        tr.c.set_dash([])
        DG.cruz(tr.c, 1340, 540, 34, 6)
        img = DG.componer_relieve(tr, img, sombra=0.2, brillo=0.3, col_brillo=P["rojo"])
        rotulo(img, "nadie los cruzó", 1380, 552, 30, P["rojo"] * 0.5 + BL * 0.5, d)
        return lento(img, t - m(6), self.d - m(6), 1.0, 1.03)

    def cuadro(self, t: float) -> np.ndarray:
        return por_segmentos(self.seg, (self._grecia, self._foto_corfu, self._viaje, self._eurodac), t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("viento", 0.0, sfx.viento(self.m(6), 461, 0.4), -10, 1.5, 1.5)
        m.agregar("whoosh", self.m(4) + 1.1, sfx.whoosh(1.4, 462), -6)
        m.agregar("escáner", self.m(6) + 0.2, SN.escaner(463, 2.2), -2)
        m.agregar("zumbido", self.m(6) - 0.3, sfx.zumbido_electronico(d - self.m(6) + 0.3, 464), -16, 1.0, 1.0)
        return m.x[:n]


# =========================================================================== 4.7


class Sub47(Subescena):
    """El país partido en dos; el Tagesschau; la AfD; Merkel; la sentencia del 22 de marzo de 2018."""

    cine = CINE

    def preparar(self) -> None:
        s = self.T.oraciones
        self.fondo = fondo()
        self.tages = abrir("4.7_tagesschau.jpg")
        self.merkel = Foto("4.7_merkel.jpg")
        self.sentencia = abrir("4.7_sentencia.jpg")
        self.tribunal = Foto("4.5_tribunal_friburgo.jpg", P["piedra"], 0.06)
        # «El caso partió a Alemania en dos» dura menos de dos segundos: el mapa partido se queda un poco más
        self.seg = Segmentos([max(s[1] + 1.0, 3.0), s[4] - 0.1, s[5] - 0.1], 1.0)

    def _partido(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        abre = suave(lim((t - 1.0) / 1.8))
        for lado in (-1, 1):
            tr = DG.Trazo()
            c = tr.c
            c.save()
            c.translate(lado * 40 * abre, 0)
            tr.tinta(mezcla(P["verde"], BL, 0.15), 0.95)
            k = 78.0
            pts = [(960 + (lon - 10.4) * k * math.cos(math.radians(51)), 560 - (lat - 51.2) * k) for lon, lat in G.ALEMANIA]
            c.new_path()
            # recorte: la mitad oeste o la este de una grieta en zigzag
            grieta = [(980, 0), (950, 300), (990, 470), (940, 640), (985, 820), (955, H)]
            if lado < 0:
                c.move_to(0, 0)
                for q in grieta:
                    c.line_to(*q)
                c.line_to(0, H)
            else:
                c.move_to(W, 0)
                for q in grieta:
                    c.line_to(*q)
                c.line_to(W, H)
            c.close_path()
            c.clip()
            D.rellenar(c, pts, suave=False)
            c.restore()
            img = DG.componer_relieve(tr, img, sombra=0.5)
        rotulo(img, "ALEMANIA · DICIEMBRE DE 2016", W / 2, 150, 28, GRIS, aparece(t, 0.3, 0.8), alinear="centro")
        return lento(img, t, max(self.m(1) + 1.5, 3.5), 1.0, 1.04)

    def _tele(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        m = self.m
        a = aparece(t, m(1) - 0.1, 0.6)
        if self.tages is not None:
            img = imagen_flotante(img, self.tages, 620, 470, 540, a, 1.0 + 0.03 * lim((t - m(1)) / 8), 0.6)
        img = panel(img, 1120, 200, 1820, 740, a)
        rotulo(img, "Tagesschau", 1170, 280, 48, BL, a)
        rotulo(img, "el noticiero más visto", 1172, 330, 28, GRIS, a, nombre="Inter-Regular.ttf")
        rotulo(img, "el primer día no dio", 1170, 430, 34, BL, aparece(t, m(1) + 1.5, 0.6))
        rotulo(img, "la noticia del arresto", 1170, 478, 34, BL, aparece(t, m(1) + 1.5, 0.6))
        rotulo(img, "«noticia regional»", 1170, 556, 34, mezcla(P["piedra"], BL, 0.6), aparece(t, m(1) + 3.2, 0.6))
        rotulo(img, "acusado de esconder el caso", 1170, 680, 34, P["rojo"] * 0.4 + BL * 0.6, aparece(t, m(2) + 0.2, 0.6))
        b = aparece(t, m(3) + 0.1, 0.6)
        img = panel(img, 120, 820, 1100, 1010, b)
        rotulo(img, "AfD", 170, 905, 50, BL, b, nombre="Inter-Bold.ttf")
        rotulo(img, "partido antiinmigración", 290, 900, 34, BL, b)
        rotulo(img, "lo usó como prueba de sus advertencias", 172, 960, 28, GRIS, b, nombre="Inter-Regular.ttf")
        return img

    def _merkel(self, t: float) -> np.ndarray:
        m = self.m
        z, cx, cy = recorrido(t - m(4), m(5) - m(4) + 1.0, 1.0, 1.06, (0.56, 0.55), (0.56, 0.5))
        img = self.merkel.ver(z, cx, cy)
        a = aparece(t, m(4) + 0.4, 0.6)
        img = panel(img, 80, H - 300, 1100, H - 80, a)
        rotulo(img, "ANGELA MERKEL · CANCILLER", 130, H - 226, 24, GRIS, a)
        rotulo(img, "«debe ser condenado", 128, H - 166, 46, BL, a)
        rotulo(img, "como cualquier otro asesino»", 128, H - 112, 46, BL, a)
        return img

    def _sentencia(self, t: float) -> np.ndarray:
        m = self.m
        z, cx, cy = recorrido(t - m(5), self.d - m(5), 1.04, 1.1, (0.5, 0.45), (0.5, 0.35))
        img = self.tribunal.ver(z, cx, cy) * 0.55
        img = cv2.GaussianBlur(img, (0, 0), 6)
        a = aparece(t, m(5) - 0.1, 0.6)
        img = panel(img, 120, 140, 900, 420, a)
        rotulo(img, "TRIBUNAL DE FRIBURGO", 170, 220, 24, GRIS, a)
        rotulo(img, "22 de marzo de 2018", 168, 300, 56, BL, a)
        rotulo(img, "juzgado como adulto", 170, 366, 32, GRIS, aparece(t, m(5) + 1.2, 0.6), nombre="Inter-Regular.ttf")
        b = aparece(t, m(6) + 0.1, 0.6)
        if self.sentencia is not None:
            img = imagen_flotante(img, self.sentencia, 1360, 470, 560, b, 1.0 + 0.03 * lim((t - m(6)) / 6), 0.6)
        img = panel(img, 120, 520, 900, 900, b)
        rotulo(img, "cadena perpetua", 170, 610, 56, BL, b)
        rotulo(img, "violación agravada y asesinato", 172, 680, 30, GRIS, b, nombre="Inter-Regular.ttf")
        rotulo(img, "y detención preventiva", 170, 790, 40, BL, aparece(t, m(6) + 2.2, 0.6))
        rotulo(img, "después de cumplirla", 172, 845, 30, GRIS, aparece(t, m(6) + 2.6, 0.6), nombre="Inter-Regular.ttf")
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return por_segmentos(self.seg, (self._partido, self._tele, self._merkel, self._sentencia), t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("grieta", 0.9, sfx.golpe_sordo(471), -6)
        m.agregar("murmullo", self.m(5) - 0.4, SN.murmullo(d - self.m(5) + 0.4, 472), -8, 1.0, 1.5)
        m.agregar("mazo", self.m(6) + 0.2, SN.mazo(473), 0)
        return m.x[:n]


# =========================================================================== registro

SUBESCENAS = {"4.0": Sub40, "4.1": Sub41, "4.2": Sub42, "4.3": Sub43, "4.4": Sub44, "4.5": Sub45, "4.6": Sub46, "4.7": Sub47}

# Fotogramas clave para revisar antes del render completo: (archivo, clip, tiempo en el clip)
REVISION = [
    ("1_dreisam_dia.png", "4.0", lambda T: T.oraciones[2] + 1.0),
    ("2_acelerometro.png", "4.1", lambda T: T.oraciones[3] + 3.0),
    ("3_orilla_sin_escaleras.png", "4.3", lambda T: T.oraciones[2] + 1.5),
    ("4_corfu_friburgo.png", "4.6", lambda T: T.oraciones[5] + 0.8),
]


def clips() -> list[str]:
    return ["titulo"] + [s.id for s in guion.leer()[NUMERO].subescenas]


def crear(id_: str) -> Subescena:
    if id_ == "titulo":
        return titulo()
    return SUBESCENAS[id_](id_, tiempos(id_))
