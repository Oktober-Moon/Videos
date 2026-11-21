"""Piezas gráficas de la escena 3: temas de color, capas con sombra y brillo, ventanas con fotos y
documentos reales, íconos, el mapa de California y el recorrido de cinco pasos de Azimuth.

Todo se dibuja con cairo a pantalla completa y se compone sobre un fondo técnico. Cada capa de
diagrama proyecta una sombra suave y puede brillar como luz de pantalla: así los diagramas flotan
sobre el fondo, con profundidad.
"""

from __future__ import annotations

import functools
import math
import re

import cv2
import numpy as np
from PIL import Image

import cine
import dibujo as D
import guion
from escenas import diagramas as DG
from escenas.base import aparece, texto
from graficos import H, W, caja_dentro, color, desenfoque, fbm, gradiente_vertical, lim, suave
from paletas import APPLE, CONNECTICUT, SAN_BERNARDINO, mezcla, rgb

TAU = math.tau
SB, AP = rgb(SAN_BERNARDINO), rgb(APPLE)
NEGRO = np.zeros(3, np.float32)
ROJO = rgb(CONNECTICUT)["rojo_patrulla"]                # alerta: el error, lo que se rompe


class Tema:
    """Colores de un mundo: fondo oscuro, texto claro, acento y un tono apagado."""

    def __init__(self, oscuro, claro, acento, tenue, panel):
        self.oscuro, self.claro, self.acento, self.tenue, self.panel = oscuro, claro, acento, tenue, panel


SANB = Tema(oscuro=mezcla(SB["azul_fbi"], NEGRO, 0.62), claro=mezcla(SB["arena"], np.ones(3), 0.55),
            acento=SB["dorado"], tenue=mezcla(SB["arena"], SB["azul_fbi"], 0.45),
            panel=mezcla(SB["azul_fbi"], NEGRO, 0.25))
MANZANA = Tema(oscuro=mezcla(AP["gris"], NEGRO, 0.72), claro=AP["blanco"], acento=AP["azul"],
               tenue=mezcla(AP["gris"], AP["blanco"], 0.55), panel=mezcla(AP["gris"], NEGRO, 0.15))


@functools.lru_cache(maxsize=4)
def _fondo(nombre: str) -> np.ndarray:
    tema = SANB if nombre == "sb" else MANZANA
    img = DG.fondo(tema.oscuro, mezcla(tema.claro, tema.oscuro, 0.4), 0.045)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    foco = np.exp(-(((xx - W * 0.5) / (W * 0.55)) ** 2 + ((yy - H * 0.42) / (H * 0.6)) ** 2))
    img = img * (0.78 + 0.42 * foco[..., None])
    img.setflags(write=False)
    return img


def fondo(tema: Tema) -> np.ndarray:
    return _fondo("sb" if tema is SANB else "ap").copy()


def rotulo(img, cadena, x, y, tam=34, col=None, a=1.0, alinear="izq", nombre="Inter-SemiBold.ttf", interletra=0.0,
           sombra=0.45):
    if col is None:
        col = SANB.claro
    return texto(img, cadena, x, y, tam, col, nombre=nombre, alinear=alinear, opacidad=a, interletra=interletra, sombra=sombra)


def antetitulo(img, cadena, x, y, col, a=1.0, alinear="izq", tam=24):
    """Rótulo chico en versalitas espaciadas (lugar, fecha, tipo de documento)."""
    return rotulo(img, cadena.upper(), x, y, tam, col, a, alinear, "Inter-SemiBold.ttf", 0.28, 0.35)


# =========================================================================== capas


class Capa:
    """Lienzo de cairo a pantalla completa. Al componerse proyecta una sombra suave y puede brillar."""

    def __init__(self):
        self.s, self.c = D.lienzo(W, H)

    def tinta(self, col, a: float = 1.0) -> None:
        D.tinta(self.c, color(col), a)

    def componer(self, img: np.ndarray, sombra: float = 0.45, brillo: float = 0.0, col_brillo=None, sigma: float = 12.0,
                 dx: int = 8, dy: int = 12) -> np.ndarray:
        """Compone solo el recuadro que ocupa lo dibujado (más un margen para la sombra y el brillo):
        casi todas las capas son chicas y procesar la pantalla entera costaba casi un segundo."""
        self.s.flush()
        datos = D._datos(self.s)
        alfa8 = datos[..., 3]
        filas = np.flatnonzero(alfa8.any(axis=1))
        if not filas.size:
            return img
        cols = np.flatnonzero(alfa8.any(axis=0))
        m = int(max(3 * sigma if brillo > 0 else 0, (54 + max(abs(dx), abs(dy))) if sombra > 0 else 0)) + 4
        y0, y1 = max(0, filas[0] - m), min(H, filas[-1] + 1 + m)
        x0, x1 = max(0, cols[0] - m), min(W, cols[-1] + 1 + m)
        capa = datos[y0:y1, x0:x1][..., [2, 1, 0, 3]].astype(np.float32) * (1.0 / 255.0)
        zona = img[y0:y1, x0:x1]
        a = capa[..., 3]
        if sombra > 0:                                   # como cine.sombra_suave(…, 18, …), en el recorte
            s = np.roll(np.roll(a, dy, axis=0), dx, axis=1)
            zona *= 1 - (_borroso(s, 18.0) * sombra)[..., None]
        if brillo > 0:
            if col_brillo is None:
                zona += _borroso(capa[..., :3], sigma) * brillo
            else:
                zona += _borroso(a, sigma)[..., None] * color(col_brillo) * brillo
        zona *= 1 - capa[..., 3:]
        zona += capa[..., :3]
        return img


def _borroso(x: np.ndarray, sigma: float) -> np.ndarray:
    """Desenfoque gaussiano; si es ancho, a media resolución (como `desenfoque` y `cine.sombra_suave`)."""
    h, w = x.shape[:2]
    if sigma < 8 or h < 8 or w < 8:
        return cv2.GaussianBlur(x, (0, 0), sigma)
    chico = cv2.resize(x, (max(1, w // 2), max(1, h // 2)), interpolation=cv2.INTER_AREA)
    chico = cv2.GaussianBlur(chico, (0, 0), sigma / 2)
    return cv2.resize(chico, (w, h), interpolation=cv2.INTER_LINEAR)


def tarjeta(c, x, y, w, h, r, relleno, a=1.0, borde=None, a_borde=0.35, grosor=1.5):
    """Recuadro redondeado relleno, con un filo de luz."""
    if a <= 0:
        return
    D.tinta(c, color(relleno), a)
    D.rect_redondeado(c, x, y, w, h, r)
    c.fill()
    if borde is not None:
        D.tinta(c, color(borde), a * a_borde)
        c.set_line_width(grosor)
        D.rect_redondeado(c, x, y, w, h, r)
        c.stroke()


def panel_esmerilado(img: np.ndarray, x0: int, y0: int, x1: int, y1: int, a: float, oscuro: float = 0.45, filo=None) -> None:
    """Vidrio esmerilado sobre una imagen (lo de atrás se desenfoca y oscurece)."""
    if a <= 0:
        return
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    zona = img[y0:y1, x0:x1]
    borrosa = cv2.GaussianBlur(zona, (0, 0), 18) * (1 - oscuro)
    img[y0:y1, x0:x1] = zona * (1 - a) + borrosa * a
    if filo is not None:
        img[y0 : y0 + 2, x0:x1] = img[y0 : y0 + 2, x0:x1] * (1 - 0.4 * a) + color(filo) * 0.4 * a


# =========================================================================== fotos y documentos reales


@functools.lru_cache(maxsize=64)
def _mascara_redondeada(w: int, h: int, r: float) -> np.ndarray:
    s, c = D.lienzo(w, h)
    c.set_source_rgba(1, 1, 1, 1)
    D.rect_redondeado(c, 0, 0, w, h, r)
    c.fill()
    m = D.a_alfa(s)
    m.setflags(write=False)
    return m


def recorte(im: Image.Image, w: int, h: int, zoom: float = 1.0, cx: float = 0.5, cy: float = 0.5) -> np.ndarray:
    """La imagen cubriendo un rectángulo de w × h, con acercamiento y centro relativos (0..1)."""
    cubre = max(w / im.width, h / im.height) * zoom
    bw, bh = w / cubre, h / cubre
    x0 = min(max(cx * im.width - bw / 2, 0), im.width - bw)
    y0 = min(max(cy * im.height - bh / 2, 0), im.height - bh)
    return np.asarray(im.resize((w, h), Image.BICUBIC, box=caja_dentro((x0, y0, x0 + bw, y0 + bh), im.width, im.height)), np.float32) / 255.0


def ventana(img: np.ndarray, im: Image.Image | None, x: float, y: float, w: float, h: float, *, a: float = 1.0,
            zoom: float = 1.0, cx: float = 0.5, cy: float = 0.5, radio: float = 14.0, borde=None, sombra: float = 0.6,
            fondo_vacio=None) -> None:
    """Pone una foto o captura real en un recuadro redondeado que flota (sombra suave y filo de luz)."""
    if a <= 0.002:
        return
    x, y, w, h = int(round(x)), int(round(y)), int(round(w)), int(round(h))
    m = _mascara_redondeada(w, h, radio)
    sx0, sy0 = max(0, -x), max(0, -y)
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x0 >= x1 or y0 >= y1:
        return
    if sombra > 0:                                       # sombra difusa, solo alrededor del recuadro
        mg = 110
        X0, Y0, X1, Y1 = max(0, x0 - mg), max(0, y0 - mg), min(W, x1 + mg), min(H, y1 + mg)
        alfa = np.zeros((Y1 - Y0, X1 - X0), np.float32)
        ms = m[sy0 : sy0 + y1 - y0, sx0 : sx0 + x1 - x0]
        oy, ox = y0 - Y0 + 22, x0 - X0 + 14
        hh, ww = min(ms.shape[0], alfa.shape[0] - oy), min(ms.shape[1], alfa.shape[1] - ox)
        if hh > 0 and ww > 0:
            alfa[oy : oy + hh, ox : ox + ww] = ms[:hh, :ww]
        img[Y0:Y1, X0:X1] *= 1 - (_borroso(alfa, 30.0) * sombra * a)[..., None]
    if im is not None:
        foto = recorte(im, w, h, zoom, cx, cy)
    else:
        foto = np.broadcast_to(color(fondo_vacio if fondo_vacio is not None else (0.1, 0.1, 0.1)), (h, w, 3))
    k = (m[sy0 : sy0 + y1 - y0, sx0 : sx0 + x1 - x0] * a)[..., None]
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - k) + foto[sy0 : sy0 + y1 - y0, sx0 : sx0 + x1 - x0] * k
    if borde is not None:
        cp = Capa()
        cp.tinta(borde, 0.45 * a)
        cp.c.set_line_width(2)
        D.rect_redondeado(cp.c, x + 1, y + 1, w - 2, h - 2, radio)
        cp.c.stroke()
        cp.componer(img, sombra=0)


def cargar(ruta) -> Image.Image | None:
    """Imagen real en RGB (sobre blanco si trae transparencia), o None si no está."""
    from escenas.base import IMAGENES
    p = IMAGENES / ruta
    if not p.exists():
        return None
    im = Image.open(p)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        fondo_ = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(fondo_, im)
    return im.convert("RGB")


def logo_blanco(ruta: str, alto: int) -> np.ndarray | None:
    """Un logotipo de una sola tinta (con transparencia) como máscara, escalado a `alto` px."""
    from escenas.base import IMAGENES
    p = IMAGENES / ruta
    if not p.exists():
        return None
    im = Image.open(p).convert("LA")
    a = np.asarray(im, np.float32)[..., 1] / 255.0
    ys, xs = np.nonzero(a > 0.05)
    a = a[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    esc = alto / a.shape[0]
    return cv2.resize(a, (max(1, int(a.shape[1] * esc)), alto), interpolation=cv2.INTER_AREA)


def poner_mascara(img: np.ndarray, m: np.ndarray, x: float, y: float, col, a: float = 1.0, brillo: float = 0.0) -> None:
    """Pinta una máscara (h, w) de un color con su esquina en (x, y)."""
    if m is None or a <= 0:
        return
    h, w = m.shape
    x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x0 >= x1 or y0 >= y1:
        return
    k = m[y0 - y : y1 - y, x0 - x : x1 - x, None] * a
    if brillo > 0:
        mg = 44
        X0, Y0, X1, Y1 = max(0, x0 - mg), max(0, y0 - mg), min(W, x1 + mg), min(H, y1 + mg)
        zona = np.zeros((Y1 - Y0, X1 - X0), np.float32)
        zona[y0 - Y0 : y1 - Y0, x0 - X0 : x1 - X0] = k[..., 0]
        img[Y0:Y1, X0:X1] += _borroso(zona, 14.0)[..., None] * color(col) * brillo
    img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - k) + color(col) * k


# =========================================================================== tiempos dentro de una oración


def en_palabra(sub, k: int, palabra: str, n: int = 1) -> float:
    """Instante aproximado en que se dice `palabra` (por su comienzo) en la oración k de la subescena."""
    palabras = [re.sub(r"[^\wáéíóúñü]", "", p.lower()) for p in guion.subescena(sub.id).oraciones[k].split()]
    vistos = 0
    i = 0
    for j, p in enumerate(palabras):
        if p.startswith(palabra.lower()):
            vistos += 1
            if vistos == n:
                i = j
                break
    o = getattr(sub, "o", sub.T.oraciones)
    fin = (o[k + 1] - 0.35) if k + 1 < len(o) else sub.T.fin_voz
    return o[k] + (fin - o[k]) * i / max(1, len(palabras))


# =========================================================================== íconos (cairo)


def icono_enchufe(c, cx, cy, s, g=None):
    """Clavija de corriente: cuerpo redondeado, dos patas y el cable."""
    g = g or s * 0.07
    c.set_line_width(g)
    D.rect_redondeado(c, cx - s * 0.28, cy - s * 0.15, s * 0.56, s * 0.42, s * 0.1)
    c.stroke()
    for dx in (-0.12, 0.12):
        c.move_to(cx + dx * s, cy - s * 0.15)
        c.line_to(cx + dx * s, cy - s * 0.42)
    c.stroke()
    c.move_to(cx, cy + s * 0.27)
    c.curve_to(cx, cy + s * 0.45, cx + s * 0.25, cy + s * 0.4, cx + s * 0.3, cy + s * 0.55)
    c.stroke()


def icono_wifi(c, cx, cy, s, g=None, barras: int = 3):
    g = g or s * 0.08
    c.set_line_width(g)
    base = cy + s * 0.32
    for k in range(barras):
        r = s * (0.22 + 0.2 * k)
        c.arc(cx, base, r, math.radians(225), math.radians(315))
        c.stroke()
    c.arc(cx, base, s * 0.06, 0, TAU)
    c.fill()


def icono_nube(c, cx, cy, s, relleno=False, g=None):
    """Nube de tres lóbulos con base plana."""
    g = g or s * 0.06
    c.new_path()
    c.move_to(cx - s * 0.42, cy + s * 0.22)
    c.arc(cx - s * 0.30, cy + s * 0.06, s * 0.17, math.radians(110), math.radians(260))
    c.arc(cx - s * 0.04, cy - s * 0.10, s * 0.26, math.radians(195), math.radians(330))
    c.arc(cx + s * 0.28, cy + s * 0.04, s * 0.19, math.radians(250), math.radians(80))
    c.line_to(cx - s * 0.42, cy + s * 0.22)
    c.close_path()
    if relleno:
        c.fill()
    else:
        c.set_line_width(g)
        c.stroke()


def icono_rayo(c, cx, cy, s):
    pts = [(0.08, -0.5), (-0.22, 0.06), (0.0, 0.06), (-0.08, 0.5), (0.22, -0.08), (0.0, -0.08)]
    c.move_to(cx + pts[0][0] * s, cy + pts[0][1] * s)
    for x, y in pts[1:]:
        c.line_to(cx + x * s, cy + y * s)
    c.close_path()
    c.fill()


def icono_audifonos(c, cx, cy, s, g=None):
    g = g or s * 0.07
    c.set_line_width(g)
    c.arc(cx, cy + s * 0.05, s * 0.36, math.pi, TAU)
    c.stroke()
    for dx in (-1, 1):
        D.rect_redondeado(c, cx + dx * s * 0.36 - s * 0.09, cy + s * 0.02, s * 0.18, s * 0.3, s * 0.06)
        c.fill()


def icono_cargador(c, cx, cy, s, g=None):
    """Cubo de cargador con su cable y un rayo."""
    g = g or s * 0.07
    c.set_line_width(g)
    D.rect_redondeado(c, cx - s * 0.25, cy - s * 0.3, s * 0.5, s * 0.5, s * 0.08)
    c.stroke()
    icono_rayo(c, cx, cy - s * 0.05, s * 0.32)
    c.move_to(cx, cy + s * 0.2)
    c.curve_to(cx, cy + s * 0.4, cx - s * 0.2, cy + s * 0.38, cx - s * 0.3, cy + s * 0.5)
    c.stroke()


def icono_portatil(c, cx, cy, s, g=None):
    g = g or s * 0.07
    c.set_line_width(g)
    D.rect_redondeado(c, cx - s * 0.36, cy - s * 0.3, s * 0.72, s * 0.46, s * 0.04)
    c.stroke()
    c.move_to(cx - s * 0.48, cy + s * 0.26)
    c.line_to(cx + s * 0.48, cy + s * 0.26)
    c.stroke()


def icono_persona(c, cx, cy, s):
    """Silueta neutra (cabeza y hombros)."""
    c.arc(cx, cy - s * 0.18, s * 0.2, 0, TAU)
    c.fill()
    c.move_to(cx - s * 0.38, cy + s * 0.45)
    c.curve_to(cx - s * 0.36, cy + s * 0.05, cx + s * 0.36, cy + s * 0.05, cx + s * 0.38, cy + s * 0.45)
    c.close_path()
    c.fill()


def icono_check(c, cx, cy, s, g=None):
    c.set_line_width(g or s * 0.14)
    c.move_to(cx - s * 0.35, cy)
    c.line_to(cx - s * 0.08, cy + s * 0.28)
    c.line_to(cx + s * 0.4, cy - s * 0.3)
    c.stroke()


def icono_bicho(c, cx, cy, s):
    """Un «bug»: cuerpo ovalado con patas y antenas."""
    D.elipse(c, cx, cy + s * 0.05, s * 0.2, s * 0.28)
    c.arc(cx, cy - s * 0.28, s * 0.11, 0, TAU)
    c.fill()
    c.set_line_width(s * 0.05)
    for k in (-1, 0, 1):
        for lado in (-1, 1):
            c.move_to(cx + lado * s * 0.18, cy + k * s * 0.14 + s * 0.05)
            c.line_to(cx + lado * s * 0.4, cy + k * s * 0.2)
    c.move_to(cx - s * 0.05, cy - s * 0.36)
    c.line_to(cx - s * 0.16, cy - s * 0.5)
    c.move_to(cx + s * 0.05, cy - s * 0.36)
    c.line_to(cx + s * 0.16, cy - s * 0.5)
    c.stroke()


def icono_reloj(c, cx, cy, s, fraccion=0.0, g=None):
    """Reloj con la manecilla en `fraccion` de vuelta."""
    c.set_line_width(g or s * 0.07)
    c.arc(cx, cy, s * 0.45, 0, TAU)
    c.stroke()
    ang = -math.pi / 2 + TAU * fraccion
    c.move_to(cx, cy)
    c.line_to(cx + math.cos(ang) * s * 0.33, cy + math.sin(ang) * s * 0.33)
    c.move_to(cx, cy)
    c.line_to(cx, cy - s * 0.2)
    c.stroke()


def icono_power(c, cx, cy, s, g=None):
    c.set_line_width(g or s * 0.1)
    c.arc(cx, cy, s * 0.38, math.radians(-60), math.radians(240))
    c.stroke()
    c.move_to(cx, cy - s * 0.5)
    c.line_to(cx, cy - s * 0.05)
    c.stroke()


def icono_balanza(c, cx, cy, s, g=None):
    """Balanza de la justicia (orden judicial)."""
    c.set_line_width(g or s * 0.06)
    c.move_to(cx, cy - s * 0.45)
    c.line_to(cx, cy + s * 0.4)
    c.move_to(cx - s * 0.25, cy + s * 0.42)
    c.line_to(cx + s * 0.25, cy + s * 0.42)
    c.move_to(cx - s * 0.42, cy - s * 0.3)
    c.line_to(cx + s * 0.42, cy - s * 0.3)
    c.stroke()
    for lado in (-1, 1):
        x = cx + lado * s * 0.4
        c.move_to(x, cy - s * 0.3)
        c.line_to(x - s * 0.14, cy + s * 0.05)
        c.move_to(x, cy - s * 0.3)
        c.line_to(x + s * 0.14, cy + s * 0.05)
        c.stroke()
        c.arc(x, cy + s * 0.05, s * 0.15, 0, math.pi)
        c.fill()


def icono_carpeta(c, cx, cy, s, g=None):
    """Carpeta (contorno), de ancho `s`."""
    c.set_line_width(g or s * 0.04)
    w, h = s, s * 0.72
    x, y = cx - w / 2, cy - h / 2
    c.move_to(x, y + h * 0.12)
    c.line_to(x, y + h)
    c.line_to(x + w, y + h)
    c.line_to(x + w, y + h * 0.12)
    c.line_to(x + w * 0.45, y + h * 0.12)
    c.line_to(x + w * 0.38, y)
    c.line_to(x + w * 0.04, y)
    c.close_path()
    c.stroke()


def icono_memoria(c, cx, cy, w, h, g=3.0):
    """Módulo de RAM: placa con chips y los contactos abajo."""
    c.set_line_width(g)
    D.rect_redondeado(c, cx - w / 2, cy - h / 2, w, h, 8)
    c.stroke()
    for k in range(4):
        x = cx - w / 2 + w * (0.08 + 0.23 * k)
        c.rectangle(x, cy - h * 0.28, w * 0.16, h * 0.42)
        c.fill()
    for k in range(18):
        x = cx - w / 2 + w * 0.05 + k * w * 0.9 / 18
        c.rectangle(x, cy + h * 0.32, w * 0.025, h * 0.14)
        c.fill()


def eslabon(c, cx, cy, w, h, ang=0.0, g=10.0, grieta: float = 0.0):
    """Eslabón de cadena (óvalo alargado) girado `ang`. `grieta` 0..1 lo abre por un lado."""
    c.save()
    c.translate(cx, cy)
    c.rotate(ang)
    c.set_line_width(g)
    r = h / 2
    if grieta <= 0:
        D.rect_redondeado(c, -w / 2, -h / 2, w, h, r)
        c.stroke()
    else:
        hueco = 0.5 * grieta
        c.new_path()
        c.arc(w / 2 - r, 0, r, -math.pi / 2 + hueco, math.pi / 2)
        c.line_to(-w / 2 + r, h / 2)
        c.arc(-w / 2 + r, 0, r, math.pi / 2, 3 * math.pi / 2)
        c.line_to(w / 2 - r - grieta * 6, -h / 2 - grieta * 4)
        c.stroke()
    c.restore()


def sello(c, cx, cy, s, g=None):
    """Sello de firma: roseta con un visto adentro."""
    pts = []
    for k in range(24):
        r = s * (0.5 if k % 2 == 0 else 0.43)
        a = k * TAU / 24
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    D.rellenar(c, pts, suave=False)


def barras_codigo(c, x, y, ancho, filas, alto_fila, semilla, cols, a=1.0, sangria=True):
    """Líneas de código abstractas: barras redondeadas de colores y largos distintos."""
    rng = np.random.default_rng(semilla)
    nivel = 0
    for f in range(filas):
        if sangria:
            nivel = int(np.clip(nivel + rng.choice([-1, 0, 0, 1]), 0, 3))
        xx = x + nivel * 34
        for _ in range(int(rng.integers(1, 4))):
            largo = rng.uniform(40, 200)
            if xx + largo > x + ancho:
                break
            col = cols[int(rng.integers(len(cols)))]
            D.tinta(c, color(col), a * rng.uniform(0.55, 0.95))
            D.rect_redondeado(c, xx, y + f * alto_fila, largo, alto_fila * 0.42, alto_fila * 0.2)
            c.fill()
            xx += largo + rng.uniform(10, 24)


# =========================================================================== recorrido de Azimuth (3.3 a 3.7)


PASOS = ("la puerta", "el programa", "el error", "la cadena", "la fuerza bruta")


def pasos(img: np.ndarray, activo: int, a: float = 1.0, tema: Tema = SANB, y: float = 92.0, aparicion=None) -> None:
    """Los cinco pasos de cómo entró Azimuth, arriba de la pantalla; el paso `activo` (0..4)
    resaltado. `aparicion`: lista de opacidades para que los pasos entren uno por uno."""
    if a <= 0:
        return
    xs = [W / 2 + (k - 2) * 300 for k in range(5)]
    cp = Capa()
    c = cp.c
    for k, x in enumerate(xs):
        ak = a * (aparicion[k] if aparicion else 1.0)
        if ak <= 0:
            continue
        if k < 4:
            cp.tinta(tema.tenue, 0.5 * ak)
            c.set_line_width(2)
            c.move_to(x + 28, y)
            c.line_to(xs[k + 1] - 28, y)
            c.stroke()
        if k == activo:
            cp.tinta(tema.acento, ak)
            c.arc(x, y, 24, 0, TAU)
            c.fill()
        else:
            cp.tinta(tema.tenue if k > activo else tema.claro, 0.75 * ak)
            c.set_line_width(2.5)
            c.arc(x, y, 22, 0, TAU)
            c.stroke()
    cp.componer(img, sombra=0.25, brillo=0.5, col_brillo=tema.acento, sigma=10)
    for k, x in enumerate(xs):
        ak = a * (aparicion[k] if aparicion else 1.0)
        if ak <= 0:
            continue
        rotulo(img, str(k + 1), x, y + 10, 28, tema.oscuro if k == activo else tema.claro, ak, "centro", sombra=0)
        rotulo(img, PASOS[k], x, y + 66, 25, tema.acento if k == activo else tema.tenue, ak, "centro",
               "Inter-SemiBold.ttf" if k == activo else "Inter-Regular.ttf", sombra=0.3)


# =========================================================================== mapa de California


CALIFORNIA = [
    (-124.21, 42.0), (-120.0, 42.0), (-120.0, 39.0), (-114.63, 35.0), (-114.57, 34.8), (-114.43, 34.6),
    (-114.13, 34.3), (-114.43, 34.08), (-114.53, 33.92), (-114.50, 33.67), (-114.72, 33.41), (-114.70, 33.09),
    (-114.47, 32.84), (-114.72, 32.72), (-117.12, 32.53), (-117.25, 32.7), (-117.28, 33.0), (-117.4, 33.2),
    (-117.6, 33.4), (-117.9, 33.6), (-118.1, 33.75), (-118.4, 33.75), (-118.4, 34.0), (-118.8, 34.0),
    (-119.2, 34.15), (-119.6, 34.4), (-120.0, 34.45), (-120.47, 34.45), (-120.64, 34.6), (-120.6, 35.1),
    (-120.9, 35.45), (-121.3, 35.7), (-121.9, 36.3), (-121.95, 36.6), (-121.8, 36.8), (-122.0, 36.95),
    (-122.4, 37.2), (-122.5, 37.5), (-122.5, 37.78), (-122.7, 37.9), (-123.0, 38.0), (-123.0, 38.25),
    (-123.4, 38.6), (-123.7, 38.95), (-123.8, 39.4), (-123.85, 39.8), (-124.1, 40.1), (-124.35, 40.4),
    (-124.1, 40.8), (-124.15, 41.1), (-124.05, 41.5), (-124.2, 41.8),
]
# Tierra alrededor (Oregón, Nevada, Arizona y Baja California), para que el mar quede solo al oeste.
TIERRA = [(-124.21, 42.0), (-124.5, 43.0), (-124.3, 46.0), (-100.0, 46.0), (-100.0, 25.0), (-114.2, 25.0),
          (-115.6, 29.6), (-116.4, 30.6), (-116.8, 31.6), (-117.12, 32.53)]
SAN_BERNARDINO_LL = (-117.29, 34.11)
LOS_ANGELES_LL = (-118.24, 34.05)


class MapaCalifornia:
    """Mapa de California dibujado una vez a 2× y recorrido con la cámara (acercamiento al punto)."""

    K = 230.0                                   # píxeles del lienzo grande por grado de latitud

    def __init__(self, tema: Tema = SANB):
        self.tema = tema
        self.w, self.h = 3840, 2160
        self.lon0, self.lat0 = -119.2, 37.2
        self.img = self._dibujar()

    def proy(self, lon, lat):
        return (self.w / 2 + (lon - self.lon0) * self.K * math.cos(math.radians(37)), self.h / 2 - (lat - self.lat0) * self.K)

    def _dibujar(self) -> Image.Image:
        t = self.tema
        w, h = self.w, self.h
        mar = gradiente_vertical([(0.0, mezcla(SB["azul_fbi"], NEGRO, 0.55)), (1.0, mezcla(SB["azul_fbi"], NEGRO, 0.8))], w, h)
        mar *= (0.85 + 0.3 * fbm(h // 8, w // 8, 32, 4, 0.5, 33).repeat(8, 0).repeat(8, 1))[..., None]
        s, c = D.lienzo(w, h)
        tierra = [self.proy(*q) for q in TIERRA] + [self.proy(*q) for q in CALIFORNIA[15:]]
        D.tinta(c, mezcla(SB["arena"], NEGRO, 0.82))
        D.rellenar(c, tierra, suave=False)
        pts = [self.proy(*q) for q in CALIFORNIA]
        D.tinta(c, mezcla(SB["arena"], NEGRO, 0.62))
        D.rellenar(c, pts, suave=False)
        D.tinta(c, mezcla(SB["arena"], t.claro, 0.3), 0.85)
        c.set_line_width(4)
        c.move_to(*pts[0])
        for q in pts[1:]:
            c.line_to(*q)
        c.close_path()
        c.stroke()
        capa = D.a_rgba(s)
        alfa = capa[..., 3]
        sombra = cv2.GaussianBlur(np.roll(np.roll(alfa, 26, 0), 16, 1), (0, 0), 24) * 0.55
        img = mar * (1 - sombra)[..., None]
        img = img * (1 - capa[..., 3:]) + capa[..., :3]
        # relieve sutil del desierto y las sierras (ruido dentro de la tierra)
        rel = fbm(h // 4, w // 4, 48, 5, 0.55, 37).repeat(4, 0).repeat(4, 1)
        img *= (0.9 + 0.2 * rel[..., None] * alfa[..., None]) + (1 - alfa[..., None]) * 0.1
        from graficos import texto_alfa
        a = texto_alfa("CALIFORNIA", "Inter-SemiBold.ttf", 66, 0.4)
        cx, cy = self.proy(-119.0, 36.6)
        y0, x0 = int(cy - a.shape[0] / 2), int(cx - a.shape[1] / 2)
        img[y0 : y0 + a.shape[0], x0 : x0 + a.shape[1]] += a[..., None] * 0.07
        return Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))

    def ver(self, u: float, objetivo=SAN_BERNARDINO_LL, zoom_max: float = 3.2) -> tuple[np.ndarray, float, float, float]:
        """Cuadro del mapa con el acercamiento `u` (0..1) hacia `objetivo`. Devuelve la imagen, la
        posición del objetivo en pantalla y la escala actual."""
        fx, fy = self.proy(*objetivo)
        z = 1.0 + (zoom_max - 1.0) * u
        cx = self.w / 2 + (fx - self.w / 2) * u
        cy = self.h / 2 + (fy - self.h / 2) * u
        bw, bh = self.w / z, self.h / z
        x0 = min(max(cx - bw / 2, 0), self.w - bw)
        y0 = min(max(cy - bh / 2, 0), self.h - bh)
        img = np.asarray(self.img.resize((W, H), Image.BILINEAR, box=caja_dentro((x0, y0, x0 + bw, y0 + bh), self.w, self.h)), np.float32) / 255
        return img, (fx - x0) * W / bw, (fy - y0) * H / bh, W / bw
