"""Gráficos 2D de las escenas 7 y 8: lienzos con sombra suave y brillo (para que los diagramas
floten con profundidad sobre el fondo), tarjetas de foto, documentos, rótulos que siguen a un objeto
del plano 3D, paneles de vidrio esmerilado e íconos (nube, servidor, orden judicial, insignia,
bocina, medidor de agua, casa, fábrica, mazo…).

Todo dibuja en coordenadas de pantalla (1920×1080) sobre imágenes float32 0..1.
"""

from __future__ import annotations

import functools
import math

import cv2
import numpy as np
from PIL import Image

import dibujo as D
from escenas.base import Foto, texto
from graficos import H, W, caja_dentro, color, fbm, gradiente_vertical, lim, suave

TAU = math.tau
NEGRO = np.zeros(3, np.float32)


# =========================================================================== lienzo con profundidad


class Lienzo:
    """Capa de cairo a pantalla completa que se compone con sombra difusa y, si se pide, brillo."""

    def __init__(self):
        self.s, self.c = D.lienzo(W, H)

    def tinta(self, col, a: float = 1.0) -> None:
        D.tinta(self.c, color(col), a)

    def componer(self, img: np.ndarray, sombra: float = 0.55, brillo: float = 0.0, col_brillo=None,
                 sigma_brillo: float = 12.0, dx: int = 9, dy: int = 13, sigma: float = 13.0, opacidad: float = 1.0) -> np.ndarray:
        capa = D.a_rgba(self.s) * opacidad
        alfa = capa[..., 3]
        if sombra > 0 and alfa.max() > 0:
            chico = cv2.resize(np.roll(np.roll(alfa, dy, 0), dx, 1), (W // 2, H // 2), interpolation=cv2.INTER_AREA)
            chico = cv2.GaussianBlur(chico, (0, 0), sigma / 2)
            img *= 1 - (cv2.resize(chico, (W, H), interpolation=cv2.INTER_LINEAR) * sombra)[..., None]
        if brillo > 0 and alfa.max() > 0:
            fuente = capa[..., :3] if col_brillo is None else alfa[..., None] * color(col_brillo)
            chico = cv2.resize(fuente, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
            chico = cv2.GaussianBlur(chico, (0, 0), sigma_brillo / 4)
            img += cv2.resize(chico, (W, H), interpolation=cv2.INTER_LINEAR) * brillo
        img *= 1 - capa[..., 3:]
        img += capa[..., :3]
        return img


@functools.lru_cache(maxsize=8)
def _fondo(oscuro: tuple, medio: tuple, semilla: int, reticula: float) -> np.ndarray:
    img = gradiente_vertical([(0.0, np.array(medio)), (0.55, np.array(oscuro) * 0.7 + np.array(medio) * 0.3), (1.0, np.array(oscuro))])
    img *= (0.88 + 0.24 * fbm(H // 8, W // 8, 22, 4, 0.5, semilla).repeat(8, 0).repeat(8, 1))[..., None]
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot((xx - W * 0.45) / W, (yy - H * 0.4) / H)
    img *= (1.15 - 0.55 * np.clip(r, 0, 1))[..., None]
    if reticula > 0:
        puntos = ((xx % 40 == 0) & (yy % 40 == 0)).astype(np.float32)
        puntos = cv2.dilate(puntos, np.ones((2, 2), np.uint8))
        img += puntos[..., None] * np.array(medio) * reticula * 2.5
    img = img.astype(np.float32)
    img.setflags(write=False)
    return img


def fondo(oscuro, medio, semilla: int = 3, reticula: float = 0.05) -> np.ndarray:
    """Fondo técnico: degradado con viñeta interna, textura leve y retícula de puntos."""
    return _fondo(tuple(map(float, color(oscuro))), tuple(map(float, color(medio))), semilla, reticula).copy()


def panel(img: np.ndarray, x0: int, y0: int, x1: int, y1: int, a: float, oscuro: float = 0.45, linea=(1, 1, 1)) -> None:
    """Vidrio esmerilado: lo de atrás se desenfoca y oscurece; un filo de luz arriba."""
    if a <= 0:
        return
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    zona = img[y0:y1, x0:x1]
    borrosa = cv2.GaussianBlur(zona, (0, 0), 18) * (1 - oscuro)
    img[y0:y1, x0:x1] = zona * (1 - a) + borrosa * a
    img[y0 : y0 + 2, x0:x1] = img[y0 : y0 + 2, x0:x1] * (1 - 0.3 * a) + np.asarray(linea, np.float32) * 0.3 * a


def desenfocar(img: np.ndarray, sigma: float, oscuro: float = 0.0) -> np.ndarray:
    chico = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    chico = cv2.GaussianBlur(chico, (0, 0), sigma / 4)
    return cv2.resize(chico, (W, H), interpolation=cv2.INTER_LINEAR) * (1 - oscuro)


def rotulo(img, cadena, x, y, tam=34, col=(1, 1, 1), a=1.0, alinear="izq", nombre="Inter-SemiBold.ttf", interletra=0.0, sombra=0.5):
    return texto(img, cadena, x, y, tam, col, nombre=nombre, alinear=alinear, opacidad=a, interletra=interletra, sombra=sombra)


def antetitulo(img, cadena, x, y, col, a=1.0, alinear="izq", tam=24):
    """Rótulo pequeño en mayúsculas espaciadas (como «MADRUGADA» en la escena 1)."""
    return texto(img, cadena.upper(), x, y, tam, col, nombre="Inter-SemiBold.ttf", alinear=alinear, opacidad=a, interletra=0.3)


# =========================================================================== rótulos sobre el 3D


def rotulo_en(img, punto, cadena, col, acento, a: float, lado: str = "der", alto: float = 90.0, largo: float = 70.0,
              tam: int = 34, sub: str | None = None) -> None:
    """Rótulo con línea guía hacia un punto de la pantalla (la proyección de un objeto del plano 3D):
    un punto con anillo, una línea que sube en diagonal y el texto al final."""
    if a <= 0 or punto is None:
        return
    x, y = punto
    if not (-200 < x < W + 200 and -200 < y < H + 200):
        return
    s = 1 if lado == "der" else -1
    codo = (x + s * alto * 0.55, y - alto)
    fin = (codo[0] + s * largo, codo[1])
    lz = Lienzo()
    lz.tinta(acento, a)
    lz.c.arc(x, y, 6, 0, TAU)
    lz.c.fill()
    lz.tinta(acento, a * 0.55)
    lz.c.set_line_width(2.0)
    lz.c.arc(x, y, 12 + 3 * math.sin(a * 3), 0, TAU)
    lz.c.stroke()
    p = suave(a)
    lz.tinta(col, a * 0.9)
    lz.c.set_line_width(2.2)
    lz.c.move_to(x + s * 10 * 0.6, y - 10 * 0.8)
    tramo1 = (codo[0] - x, codo[1] - y)
    lz.c.line_to(x + tramo1[0] * min(1, p * 2), y + tramo1[1] * min(1, p * 2))
    if p > 0.5:
        lz.c.line_to(codo[0] + s * largo * (p - 0.5) * 2, codo[1])
    lz.c.stroke()
    lz.componer(img, sombra=0.35, brillo=0.25, col_brillo=acento, sigma_brillo=8)
    ta = suave((a - 0.4) / 0.6)
    tx = fin[0] + s * 14
    texto(img, cadena, tx, codo[1] + tam * 0.35, tam, col, alinear="izq" if s > 0 else "der", opacidad=ta)
    if sub:
        texto(img, sub, tx, codo[1] + tam * 0.35 + tam * 1.05, int(tam * 0.68), col, nombre="Inter-Regular.ttf",
              alinear="izq" if s > 0 else "der", opacidad=ta * 0.8)


# =========================================================================== fotos y documentos


def tarjeta_foto(img: np.ndarray, foto: Foto, x0: int, y0: int, fw: int, fh: int | None = None, z: float = 1.0,
                 cx: float = 0.5, cy: float = 0.4, a: float = 1.0, borde=(0.92, 0.92, 0.92), sombra: float = 0.6) -> tuple:
    """Foto enmarcada con su sombra. Si `fh` es None, el marco toma la proporción de la foto.
    Devuelve (x0, y0, ancho, alto) del marco."""
    if not foto.existe or a <= 0:
        return x0, y0, fw, fh or fw
    im = foto.im
    if fh is None:
        fh = round(fw * im.height / im.width)
    cubre = max(fw / im.width, fh / im.height) * z
    bw, bh = fw / cubre, fh / cubre
    bx = min(max(cx * im.width - bw / 2, 0), im.width - bw)
    by = min(max(cy * im.height - bh / 2, 0), im.height - bh)
    recorte = np.asarray(im.resize((fw, fh), Image.BICUBIC, box=caja_dentro((bx, by, bx + bw, by + bh), im.width, im.height)), np.float32) / 255
    alfa = np.zeros((H, W), np.float32)
    ya, yb, xa, xb = max(0, y0), min(H, y0 + fh), max(0, x0), min(W, x0 + fw)
    alfa[ya:yb, xa:xb] = 1.0
    chico = cv2.resize(np.roll(np.roll(alfa, 18, 0), 12, 1), (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    sombra_m = cv2.resize(cv2.GaussianBlur(chico, (0, 0), 6), (W, H), interpolation=cv2.INTER_LINEAR)
    img *= 1 - (sombra_m * sombra * a)[..., None]
    zona = img[ya:yb, xa:xb]
    img[ya:yb, xa:xb] = zona * (1 - a) + recorte[ya - y0 : yb - y0, xa - x0 : xb - x0] * a
    b = np.asarray(borde, np.float32)
    for (sa, sb, sc, sd) in ((y0 - 2, y0, x0 - 2, x0 + fw + 2), (y0 + fh, y0 + fh + 2, x0 - 2, x0 + fw + 2),
                             (y0, y0 + fh, x0 - 2, x0), (y0, y0 + fh, x0 + fw, x0 + fw + 2)):
        sa, sb, sc, sd = max(0, sa), min(H, sb), max(0, sc), min(W, sd)
        if sa < sb and sc < sd:
            img[sa:sb, sc:sd] = img[sa:sb, sc:sd] * (1 - 0.55 * a) + b * 0.55 * a
    return x0, y0, fw, fh


def documento(img: np.ndarray, foto: Foto, t: float, dur: float, a: float = 1.0, ancho: int = 1180,
              z0: float = 1.0, z1: float = 1.08, cy0: float = 0.45, cy1: float = 0.5, giro: float = -1.2) -> None:
    """Captura de un titular como hoja que flota, apenas girada, con sombra, y que se acerca despacio."""
    if not foto.existe or a <= 0:
        return
    u = suave(lim(t / max(dur, 1e-3)))
    z = z0 + (z1 - z0) * u
    im = foto.im
    w = int(ancho * z)
    h = int(w * im.height / im.width)
    hoja = np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255
    hoja = np.dstack([hoja, np.ones((h, w), np.float32)])
    ang = giro + 0.6 * u
    cx = W / 2
    cy = H / 2 + (cy0 - 0.5 + (cy1 - cy0) * u) * h * 0.6
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    M[0, 2] += cx - w / 2
    M[1, 2] += cy - h / 2
    capa = cv2.warpAffine(hoja, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    alfa = capa[..., 3] * a
    chico = cv2.resize(np.roll(np.roll(alfa, 26, 0), 16, 1), (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    sombra_m = cv2.resize(cv2.GaussianBlur(chico, (0, 0), 7), (W, H), interpolation=cv2.INTER_LINEAR)
    img *= 1 - (sombra_m * 0.7)[..., None]
    img *= 1 - alfa[..., None]
    img += capa[..., :3] * alfa[..., None]


# =========================================================================== íconos (cairo)


def nube(c, cx, cy, s):
    """Nube de lado `s` (contorno; se rellena o se traza afuera)."""
    c.new_sub_path()
    for (dx, dy, r) in ((-0.28, 0.08, 0.22), (-0.05, -0.1, 0.3), (0.25, 0.0, 0.24), (0.38, 0.14, 0.14)):
        c.new_sub_path()
        c.arc(cx + dx * s, cy + dy * s, r * s, 0, TAU)
    D.rect_redondeado(c, cx - 0.45 * s, cy + 0.02 * s, 0.95 * s, 0.26 * s, 0.13 * s)


def nube_contorno(c, cx, cy, s, col_linea, col_relleno, a: float = 1.0, grosor: float = 4.0):
    """Nube con solo su silueta exterior: se rellena del color de la línea y encima, un poco más
    chica, del color de adentro (así no se ven los círculos que la forman)."""
    D.tinta(c, color(col_linea), a)
    nube(c, cx, cy, s)
    c.fill()
    D.tinta(c, color(col_relleno), a)
    nube(c, cx, cy + grosor * 0.15, s - 2.6 * grosor)
    c.fill()


def servidor(c, cx, cy, w, h, luces: float = 1.0, grosor=3.0):
    """Gabinete de servidores: tres módulos con su ranura y un LED cada uno."""
    c.set_line_width(grosor)
    D.rect_redondeado(c, cx - w / 2, cy - h / 2, w, h, w * 0.06)
    c.stroke()
    for k in range(3):
        y = cy - h / 2 + h * (0.12 + 0.28 * k)
        D.rect_redondeado(c, cx - w * 0.38, y, w * 0.76, h * 0.2, w * 0.03)
        c.stroke()
        c.move_to(cx - w * 0.28, y + h * 0.1)
        c.line_to(cx + w * 0.05, y + h * 0.1)
        c.stroke()
        if luces > 0:
            c.arc(cx + w * 0.24, y + h * 0.1, w * 0.04, 0, TAU)
            c.fill()


def orden_judicial(c, x, y, s, grosor=3.0):
    """Documento con renglones y un sello redondo: la orden judicial."""
    w = s * 0.76
    c.set_line_width(grosor)
    c.move_to(x, y)
    c.line_to(x + w - s * 0.2, y)
    c.line_to(x + w, y + s * 0.2)
    c.line_to(x + w, y + s)
    c.line_to(x, y + s)
    c.close_path()
    c.stroke()
    for k in range(5):
        yy = y + s * (0.3 + 0.1 * k)
        c.move_to(x + s * 0.12, yy)
        c.line_to(x + w - s * (0.12 if k % 2 else 0.25), yy)
    c.stroke()
    c.arc(x + w * 0.68, y + s * 0.85, s * 0.09, 0, TAU)
    c.stroke()


def insignia(c, cx, cy, s, grosor=3.0):
    """Placa de policía (estrella dentro de un escudo)."""
    c.set_line_width(grosor)
    c.move_to(cx, cy - s * 0.5)
    c.curve_to(cx + s * 0.3, cy - s * 0.42, cx + s * 0.42, cy - s * 0.45, cx + s * 0.45, cy - s * 0.35)
    c.curve_to(cx + s * 0.45, cy + s * 0.1, cx + s * 0.25, cy + s * 0.38, cx, cy + s * 0.52)
    c.curve_to(cx - s * 0.25, cy + s * 0.38, cx - s * 0.45, cy + s * 0.1, cx - s * 0.45, cy - s * 0.35)
    c.curve_to(cx - s * 0.42, cy - s * 0.45, cx - s * 0.3, cy - s * 0.42, cx, cy - s * 0.5)
    c.close_path()
    c.stroke()
    pts = []
    for k in range(10):
        r = s * (0.22 if k % 2 == 0 else 0.1)
        a = -math.pi / 2 + k * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + s * 0.02 + r * math.sin(a)))
    c.move_to(*pts[0])
    for q in pts[1:]:
        c.line_to(*q)
    c.close_path()
    c.fill()


def bocina(c, cx, cy, h, grosor=3.0, anillo: float = 0.0, col_anillo=None):
    """Bocina cilíndrica de perfil (el Echo), con su rejilla y el anillo de arriba."""
    w = h * 0.36
    c.set_line_width(grosor)
    D.rect_redondeado(c, cx - w / 2, cy - h / 2, w, h, w * 0.08)
    c.stroke()
    for k in range(7):
        for j in range(4):
            c.arc(cx - w * 0.3 + j * w * 0.2, cy - h * 0.05 + k * h * 0.075, h * 0.012, 0, TAU)
            c.fill()
    c.move_to(cx - w / 2, cy - h * 0.40)
    c.line_to(cx + w / 2, cy - h * 0.40)
    c.stroke()
    if anillo > 0 and col_anillo is not None:
        D.tinta(c, color(col_anillo), anillo)
        D.rect_redondeado(c, cx - w / 2 + 2, cy - h * 0.455, w - 4, h * 0.045, h * 0.02)
        c.fill()


def casa(c, cx, cy, s, grosor=3.0):
    c.set_line_width(grosor)
    c.move_to(cx - s * 0.5, cy - s * 0.05)
    c.line_to(cx, cy - s * 0.5)
    c.line_to(cx + s * 0.5, cy - s * 0.05)
    c.move_to(cx - s * 0.4, cy - s * 0.14)
    c.line_to(cx - s * 0.4, cy + s * 0.42)
    c.line_to(cx + s * 0.4, cy + s * 0.42)
    c.line_to(cx + s * 0.4, cy - s * 0.14)
    c.stroke()
    c.rectangle(cx - s * 0.1, cy + s * 0.12, s * 0.2, s * 0.3)
    c.stroke()


def edificio(c, cx, cy, s, grosor=3.0):
    """Oficinas de la compañía de agua: edificio con ventanas y un tanque."""
    c.set_line_width(grosor)
    c.rectangle(cx - s * 0.42, cy - s * 0.3, s * 0.58, s * 0.8)
    c.stroke()
    for i in range(3):
        for j in range(4):
            c.rectangle(cx - s * 0.34 + i * s * 0.17, cy - s * 0.22 + j * s * 0.17, s * 0.09, s * 0.09)
    c.fill()
    c.move_to(cx + s * 0.25, cy + s * 0.5)
    c.line_to(cx + s * 0.25, cy - s * 0.05)
    c.stroke()
    c.arc(cx + s * 0.34, cy - s * 0.18, s * 0.14, 0, TAU)
    c.stroke()


def medidor(c, cx, cy, s, grosor=3.0):
    """Medidor de agua: cuerpo redondo sobre el tubo, con su carátula."""
    c.set_line_width(grosor)
    c.arc(cx, cy, s * 0.5, 0, TAU)
    c.stroke()
    c.arc(cx, cy, s * 0.38, 0, TAU)
    c.stroke()
    c.rectangle(cx - s * 0.3, cy - s * 0.12, s * 0.6, s * 0.24)
    c.stroke()


def antena(c, cx, cy, s, ondas: float, grosor=3.0):
    """Antena con ondas que salen (`ondas` 0..1 anima los arcos)."""
    c.set_line_width(grosor)
    c.move_to(cx, cy)
    c.line_to(cx, cy - s * 0.5)
    c.stroke()
    for k in range(3):
        f = (ondas + k / 3) % 1.0
        r = s * (0.15 + 0.6 * f)
        c.save()
        c.set_source_rgba(*c.get_source().get_rgba()[:3], c.get_source().get_rgba()[3] * (1 - f))
        c.arc(cx, cy - s * 0.5, r, -math.pi * 0.8, -math.pi * 0.2)
        c.stroke()
        c.restore()


def mazo(c, cx, cy, s, giro=0.0, grosor=3.0):
    """Mazo de juez (de perfil) y su base."""
    c.save()
    c.translate(cx, cy)
    c.rotate(giro)
    D.rect_redondeado(c, -s * 0.32, -s * 0.12, s * 0.64, s * 0.24, s * 0.06)
    c.fill()
    c.rectangle(-s * 0.04, s * 0.1, s * 0.08, s * 0.6)
    c.fill()
    c.restore()
    c.set_line_width(grosor)
    D.rect_redondeado(c, cx - s * 0.4, cy + s * 0.75, s * 0.8, s * 0.12, s * 0.04)
    c.stroke()


def lupa(c, cx, cy, s, grosor=3.0):
    c.set_line_width(grosor)
    c.arc(cx, cy, s * 0.32, 0, TAU)
    c.stroke()
    c.set_line_width(grosor * 1.6)
    c.move_to(cx + s * 0.23, cy + s * 0.23)
    c.line_to(cx + s * 0.5, cy + s * 0.5)
    c.stroke()


def palomita(c, cx, cy, s, p: float = 1.0, grosor=5.0):
    """Marca de «sí» que se traza con `p`."""
    pts = [(cx - s * 0.4, cy), (cx - s * 0.1, cy + s * 0.3), (cx + s * 0.45, cy - s * 0.35)]
    from escenas import diagramas as DG
    DG.linea(c, pts, p, grosor)


def tacha(c, cx, cy, s, p: float = 1.0, grosor=6.0):
    """Cruz que se traza con `p` (dos trazos)."""
    from escenas import diagramas as DG
    DG.linea(c, [(cx - s / 2, cy - s / 2), (cx + s / 2, cy + s / 2)], min(1.0, p * 2), grosor)
    if p > 0.5:
        DG.linea(c, [(cx + s / 2, cy - s / 2), (cx - s / 2, cy + s / 2)], (p - 0.5) * 2, grosor)


def reloj_pulsera(c, cx, cy, s, grosor=3.0):
    c.set_line_width(grosor)
    D.rect_redondeado(c, cx - s * 0.3, cy - s * 0.35, s * 0.6, s * 0.7, s * 0.14)
    c.stroke()
    c.rectangle(cx - s * 0.18, cy - s * 0.62, s * 0.36, s * 0.27)
    c.rectangle(cx - s * 0.18, cy + s * 0.35, s * 0.36, s * 0.27)
    c.stroke()


def camarita(c, cx, cy, s, grosor=3.0):
    """Cámara de seguridad barata de frente, con su pie."""
    c.set_line_width(grosor)
    D.rect_redondeado(c, cx - s * 0.4, cy - s * 0.45, s * 0.8, s * 0.7, s * 0.14)
    c.stroke()
    c.arc(cx, cy - s * 0.1, s * 0.2, 0, TAU)
    c.stroke()
    c.arc(cx, cy - s * 0.1, s * 0.07, 0, TAU)
    c.fill()
    c.move_to(cx, cy + s * 0.25)
    c.line_to(cx, cy + s * 0.45)
    c.move_to(cx - s * 0.25, cy + s * 0.48)
    c.line_to(cx + s * 0.25, cy + s * 0.48)
    c.stroke()


def fabrica(c, cx, cy, s, grosor=3.0):
    """Sensor de fábrica: caja con antena y una chimenea de fondo."""
    c.set_line_width(grosor)
    D.rect_redondeado(c, cx - s * 0.42, cy - s * 0.2, s * 0.84, s * 0.55, s * 0.06)
    c.stroke()
    c.move_to(cx + s * 0.25, cy - s * 0.2)
    c.line_to(cx + s * 0.32, cy - s * 0.55)
    c.stroke()
    c.arc(cx - s * 0.15, cy + s * 0.08, s * 0.1, 0, TAU)
    c.stroke()


def waveform(c, x0, y0, ancho, alto, t, semilla=0, n=64, a=1.0):
    """Forma de onda de voz que corre de derecha a izquierda."""
    rng = np.random.default_rng(semilla)
    fases = rng.uniform(0, TAU, 5)
    c.set_line_width(3)
    for k in range(n):
        x = x0 + ancho * k / (n - 1)
        u = k / n * 9 + t * 4
        amp = abs(math.sin(u * 0.9 + fases[0]) * math.sin(u * 0.37 + fases[1]) + 0.3 * math.sin(u * 2.3 + fases[2]))
        amp = 0.08 + 0.92 * amp ** 1.4
        c.move_to(x, y0 - amp * alto / 2)
        c.line_to(x, y0 + amp * alto / 2)
    c.stroke()


# =========================================================================== mapas


# Contorno aproximado de Arkansas (lon, lat), en el sentido del reloj desde la esquina noroeste.
ARKANSAS = [
    (-94.62, 36.50), (-90.15, 36.50), (-90.08, 36.30), (-90.38, 36.00), (-89.71, 36.00), (-89.66, 35.80),
    (-89.95, 35.60), (-90.10, 35.20), (-90.16, 34.95), (-90.55, 34.60), (-90.58, 34.38), (-90.88, 34.05),
    (-91.05, 33.75), (-91.20, 33.45), (-91.16, 33.00), (-94.04, 33.00), (-94.04, 33.55), (-94.48, 33.64),
    (-94.43, 35.39), (-94.62, 36.50),
]
BENTONVILLE = (-94.21, 36.37)
# Contorno muy simplificado de Estados Unidos continental, para ubicar Arkansas.
EEUU = [
    (-124.7, 48.4), (-123.0, 46.2), (-124.2, 42.0), (-124.4, 40.4), (-122.4, 37.2), (-120.6, 34.6), (-117.1, 32.5),
    (-114.7, 32.7), (-111.1, 31.3), (-108.2, 31.8), (-106.5, 31.8), (-104.5, 29.6), (-103.0, 29.0), (-101.4, 29.8),
    (-99.5, 27.5), (-97.4, 25.9), (-97.4, 27.8), (-96.0, 28.6), (-94.0, 29.7), (-91.5, 29.5), (-89.6, 29.2),
    (-89.4, 30.3), (-87.5, 30.3), (-85.1, 29.7), (-83.6, 29.9), (-82.7, 27.7), (-81.0, 25.2), (-80.1, 26.5),
    (-80.6, 28.5), (-81.4, 30.7), (-80.9, 32.1), (-78.9, 33.6), (-75.7, 35.3), (-76.3, 37.0), (-75.9, 38.3),
    (-74.0, 40.5), (-71.9, 41.3), (-70.0, 41.8), (-70.7, 43.0), (-69.0, 44.1), (-67.0, 44.8), (-67.8, 47.1),
    (-69.2, 47.4), (-71.5, 45.0), (-75.0, 45.0), (-76.8, 43.6), (-79.0, 43.3), (-79.1, 42.8), (-82.5, 41.7),
    (-82.4, 43.0), (-82.1, 45.6), (-84.6, 46.5), (-88.4, 48.3), (-89.6, 48.0), (-94.8, 49.4), (-95.2, 49.0),
    (-123.3, 49.0),
]
