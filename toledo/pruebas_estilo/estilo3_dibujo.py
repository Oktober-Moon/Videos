"""Prueba de estilo 3: ilustración dibujada con código, con mucho detalle.

La misma calle y el mismo tranvía que el estilo 2 (`calle_datos.py`), pero dibujados como
ilustración vectorial: cada cosa es un polígono en perspectiva con su degradado y su línea, en vez
de un render 3D. Se proyecta la calle con una cámara de agujero (pinhole) y se pinta de lo lejano a
lo cercano. La hora azul se cuenta con luces: faroles, vitrinas, ventanas encendidas, los faros del
tranvía y sus reflejos alargados en el empedrado mojado.

Uso: python pruebas_estilo/estilo3_dibujo.py [cuadro]  -> revision/estilos/estilo3_dibujo.mp4 (o un .png)
"""

from __future__ import annotations

import math
import random
import subprocess
import sys
from pathlib import Path

import cairo
import cv2
import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import calle_datos as C  # noqa: E402

W, H = 1920, 1080
FOCAL = C.LENTE / 36.0 * W
SALIDA = AQUI.parent / "revision" / "estilos"
NIEBLA = np.array([0.17, 0.18, 0.26])
CALIDO = (1.0, 0.70, 0.40)
AMBIENTE = np.array([0.40, 0.43, 0.52])      # luz de cielo de la hora azul sobre las superficies

EDIFICIOS = C.edificios()
FAROLES = C.faroles()


# --------------------------------------------------------------------------- cámara

class Camara:
    def __init__(self, t: float):
        c, f, r, u = C.camara_base(t)
        self.c, self.f, self.r, self.u = c, f, r, u

    def a_cam(self, p):
        dx, dy, dz = p[0] - self.c[0], p[1] - self.c[1], p[2] - self.c[2]
        r, u, f = self.r, self.u, self.f
        return (dx * r[0] + dy * r[1] + dz * r[2], dx * u[0] + dy * u[1] + dz * u[2],
                dx * f[0] + dy * f[1] + dz * f[2])

    @staticmethod
    def a_pantalla(q):
        return (W / 2 + FOCAL * q[0] / q[2], H / 2 - FOCAL * q[1] / q[2])

    def punto(self, p):
        q = self.a_cam(p)
        return None if q[2] < 0.15 else self.a_pantalla(q)

    def poligono(self, pts):
        q = recortar([self.a_cam(p) for p in pts], 0.15)
        return [self.a_pantalla(v) for v in q]

    def distancia(self, p) -> float:
        return math.dist(p, self.c)

    def escala(self, p) -> float:
        """Píxeles por metro a la distancia de p."""
        q = self.a_cam(p)
        return FOCAL / max(q[2], 0.15)


def recortar(q, cerca):
    """Recorta un polígono (en coordenadas de cámara) contra el plano z = cerca."""
    out = []
    n = len(q)
    for i in range(n):
        a, b = q[i], q[(i + 1) % n]
        ina, inb = a[2] >= cerca, b[2] >= cerca
        if ina:
            out.append(a)
        if ina != inb:
            t = (cerca - a[2]) / (b[2] - a[2])
            out.append(tuple(a[k] + (b[k] - a[k]) * t for k in range(3)))
    return out


def nb(color, d: float):
    """Mezcla con la neblina según la distancia (perspectiva aérea)."""
    k = 1 - math.exp(-d * 0.0105)
    c = np.asarray(color, float)
    return tuple(c * (1 - k) + NIEBLA * k)


# --------------------------------------------------------------------------- pintura

def trazar(ctx, pts):
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def llenar(ctx, pts, color, alfa=1.0):
    if len(pts) < 3:
        return
    trazar(ctx, pts)
    ctx.set_source_rgba(*color, alfa)
    ctx.fill()


def degradado(ctx, pts, p0, p1, c0, c1, a0=1.0, a1=1.0):
    if len(pts) < 3 or p0 is None or p1 is None:
        return
    g = cairo.LinearGradient(*p0, *p1)
    g.add_color_stop_rgba(0, *c0, a0)
    g.add_color_stop_rgba(1, *c1, a1)
    trazar(ctx, pts)
    ctx.set_source(g)
    ctx.fill()


def linea(ctx, a, b, color, ancho, alfa=1.0):
    if a is None or b is None:
        return
    ctx.move_to(*a)
    ctx.line_to(*b)
    ctx.set_source_rgba(*color, alfa)
    ctx.set_line_width(ancho)
    ctx.stroke()


def resplandor(ctx, centro, radio, color, alfa, achatado=1.0):
    """Mancha de luz radial; `achatado` < 1 la aplasta en vertical (luz sobre el piso)."""
    if centro is None or radio < 0.5:
        return
    ctx.save()
    ctx.translate(*centro)
    ctx.scale(1.0, achatado)
    g = cairo.RadialGradient(0, 0, 0, 0, 0, radio)
    g.add_color_stop_rgba(0, *color, alfa)
    g.add_color_stop_rgba(0.35, *color, alfa * 0.45)
    g.add_color_stop_rgba(1, *color, 0)
    ctx.set_source(g)
    ctx.arc(0, 0, radio, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


def sombrear(color, luz=AMBIENTE):
    return tuple(np.asarray(color) * luz)


# --------------------------------------------------------------------------- cielo y piso

def cielo(ctx, cam):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0.0, 0.03, 0.05, 0.13)
    g.add_color_stop_rgb(0.45, 0.10, 0.11, 0.22)
    g.add_color_stop_rgb(0.62, 0.30, 0.22, 0.28)
    g.add_color_stop_rgb(1.0, 0.30, 0.22, 0.28)
    ctx.rectangle(0, 0, W, H)
    ctx.set_source(g)
    ctx.fill()
    fuga = cam.punto((0.0, 600.0, 3.0))
    resplandor(ctx, fuga, 700, (0.85, 0.48, 0.32), 0.45, 0.55)


CHARCOS = [(random.Random(5 + i).uniform(-2.8, 2.8), random.Random(50 + i).uniform(2, 70),
            random.Random(90 + i).uniform(0.4, 1.5), random.Random(130 + i).uniform(0.3, 0.9)) for i in range(26)]


def piso(ctx, cam, brillo):
    y0, y1 = C.Y_MIN, C.Y_MAX
    calzada = cam.poligono([(-C.BORDILLO, y0, 0), (C.BORDILLO, y0, 0), (C.BORDILLO, y1, 0), (-C.BORDILLO, y1, 0)])
    degradado(ctx, calzada, (0, H), (0, H * 0.55), (0.11, 0.11, 0.13), nb((0.09, 0.09, 0.12), 120))
    for lado in (-1, 1):
        xa, xb = lado * (C.BORDILLO + 0.22), lado * C.FACHADA
        acera = cam.poligono([(xa, y0, C.ACERA_ALTO), (xb, y0, C.ACERA_ALTO), (xb, y1, C.ACERA_ALTO), (xa, y1, C.ACERA_ALTO)])
        degradado(ctx, acera, (0, H), (0, H * 0.55), (0.17, 0.17, 0.19), nb((0.13, 0.13, 0.16), 120))
        tope = cam.poligono([(lado * C.BORDILLO, y0, 0.14), (lado * (C.BORDILLO + 0.22), y0, 0.14),
                             (lado * (C.BORDILLO + 0.22), y1, 0.14), (lado * C.BORDILLO, y1, 0.14)])
        llenar(ctx, tope, (0.30, 0.30, 0.32))
        if lado < 0:                                           # cara del bordillo que mira a la cámara
            llenar(ctx, cam.poligono([(-C.BORDILLO, y0, 0), (-C.BORDILLO, y1, 0), (-C.BORDILLO, y1, 0.14),
                                      (-C.BORDILLO, y0, 0.14)]), (0.20, 0.20, 0.22))
    # charcos: espejos de cielo
    for x, y, rx, ry in CHARCOS:
        pts = cam.poligono([(x + rx * math.cos(a), y + ry * math.sin(a) * 2.4, 0.002)
                            for a in np.linspace(0, 2 * math.pi, 20, endpoint=False)])
        llenar(ctx, pts, nb((0.17, 0.16, 0.25), cam.distancia((x, y, 0))), 0.5)
    adoquines(ctx, cam)
    losas(ctx, cam)
    # rieles: cabeza brillante (refleja el cielo) y ranura oscura
    for x in (-C.ANCHO_VIA / 2, C.ANCHO_VIA / 2):
        for dx, color, a in ((-math.copysign(0.05, x), (0.02, 0.02, 0.03), 0.9), (0.0, (0.55, 0.55, 0.65), 0.95)):
            pts = cam.poligono([(x + dx - 0.03, y0, 0.003), (x + dx + 0.03, y0, 0.003),
                                (x + dx + 0.03, y1, 0.003), (x + dx - 0.03, y1, 0.003)])
            llenar(ctx, pts, color, a)


def adoquines(ctx, cam):
    """Juntas del empedrado: filas a lo ancho y juntas verticales trabadas, solo donde se ven."""
    fila = 0.125
    k0 = int(math.floor(max(C.Y_MIN, cam.c[1] - 1) / fila))
    previa = None
    for k in range(k0, k0 + 1600):
        y = k * fila
        a, b = cam.punto((-C.BORDILLO, y, 0)), cam.punto((C.BORDILLO, y, 0))
        if a is None or b is None:
            continue
        if previa is not None and abs(previa - a[1]) < 2.2:
            break
        sep = abs(previa - a[1]) if previa is not None else 99
        previa = a[1]
        linea(ctx, a, b, (0.035, 0.035, 0.045), 1.0 if sep < 8 else 1.6, min(0.9, sep / 10))
        if sep > 5:
            n = int(2 * C.BORDILLO / 0.21)
            off = 0.105 * (k % 2)
            for j in range(n):
                x = -C.BORDILLO + off + j * 0.21
                linea(ctx, cam.punto((x, y, 0)), cam.punto((x, y + fila, 0)), (0.035, 0.035, 0.045), 1.0,
                      min(0.8, sep / 14))
                if sep > 11 and (j + k) % 3 == 0:                  # brillo de agua en el canto de la piedra
                    linea(ctx, cam.punto((x + 0.03, y + 0.02, 0)), cam.punto((x + 0.15, y + 0.02, 0)),
                          (0.45, 0.47, 0.6), 1.2, 0.25)


def losas(ctx, cam):
    for lado in (-1, 1):
        xa, xb = lado * (C.BORDILLO + 0.22), lado * C.FACHADA
        previa = None
        for k in range(int(C.Y_MIN / 0.6), int(C.Y_MAX / 0.6)):
            y = k * 0.6
            a, b = cam.punto((xa, y, C.ACERA_ALTO)), cam.punto((xb, y, C.ACERA_ALTO))
            if a is None or b is None:
                continue
            if previa is not None and abs(previa - a[1]) < 2.5 and y > cam.c[1]:
                break
            previa = a[1]
            linea(ctx, a, b, (0.08, 0.08, 0.1), 1.0, 0.5)
        x = xa
        while abs(x) < C.FACHADA:
            linea(ctx, cam.punto((x, max(C.Y_MIN, cam.c[1] + 0.5), C.ACERA_ALTO)), cam.punto((x, 90, C.ACERA_ALTO)),
                  (0.08, 0.08, 0.1), 1.0, 0.4)
            x += lado * 0.6


def reflejo(ctx, cam, p, color, ancho_m, alfa):
    """Reflejo alargado de una luz en el piso mojado: va del pie de la luz hacia la cámara."""
    pie = cam.punto((p[0], p[1], 0.0))
    imagen = cam.punto((p[0], p[1], -p[2]))
    if pie is None or imagen is None:
        return
    largo = (imagen[1] - pie[1]) * 1.25
    ancho = max(2.0, ancho_m * cam.escala(p))
    ctx.save()
    ctx.translate(pie[0], pie[1] + largo * 0.45)
    ctx.scale(ancho / max(largo, 1.0), 1.0)
    g = cairo.RadialGradient(0, 0, 0, 0, 0, largo * 0.55)
    g.add_color_stop_rgba(0, *color, alfa)
    g.add_color_stop_rgba(0.5, *color, alfa * 0.4)
    g.add_color_stop_rgba(1, *color, 0)
    ctx.set_source(g)
    ctx.arc(0, 0, largo * 0.55, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


def luces_en_piso(ctx, cam, yf):
    ctx.save()
    ctx.set_operator(cairo.OPERATOR_ADD)
    for lado, y in FAROLES:
        x = lado * (C.FACHADA - 0.95)
        c = cam.punto((x, y, 0.0))
        if c is None:
            continue
        s = cam.escala((x, y, 0))
        a = cam.punto((x, y + 1, 0))
        achat = min(1.0, abs(a[1] - c[1]) / max(s, 1e-3) + 0.05) if a else 0.3
        t = math.exp(-cam.distancia((x, y, 0)) * 0.02)
        resplandor(ctx, c, 5.5 * s, CALIDO, 0.20 * t, achat)
        reflejo(ctx, cam, (x, y, 4.35), CALIDO, 0.5, 0.55 * t)
    for e in EDIFICIOS:
        ancho_v = min(e.ancho * 0.62, 6.0)
        p = (e.x - e.lado * 0.05, e.y0 + e.ancho / 2 - 0.6, 2.2)
        if 0 < p[1] - cam.c[1] < 70:
            reflejo(ctx, cam, p, (1.0, 0.80, 0.55), ancho_v * 0.8, 0.22 * math.exp(-cam.distancia(p) * 0.03))
    # faros del tranvía: charco de luz delante y dos reflejos largos
    c = cam.punto((0, yf - 5.0, 0))
    if c is not None:
        s = cam.escala((0, yf - 5.0, 0))
        resplandor(ctx, c, 6.0 * s, (1.0, 0.95, 0.85), 0.28, 0.35)
    for x in (-0.78, 0.78):
        reflejo(ctx, cam, (x, yf + 0.1, 0.875), (1.0, 0.96, 0.9), 0.35, 0.8)
    reflejo(ctx, cam, (0, yf + 0.5, 3.0), (1.0, 0.6, 0.15), 1.4, 0.35)
    ctx.restore()


# --------------------------------------------------------------------------- casas

def rect_fachada(cam, e, ya, yb, za, zb, sale=0.0):
    x = e.x - e.lado * sale
    return cam.poligono([(x, ya, za), (x, yb, za), (x, yb, zb), (x, ya, zb)])


def casa(ctx, glow, cam, e: C.Edificio):
    s, fx = e.lado, e.x
    y0, y1 = e.y0, e.y0 + e.ancho
    ym = (y0 + y1) / 2
    d = cam.distancia((fx, ym, e.alto / 2))
    if y1 < cam.c[1] - 2:
        return
    px_alto = e.alto * cam.escala((fx, ym, e.alto / 2))
    detalle = px_alto > 60
    col = lambda c: nb(sombrear(c), d)  # noqa: E731

    # tejado: silueta contra el cielo (desde la calle se ve el contorno, no las tejas)
    vuelo = 0.5
    ef, cx_, atras = fx - s * vuelo, fx + s * e.fondo / 2, fx + s * (e.fondo + vuelo)
    zc = e.alto + e.tejado
    pts3 = [(ef, y0, e.alto - 0.12), (ef, y1, e.alto - 0.12), (cx_, y0, zc), (cx_, y1, zc), (atras, y0, e.alto - 0.12), (atras, y1, e.alto - 0.12)]
    pp = [cam.punto(p) for p in pts3]
    if all(p is not None for p in pp):
        casco = cv2.convexHull(np.array(pp, np.float32)).reshape(-1, 2).tolist()
        llenar(ctx, casco, nb((0.11, 0.06, 0.06), d))
        linea(ctx, pp[2], pp[3], nb((0.2, 0.13, 0.12), d), 1.2)
    # pared lateral (testero) que asoma por encima de la casa vecina más baja
    testero = cam.poligono([(fx, y0, 0), (fx + s * e.fondo, y0, 0), (fx + s * e.fondo, y0, e.alto), (cx_, y0, zc), (fx, y0, e.alto)])
    llenar(ctx, testero, col(np.asarray(e.color) * 0.72))
    # fachada: más clara arriba (cielo) y algo más oscura a media altura
    fach = rect_fachada(cam, e, y0, y1, 0, e.alto)
    arriba, abajo = cam.punto((fx, ym, e.alto)), cam.punto((fx, ym, 0))
    degradado(ctx, fach, arriba, abajo, col(np.asarray(e.color) * 1.12), col(np.asarray(e.color) * 0.82))
    # luz de los faroles sobre esta fachada
    if fach:
        ctx.save()
        trazar(ctx, fach)
        ctx.clip()
        ctx.set_operator(cairo.OPERATOR_ADD)
        for lado, yl in FAROLES:
            if lado != s or not (y0 - 9 < yl < y1 + 9):
                continue
            c = cam.punto((fx, yl, 4.2))
            if c is not None:
                resplandor(ctx, c, 5.0 * cam.escala((fx, yl, 4.2)), CALIDO, 0.38)
        # la vitrina ilumina la parte baja
        c = cam.punto((fx, ym - 0.6, 1.8))
        if c is not None:
            resplandor(ctx, c, 3.5 * cam.escala((fx, ym, 1.8)), (1.0, 0.8, 0.55), 0.22)
        ctx.restore()
    if d > 150:
        for yc_, z, w, h, luz in e.ventanas():
            llenar(ctx, rect_fachada(cam, e, yc_ - w / 2, yc_ + w / 2, z, z + h), (0.9, 0.62, 0.35) if luz else col((0.12, 0.13, 0.2)))
        return

    # zócalo de arenisca roja y cornisas
    llenar(ctx, rect_fachada(cam, e, y0, y1, 0, 0.9, 0.06), col((0.48, 0.28, 0.22)))
    for z, alto, sale in [(C.PISO_BAJO - 0.16, 0.22, 0.1)] + [(C.PISO_BAJO + p * C.PISO + 0.14, 0.12, 0.05) for p in range(1, e.pisos)] + [(e.alto - 0.31, 0.32, 0.22)]:
        llenar(ctx, rect_fachada(cam, e, y0, y1, z, z + alto, sale), col(np.asarray(e.color) * 1.18))
        if detalle:
            linea(ctx, cam.punto((fx - s * sale, y0, z)), cam.punto((fx - s * sale, y1, z)), col(np.asarray(e.color) * 0.45), 1.2)

    # ventanas
    for yc_, z, w, h, luz in e.ventanas():
        if detalle:
            llenar(ctx, rect_fachada(cam, e, yc_ - w / 2 - 0.12, yc_ + w / 2 + 0.12, z - 0.12, z + h + 0.12, 0.06), col((0.86, 0.85, 0.82)))
        vid = rect_fachada(cam, e, yc_ - w / 2, yc_ + w / 2, z, z + h, 0.04)
        a, b = cam.punto((fx, yc_, z + h)), cam.punto((fx, yc_, z))
        if luz:
            degradado(ctx, vid, a, b, (1.0, 0.78, 0.48), (0.78, 0.45, 0.22))
            if detalle:                                                        # cortinas
                for lado_c in (-1, 1):
                    llenar(ctx, rect_fachada(cam, e, yc_ + lado_c * w / 2 - (w * 0.22 if lado_c > 0 else 0),
                                             yc_ + lado_c * w / 2 + (w * 0.22 if lado_c < 0 else 0), z, z + h, 0.045),
                           (0.95, 0.85, 0.65), 0.45)
            c = cam.punto((fx - s * 0.1, yc_, z + h / 2))
            resplandor(glow, c, 1.2 * cam.escala((fx, yc_, z)), (1.0, 0.7, 0.4), 0.28 * math.exp(-d * 0.02))
        else:
            degradado(ctx, vid, a, b, nb((0.16, 0.18, 0.30), d), nb((0.04, 0.05, 0.09), d))
            if detalle:                                                        # reflejo del cielo, en diagonal
                llenar(ctx, cam.poligono([(fx - s * 0.05, yc_ - w * 0.3, z + h), (fx - s * 0.05, yc_ - w * 0.05, z + h),
                                          (fx - s * 0.05, yc_ + w * 0.45, z + h * 0.35), (fx - s * 0.05, yc_ + w * 0.2, z + h * 0.35)]),
                       (0.55, 0.6, 0.8), 0.12)
        if detalle:
            cm = col((0.86, 0.85, 0.82))
            ancho = max(1.0, 0.05 * cam.escala((fx, yc_, z)))
            linea(ctx, cam.punto((fx - s * 0.05, yc_, z)), cam.punto((fx - s * 0.05, yc_, z + h)), cm, ancho)
            linea(ctx, cam.punto((fx - s * 0.05, yc_ - w / 2, z + h * 0.62)), cam.punto((fx - s * 0.05, yc_ + w / 2, z + h * 0.62)), cm, ancho)
            llenar(ctx, rect_fachada(cam, e, yc_ - w / 2 - 0.15, yc_ + w / 2 + 0.15, z - 0.11, z - 0.01, 0.1), col((0.55, 0.36, 0.3)))
            if e.postigos:
                for lado_p in (-1, 1):
                    yc2 = yc_ + lado_p * (w / 2 + 0.42)
                    llenar(ctx, rect_fachada(cam, e, yc2 - 0.3, yc2 + 0.3, z - 0.02, z + h + 0.03, 0.08), col(np.asarray(e.postigos) * 1.3))
                    for k in range(1, 9):                                  # tablillas
                        zz = z + h * k / 9
                        linea(ctx, cam.punto((fx - s * 0.09, yc2 - 0.27, zz)), cam.punto((fx - s * 0.09, yc2 + 0.27, zz)),
                              col(np.asarray(e.postigos) * 0.6), 1.0, 0.8)

    # planta baja: vitrina encendida, puerta y toldo
    ancho_v = min(e.ancho * 0.62, 6.0)
    yv = ym - 0.6
    llenar(ctx, rect_fachada(cam, e, yv - ancho_v / 2 - 0.14, yv + ancho_v / 2 + 0.14, 0.9, 3.46, 0.05), col((0.10, 0.10, 0.11)))
    vit = rect_fachada(cam, e, yv - ancho_v / 2, yv + ancho_v / 2, 1.0, 3.3, 0.06)
    degradado(ctx, vit, cam.punto((fx, yv, 3.3)), cam.punto((fx, yv, 1.0)), (1.0, 0.86, 0.62), (0.85, 0.55, 0.30))
    if detalle:
        for k in (1, 2):                                                     # repisas y objetos a contraluz
            zz = 1.0 + k * 0.75
            linea(ctx, cam.punto((fx - s * 0.07, yv - ancho_v / 2, zz)), cam.punto((fx - s * 0.07, yv + ancho_v / 2, zz)), (0.45, 0.28, 0.16), 1.2, 0.8)
        rng = random.Random(int(e.y0 * 10) + s)
        for _ in range(int(ancho_v * 2)):
            yy, hh, ww = rng.uniform(yv - ancho_v / 2 + 0.2, yv + ancho_v / 2 - 0.2), rng.uniform(0.15, 0.55), rng.uniform(0.1, 0.3)
            zz = 1.0 + rng.choice([0, 0.75, 1.5])
            llenar(ctx, rect_fachada(cam, e, yy - ww / 2, yy + ww / 2, zz, zz + hh, 0.08), (0.42, 0.26, 0.18), 0.55)
        for k in range(1, 3):
            yy = yv - ancho_v / 2 + ancho_v * k / 3
            linea(ctx, cam.punto((fx - s * 0.07, yy, 1.0)), cam.punto((fx - s * 0.07, yy, 3.3)), (0.12, 0.1, 0.1), max(1.0, 0.06 * cam.escala((fx, yy, 2))))
    c = cam.punto((fx - s * 0.3, yv, 2.1))
    resplandor(glow, c, 2.6 * cam.escala((fx, yv, 2.1)), (1.0, 0.8, 0.55), 0.22 * math.exp(-d * 0.02))
    yp = ym + ancho_v / 2 + 0.3
    llenar(ctx, rect_fachada(cam, e, yp - 0.55, yp + 0.55, 0.0, 2.3, 0.03), col((0.18, 0.12, 0.09)))
    if e.toldo:
        a0, a1 = yv - ancho_v / 2 - 0.15, yv + ancho_v / 2 + 0.15
        n = max(2, int((a1 - a0) * 4.4))
        for k in range(n):
            ya, yb = a0 + (a1 - a0) * k / n, a0 + (a1 - a0) * (k + 1) / n
            tela = np.asarray(e.toldo) if k % 2 == 0 else np.array([0.85, 0.83, 0.78])
            arriba = cam.poligono([(fx, ya, 3.55), (fx, yb, 3.55), (fx - s * 1.5, yb, 2.95), (fx - s * 1.5, ya, 2.95)])
            llenar(ctx, arriba, nb(tela * np.array([0.55, 0.52, 0.55]), d))       # por debajo: sombra
            caida = cam.poligono([(fx - s * 1.5, ya, 2.95), (fx - s * 1.5, yb, 2.95), (fx - s * 1.5, yb, 2.67), (fx - s * 1.5, ya, 2.67)])
            llenar(ctx, caida, nb(tela * np.array([0.62, 0.6, 0.62]) + 0.05, d))
    # contorno de la casa
    if detalle and fach:
        trazar(ctx, fach)
        ctx.set_source_rgba(0.04, 0.04, 0.06, 0.5)
        ctx.set_line_width(1.0)
        ctx.stroke()


def farol(ctx, glow, cam, lado, y):
    fx = lado * C.FACHADA
    cx = fx - lado * 0.95
    s = cam.escala((cx, y, 4.4))
    if cam.punto((cx, y, 4.4)) is None:
        return
    oscuro = (0.04, 0.04, 0.05)
    linea(ctx, cam.punto((fx, y, 4.9)), cam.punto((cx, y, 4.9)), oscuro, max(1.0, 0.05 * s))
    linea(ctx, cam.punto((fx, y, 4.45)), cam.punto((fx - lado * 0.6, y, 4.88)), oscuro, max(1.0, 0.035 * s))
    linea(ctx, cam.punto((cx, y, 4.9)), cam.punto((cx, y, 4.62)), oscuro, max(1.0, 0.04 * s))
    cuerpo = cam.poligono([(cx, y - 0.13, 4.18), (cx, y + 0.13, 4.18), (cx, y + 0.17, 4.6), (cx, y - 0.17, 4.6)])
    llenar(ctx, cuerpo, (1.0, 0.86, 0.62))
    techo = cam.poligono([(cx, y - 0.2, 4.6), (cx, y + 0.2, 4.6), (cx, y, 4.75)])
    llenar(ctx, techo, oscuro)
    if cuerpo:
        trazar(ctx, cuerpo)
        ctx.set_source_rgba(*oscuro, 1)
        ctx.set_line_width(max(1.0, 0.02 * s))
        ctx.stroke()
    c = cam.punto((cx, y, 4.4))
    t = math.exp(-cam.distancia((cx, y, 4.4)) * 0.02)          # la neblina se come el brillo lejano
    resplandor(glow, c, 1.8 * s, CALIDO, 0.85 * t)
    resplandor(glow, c, 0.5 * s, (1.0, 0.9, 0.75), 1.0 * t)


# --------------------------------------------------------------------------- tranvía

AZUL = np.array([0.05, 0.20, 0.55])
VERDE = np.array([0.0, 0.48, 0.30])


def tranvia(ctx, glow, cam, yf, espejo=False):
    zs = -1.0 if espejo else 1.0
    P = lambda x, y, z: (x, y, zs * z)  # noqa: E731
    tramos = C.tramos_y()
    n = len(tramos)
    base, techo = C.BASE_T, C.BASE_T + C.ALTO_T
    luz_cielo = np.array([0.55, 0.6, 0.78])
    if not espejo:                                          # sombra de contacto en el piso
        largo_total = tramos[-1][0] + tramos[-1][1]
        llenar(ctx, cam.poligono([(-1.35, yf - 0.2, 0.004), (1.35, yf - 0.2, 0.004), (1.35, yf + largo_total, 0.004),
                                  (-1.35, yf + largo_total, 0.004)]), (0.0, 0.0, 0.0), 0.65)
    for k in reversed(range(n)):
        y0, largo = tramos[k]
        a, b = yf + y0, yf + y0 + largo
        punta, cola = k == 0, k == n - 1
        d = cam.distancia((1.15, (a + b) / 2, 1.8))
        sc = cam.escala((1.15, a, 1.8))
        # fuelle hacia el tramo siguiente
        if not cola:
            llenar(ctx, cam.poligono([P(1.03, b, 0.45), P(1.03, b + C.HUECO, 0.45), P(1.03, b + C.HUECO, 3.2), P(1.03, b, 3.2)]), (0.03, 0.03, 0.035))
        # costado derecho (el que ve la cámara)
        ya_b, ya_t = (a + 0.30, a + 0.65) if punta else (a, a)
        yb_b, yb_t = (b - 0.30, b - 0.65) if cola else (b, b)
        lado = cam.poligono([P(1.15, ya_b, base), P(1.15, yb_b, base), P(1.15, yb_t, techo), P(1.15, ya_t, techo)])
        degradado(ctx, lado, cam.punto(P(1.15, a, techo)), cam.punto(P(1.15, a, base)),
                  nb(AZUL * 0.75 + luz_cielo * 0.18, d), nb(AZUL * 0.42, d))
        x = 1.152
        # faldón y franja plateada
        llenar(ctx, cam.poligono([P(x, ya_b, base), P(x, yb_b, base), P(x, yb_b, 0.58), P(x, ya_b, 0.58)]), (0.025, 0.025, 0.03))
        llenar(ctx, cam.poligono([P(x, ya_b + 0.1, 1.465), P(x, yb_b - 0.1, 1.465), P(x, yb_b - 0.1, 1.565), P(x, ya_b + 0.1, 1.565)]),
               nb((0.62, 0.64, 0.7), d))
        # puertas dobles al centro de cada tramo y ventanas entre parantes
        yc = (a + b) / 2
        puerta = (yc - 0.7, yc + 0.7)
        inicio, fin = (a + 1.0, b - 1.0) if (punta or cola) else (a + 0.35, b - 0.35)
        ventanas = []
        y = inicio
        while y + 1.2 <= fin:
            ya, yb = y, min(y + 1.45, fin)
            if yb > puerta[0] - 0.1 and ya < puerta[1] + 0.1:
                y = puerta[1] + 0.25
                continue
            ventanas.append((ya, yb))
            y = yb + 0.25
        for ya, yb in ventanas:
            pts = cam.poligono([P(x, ya, 1.645), P(x, yb, 1.645), P(x, yb, 2.905), P(x, ya, 2.905)])
            degradado(ctx, pts, cam.punto(P(x, ya, 2.9)), cam.punto(P(x, ya, 1.65)), (0.98, 0.90, 0.72), (0.48, 0.38, 0.28))
            if not espejo:                                                 # pasamanos y respaldos a contraluz
                linea(ctx, cam.punto((x, ya, 2.55)), cam.punto((x, yb, 2.55)), (0.25, 0.2, 0.16), max(1.0, 0.03 * sc), 0.7)
                for q in np.arange(ya + 0.25, yb - 0.1, 0.48):
                    llenar(ctx, cam.poligono([(x, q, 1.65), (x, q + 0.28, 1.65), (x, q + 0.28, 1.98), (x, q, 1.98)]), (0.2, 0.14, 0.12), 0.7)
                llenar(ctx, cam.poligono([(x + 0.002, ya + 0.1, 2.905), (x + 0.002, ya + 0.45, 2.905), (x + 0.002, yb, 1.95), (x + 0.002, yb - 0.35, 1.95)]),
                       (0.8, 0.85, 1.0), 0.10)
        for lado_p in (-1, 1):                                             # puerta: dos hojas con vidrio
            y_a, y_b = (puerta[0], yc - 0.02) if lado_p < 0 else (yc + 0.02, puerta[1])
            llenar(ctx, cam.poligono([P(x, y_a, 0.45), P(x, y_b, 0.45), P(x, y_b, 2.98), P(x, y_a, 2.98)]), nb(AZUL * 0.35, d))
            pts = cam.poligono([P(x + 0.001, y_a + 0.08, 0.75), P(x + 0.001, y_b - 0.08, 0.75), P(x + 0.001, y_b - 0.08, 2.85), P(x + 0.001, y_a + 0.08, 2.85)])
            degradado(ctx, pts, cam.punto(P(x, y_a, 2.85)), cam.punto(P(x, y_a, 0.75)), (0.9, 0.82, 0.65), (0.35, 0.28, 0.22))
        if not espejo:
            linea(ctx, cam.punto((x, ya_t, techo - 0.02)), cam.punto((x, yb_t, techo - 0.02)), (0.6, 0.66, 0.85), max(1.0, 0.03 * sc), 0.6)
        if punta:
            frente(ctx, glow, cam, a, d, espejo, P)
        if k == 1 and not espejo:
            yp = (a + b) / 2
            negro = (0.03, 0.03, 0.04)
            codo = (0, yp + 1.0, 4.75)
            linea(ctx, cam.punto((0, yp - 0.4, techo + 0.1)), cam.punto(codo), negro, max(1.0, 0.06 * sc))
            linea(ctx, cam.punto(codo), cam.punto((0, yp - 0.1, 5.95)), negro, max(1.0, 0.05 * sc))
            linea(ctx, cam.punto((-0.8, yp - 0.1, 5.95)), cam.punto((0.8, yp - 0.1, 5.95)), negro, max(1.0, 0.05 * sc))


def frente(ctx, glow, cam, a, d, espejo, P):
    """Nariz del tranvía: parabrisas inclinado, letrero de destino, faros y la «sonrisa» plateada."""
    def F(u, v, sale=0.0):
        """u de −1 a 1 a lo ancho, v de 0 (abajo) a 1 (arriba) sobre la cara inclinada."""
        return P(u * (0.95 - 0.09 * v), a + 0.08 + 0.40 * v - sale, C.BASE_T + C.ALTO_T * v)

    def caja_f(u0, u1, v0, v1, sale=0.0):
        return cam.poligono([F(u0, v0, sale), F(u1, v0, sale), F(u1, v1, sale), F(u0, v1, sale)])

    v_vid0, v_vid1 = (1.275 - C.BASE_T) / C.ALTO_T, (2.945 - C.BASE_T) / C.ALTO_T
    llenar(ctx, caja_f(-1, 0, 0, v_vid0), nb(AZUL * 0.62, d))
    llenar(ctx, caja_f(0, 1, 0, v_vid0), nb(VERDE * 0.62, d))
    llenar(ctx, caja_f(-1, 1, v_vid1, 1), nb(AZUL * 0.55, d))
    llenar(ctx, caja_f(-1, 1, 0, 0.09), (0.03, 0.03, 0.035))
    # esquina redondeada (chaflán) entre el frente y el costado derecho
    for z0, z1, colr in ((C.BASE_T, 1.275, VERDE * 0.5), (1.275, 2.945, None), (2.945, C.BASE_T + C.ALTO_T, AZUL * 0.5)):
        v0, v1 = (z0 - C.BASE_T) / C.ALTO_T, (z1 - C.BASE_T) / C.ALTO_T
        q = lambda v, ext: (P(0.95 - 0.09 * v, a + 0.08 + 0.4 * v, C.BASE_T + C.ALTO_T * v) if not ext  # noqa: E731
                            else P(1.15 - 0.115 * v, a + 0.30 + 0.35 * v, C.BASE_T + C.ALTO_T * v))
        pts = cam.poligono([q(v0, False), q(v0, True), q(v1, True), q(v1, False)])
        if colr is None:
            degradado(ctx, pts, cam.punto(q(v1, False)), cam.punto(q(v0, False)), (0.25, 0.28, 0.38), (0.04, 0.05, 0.07))
        else:
            degradado(ctx, pts, cam.punto(q(v0, False)), cam.punto(q(v0, True)), nb(colr * 1.3, d), nb(colr, d))
    # parabrisas: oscuro, con el cielo reflejado arriba y el puesto del conductor apenas iluminado
    vid = caja_f(-0.97, 0.97, v_vid0, v_vid1, 0.005)
    degradado(ctx, vid, cam.punto(F(0, v_vid1)), cam.punto(F(0, v_vid0)), (0.17, 0.19, 0.30), (0.02, 0.02, 0.03))
    if espejo:
        return
    llenar(ctx, caja_f(-0.7, 0.2, v_vid0, v_vid0 + 0.12, 0.01), (0.55, 0.42, 0.3), 0.35)
    llenar(ctx, cam.poligono([F(-0.2, v_vid1, 0.01), F(0.25, v_vid1, 0.01), F(0.9, v_vid0 + 0.1, 0.01), F(0.45, v_vid0 + 0.1, 0.01)]),
           (0.85, 0.9, 1.0), 0.10)
    sc = cam.escala(F(0, 0.5))
    linea(ctx, cam.punto(F(0.25, v_vid0 + 0.03, 0.02)), cam.punto(F(-0.1, v_vid0 + 0.33, 0.02)), (0.02, 0.02, 0.02), max(1.0, 0.03 * sc))
    # letrero de destino: texto naranja en perspectiva
    v_l0, v_l1 = (2.975 - C.BASE_T) / C.ALTO_T, (3.235 - C.BASE_T) / C.ALTO_T
    llenar(ctx, caja_f(-0.82, 0.82, v_l0, v_l1, 0.01), (0.02, 0.02, 0.025))
    p00, p10, p01 = cam.punto(F(-0.82, v_l1, 0.015)), cam.punto(F(0.82, v_l1, 0.015)), cam.punto(F(-0.82, v_l0, 0.015))
    if None not in (p00, p10, p01):
        ancho_m, alto_m = 1.64 * 0.9, 0.26
        ctx.save()
        ctx.transform(cairo.Matrix((p10[0] - p00[0]) / ancho_m, (p10[1] - p00[1]) / ancho_m,
                                   (p01[0] - p00[0]) / alto_m, (p01[1] - p00[1]) / alto_m, p00[0], p00[1]))
        ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(0.17)
        ctx.set_source_rgb(0.85, 0.12, 0.08)
        ctx.rectangle(0.08, 0.04, 0.2, 0.18)
        ctx.fill()
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.move_to(0.13, 0.195)
        ctx.show_text("1")
        ctx.set_source_rgb(1.0, 0.62, 0.15)
        ctx.move_to(0.42, 0.195)
        ctx.show_text("Littenweiler")
        ctx.restore()
        c = cam.punto(F(0, (v_l0 + v_l1) / 2, 0.05))
        resplandor(glow, c, 0.9 * sc, (1.0, 0.55, 0.15), 0.35, 0.4)
    # filete plateado recto bajo los faros (una curva, con los faros encima, se leía como una cara)
    linea(ctx, cam.punto(F(-0.95, 0.075, 0.01)), cam.punto(F(0.95, 0.075, 0.01)), (0.62, 0.64, 0.7), max(1.0, 0.03 * sc))
    v_f = (0.875 - C.BASE_T) / C.ALTO_T
    for u in (-0.82, 0.82):
        llenar(ctx, caja_f(u - 0.11, u + 0.11, v_f - 0.022, v_f + 0.022, 0.012), (1.0, 0.98, 0.94))
        c = cam.punto(F(u, v_f, 0.05))
        resplandor(glow, c, 0.8 * sc, (1.0, 0.95, 0.85), 0.75)
        resplandor(glow, c, 0.25 * sc, (1.0, 1.0, 1.0), 1.0)
    v_p = (0.705 - C.BASE_T) / C.ALTO_T
    for u in (-0.53, 0.53):
        llenar(ctx, caja_f(u - 0.05, u + 0.05, v_p - 0.012, v_p + 0.012, 0.012), (1.0, 0.15, 0.08))
        resplandor(glow, cam.punto(F(u, v_p, 0.05)), 0.4 * sc, (1.0, 0.1, 0.05), 0.6)


def catenaria(ctx, cam):
    negro = (0.04, 0.04, 0.06)
    for z, grosor in ((6.0, 0.018), (6.35, 0.012)):
        linea(ctx, cam.punto((0, max(C.Y_MIN, cam.c[1] + 0.5), z)), cam.punto((0, C.Y_MAX, z)), negro, 1.3)
    y = C.Y_MIN + 6
    while y < C.Y_MAX:
        if y > cam.c[1] + 0.5:
            linea(ctx, cam.punto((-C.FACHADA, y, 7.2)), cam.punto((C.FACHADA, y, 7.2)), negro, max(1.0, 0.014 * cam.escala((0, y, 7.2))))
            linea(ctx, cam.punto((0, y, 6.0)), cam.punto((0, y, 7.2)), negro, 1.0)
        y += 27.0


# --------------------------------------------------------------------------- cuadro completo

def cuadro(t: float) -> np.ndarray:
    cam = Camara(t)
    yf = C.frente(t)
    sup = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    sup_g = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx, glow = cairo.Context(sup), cairo.Context(sup_g)
    for c_ in (ctx, glow):
        c_.set_antialias(cairo.ANTIALIAS_BEST)
        c_.set_line_cap(cairo.LINE_CAP_ROUND)
    glow.set_operator(cairo.OPERATOR_ADD)
    cielo(ctx, cam)
    piso(ctx, cam, 1.0)
    ctx.push_group()                                         # reflejo del tranvía en el piso mojado
    tranvia(ctx, glow, cam, yf, espejo=True)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(0.22)
    luces_en_piso(ctx, cam, yf)
    for lado in (-1, 1):
        for e in sorted((e for e in EDIFICIOS if e.lado == lado), key=lambda e: -e.y0):
            casa(ctx, glow, cam, e)
    for lado, y in sorted(FAROLES, key=lambda f: -f[1]):
        farol(ctx, glow, cam, lado, y)
    tranvia(ctx, glow, cam, yf)
    catenaria(ctx, cam)
    img = np.frombuffer(sup.get_data(), np.uint8).reshape(H, W, 4)[..., 2::-1].astype(np.float32) / 255
    g = np.frombuffer(sup_g.get_data(), np.uint8).reshape(H, W, 4)[..., 2::-1].astype(np.float32) / 255
    # brillo: las luces se abren en dos tamaños, como en una lente real
    chico = cv2.resize(g, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    halo = cv2.resize(cv2.GaussianBlur(chico, (0, 0), 3) * 0.7 + cv2.GaussianBlur(chico, (0, 0), 14) * 0.5, (W, H))
    img = img + g * 0.8 + halo
    img = 1 - np.exp(-img * 1.15)                            # compresión suave de las luces altas
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    img *= (1 - 0.35 * np.clip(r - 0.45, 0, None) ** 1.5)[..., None]
    return np.clip(img, 0, 1)


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1:
        f = int(sys.argv[1])
        img = cuadro((f - 1) / C.FPS)
        cv2.imwrite(str(SALIDA / f"estilo3_prueba_{f:04d}.png"), (img[..., ::-1] * 255).astype(np.uint8))
        return
    tmp = SALIDA / "estilo3_dibujo.tmp.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(C.FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                          "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    for i in range(C.CUADROS):
        img = cuadro(i / C.FPS)
        if i == int(C.CUADROS * 0.75):
            cv2.imwrite(str(SALIDA / "estilo3_dibujo.png"), (img[..., ::-1] * 255).astype(np.uint8))
        p.stdin.write((img * 255 + 0.5).astype(np.uint8).tobytes())
        if i % 30 == 0:
            print(f"  cuadro {i}/{C.CUADROS}", flush=True)
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg falló")
    tmp.replace(SALIDA / "estilo3_dibujo.mp4")
    print("listo")


if __name__ == "__main__":
    main()
