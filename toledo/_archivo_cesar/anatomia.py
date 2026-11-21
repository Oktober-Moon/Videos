"""Figuras realistas por campos de distancia con signo (SDF).

Las siluetas de `siluetas.py` se arman con cápsulas de grosor casi constante: se leen bien de
lejos, pero de cerca parecen tubos. Aquí cada figura se arma con primitivas anatómicas (conos
redondeados con el perfil de cada músculo, elipses, polígonos suaves, hebras de pelo) unidas
con un mínimo suave, de modo que hombro, codo o rodilla se funden como en un cuerpo real.

El campo de distancia sirve además para iluminar: su gradiente es la normal del contorno; con
ella se calcula el borde que mira hacia la luz en un contraluz, y con el espesor local, la luz
que atraviesa las partes delgadas (orejas, dedos, tela).

Unidades: cada modelo se describe en unidades propias (altura de la persona, alzada del caballo,
largo de la mano), con x hacia donde mira la figura e y hacia abajo; al dibujar se escala a
píxeles de pantalla. Los ángulos van en grados; positivo gira en el sentido del reloj en
pantalla, que para una figura que mira a la derecha es «hacia delante».
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, fields

import cairo
import numpy as np
from scipy import ndimage

from graficos import color

LEJOS = np.float32(1e4)


# =========================================================================== distancias


def d_cono(X, Y, a, b, ra: float, rb: float):
    """Cono redondeado (cápsula de radios distintos) de `a` (radio ra) a `b` (radio rb)."""
    ax, ay = float(a[0]), float(a[1])
    vx, vy = float(b[0]) - ax, float(b[1]) - ay
    h = math.hypot(vx, vy)
    px, py = X - ax, Y - ay
    if h < 1e-6 or abs(ra - rb) >= h:
        da = np.sqrt(px * px + py * py) - ra
        db = np.sqrt((X - float(b[0])) ** 2 + (Y - float(b[1])) ** 2) - rb
        return np.minimum(da, db)
    ux, uy = vx / h, vy / h
    qy = px * ux + py * uy
    qx = np.abs(py * ux - px * uy)
    bb = (ra - rb) / h
    aa = math.sqrt(1.0 - bb * bb)
    k = qx * -bb + qy * aa
    lado = qx * aa + qy * bb - ra
    da = np.sqrt(qx * qx + qy * qy) - ra
    db = np.sqrt(qx * qx + (qy - h) ** 2) - rb
    return np.where(k < 0, da, np.where(k > aa * h, db, lado))


def d_elipse(X, Y, c, rx: float, ry: float, ang: float = 0.0):
    """Elipse (aproximación de distancia de Quílez, exacta en el borde)."""
    r = math.radians(ang)
    ca, sa = math.cos(r), math.sin(r)
    px, py = X - float(c[0]), Y - float(c[1])
    lx = px * ca + py * sa
    ly = -px * sa + py * ca
    k0 = np.sqrt((lx / rx) ** 2 + (ly / ry) ** 2)
    k1 = np.sqrt((lx / (rx * rx)) ** 2 + (ly / (ry * ry)) ** 2)
    d = k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)
    return np.where(k0 < 1e-6, -min(rx, ry), d)


def spline(pts, n: int = 6, cerrado: bool = True) -> np.ndarray:
    """Catmull-Rom uniforme: `n` puntos por tramo."""
    p = np.asarray(pts, np.float64)
    if len(p) < 3:
        return p
    P = np.vstack([p[-1:], p, p[:2]]) if cerrado else np.vstack([p[:1], p, p[-1:]])
    tramos = len(p) if cerrado else len(p) - 1
    t = np.linspace(0, 1, n, endpoint=False)[:, None]
    out = []
    for i in range(tramos):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    if not cerrado:
        out.append(p[-1:])
    return np.vstack(out)


def _campo_poligono(pts: np.ndarray, x0: int, y0: int, w: int, h: int) -> np.ndarray:
    """Distancia con signo a un polígono en una ventana: cairo da la cobertura con antialias
    (borde subpíxel) y la transformada de distancia euclidiana, el resto del campo."""
    sup = cairo.ImageSurface(cairo.FORMAT_A8, w, h)
    c = cairo.Context(sup)
    c.translate(-x0, -y0)
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()
    c.set_source_rgba(0, 0, 0, 1)
    c.fill()
    sup.flush()
    paso = sup.get_stride()
    cob = np.frombuffer(sup.get_data(), np.uint8).reshape(h, paso)[:, :w].astype(np.float32) / 255.0
    dentro = cob >= 0.5
    if not dentro.any():
        return np.full((h, w), LEJOS, np.float32)
    d_in = ndimage.distance_transform_edt(dentro).astype(np.float32)
    d_out = ndimage.distance_transform_edt(~dentro).astype(np.float32)
    d = np.where(dentro, 0.5 - d_in, d_out - 0.5)
    borde = (cob > 0.0) & (cob < 1.0)
    return np.where(borde, 0.5 - cob, d)


# =========================================================================== la silueta


class Silueta:
    """Campo de distancia (px) sobre una ventana de pantalla, compuesto con uniones suaves."""

    def __init__(self, caja, margen: int = 8):
        x0, y0, x1, y1 = caja
        self.x0 = int(math.floor(x0)) - margen
        self.y0 = int(math.floor(y0)) - margen
        self.w = max(1, int(math.ceil(x1)) + margen - self.x0)
        self.h = max(1, int(math.ceil(y1)) + margen - self.y0)
        self.d = np.full((self.h, self.w), LEJOS, np.float32)

    # ---- ventanas
    def _zona(self, x0, y0, x1, y1):
        j0 = max(0, int(math.floor(x0)) - self.x0)
        j1 = min(self.w, int(math.ceil(x1)) - self.x0 + 1)
        i0 = max(0, int(math.floor(y0)) - self.y0)
        i1 = min(self.h, int(math.ceil(y1)) - self.y0 + 1)
        if j0 >= j1 or i0 >= i1:
            return None
        X = (np.arange(j0, j1, dtype=np.float32) + np.float32(self.x0 + 0.5))[None, :]
        Y = (np.arange(i0, i1, dtype=np.float32) + np.float32(self.y0 + 0.5))[:, None]
        return (slice(i0, i1), slice(j0, j1)), X, Y

    def _mezclar(self, sl, dn, k: float, modo: str) -> None:
        d = self.d[sl]
        dn = dn.astype(np.float32, copy=False)
        if modo == "union":
            if k <= 0:
                np.minimum(d, dn, out=d)
            else:
                h = np.clip(0.5 + 0.5 * (d - dn) / k, 0.0, 1.0)
                self.d[sl] = d + (dn - d) * h - k * h * (1.0 - h)
        elif modo == "resta":
            if k <= 0:
                np.maximum(d, -dn, out=d)
            else:
                h = np.clip(0.5 - 0.5 * (d + dn) / k, 0.0, 1.0)
                self.d[sl] = d + (-dn - d) * h + k * h * (1.0 - h)
        else:
            raise ValueError(modo)

    def _aplicar(self, caja, fn, k: float, modo: str) -> None:
        m = k + 3
        z = self._zona(caja[0] - m, caja[1] - m, caja[2] + m, caja[3] + m)
        if z is None:
            return
        sl, X, Y = z
        self._mezclar(sl, fn(X, Y), k, modo)

    # ---- primitivas (coordenadas y radios en px de pantalla)
    def cono(self, a, b, ra: float, rb: float, k: float = 0.0, modo: str = "union") -> None:
        r = max(ra, rb)
        caja = (min(a[0], b[0]) - r, min(a[1], b[1]) - r, max(a[0], b[0]) + r, max(a[1], b[1]) + r)
        self._aplicar(caja, lambda X, Y: d_cono(X, Y, a, b, ra, rb), k, modo)

    def circulo(self, c, r: float, k: float = 0.0, modo: str = "union") -> None:
        self.cono(c, c, r, r, k, modo)

    def elipse(self, c, rx: float, ry: float, ang: float = 0.0, k: float = 0.0, modo: str = "union") -> None:
        r = max(rx, ry)
        caja = (c[0] - r, c[1] - r, c[0] + r, c[1] + r)
        self._aplicar(caja, lambda X, Y: d_elipse(X, Y, c, rx, ry, ang), k, modo)

    def poligono(self, pts, k: float = 0.0, modo: str = "union", suave: bool = True, n: int = 5) -> None:
        p = spline(pts, n) if suave else np.asarray(pts, np.float64)
        m = k + 4
        x0 = int(math.floor(p[:, 0].min() - m))
        y0 = int(math.floor(p[:, 1].min() - m))
        x1 = int(math.ceil(p[:, 0].max() + m))
        y1 = int(math.ceil(p[:, 1].max() + m))
        j0, j1 = max(0, x0 - self.x0), min(self.w, x1 - self.x0)
        i0, i1 = max(0, y0 - self.y0), min(self.h, y1 - self.y0)
        if j0 >= j1 or i0 >= i1:
            return
        dn = _campo_poligono(p, self.x0 + j0, self.y0 + i0, j1 - j0, i1 - i0)
        self._mezclar((slice(i0, i1), slice(j0, j1)), dn, k, modo)

    def hebra(self, pts, r0: float, r1: float, k: float = 0.0) -> None:
        """Cadena de conos con radio que va de r0 a r1 (pelo, crin, cuerdas)."""
        p = np.asarray(pts, np.float64)
        n = len(p) - 1
        for i in range(n):
            ra = r0 + (r1 - r0) * i / n
            rb = r0 + (r1 - r0) * (i + 1) / n
            self.cono(p[i], p[i + 1], ra, rb, k)

    # ---- lectura
    def alfa(self, blando: float = 1.0) -> np.ndarray:
        return np.clip(0.5 - self.d / blando, 0.0, 1.0)

    def rejilla(self):
        X = np.arange(self.w, dtype=np.float32)[None, :] + np.float32(self.x0 + 0.5)
        Y = np.arange(self.h, dtype=np.float32)[:, None] + np.float32(self.y0 + 0.5)
        return X, Y

    def normal(self, suavizado: float = 0.8):
        d = np.minimum(self.d, 60.0)
        if suavizado > 0:
            d = ndimage.gaussian_filter(d, suavizado)
        gy, gx = np.gradient(d)
        n = np.sqrt(gx * gx + gy * gy) + 1e-6
        return gx / n, gy / n

    def borde(self, luz, ancho: float, potencia: float = 1.5, ambiente: float = 0.0,
              direccion: bool = False) -> np.ndarray:
        """Intensidad (0..1) del borde que mira hacia la luz: un punto de pantalla o, con
        `direccion`, un vector hacia la fuente."""
        nx, ny = self.normal()
        if direccion:
            lx, ly = float(luz[0]), float(luz[1])
            m = math.hypot(lx, ly) + 1e-9
            lx, ly = lx / m, ly / m
        else:
            X, Y = self.rejilla()
            lx, ly = float(luz[0]) - X, float(luz[1]) - Y
            m = np.sqrt(lx * lx + ly * ly) + 1e-6
            lx, ly = lx / m, ly / m
        cara = np.clip(nx * lx + ny * ly, 0.0, 1.0) ** potencia
        banda = np.clip(1.0 + self.d / ancho, 0.0, 1.0) ** 2
        return self.alfa() * banda * (ambiente + (1.0 - ambiente) * cara)

    def espesor(self, radio: float) -> np.ndarray:
        """Medio espesor local (px) de la parte a la que pertenece cada píxel."""
        dentro = np.clip(-self.d, 0.0, 200.0)
        return ndimage.maximum_filter(dentro, size=2 * int(radio) + 1)


def pintar(img: np.ndarray, sil: Silueta, base, *, bordes=(), trans=None, luces=(),
           opacidad: float = 1.0, blando: float = 1.0, tapado: np.ndarray | None = None
           ) -> np.ndarray | None:
    """Compone la silueta sobre `img` (RGB float) con su color base y sus luces.

    bordes: dicts con luz, ancho, color, fuerza y opcionales potencia, ambiente, direccion.
    trans:  dict con radio, tau, color, fuerza: luz que atraviesa las partes delgadas.
    luces:  pares (mapa h×w, color) que se suman tal cual (pliegues translúcidos, reflejos).
    tapado: alfa a pantalla completa de lo que ya está detrás; donde hay algo oscuro detrás,
            no hay cielo que ilumine el borde. Se actualiza con esta silueta.
    Devuelve el alfa de la ventana o None si quedó fuera.
    """
    alto, ancho = img.shape[:2]
    j0, i0 = max(0, -sil.x0), max(0, -sil.y0)
    j1, i1 = min(sil.w, ancho - sil.x0), min(sil.h, alto - sil.y0)
    if j0 >= j1 or i0 >= i1 or opacidad <= 0:
        return None
    a = sil.alfa(blando)
    libre = np.ones_like(a)
    if tapado is not None:
        libre[i0:i1, j0:j1] = 1.0 - 0.9 * tapado[sil.y0 + i0 : sil.y0 + i1, sil.x0 + j0 : sil.x0 + j1]
    col = np.empty(a.shape + (3,), np.float32)
    col[...] = color(base)
    for b in bordes:
        e = sil.borde(b["luz"], b["ancho"], b.get("potencia", 1.5), b.get("ambiente", 0.0),
                      b.get("direccion", False))
        col += (e * libre)[..., None] * (color(b["color"]) * b["fuerza"])
    if trans:
        t = np.exp(-sil.espesor(trans["radio"]) / trans["tau"]) * libre
        col += t[..., None] * (color(trans["color"]) * trans["fuerza"])
    for mapa, c in luces:
        col += mapa[..., None] * color(c)
    aa = a[i0:i1, j0:j1, None] * opacidad
    region = img[sil.y0 + i0 : sil.y0 + i1, sil.x0 + j0 : sil.x0 + j1]
    region *= 1.0 - aa
    region += col[i0:i1, j0:j1] * aa
    if tapado is not None:
        zona = tapado[sil.y0 + i0 : sil.y0 + i1, sil.x0 + j0 : sil.x0 + j1]
        np.maximum(zona, aa[..., 0], out=zona)
    return a


def estampar(rgba: np.ndarray, sil: Silueta, col, opacidad: float = 1.0, blando: float = 1.0) -> None:
    """Hornea la silueta en una capa RGBA premultiplicada (operador «sobre»)."""
    alto, ancho = rgba.shape[:2]
    j0, i0 = max(0, -sil.x0), max(0, -sil.y0)
    j1, i1 = min(sil.w, ancho - sil.x0), min(sil.h, alto - sil.y0)
    if j0 >= j1 or i0 >= i1:
        return
    a = sil.alfa(blando)[i0:i1, j0:j1, None] * opacidad
    reg = rgba[sil.y0 + i0 : sil.y0 + i1, sil.x0 + j0 : sil.x0 + j1]
    reg *= 1.0 - a
    reg[..., :3] += a * color(col)
    reg[..., 3:] += a


# =========================================================================== geometría


def _rad(g: float) -> float:
    return math.radians(g)


def rot(v, g: float) -> np.ndarray:
    """Gira un vector 2D `g` grados en el sentido del reloj en pantalla (y hacia abajo)."""
    r = _rad(g)
    c, s = math.cos(r), math.sin(r)
    return np.array([v[0] * c - v[1] * s, v[0] * s + v[1] * c])


def abajo(g: float) -> np.ndarray:
    """Dirección de un miembro que cuelga, girado `g` grados hacia delante."""
    r = _rad(g)
    return np.array([math.sin(r), math.cos(r)])


def arriba(g: float) -> np.ndarray:
    r = _rad(g)
    return np.array([math.sin(r), -math.cos(r)])


def _mezcla_dc(a, b, x: float):
    vals = {}
    for f in fields(a):
        va, vb = getattr(a, f.name), getattr(b, f.name)
        if isinstance(va, (int, float)) and not isinstance(va, bool):
            vals[f.name] = va + (vb - va) * x
        elif isinstance(va, tuple) and va and isinstance(va[0], (int, float)):
            vals[f.name] = tuple(p + (q - p) * x for p, q in zip(va, vb))
        else:
            vals[f.name] = va if x < 0.5 else vb
    return type(a)(**vals)


# =========================================================================== la mano (3D)
# Mano derecha en coordenadas propias (unidad = largo de la mano, de la muñeca a la punta del
# medio): x hacia los dedos, y hacia el lado del pulgar, z hacia el dorso. Cada hueso es un cono
# redondeado en 3D; la proyección ortográfica de un cono es otro cono, así que la misma mano
# sirve vista desde cualquier ángulo.

_MCP = np.array([[0.505, 0.165, 0.0], [0.530, 0.056, 0.010], [0.508, -0.052, 0.004],
                 [0.462, -0.150, -0.012]])
_FALANGES = [(0.200, 0.118, 0.090), (0.222, 0.135, 0.094), (0.208, 0.128, 0.090), (0.165, 0.098, 0.082)]
_RADIOS = [(0.048, 0.043, 0.038, 0.033), (0.049, 0.044, 0.039, 0.034), (0.046, 0.041, 0.037, 0.032),
           (0.040, 0.036, 0.032, 0.029)]
_CMC = np.array([0.085, 0.105, -0.040])
_PULGAR = (0.185, 0.130, 0.112)
_R_PULGAR = (0.070, 0.060, 0.053, 0.046)


@dataclass
class PoseMano:
    abd: tuple = (5.0, 0.0, -6.0, -13.0)     # separación de índice, medio, anular y meñique
    mcp: tuple = (15.0, 18.0, 22.0, 26.0)    # flexión de los nudillos
    pip: tuple = (20.0, 24.0, 28.0, 30.0)
    dip: tuple = (10.0, 12.0, 14.0, 14.0)
    pulgar_abd: float = 42.0                 # se abre hacia el lado del pulgar
    pulgar_opo: float = 25.0                 # gira hacia la palma
    pulgar_flex: tuple = (10.0, 15.0)        # MCP e IP

    def mezcla(self, otra: "PoseMano", x: float) -> "PoseMano":
        return _mezcla_dc(self, otra, x)


MANO_RELAJADA = PoseMano()
MANO_ABIERTA = PoseMano(abd=(9, 1, -8, -18), mcp=(4, 4, 6, 8), pip=(6, 6, 8, 10), dip=(3, 3, 4, 5),
                        pulgar_abd=55, pulgar_opo=10, pulgar_flex=(4, 6))
MANO_AHUECADA = PoseMano(abd=(4, 0, -4, -9), mcp=(12, 12, 15, 18), pip=(22, 24, 26, 28),
                         dip=(12, 12, 13, 14), pulgar_abd=40, pulgar_opo=30, pulgar_flex=(10, 12))
MANO_PUNO = PoseMano(abd=(2, 0, -3, -7), mcp=(70, 76, 80, 84), pip=(95, 98, 98, 96),
                     dip=(45, 45, 45, 42), pulgar_abd=20, pulgar_opo=55, pulgar_flex=(30, 35))
MANO_SOSTIENE = PoseMano(abd=(2, 0, -3, -7), mcp=(52, 58, 62, 66), pip=(78, 82, 84, 84),
                         dip=(30, 32, 32, 30), pulgar_abd=24, pulgar_opo=48, pulgar_flex=(16, 22))
MANO_PLUMA = PoseMano(abd=(2, -2, -6, -12), mcp=(60, 64, 72, 80), pip=(50, 78, 92, 96),
                      dip=(30, 32, 40, 42), pulgar_abd=10, pulgar_opo=30, pulgar_flex=(10, 0))


def _flexion(d0: np.ndarray, phi: float) -> np.ndarray:
    """Dirección de una falange: la del dedo inclinada `phi` grados hacia la palma (-z)."""
    r = _rad(phi)
    return d0 * math.cos(r) + np.array([0.0, 0.0, -1.0]) * math.sin(r)


def esqueleto_mano(p: PoseMano) -> dict:
    """Articulaciones 3D: 'dedos' = 4 cadenas [MCP, PIP, DIP, yema]; 'pulgar' = [CMC, MCP, IP, yema]."""
    dedos = []
    for i in range(4):
        a0 = _rad(p.abd[i])
        d0 = np.array([math.cos(a0), math.sin(a0), 0.0])
        ang = [p.mcp[i], p.mcp[i] + p.pip[i], p.mcp[i] + p.pip[i] + p.dip[i]]
        cad = [_MCP[i].copy()]
        for k in range(3):
            cad.append(cad[-1] + _flexion(d0, ang[k]) * _FALANGES[i][k])
        dedos.append(cad)
    a0, o0 = _rad(p.pulgar_abd), _rad(p.pulgar_opo)
    d = np.array([math.cos(a0) * math.cos(o0), math.sin(a0) * math.cos(o0), -math.sin(o0)])
    hacia = np.array([0.25, -0.55, -0.80])
    hacia /= np.linalg.norm(hacia)
    pul = [_CMC.copy()]
    flex = (0.0,) + tuple(p.pulgar_flex)
    for k in range(3):
        perp = hacia - d * float(hacia @ d)
        n = np.linalg.norm(perp)
        if n > 1e-6:
            perp /= n
            r = _rad(flex[k])
            d = d * math.cos(r) + perp * math.sin(r)
        pul.append(pul[-1] + d * _PULGAR[k])
    return {"dedos": dedos, "pulgar": pul}


def huesos_mano(p: PoseMano, antebrazo: float = 0.9, grosor: float = 1.0) -> list:
    """Lista de conos 3D (a, b, ra, rb, k) de una mano derecha en sus coordenadas."""
    g = grosor
    c = []
    e = esqueleto_mano(p)
    # antebrazo y muñeca: dos conos paralelos dan la sección ovalada
    for s in (-1, 1):
        c.append((np.array([0.04, 0.045 * s, 0.0]), np.array([-antebrazo, 0.055 * s, 0.0]),
                  0.100 * g, 0.150 * g, 0.03))
    # palma: metacarpianos, almohadilla, hipotenar y eminencia tenar
    for i in range(4):
        base = np.array([0.07, _MCP[i, 1] * 0.50, 0.0])
        c.append((base, _MCP[i], 0.056 * g, 0.052 * g, 0.04))
    c.append((np.array([0.13, 0.0, -0.034]), np.array([0.42, -0.010, -0.028]), 0.070 * g, 0.062 * g, 0.035))
    c.append((np.array([0.10, -0.095, -0.024]), np.array([0.40, -0.135, -0.020]), 0.056 * g, 0.050 * g, 0.035))
    # dedos (el nudillo de cada articulación, un poco más ancho que la falange)
    for i, cad in enumerate(e["dedos"]):
        r = _RADIOS[i]
        for k in range(3):
            c.append((cad[k], cad[k + 1], r[k] * g, r[k + 1] * g, 0.006))
            if k < 2:
                c.append((cad[k + 1], cad[k + 1], r[k + 1] * 1.1 * g, r[k + 1] * 1.1 * g, 0.004))
    # pulgar: metacarpiano desde la base de la palma, luego dos falanges que se cierran sobre ella
    pul = e["pulgar"]
    for k in range(3):
        c.append((pul[k], pul[k + 1], _R_PULGAR[k] * g, _R_PULGAR[k + 1] * g, 0.03 if k == 0 else 0.006))
    # eminencia tenar: une la base del pulgar con la palma
    c.append((np.array([0.12, 0.05, -0.035]), pul[1] * 0.85 + _CMC * 0.15, 0.078 * g, 0.058 * g, 0.035))
    return c


def orientacion(dedos, dorso, derecha: bool = True) -> np.ndarray:
    """Matriz 3×3 que lleva la mano a la vista (x derecha, y abajo, z hacia el fondo).

    `dedos`: hacia dónde apuntan los dedos; `dorso`: hacia dónde mira el dorso. Para una mano
    izquierda se refleja el eje del pulgar.
    """
    x = np.asarray(dedos, float)
    x = x / np.linalg.norm(x)
    z = np.asarray(dorso, float)
    z = z - x * float(z @ x)
    z = z / np.linalg.norm(z)
    y = np.cross(z, x)
    if not derecha:
        y = -y
    return np.stack([x, y, z], axis=1)


def girar_eje(v, eje, g: float) -> np.ndarray:
    """Rodrigues: gira el vector 3D `v` alrededor de `eje` `g` grados."""
    k = np.asarray(eje, float)
    k = k / np.linalg.norm(k)
    v = np.asarray(v, float)
    r = _rad(g)
    return v * math.cos(r) + np.cross(k, v) * math.sin(r) + k * float(k @ v) * (1 - math.cos(r))


def mano(sil: Silueta, muneca, L: float, M: np.ndarray, pose: PoseMano, antebrazo: float = 0.9,
         grosor: float = 1.0, k_extra: float = 0.0, a_pantalla=None) -> dict:
    """Dibuja una mano en `sil`. `muneca` en pantalla, `L` px de largo, `M` de `orientacion`.

    `a_pantalla` (opcional) transforma puntos de la vista antes de dibujar (para reflejar).
    Devuelve puntos útiles en pantalla: palma, yemas, base de los dedos.
    """
    o = np.asarray(muneca, float)

    def P(q):
        v = M @ q
        p = o + L * v[:2]
        return a_pantalla(p) if a_pantalla else p

    for a, b, ra, rb, k in huesos_mano(pose, antebrazo, grosor):
        sil.cono(P(a), P(b), ra * L, rb * L, (k + k_extra) * L)
    return {"palma": P(np.array([0.30, 0.0, -0.09])), "nudillos": P(_MCP[1]),
            "base_dedos": P(_MCP[1] + np.array([0.0, 0.0, -0.06]))}


# =========================================================================== la persona (perfil)


@dataclass
class Pose:
    inclinacion: float = 1.5    # todo el cuerpo, desde la cadera
    torso: float = -3.0         # pecho respecto a la pelvis (− erguido)
    cuello: float = 4.0
    cabeza: float = -2.0        # + baja la mirada
    hombro_c: float = 4.0       # brazo cercano: grados desde la vertical (+ hacia delante)
    codo_c: float = 12.0        # + el antebrazo sube hacia delante
    muneca_c: float = 0.0       # + flexiona hacia la palma
    giro_c: float = 0.0         # pronación del antebrazo
    hombro_l: float = -6.0
    codo_l: float = 14.0
    muneca_l: float = 0.0
    giro_l: float = 0.0
    cadera_c: float = 3.0       # muslo: + hacia delante
    rodilla_c: float = 3.0      # + la pierna se dobla hacia atrás
    pie_c: float = 0.0
    cadera_l: float = -4.0
    rodilla_l: float = 5.0
    pie_l: float = 0.0
    mano_c: PoseMano = field(default_factory=lambda: MANO_RELAJADA)
    mano_l: PoseMano = field(default_factory=lambda: MANO_RELAJADA)

    def mezcla(self, otra: "Pose", x: float) -> "Pose":
        p = _mezcla_dc(self, otra, x)
        p.mano_c = self.mano_c.mezcla(otra.mano_c, x)
        p.mano_l = self.mano_l.mezcla(otra.mano_l, x)
        return p


@dataclass
class Ropa:
    tipo: str = "romano"        # "romano": coraza, pteruges, túnica, botas | "galo": túnica, bracas, espada
    pelo: str = "corto"         # "corto" | "calvo" | "largo"
    bigote: bool = False
    capa: bool = True
    largo_capa: float = 0.78    # 0 hombros .. 1 tobillos
    viento: float = 0.3
    nariz: float = 1.0          # 1 recta, >1 aguileña
    complexion: float = 1.0
    semilla: int = 0


def esqueleto(p: Pose) -> dict:
    """Articulaciones en unidades de altura; pies en y = 0 (sin apoyar), mira hacia +x."""
    j: dict = {}
    cad = np.array([0.0, -0.515])
    a_pel = p.inclinacion
    cint = cad + arriba(a_pel) * 0.105
    a_pe = a_pel + p.torso
    cu0 = cint + arriba(a_pe) * 0.205 + rot((-0.010, 0.0), a_pe)
    hom = cint + arriba(a_pe) * 0.182 + rot((-0.010, 0.0), a_pe)
    a_cu = a_pe + 14 + p.cuello
    cu1 = cu0 + arriba(a_cu) * 0.062
    a_ca = a_pe + p.cuello + p.cabeza
    cab = cu1 + rot((0.012, -0.034), a_ca)
    j.update(cadera=cad, cintura=cint, cuello0=cu0, cuello1=cu1, hombro=hom, cabeza=cab,
             a_pelvis=a_pel, a_pecho=a_pe, a_cuello=a_cu, a_cabeza=a_ca)
    for l in "cl":
        a_br = a_pe + getattr(p, "hombro_" + l)
        codo = hom + abajo(a_br) * 0.180
        a_an = a_br + getattr(p, "codo_" + l)
        mun = codo + abajo(a_an) * 0.150
        a_mu = a_pel + getattr(p, "cadera_" + l)
        rod = cad + abajo(a_mu) * 0.235
        a_ti = a_mu - getattr(p, "rodilla_" + l)
        tob = rod + abajo(a_ti) * 0.235
        j.update({"codo_" + l: codo, "muneca_" + l: mun, "rodilla_" + l: rod, "tobillo_" + l: tob,
                  "a_brazo_" + l: a_br, "a_ante_" + l: a_an, "a_muslo_" + l: a_mu, "a_tibia_" + l: a_ti})
    return j


# Contornos en coordenadas de su hueso (x adelante, y abajo).
# Cabeza: origen cerca del oído; de la coronilla al mentón mide 0.13 de la altura.
CABEZA = [(0.000, -0.076), (0.018, -0.074), (0.031, -0.068), (0.041, -0.057), (0.047, -0.044),
          (0.0495, -0.031), (0.0505, -0.025), (0.047, -0.020), (0.052, -0.011), (0.059, 0.002), (0.0645, 0.011),
          (0.061, 0.0155), (0.055, 0.0175), (0.0535, 0.021), (0.0555, 0.026), (0.052, 0.0295),
          (0.054, 0.033), (0.050, 0.038), (0.0475, 0.041), (0.0505, 0.047), (0.048, 0.054),
          (0.038, 0.058), (0.024, 0.054), (0.012, 0.047), (-0.004, 0.036), (-0.018, 0.030),
          (-0.034, 0.020), (-0.046, 0.006), (-0.054, -0.014), (-0.055, -0.036), (-0.046, -0.058),
          (-0.026, -0.071)]
TORSO = [(0.070, 0.0), (0.076, -0.036), (0.081, -0.075), (0.086, -0.110), (0.084, -0.143),
         (0.073, -0.172), (0.050, -0.196), (0.028, -0.207), (-0.034, -0.214), (-0.052, -0.199),
         (-0.065, -0.170), (-0.070, -0.132), (-0.066, -0.088), (-0.058, -0.044), (-0.054, 0.0)]
CORAZA = [(0.080, 0.032), (0.079, 0.0), (0.082, -0.036), (0.086, -0.068), (0.092, -0.098),
          (0.093, -0.128), (0.086, -0.160), (0.068, -0.188), (0.040, -0.204), (0.024, -0.210),
          (-0.036, -0.216), (-0.058, -0.200), (-0.072, -0.168), (-0.076, -0.128), (-0.072, -0.084),
          (-0.064, -0.040), (-0.062, 0.0), (-0.068, 0.032)]
PELVIS = [(0.066, -0.105), (0.072, -0.070), (0.068, -0.030), (0.052, 0.006), (0.020, 0.032),
          (-0.030, 0.046), (-0.063, 0.031), (-0.079, -0.006), (-0.077, -0.050), (-0.063, -0.090),
          (-0.056, -0.105)]
PIE = [(0.018, -0.014), (0.044, 0.002), (0.070, 0.016), (0.094, 0.025), (0.112, 0.030),
       (0.123, 0.037), (0.121, 0.046), (0.090, 0.047), (0.050, 0.046), (0.010, 0.043),
       (-0.022, 0.047), (-0.036, 0.040), (-0.038, 0.022), (-0.026, 0.0), (-0.018, -0.020)]


@dataclass
class Figura:
    cuerpo: Silueta
    capa: Silueta | None
    j: dict
    escala: float
    espejo: bool


def _caja(puntos, margen):
    a = np.array(puntos)
    return (a[:, 0].min() - margen, a[:, 1].min() - margen, a[:, 0].max() + margen, a[:, 1].max() + margen)


def persona(pose: Pose, ropa: Ropa, x: float, y: float, alto: float, espejo: bool = False,
            t: float = 0.0) -> Figura:
    """Arma una persona de perfil con los pies en (x, y) y `alto` px de estatura."""
    j = esqueleto(pose)
    dy = -(max(j["tobillo_c"][1], j["tobillo_l"][1]) + 0.046)
    sx = -1.0 if espejo else 1.0
    s = alto
    rng = np.random.default_rng(ropa.semilla)

    def P(p):
        return np.array([x + sx * p[0] * s, y + (p[1] + dy) * s])

    def ang(g):  # un ángulo de figura llevado a pantalla
        return -g if espejo else g

    puntos = [P(v) for k, v in j.items() if isinstance(v, np.ndarray) and v.shape == (2,)]
    caja = _caja(puntos, 0.36 * s)
    cuerpo = Silueta(caja)
    capa = Silueta(caja) if ropa.capa else None
    S = cuerpo
    cx = ropa.complexion

    def cono(a, b, ra, rb, k=0.0, sil=None):
        (sil or S).cono(P(a), P(b), ra * s * cx, rb * s * cx, k * s)

    def elip(c, rx, ry, g, k=0.0, sil=None, modo="union"):
        (sil or S).elipse(P(c), rx * s * cx, ry * s * cx, ang(g), k * s, modo)

    def poli(pts, k=0.0, sil=None, modo="union"):
        (sil or S).poligono([P(q) for q in pts], k * s, modo)

    def en(o, g, pts):  # contorno de hueso -> figura
        return [o + rot(q, g) for q in pts]

    romano = ropa.tipo == "romano"
    a_pe, a_pel = j["a_pecho"], j["a_pelvis"]

    # ---- capa (detrás de todo, en su propia silueta)
    if capa is not None:
        _capa(j, ropa, t, capa, P, s)

    # ---- piernas (la lejana primero; en silueta da igual, pero las bracas llevan pliegues)
    for l in "lc":
        cad, rod, tob = j["cadera"], j["rodilla_" + l], j["tobillo_" + l]
        a_mu, a_ti = j["a_muslo_" + l], j["a_tibia_" + l]
        ext = 0.0 if romano else 0.010
        cono(cad, rod, 0.054 + ext, 0.034 + ext, 0.02)
        elip(cad + abajo(a_mu) * 0.09 + rot((0.012, 0), -a_mu), 0.038 + ext, 0.09, -a_mu, 0.02)
        elip(rod + rot((0.008, 0.0), -a_ti), 0.031 + ext * 0.6, 0.038, -a_ti, 0.012)
        cono(rod, tob, 0.029 + ext, 0.0150 + ext * 1.1, 0.012)
        elip(rod + abajo(a_ti) * 0.070 + rot((-0.016, 0), -a_ti), 0.024 + ext * 0.7, 0.068, -a_ti, 0.022)
        if not romano:  # bracas: tela holgada que hace bolsas suaves y se recoge en el tobillo
            for k_ in range(6):
                u = (k_ + rng.uniform(0.2, 0.8)) / 6
                lado = 1 if k_ % 2 else -1
                base, d, g = (cad, rod, a_mu) if u < 0.5 else (rod, tob, a_ti)
                uu = (u % 0.5) * 2
                c0 = base + (d - base) * uu + rot((lado * (0.026 + ext * 0.5), 0), -g)
                elip(c0, 0.010, 0.026, -g + rng.uniform(-20, 20), 0.012)
            cono(tob + np.array([0, -0.035]), tob + np.array([0, 0.0]), 0.024, 0.021, 0.01)
        pie = en(tob, getattr(pose, "pie_" + l), PIE)
        poli(pie, 0.006)
        if romano:  # calcei: bota de cuero que cubre el tobillo
            cono(tob + np.array([0.006, 0.012]), tob + abajo(a_ti) * -0.045, 0.022, 0.0205, 0.008)
            cono(tob + abajo(a_ti) * -0.040, tob + abajo(a_ti) * -0.046, 0.0225, 0.0225, 0.0)

    # ---- tronco
    poli(en(j["cadera"], a_pel, PELVIS), 0.02)
    poli(en(j["cintura"], a_pe, CORAZA if romano else TORSO), 0.025)
    if romano:
        # túnica hasta la rodilla
        _faldon(j, a_pe, poli, rng, 0.22, t, ropa.viento)
    else:
        _faldon(j, a_pe, poli, rng, 0.17, t, ropa.viento, holgura=0.012)
        # cinturón con la espada larga colgando hacia atrás
        c0 = j["cintura"] + rot((-0.030, 0.035), a_pe)
        eje = rot(np.array([-0.40, 0.92]) / math.hypot(0.40, 0.92), a_pel)
        lado = np.array([eje[1], -eje[0]])
        largo = 0.40
        vaina = [c0 + lado * 0.011, c0 + eje * largo * 0.94 + lado * 0.010, c0 + eje * largo + lado * 0.004,
                 c0 + eje * (largo + 0.012), c0 + eje * largo - lado * 0.004, c0 + eje * largo * 0.94 - lado * 0.010,
                 c0 - lado * 0.011]
        poli(vaina, 0.002)
        cono(c0 - eje * 0.02, c0 - eje * 0.075, 0.0065, 0.0075)          # empuñadura
        cono(c0 - eje * 0.075 - lado * 0.008, c0 - eje * 0.075 + lado * 0.008, 0.007, 0.007)

    # ---- cuello y cabeza
    cu0, cu1, cab, a_ca = j["cuello0"], j["cuello1"], j["cabeza"], j["a_cabeza"]
    cono(cu0 + rot((0.006, 0.0), a_pe), cu1, 0.032, 0.029, 0.015)
    garganta = cab + rot((0.026, 0.050), a_ca)
    cono(cu0 + rot((0.022, -0.004), a_pe), garganta, 0.020, 0.016, 0.012)
    cono(cu1 + rot((-0.02, 0.01), a_ca), j["hombro"] + rot((-0.012, -0.022), a_pe), 0.022, 0.028, 0.02)
    cabeza = [list(q) for q in CABEZA]
    if ropa.nariz != 1.0:  # puente más alto y punta más baja: nariz aguileña
        for i in (8, 9, 10, 11):
            cabeza[i][0] += 0.004 * (ropa.nariz - 1.0) * (1.4 if i == 9 else 1.0)
            cabeza[i][1] += 0.003 * (ropa.nariz - 1.0) * (i - 8) / 3
    poli(en(cab, a_ca, cabeza), 0.004)
    _pelo(j, ropa, t, cono, elip, poli, P, rng, S, s)

    # ---- brazos y manos (el lejano primero)
    for l in "lc":
        hom, codo, mun = j["hombro"], j["codo_" + l], j["muneca_" + l]
        a_br, a_an = j["a_brazo_" + l], j["a_ante_" + l]
        manga = 0.0 if romano else 0.010
        elip(hom + abajo(a_br) * 0.030, 0.038, 0.054, -a_br, 0.02)                 # deltoides
        cono(hom, codo, 0.029 + manga, 0.021 + manga, 0.015)
        elip(hom + abajo(a_br) * 0.090 + rot((0.006, 0), -a_br), 0.022 + manga, 0.05, -a_br, 0.014)
        elip(hom + abajo(a_br) * 0.080 + rot((-0.007, 0), -a_br), 0.022 + manga, 0.055, -a_br, 0.014)
        cono(codo, codo + abajo(a_an) * 0.04, 0.021 + manga, 0.0235 + manga, 0.012)
        cono(codo + abajo(a_an) * 0.04, mun, 0.0235 + manga, 0.0135 + manga * 0.6, 0.012)
        cono(codo + rot((-0.006, 0.0), -a_br), codo + abajo(a_br) * 0.016 + rot((-0.016, 0), -a_br), 0.017, 0.012, 0.01)
        if not romano:  # puño de la manga
            cono(mun + abajo(a_an) * -0.02, mun + abajo(a_an) * -0.005, 0.024, 0.024, 0.004)
        if romano:  # pteruges del hombro
            for i in range(4):
                g = a_br + (i - 1.5) * 5
                cono(hom + abajo(g) * 0.012 + rot(((i - 1.5) * 0.012, 0), -a_br),
                     hom + abajo(g) * 0.072 + rot(((i - 1.5) * 0.0135, 0), -a_br), 0.0085, 0.0085, 0.0)
        _mano_figura(S, j, pose, l, P, s, espejo)
    return Figura(cuerpo, capa, {k: (P(v) if isinstance(v, np.ndarray) and v.shape == (2,) else v)
                                 for k, v in j.items()}, s, espejo)


def _mano_figura(S: Silueta, j: dict, pose: Pose, l: str, P, s: float, espejo: bool) -> None:
    """Mano 3D al final del antebrazo, en coordenadas de figura y luego a pantalla."""
    mun = j["muneca_" + l]
    a_an = j["a_ante_" + l]
    d2 = abajo(a_an)
    d = np.array([d2[0], d2[1], 0.0])
    cerca = l == "c"
    dorso = np.array([0.0, 0.0, -1.0 if cerca else 1.0])
    dorso = girar_eje(dorso, d, getattr(pose, "giro_" + l) * (1 if cerca else -1))
    flex = getattr(pose, "muneca_" + l)
    dedos = girar_eje(d, np.cross(dorso, d), flex) if flex else d
    M = orientacion(dedos, dorso, derecha=cerca)
    L = 0.106

    def a_pantalla(q):
        return P(mun + q)

    o = np.zeros(2)
    for a, b, ra, rb, k in huesos_mano(getattr(pose, "mano_" + l), antebrazo=0.35):
        pa = a_pantalla(L * (M @ a)[:2] + o)
        pb = a_pantalla(L * (M @ b)[:2] + o)
        S.cono(pa, pb, ra * L * s, rb * L * s, k * L * s)
    j["mano_" + l] = mun + L * (M @ np.array([0.40, 0.0, -0.05]))[:2]
    j["M_" + l] = M


def _faldon(j, a_pe, poli, rng, largo, t, viento, holgura=0.0):
    """Faldón de túnica de la cintura a `largo` bajo la cadera, con pliegues en el ruedo."""
    cint = j["cintura"]
    rc, rl = j["rodilla_c"], j["rodilla_l"]
    y_ru = j["cadera"][1] + largo
    xs = [rc[0], rl[0]]
    frente = max(xs) + 0.062 + holgura
    atras = min(xs) - 0.072 - holgura - viento * 0.02
    pts = [cint + rot((0.070 + holgura, 0.0), a_pe)]
    pts.append(np.array([max(frente - 0.012, pts[0][0] + 0.006), pts[0][1] + (y_ru - pts[0][1]) * 0.45]))
    n = 7
    for i in range(n + 1):
        u = i / n
        xx = frente + (atras - frente) * u
        yy = y_ru + 0.006 * math.sin(u * 9.0 + 0.8 * math.sin(t * 1.3)) - 0.012 * u * viento
        pts.append(np.array([xx, yy]))
    pts.append(np.array([atras + 0.016, pts[0][1] + (y_ru - pts[0][1]) * 0.45]))
    pts.append(cint + rot((-0.056 - holgura, 0.0), a_pe))
    poli(pts, 0.012)


def _capa(j, ropa, t, sil, P, s):
    """Capa que cae del hombro por la espalda; el viento la separa del cuerpo y ondula el ruedo."""
    a_pe = j["a_pecho"]
    hom, cu0 = j["hombro"], j["cuello0"]
    tob = min(j["tobillo_c"][1], j["tobillo_l"][1])
    y0 = hom[1] - 0.03
    y_ru = y0 + (tob + 0.02 - y0) * ropa.largo_capa
    detras = min(j["rodilla_c"][0], j["rodilla_l"][0], j["cadera"][0]) - 0.07
    v = ropa.viento
    atras = []
    n = 9
    for i in range(n + 1):
        u = i / n
        yy = y0 + (y_ru - y0) * u
        base = cu0[0] - 0.05 + (detras - cu0[0] + 0.05) * min(1.0, u * 1.5) - 0.03 * u * u
        ola = v * 0.016 * math.sin(6.28 * (0.55 * t - 1.3 * u)) + v * 0.006 * math.sin(6.28 * (1.3 * t - 3.1 * u))
        xx = base - v * 0.10 * u ** 1.2 + ola - 0.012
        atras.append(np.array([xx, yy - v * 0.05 * u * u]))
    ruedo = []
    xf = detras + 0.11
    for i in range(1, 8):
        u = i / 8
        xx = atras[-1][0] + (xf - atras[-1][0]) * u
        yy = atras[-1][1] + (y_ru - atras[-1][1]) * u + 0.007 * math.sin(u * 13 + t * 1.7)
        ruedo.append(np.array([xx, yy]))
    frente = [np.array([xf, y_ru]), np.array([xf + 0.006, (y0 + y_ru) / 2]),
              hom + rot((-0.012, 0.03), a_pe), hom + rot((-0.022, -0.012), a_pe), cu0 + rot((-0.034, 0.004), a_pe)]
    sil.poligono([P(q) for q in atras + ruedo + frente], 0.01 * s)


def _pelo(j, ropa, t, cono, elip, poli, P, rng, S, s):
    cab, a_ca = j["cabeza"], j["a_cabeza"]

    def H(q):
        return cab + rot(q, a_ca)

    if ropa.pelo in ("corto", "calvo"):
        for q in spline(CABEZA, 4):
            arriba_ = q[1] < -0.045 and q[0] < 0.036
            atras = q[0] < -0.008 and q[1] < 0.026
            if not (arriba_ or atras):
                continue
            if ropa.pelo == "calvo" and q[1] < -0.04 and q[0] > -0.045:
                continue
            if rng.uniform() < 0.85:
                elip(H(np.array(q) * 1.012), 0.0042, 0.003, rng.uniform(0, 180), 0.004)
    elif ropa.pelo == "casco":
        elip(H((-0.004, -0.036)), 0.059, 0.050, 0, 0.006)
        cono(H((-0.004, -0.084)), H((-0.004, -0.096)), 0.008, 0.006, 0.003)
        cono(H((-0.046, -0.004)), H((-0.080, 0.006)), 0.014, 0.010, 0.006)
        cono(H((0.040, -0.040)), H((0.056, -0.036)), 0.006, 0.004, 0.003)
    elif ropa.pelo == "largo":
        v = ropa.viento
        masa = [(0.040, -0.058), (0.026, -0.078), (0.0, -0.084), (-0.032, -0.077), (-0.056, -0.054),
                (-0.066, -0.020), (-0.070, 0.020), (-0.074, 0.060), (-0.060, 0.080), (-0.040, 0.050),
                (-0.022, 0.020), (0.0, -0.010), (0.030, -0.040)]
        poli([H(q) for q in masa], 0.004)
        for i in range(22):
            u = i / 21
            q0 = np.array([-0.040 - 0.030 * u, -0.07 + 0.13 * u])
            largo = 0.05 + 0.04 * rng.uniform()
            pts = []
            for k in range(6):
                w = k / 5
                ola = 0.01 * math.sin(t * 2.2 + i * 0.7 + w * 3) * v
                pts.append(H(q0 + np.array([-0.012 * w - v * 0.035 * w * w + ola, largo * w])))
            for k in range(5):
                r0 = 0.0055 * (1 - k / 5) + 0.0012
                r1 = 0.0055 * (1 - (k + 1) / 5) + 0.0012
                cono(pts[k], pts[k + 1], r0, r1)
    if ropa.bigote:
        for i, (dx, l) in enumerate([(0.0, 0.034), (0.004, 0.030), (-0.004, 0.032)]):
            q0 = np.array([0.053 + dx * 0.5, 0.019])
            pts = [H(q0 + np.array([-0.004 * w + dx * w, l * w])) for w in np.linspace(0, 1, 5)]
            for k in range(4):
                cono(pts[k], pts[k + 1], 0.0045 - k * 0.0008, 0.0045 - (k + 1) * 0.0008)


# =========================================================================== el caballo (perfil)
# Unidades: alzada a la cruz = 1; origen en el suelo bajo el vientre; mira hacia +x.
# Proporciones de un caballo de silla: cuerpo tan largo como alto, pecho tan hondo como larga
# la pierna, cabeza de unos 0.4 de la alzada.

CUERPO_CABALLO = [
    (0.270, -1.000), (0.170, -0.968), (0.060, -0.948), (-0.070, -0.952), (-0.190, -0.972),
    (-0.300, -0.996), (-0.395, -0.994), (-0.470, -0.968), (-0.528, -0.922), (-0.560, -0.862),
    (-0.566, -0.800), (-0.548, -0.728), (-0.512, -0.662), (-0.462, -0.606), (-0.392, -0.574),
    (-0.330, -0.608), (-0.270, -0.592), (-0.160, -0.552), (-0.020, -0.534), (0.120, -0.538),
    (0.230, -0.560), (0.330, -0.600), (0.420, -0.640), (0.478, -0.698), (0.500, -0.758),
    (0.484, -0.820), (0.420, -0.900), (0.340, -0.976)]
CRUZ_PIVOTE = np.array([0.36, -0.86])
NUCA = np.array([0.655, -1.395])
CUELLO = [(0.240, -0.990), (0.318, -1.078), (0.408, -1.184), (0.498, -1.284), (0.574, -1.354),
          (0.628, -1.393)]
# cabeza en coordenadas relativas a la nuca, con el hocico abajo a la derecha
CABEZA_CABALLO = [(0.020, -0.018), (0.052, -0.012), (0.082, 0.020), (0.128, 0.090), (0.172, 0.162),
                  (0.208, 0.222), (0.228, 0.262), (0.240, 0.292), (0.242, 0.312), (0.236, 0.328),
                  (0.222, 0.336), (0.212, 0.334), (0.206, 0.342), (0.190, 0.344), (0.172, 0.334),
                  (0.150, 0.300), (0.122, 0.262), (0.092, 0.240), (0.060, 0.218), (0.036, 0.188),
                  (0.020, 0.160), (0.004, 0.150), (-0.020, 0.170)]
GARGANTA = [(-0.058, 0.236), (-0.110, 0.345), (-0.155, 0.445), (-0.200, 0.530), (-0.245, 0.605)]
BOCA = np.array([0.205, 0.336])


@dataclass
class PoseCaballo:
    cuello: float = 0.0      # + baja la cabeza (gira el cuello desde la cruz)
    cabeza: float = 0.0      # + mete el hocico
    orejas: float = 0.0      # + hacia atrás
    descanso: float = 1.0    # pata trasera lejana descansando sobre la punta del casco
    respira: float = 0.0     # -1..1


def _casco(poli, corona, inclin: float) -> None:
    pts = [(-0.020, -0.006), (0.016, -0.004), (0.036, 0.026), (0.040, 0.034), (-0.042, 0.034),
           (-0.042, 0.024), (-0.032, 0.006)]
    poli([corona + rot(q, inclin) for q in pts], 0.006)


def _pata_delantera(cono, elip, poli, top, codo, rodilla, menudillo, corona, inclin=0.0):
    cono(top, rodilla + np.array([0, -0.035]), 0.074, 0.040, 0.03)
    elip(codo, 0.050, 0.040, 0.0, 0.02)
    elip(rodilla, 0.043, 0.050, 0.0, 0.015)
    elip(rodilla + np.array([-0.028, -0.008]), 0.018, 0.020, 0.0, 0.01)
    cono(rodilla + np.array([0, 0.01]), menudillo + np.array([0, -0.025]), 0.031, 0.028, 0.012)
    elip(menudillo + np.array([-0.004, 0]), 0.042, 0.036, 0.0, 0.012)
    cono(menudillo, corona, 0.027, 0.026, 0.008)
    _casco(poli, corona, inclin)


def _pata_trasera(cono, elip, poli, top, corvejon, menudillo, corona, inclin=0.0):
    d = corvejon - top
    cono(top, corvejon - d * 0.12, 0.086, 0.044, 0.03)
    eje = d / (np.linalg.norm(d) + 1e-9)
    elip(top + d * 0.42 + np.array([-eje[1], eje[0]]) * 0.030, 0.040, 0.10,
         -math.degrees(math.atan2(eje[0], eje[1])), 0.03)
    elip(corvejon, 0.044, 0.050, 0.0, 0.015)
    cono(corvejon + np.array([-0.012, -0.016]), corvejon + np.array([-0.042, -0.046]), 0.020, 0.016, 0.01)
    cono(corvejon + np.array([0, 0.02]), menudillo + np.array([0, -0.025]), 0.033, 0.029, 0.012)
    elip(menudillo + np.array([-0.004, 0]), 0.043, 0.036, 0.0, 0.012)
    cono(menudillo, corona, 0.027, 0.026, 0.008)
    _casco(poli, corona, inclin)


def caballo(pose: PoseCaballo, x: float, y: float, alzada: float, espejo: bool = False,
            t: float = 0.0, viento: float = 0.3, riendas_a=None, semilla: int = 0,
            silla: bool = True) -> Figura:
    """Caballo de pie, de perfil, con los cascos en y. `riendas_a`: punto de pantalla donde
    terminan las riendas (la mano de quien lo sujeta)."""
    s = alzada
    sx = -1.0 if espejo else 1.0
    rng = np.random.default_rng(semilla)

    def P(p):
        return np.array([x + sx * p[0] * s, y + p[1] * s])

    def Pinv(q):
        return np.array([(q[0] - x) / (sx * s), (q[1] - y) / s])

    caja = (min(P((-0.75, 0))[0], P((1.05, 0))[0]), y - 1.62 * s, max(P((-0.75, 0))[0], P((1.05, 0))[0]), y + 0.02 * s)
    if riendas_a is not None:
        caja = (min(caja[0], riendas_a[0]), caja[1], max(caja[2], riendas_a[0]), max(caja[3], riendas_a[1]))
    S = Silueta(caja)

    def cono(a, b, ra, rb, k=0.0):
        S.cono(P(a), P(b), ra * s, rb * s, k * s)

    def elip(c, rx, ry, g, k=0.0):
        S.elipse(P(c), rx * s, ry * s, -g if espejo else g, k * s)

    def poli(pts, k=0.0):
        S.poligono([P(q) for q in pts], k * s)

    def a(*v):
        return np.array(v, float)

    # ---- patas lejanas (algo corridas, para que las cuatro se lean)
    _pata_delantera(cono, elip, poli, a(0.30, -0.70), a(0.245, -0.585), a(0.262, -0.300),
                    a(0.268, -0.085), a(0.292, -0.034))
    dsc = pose.descanso
    corv = a(-0.405, -0.318) + a(0.035, 0.012) * dsc
    men = a(-0.398, -0.085) + a(0.060, 0.022) * dsc
    cor = a(-0.374, -0.034) + a(0.062, -0.016) * dsc
    _pata_trasera(cono, elip, poli, a(-0.34, -0.62), corv, men, cor, inclin=28 * dsc)

    # ---- cuerpo
    r = 1.0 + 0.006 * pose.respira
    cuerpo = [(px, -0.77 + (py + 0.77) * (r if px > -0.3 else 1.0)) for px, py in CUERPO_CABALLO]
    poli(cuerpo, 0.02)
    elip(a(0.33, -0.80), 0.16, 0.20, -25, 0.05)          # paletilla
    elip(a(-0.38, -0.80), 0.20, 0.17, 10, 0.05)          # anca

    # ---- patas cercanas
    _pata_delantera(cono, elip, poli, a(0.36, -0.70), a(0.300, -0.585), a(0.333, -0.300),
                    a(0.338, -0.085), a(0.362, -0.034))
    _pata_trasera(cono, elip, poli, a(-0.40, -0.62), a(-0.462, -0.318), a(-0.462, -0.085),
                  a(-0.440, -0.034))

    # ---- cuello y cabeza (giran desde la base del cuello)
    def girar(q, peso=True):
        q = np.asarray(q, float)
        w = min(1.0, max(0.0, (np.linalg.norm(q - CRUZ_PIVOTE) - 0.08) / 0.30)) if peso else 1.0
        return CRUZ_PIVOTE + rot(q - CRUZ_PIVOTE, pose.cuello * w)

    nuca = girar(NUCA)
    g_cab = pose.cuello + pose.cabeza

    def C(q):  # punto de la cabeza (relativo a la nuca) a figura
        return nuca + rot(np.asarray(q) * 1.0, g_cab)

    cresta = [girar(q) for q in CUELLO]
    garganta = [nuca + rot(q, pose.cuello) for q in GARGANTA]
    contorno = cresta + [C(q) for q in CABEZA_CABALLO] + garganta + [a(0.40, -0.83), a(0.32, -0.91)]
    poli(contorno, 0.02)
    elip(C((0.025, 0.130)), 0.062, 0.070, 0, 0.02)       # carrillo
    # orejas
    for i, (dx, g0) in enumerate(((-0.006, 8.0), (0.016, 18.0))):
        base = C((dx, -0.008))
        g = g0 - pose.orejas - 4 * math.sin(t * 0.9 + i * 2.0) * (1 if i else 0.4)
        eje = rot((0.0, -1.0), g + g_cab * 0.3)
        lado = np.array([-eje[1], eje[0]])
        poli([base - lado * 0.018, base + eje * 0.06 - lado * 0.016, base + eje * 0.105,
              base + eje * 0.06 + lado * 0.012, base + lado * 0.016], 0.004)

    # ---- crin y tupé: mechones que salen de la cresta y caen sobre el cuello; el viento
    # los levanta hacia atrás y deja el borde superior velludo, no peinado
    tramo = spline(cresta + [nuca], 10, cerrado=False)
    for i in range(len(tramo) - 1):
        for _ in range(5):
            c0 = tramo[i] + (tramo[i + 1] - tramo[i]) * rng.uniform()
            n_ = rot(tramo[i + 1] - tramo[i], -90)
            n_ = n_ / (np.linalg.norm(n_) + 1e-9)            # normal hacia afuera de la cresta
            alza = (0.004 + 0.028 * rng.uniform() ** 2) * (0.6 + viento)
            atras = 0.015 + 0.05 * rng.uniform()
            cae = 0.01 + 0.06 * rng.uniform()
            ola = math.sin(t * 2.3 + i * 0.37 + rng.uniform(0, 6)) * 0.010 * viento
            pts = [c0 - n_ * 0.012, c0 + n_ * alza * 0.7 + a(-atras * 0.3, 0),
                   c0 + n_ * alza + a(-atras * (0.8 + viento) + ola, 0.0),
                   c0 + n_ * (alza * 0.3) + a(-atras * (1.2 + viento) + ola, cae)]
            S.hebra([P(q) for q in spline(pts, 3, cerrado=False)], 0.0048 * s, 0.0008 * s)
    for k in range(7):
        c0 = C((0.012 + 0.004 * k, -0.004))
        pts = [c0, c0 + rot((0.03 + 0.004 * k, 0.012), g_cab * 0.5 + 10 * math.sin(t + k)),
               c0 + rot((0.05 + 0.006 * k, 0.05), g_cab * 0.5)]
        S.hebra([P(q) for q in spline(pts, 3, cerrado=False)], 0.005 * s, 0.0015 * s)

    # ---- cola: maslo y luego cerdas que caen y se abren
    maslo0, maslo1 = a(-0.530, -0.935), a(-0.585, -0.835)
    cono(maslo0, maslo1, 0.034, 0.028, 0.02)
    poli([maslo0 + a(0.01, 0.0), maslo1 + a(0.03, 0.02), maslo1 + a(0.01, 0.22), maslo1 + a(-0.05, 0.20),
          maslo1 + a(-0.045, 0.0)], 0.02)
    for k in range(70):
        u = rng.uniform()
        c0 = maslo0 + (maslo1 - maslo0) * (0.3 + 0.7 * u)
        largo = 0.36 + 0.22 * rng.uniform()
        abre = rng.normal(0, 0.028)
        ola = viento * 0.05
        pts = []
        for w in np.linspace(0, 1, 6):
            vaiv = math.sin(t * 1.6 - w * 2.4 + k * 0.3) * 0.012 * w + math.sin(t * 0.7) * 0.02 * w * w
            pts.append(c0 + a(-0.02 * w - ola * w * w + abre * w + vaiv, largo * w * (1 - 0.08 * w)))
        S.hebra([P(q) for q in spline(pts, 3, cerrado=False)], 0.010 * s, 0.0015 * s)

    # ---- silla celta de cuatro cuernos y su manta
    if silla:
        manta = [a(-0.06, -0.975), a(0.27, -0.995), a(0.29, -0.90), a(0.28, -0.80), a(0.12, -0.79),
                 a(-0.04, -0.80), a(-0.07, -0.88)]
        poli(manta, 0.01)
        poli([a(-0.02, -0.990), a(0.24, -1.005), a(0.235, -1.045), a(0.20, -1.03), a(0.11, -1.012),
              a(0.03, -1.03), a(-0.01, -1.05)], 0.008)
        for cx_, g in ((0.225, 25.0), (-0.005, -25.0)):
            cono(a(cx_, -1.035), a(cx_, -1.035) + rot((0.0, -0.05), g), 0.010, 0.007, 0.004)

    # ---- riendas: del bocado a la mano, con una caída suave
    boca = C(BOCA)
    if riendas_a is not None:
        fin = Pinv(riendas_a)
        mid = (boca + fin) / 2 + a(0, 0.08 + 0.02 * math.sin(t * 1.3))
        S.hebra([P(q) for q in spline([boca, mid, fin], 8, cerrado=False)], 0.0045 * s, 0.0045 * s)
    j = {"boca": P(boca), "nuca": P(nuca), "cruz": P(a(0.27, -1.0)), "silla": P(a(0.11, -1.01)),
         "cola": P(maslo0)}
    return Figura(S, None, j, s, espejo)
