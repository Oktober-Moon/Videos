"""Piezas de diagramas técnicos animados (chips, teléfonos, claves, flechas) dibujadas con cairo.

Cada pieza recibe un avance `p` (0..1) para dibujarse paso a paso al ritmo de la narración: una
flecha crece, una caja traza su borde y luego se rellena, un candado se cierra. Se dibuja sobre un
`Trazo` (un lienzo de pantalla completa) que al final se compone sobre la imagen con un brillo
opcional, como luz de pantalla.
"""

from __future__ import annotations

import functools
import math

import numpy as np
from scipy import ndimage

import dibujo as D
from graficos import H, W, color, desenfoque, fbm, gradiente_vertical, lim, suave, texto_alfa

TAU = math.tau


# --------------------------------------------------------------------------- lienzo


class Trazo:
    """Lienzo de cairo a pantalla completa para un cuadro."""

    def __init__(self):
        self.s, self.c = D.lienzo(W, H)

    def tinta(self, col, a: float = 1.0) -> None:
        D.tinta(self.c, color(col), a)

    def componer(self, img: np.ndarray, brillo: float = 0.0, col_brillo=None, sigma: float = 10.0) -> np.ndarray:
        capa = D.a_rgba(self.s)
        if brillo > 0:
            b = desenfoque(capa[..., 3:] if col_brillo is not None else capa[..., :3], sigma)
            img += (b * color(col_brillo) if col_brillo is not None else b) * brillo
        img *= 1 - capa[..., 3:]
        img += capa[..., :3]
        return img


@functools.lru_cache(maxsize=8)
def fondo_tecnico(oscuro: tuple, claro: tuple, puntos: float = 0.06, semilla: int = 1) -> np.ndarray:
    """Fondo de diagrama: degradado oscuro con una retícula de puntos tenue y algo de textura."""
    img = gradiente_vertical([(0.0, np.array(claro) * 0.55 + np.array(oscuro) * 0.45), (1.0, np.array(oscuro))])
    img = img * (0.9 + 0.2 * fbm(H // 8, W // 8, 24, 4, 0.5, semilla).repeat(8, 0).repeat(8, 1))[..., None]
    yy, xx = np.mgrid[0:H, 0:W]
    reticula = ((xx % 48 == 0) & (yy % 48 == 0)).astype(np.float32)
    reticula = ndimage.grey_dilation(reticula, size=(2, 2))
    img += reticula[..., None] * np.array(claro) * puntos
    img.setflags(write=False)
    return img


def fondo(oscuro, claro, puntos: float = 0.06) -> np.ndarray:
    return fondo_tecnico(tuple(map(float, color(oscuro))), tuple(map(float, color(claro))), puntos).copy()


# --------------------------------------------------------------------------- trazos animados


def linea(c, pts, p: float = 1.0, grosor: float = 3.0) -> None:
    """Polilínea dibujada hasta la fracción `p` de su largo."""
    p = lim(p)
    if p <= 0 or len(pts) < 2:
        return
    pts = [np.asarray(q, float) for q in pts]
    largos = [np.linalg.norm(b - a) for a, b in zip(pts, pts[1:])]
    falta = sum(largos) * p
    c.set_line_width(grosor)
    c.move_to(*pts[0])
    for a, b, l in zip(pts, pts[1:], largos):
        if falta >= l:
            c.line_to(*b)
            falta -= l
        else:
            q = a + (b - a) * (falta / max(l, 1e-9))
            c.line_to(*q)
            break
    c.stroke()


def flecha(c, a, b, p: float = 1.0, grosor: float = 4.0, punta: float = 18.0, curva: float = 0.0) -> np.ndarray:
    """Flecha de a a b que crece con `p`; `curva` la arquea (px). Devuelve la punta actual."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = np.array([-(b - a)[1], (b - a)[0]])
    n = n / (np.linalg.norm(n) + 1e-9)
    m = (a + b) / 2 + n * curva
    us = np.linspace(0, 1, 40)
    pts = [(1 - u) ** 2 * a + 2 * (1 - u) * u * m + u * u * b for u in us]
    p = lim(p)
    if p <= 0:
        return a
    k = max(2, int(round(p * (len(pts) - 1))) + 1)
    linea(c, pts[:k], 1.0, grosor)
    fin, antes = pts[k - 1], pts[max(0, k - 3)]
    d = fin - antes
    d = d / (np.linalg.norm(d) + 1e-9)
    nn = np.array([-d[1], d[0]])
    c.move_to(*(fin + d * punta * 0.35))
    c.line_to(*(fin - d * punta * 0.7 + nn * punta * 0.5))
    c.line_to(*(fin - d * punta * 0.7 - nn * punta * 0.5))
    c.close_path()
    c.fill()
    return fin


def caja(c, x, y, w, h, r: float = 14, p: float = 1.0, grosor: float = 3.0, relleno=None, a_relleno: float = 1.0) -> None:
    """Caja redondeada: el borde se traza con `p` y el relleno aparece en la segunda mitad."""
    p = lim(p)
    if p <= 0:
        return
    if relleno is not None and p > 0.5:
        D.tinta(c, color(relleno), a_relleno * suave((p - 0.5) * 2))
        D.rect_redondeado(c, x, y, w, h, r)
        c.fill()
    perimetro = 2 * (w + h)
    c.save()
    c.set_line_width(grosor)
    if p * 1.6 < 1.0:
        c.set_dash([perimetro * p * 1.6, perimetro * 2])
    D.rect_redondeado(c, x, y, w, h, r)
    c.stroke()
    c.restore()


# --------------------------------------------------------------------------- íconos


def candado(c, cx, cy, s: float, cerrado: float = 1.0, grosor: float = 0.0) -> None:
    """Candado de alto `s`: el arco baja y se cierra con `cerrado` (0 abierto, 1 cerrado)."""
    w, h = s * 0.8, s * 0.55
    D.rect_redondeado(c, cx - w / 2, cy - h * 0.1, w, h, s * 0.08)
    c.fill()
    alza = (1 - cerrado) * s * 0.28
    c.set_line_width(grosor or s * 0.11)
    r = w * 0.32
    c.new_sub_path()
    c.arc(cx, cy - h * 0.1 - r * 0.9 - alza, r, math.pi, 0)
    c.move_to(cx - r, cy - h * 0.1 - r * 0.9 - alza)
    c.line_to(cx - r, cy - h * 0.1 + (0 if cerrado > 0.5 else -alza))
    c.move_to(cx + r, cy - h * 0.1 - r * 0.9 - alza)
    c.line_to(cx + r, cy - h * 0.1 - alza * 0.2)
    c.stroke()


def telefono(c, cx, cy, h: float, grosor: float = 4.0, pantalla=None, a_pantalla: float = 1.0) -> tuple:
    """Teléfono de frente (sin botón): devuelve el rectángulo de la pantalla (x, y, w, h)."""
    w = h * 0.49
    x, y = cx - w / 2, cy - h / 2
    if pantalla is not None:
        trazo = c.get_source()                                    # el contorno conserva su color
        D.tinta(c, color(pantalla), a_pantalla)
        D.rect_redondeado(c, x + h * 0.025, y + h * 0.025, w - h * 0.05, h - h * 0.05, h * 0.07)
        c.fill()
        c.set_source(trazo)
    c.set_line_width(grosor)
    D.rect_redondeado(c, x, y, w, h, h * 0.09)
    c.stroke()
    D.rect_redondeado(c, cx - h * 0.06, y + h * 0.035, h * 0.12, h * 0.025, h * 0.012)
    c.fill()
    return x + h * 0.025, y + h * 0.025, w - h * 0.05, h - h * 0.05


def chip(c, cx, cy, s: float, grosor: float = 3.0, pines: int = 7, p: float = 1.0) -> None:
    """Chip cuadrado de lado `s` con patas en los cuatro lados."""
    caja(c, cx - s / 2, cy - s / 2, s, s, s * 0.06, p, grosor)
    if p < 0.6:
        return
    a = suave((p - 0.6) / 0.4)
    c.set_line_width(grosor * 0.9)
    largo = s * 0.09 * a
    for k in range(pines):
        u = -s / 2 + s * (k + 1) / (pines + 1)
        for (x0, y0, dx, dy) in ((cx + u, cy - s / 2, 0, -1), (cx + u, cy + s / 2, 0, 1),
                                 (cx - s / 2, cy + u, -1, 0), (cx + s / 2, cy + u, 1, 0)):
            c.move_to(x0, y0)
            c.line_to(x0 + dx * largo, y0 + dy * largo)
    c.stroke()


def computadora(c, cx, cy, s: float, grosor: float = 4.0, p: float = 1.0) -> tuple:
    """Monitor de laboratorio con su pie; devuelve el rectángulo de la pantalla."""
    w, h = s * 1.6, s
    caja(c, cx - w / 2, cy - h / 2, w, h, s * 0.04, p, grosor)
    if p > 0.5:
        a = suave((p - 0.5) * 2)
        c.set_line_width(grosor)
        c.move_to(cx, cy + h / 2)
        c.line_to(cx, cy + h / 2 + s * 0.16 * a)
        c.move_to(cx - s * 0.3 * a, cy + h / 2 + s * 0.17)
        c.line_to(cx + s * 0.3 * a, cy + h / 2 + s * 0.17)
        c.stroke()
    m = s * 0.05
    return cx - w / 2 + m, cy - h / 2 + m, w - 2 * m, h - 2 * m


def archivo(c, x, y, s: float, grosor: float = 3.0) -> None:
    """Hoja con la esquina doblada, de alto `s`."""
    w = s * 0.78
    d = s * 0.25
    c.set_line_width(grosor)
    c.move_to(x, y)
    c.line_to(x + w - d, y)
    c.line_to(x + w, y + d)
    c.line_to(x + w, y + s)
    c.line_to(x, y + s)
    c.close_path()
    c.move_to(x + w - d, y)
    c.line_to(x + w - d, y + d)
    c.line_to(x + w, y + d)
    c.stroke()


def tarjeta_grafica(c, x, y, s: float, grosor: float = 3.0, giro: float = 0.0) -> None:
    """Tarjeta gráfica de perfil: placa, dos ventiladores y el conector."""
    w, h = s * 2.2, s * 0.9
    D.rect_redondeado(c, x, y, w, h, s * 0.06)
    c.set_line_width(grosor)
    c.stroke()
    for k in (0.3, 0.72):
        fx, fy, r = x + w * k, y + h * 0.5, h * 0.34
        c.arc(fx, fy, r, 0, TAU)
        c.stroke()
        for a in range(5):
            ang = giro + a * TAU / 5
            c.move_to(fx, fy)
            c.line_to(fx + math.cos(ang) * r * 0.85, fy + math.sin(ang) * r * 0.85)
        c.stroke()
    c.rectangle(x + w * 0.1, y + h, w * 0.6, s * 0.08)
    c.fill()


def llave(c, cx, cy, s: float, grosor: float = 0.0) -> None:
    """Llave de largo `s` acostada (cabeza redonda a la izquierda)."""
    g = grosor or s * 0.07
    r = s * 0.17
    c.set_line_width(g)
    c.arc(cx - s / 2 + r, cy, r, 0, TAU)
    c.stroke()
    c.move_to(cx - s / 2 + 2 * r, cy)
    c.line_to(cx + s / 2, cy)
    c.move_to(cx + s / 2 - s * 0.05, cy)
    c.line_to(cx + s / 2 - s * 0.05, cy + s * 0.15)
    c.move_to(cx + s / 2 - s * 0.2, cy)
    c.line_to(cx + s / 2 - s * 0.2, cy + s * 0.11)
    c.stroke()


def cruz(c, cx, cy, s: float, grosor: float = 5.0) -> None:
    c.set_line_width(grosor)
    c.move_to(cx - s / 2, cy - s / 2)
    c.line_to(cx + s / 2, cy + s / 2)
    c.move_to(cx + s / 2, cy - s / 2)
    c.line_to(cx - s / 2, cy + s / 2)
    c.stroke()


# --------------------------------------------------------------------------- ceros y unos


@functools.lru_cache(maxsize=16)
def _digitos(tam: int, nombre: str = "Inter-Regular.ttf") -> tuple:
    return tuple(texto_alfa(ch, nombre, tam, margen=0) for ch in "01")


def bits(img: np.ndarray, x0: int, y0: int, cols: int, filas: int, tam: int, t: float, col, *, semilla: int = 0,
         cambio: float = 6.0, opacidad: float = 1.0, mascara=None) -> None:
    """Rejilla de ceros y unos que parpadean: cada celda cambia de valor a su propio ritmo.

    `mascara(i, j) -> 0..1` permite encender solo una parte (p. ej. un barrido de izquierda a derecha).
    """
    if opacidad <= 0:
        return
    g0, g1 = _digitos(tam)
    rng = np.random.default_rng(semilla)
    fase = rng.uniform(0, 100, (filas, cols))
    vel = rng.uniform(0.3, 1.0, (filas, cols)) * cambio
    valor = ((np.floor(fase + t * vel)).astype(int) * 2654435761 % 7) < 3
    brillo = 0.45 + 0.55 * rng.random((filas, cols))
    paso_x, paso_y = int(tam * 0.9), int(tam * 1.25)
    colr = color(col)
    for i in range(filas):
        for j in range(cols):
            m = mascara(i, j) if mascara else 1.0
            if m <= 0.01:
                continue
            g = g1 if valor[i, j] else g0
            x, y = x0 + j * paso_x, y0 + i * paso_y
            h, w = g.shape
            if 0 <= y < H - h and 0 <= x < W - w:
                img[y : y + h, x : x + w] += g[..., None] * colr * (brillo[i, j] * opacidad * m)


def ruido_visual(h: int, w: int, t: float, semilla: int = 0) -> np.ndarray:
    """Estática gris (archivos cifrados que no se pueden leer)."""
    rng = np.random.default_rng(semilla + int(t * 24) * 7919)
    n = rng.random((h // 3 + 1, w // 3 + 1)).astype(np.float32)
    return n.repeat(3, 0).repeat(3, 1)[:h, :w]


# --------------------------------------------------------------------------- acabado con profundidad
# (agregado para las escenas 2 y 4: las piezas flotan sobre el fondo con sombra suave, las tarjetas
# son de vidrio esmerilado y el fondo tiene un foco de luz; lo de arriba sigue igual)


def componer_relieve(trazo: Trazo, img: np.ndarray, *, sombra: float = 0.55, dx: int = 9, dy: int = 13,
                     sigma: float = 13.0, brillo: float = 0.0, col_brillo=None, sigma_brillo: float = 12.0) -> np.ndarray:
    """Como `Trazo.componer`, con una sombra difusa debajo de lo dibujado: el diagrama se despega del
    fondo. `brillo` agrega el halo de color de las piezas encendidas. Trabaja solo en la zona que
    ocupa el dibujo (más el alcance de la sombra y del halo)."""
    import cv2

    capa = D.a_rgba(trazo.s)
    alfa = capa[..., 3]
    filas = np.flatnonzero(alfa.max(axis=1) > 0)
    if filas.size == 0:
        return img
    cols = np.flatnonzero(alfa.max(axis=0) > 0)
    pad = int(3 * max(sigma, sigma_brillo if brillo > 0 else 0)) + max(abs(dx), abs(dy)) + 4
    ya, yb = max(0, filas[0] - pad), min(H, filas[-1] + 1 + pad)
    xa, xb = max(0, cols[0] - pad), min(W, cols[-1] + 1 + pad)
    c = capa[ya:yb, xa:xb]
    z = img[ya:yb, xa:xb]
    if sombra > 0:
        s = np.roll(np.roll(c[..., 3], dy, axis=0), dx, axis=1)
        h, w = s.shape
        chico = cv2.GaussianBlur(cv2.resize(s, (max(1, w // 2), max(1, h // 2)), interpolation=cv2.INTER_AREA), (0, 0), sigma / 2)
        s = cv2.resize(chico, (w, h), interpolation=cv2.INTER_LINEAR)
        z *= (1 - np.clip(s * sombra, 0, 0.9))[..., None]
    if brillo > 0:
        fuente = c[..., 3:] if col_brillo is not None else c[..., :3]
        h, w = fuente.shape[:2]
        chico = cv2.resize(np.ascontiguousarray(fuente), (max(1, w // 2), max(1, h // 2)), interpolation=cv2.INTER_AREA)
        b = cv2.resize(cv2.GaussianBlur(chico, (0, 0), sigma_brillo / 2), (w, h), interpolation=cv2.INTER_LINEAR)
        if b.ndim == 2:
            b = b[..., None]
        z += (b * color(col_brillo) if col_brillo is not None else b) * brillo
    z *= 1 - c[..., 3:]
    z += c[..., :3]
    return img


@functools.lru_cache(maxsize=128)
def _tarjeta_forma(x0: int, y0: int, x1: int, y1: int, radio: int):
    """Máscara, sombra y filo de luz de una tarjeta, recortados a su zona (se dibujan una sola vez)."""
    import cv2

    pad = 72
    ya, yb, xa, xb = max(0, y0 - pad), min(H, y1 + pad), max(0, x0 - pad), min(W, x1 + pad)
    w, h = xb - xa, yb - ya
    s, c = D.lienzo(w, h)
    D.tinta(c, (1, 1, 1), 1.0)
    D.rect_redondeado(c, x0 - xa, y0 - ya, x1 - x0, y1 - y0, radio)
    c.fill()
    m = D.a_alfa(s)
    sombra = cv2.GaussianBlur(np.roll(np.roll(m, 16, 0), 8, 1), (0, 0), 18)
    s2, c2 = D.lienzo(w, h)
    D.tinta(c2, (1, 1, 1), 1.0)
    c2.set_line_width(1.6)
    D.rect_redondeado(c2, x0 - xa + 0.8, y0 - ya + 0.8, x1 - x0 - 1.6, y1 - y0 - 1.6, radio)
    c2.stroke()
    degr = np.clip(1.0 - (np.arange(h, dtype=np.float32)[:, None] - (y0 - ya)) / max(1, (y1 - y0)), 0.15, 1.0)
    filo = D.a_alfa(s2) * degr
    for arr in (m, sombra, filo):
        arr.setflags(write=False)
    return ya, yb, xa, xb, m, sombra, filo


def tarjeta(img: np.ndarray, x0: int, y0: int, x1: int, y1: int, a: float = 1.0, *, radio: int = 22,
            tinte=(1.0, 1.0, 1.0), oscuro: float = 0.35, borde: float = 0.22, sombra: float = 0.5) -> np.ndarray:
    """Tarjeta de vidrio esmerilado con esquinas redondeadas: lo de atrás se desenfoca y se oscurece,
    con un filo de luz arriba y una sombra suave debajo. Devuelve la imagen (se modifica en su lugar)."""
    import cv2

    if a <= 0.002:
        return img
    ya, yb, xa, xb, m, sm, filo = _tarjeta_forma(int(x0), int(y0), int(x1), int(y1), int(radio))
    zona = img[ya:yb, xa:xb]
    if sombra > 0:
        zona *= (1 - np.clip(sm * sombra * a, 0, 0.8))[..., None]
    tinte = np.asarray(color(tinte), np.float32)
    h, w = zona.shape[:2]                                  # desenfoque a un cuarto de resolución: igual de suave, 10 veces más rápido
    chica = cv2.resize(zona, (max(1, w // 4), max(1, h // 4)), interpolation=cv2.INTER_AREA)
    borrosa = cv2.resize(cv2.GaussianBlur(chica, (0, 0), 4.5), (w, h), interpolation=cv2.INTER_LINEAR)
    borrosa = borrosa * (1 - oscuro) + tinte * 0.035
    k = (m * a)[..., None]
    zona[:] = zona * (1 - k) + borrosa * k
    if borde > 0:
        zona += (filo * borde * a)[..., None] * tinte
    return img


@functools.lru_cache(maxsize=8)
def _foco(cx: float, cy: float, radio: float) -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot((xx - cx) / radio, (yy - cy) / radio)
    f = np.exp(-d * d)
    f.setflags(write=False)
    return f


def fondo_profundo(oscuro, claro, foco=(W * 0.5, H * 0.45), radio: float = 900.0, luz: float = 0.55,
                   puntos: float = 0.05) -> np.ndarray:
    """Fondo de diagrama con un foco de luz suave detrás del centro (da profundidad), la retícula de
    puntos tenue y la textura de `fondo`."""
    img = fondo(oscuro, claro, puntos)
    img += _foco(float(foco[0]), float(foco[1]), float(radio))[..., None] * np.asarray(color(claro), np.float32) * luz * 0.25
    return img


def mover(c, t: float, dur: float, z0: float = 1.0, z1: float = 1.04, centro=(W / 2, H / 2), deriva=(0.0, 0.0)) -> None:
    """Movimiento de cámara lento sobre el diagrama (acercamiento y deriva), aplicado al contexto de
    cairo: así los diagramas no quedan quietos como una lámina."""
    u = lim(t / max(dur, 1e-6))
    u = 0.5 - 0.5 * math.cos(math.pi * u)
    z = z0 + (z1 - z0) * u
    cx, cy = centro
    c.translate(cx + deriva[0] * u, cy + deriva[1] * u)
    c.scale(z, z)
    c.translate(-cx, -cy)


def a_pantalla(x: float, y: float, t: float, dur: float, z0: float = 1.0, z1: float = 1.04, centro=(W / 2, H / 2),
               deriva=(0.0, 0.0)) -> tuple[float, float, float]:
    """Dónde cae el punto (x, y) del diagrama con el mismo movimiento de `mover`, y la escala: para
    poner los rótulos encima en su lugar."""
    u = lim(t / max(dur, 1e-6))
    u = 0.5 - 0.5 * math.cos(math.pi * u)
    z = z0 + (z1 - z0) * u
    cx, cy = centro
    return cx + deriva[0] * u + (x - cx) * z, cy + deriva[1] * u + (y - cy) * z, z
