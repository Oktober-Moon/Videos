"""Escena 2 — Un chip que no obedece.

Lugares y objetos en 3D (Blender, `tres_d/planos_e02.py`): la cámara del tranvía, la mesa de
evidencias con el iPhone en su bolsa, el teléfono abierto con su chip de memoria, el escritorio del
perito con la laptop y el cable, el teléfono que vibra con cada error y el Android en la mesa de noche.
Lo que muestran las pantallas se dibuja en 2D y se pega sobre el vidrio con la misma cámara
(`escenas/pantallas_e02.py`, `tres_d/vista_e02.py`). Los diagramas técnicos (Secure Enclave, UID,
contraseña + UID, los 80 ms, las dos zonas de FBE) son gráficos con sombra, brillo y profundidad.

2.0  Cámara del tranvía; el arresto; el sospechoso (foto); su iPhone en la mesa de evidencias.
2.1  Se abre un iPhone: el chip de memoria flash se ilumina; adentro, ceros y unos.
2.2  Extracción física en el escritorio del perito: cable, copia bit por bit, lo borrado que sigue
     ahí, millones de contraseñas por segundo; el teléfono ni se entera.
2.3  El Secure Enclave dentro del procesador A7 (foto y diagrama); el Titan M de Google.
2.4  El UID grabado en el silicio, que ningún programa puede leer.
2.5  Contraseña + UID = la clave que abre los archivos (o ruido).
2.6  80 milisegundos por intento y lo que eso suma.
2.7  La copia del laboratorio ya no sirve: la flecha hacia el teléfono se rompe.
2.8  El teléfono sobre la mesa: cada error alarga la espera, hasta «iPhone no disponible».
2.9  Un Android en la mesa de noche: se reinició y no arranca sin el PIN (la alarma no suena).
2.10 FBE: dos zonas de memoria; transición a los titulares de «FBI contra Apple».

Paletas: Friburgo en 2.0; mundo Apple de 2.1 a 2.8; Android en 2.9 y 2.10.
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
from escenas import pantallas_e02 as PT
from escenas.base import SR, Foto, Segmentos, Subescena, TarjetaTitulo, aparece, recorrido, texto
from escenas.plano3d import Plano3D
from escenas.tiempos_e02 import tiempos
from graficos import H, W, Luces, caja_dentro, gradiente_vertical, lim, suave
from paletas import ANDROID, APPLE, FRIBURGO, mezcla, rgb
from tres_d import vista_e02 as V

NUMERO = 2
F, AP, AN = rgb(FRIBURGO), rgb(APPLE), rgb(ANDROID)
NEGRO = np.zeros(3, np.float32)
BL = AP["blanco"]
AZ = AP["azul"]
GRIS_TXT = mezcla(AP["gris"], AP["blanco"], 0.55)
CRUCE = 0.9

# Todo en Eevee: son interiores con luz suave y objetos de cerca, sin calles mojadas de noche; la
# cámara del tranvía se degrada después a imagen de vigilancia.
MOTOR = {"e02_tranvia_cctv": "eevee", "e02_mesa_evidencias": "eevee", "e02_iphone_abierto": "eevee",
         "e02_laboratorio": "eevee", "e02_laboratorio_cifrado": "eevee", "e02_telefono_errores": "eevee",
         "e02_android_noche": "eevee"}

# Acabado de cine (el 3D ya trae su curva de color): leve tono partido con la paleta del lugar.
CINE_F = dict(sombras=mezcla(F["verde"], NEGRO, 0.45), luces=F["blanco"], mezcla=0.12, saturacion=0.95,
              contraste=0.06, halo=0.12, grano=0.012, vineta=0.32)
CINE_AP = dict(sombras=mezcla(AP["gris"], NEGRO, 0.35), luces=AP["blanco"], mezcla=0.10, saturacion=0.95,
               contraste=0.06, halo=0.14, grano=0.012, vineta=0.32)
CINE_DIAG = dict(sombras=mezcla(AP["gris"], NEGRO, 0.5), luces=AP["blanco"], mezcla=0.06, saturacion=1.0,
                 contraste=0.04, halo=0.22, grano=0.010, vineta=0.38)
CINE_AN = dict(sombras=mezcla(AN["gris"], NEGRO, 0.4), luces=AN["blanco"], mezcla=0.10, saturacion=0.95,
               contraste=0.06, halo=0.16, grano=0.012, vineta=0.34)


# =========================================================================== utilidades


def fondo_apple() -> np.ndarray:
    return DG.fondo_profundo(mezcla(AP["gris"], NEGRO, 0.74), mezcla(AP["gris"], AP["blanco"], 0.14))


def fondo_android() -> np.ndarray:
    return DG.fondo_profundo(mezcla(AN["gris"], NEGRO, 0.55), mezcla(AN["gris"], AN["verde"], 0.14))


def rotulo(img, cadena, x, y, tam=34, col=BL, a=1.0, alinear="izq", nombre="Inter-SemiBold.ttf"):
    return texto(img, cadena, x, y, tam, col, nombre=nombre, alinear=alinear, opacidad=a, sombra=0.45)


def cuadro_de(plano: Plano3D, t: float) -> float:
    """El tiempo exacto del cuadro de Blender que muestra `plano.cuadro(t)` (la cámara de la
    proyección tiene que ser la de ese cuadro, no la del instante t)."""
    f = min(plano.n, max(1, int(round(t * 30)) + 1))
    return (f - 1) / 30


def lento(img: np.ndarray, t: float, d: float, z0: float = 1.0, z1: float = 1.035, deriva=(0.0, 0.0)) -> np.ndarray:
    """Movimiento de cámara lento sobre un diagrama ya compuesto: acercamiento y deriva suaves."""
    u = 0.5 - 0.5 * math.cos(math.pi * lim(t / max(d, 1e-6)))
    z = z0 + (z1 - z0) * u
    if abs(z - 1) < 1e-4 and not any(deriva):
        return img
    M = np.float32([[z, 0, W / 2 * (1 - z) + deriva[0] * u], [0, z, H / 2 * (1 - z) + deriva[1] * u]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def panel(img, x0, y0, x1, y1, a, tinte=BL):
    return DG.tarjeta(img, x0, y0, x1, y1, a, tinte=tinte)


def leyenda(img, t, lineas, x=110, y=H - 250, ancho=760, tam=40, col=BL, sub_col=None):
    """Un rótulo en tarjeta de vidrio abajo a la izquierda: [(texto, inicio, fin, es_sub)]."""
    activos = [(c, a, b, s) for c, a, b, s in lineas if aparece(t, a, 0.5, b, 0.5) > 0]
    if not activos:
        return img
    alfa = max(aparece(t, a, 0.5, b, 0.5) for _, a, b, _ in activos)
    alto = 40 + sum(56 if not s else 44 for _, _, _, s in lineas)
    img = panel(img, x - 40, y - 64, x + ancho, y - 64 + alto, alfa)
    yy = y
    for cadena, a, b, sub in lineas:
        op = aparece(t, a, 0.5, b, 0.5)
        if sub:
            rotulo(img, cadena, x, yy - 8, int(tam * 0.7), sub_col if sub_col is not None else GRIS_TXT, op, nombre="Inter-Regular.ttf")
            yy += 44
        else:
            rotulo(img, cadena, x, yy, tam, col, op)
            yy += 56
    return img


def contorno_brillante(img, puntos, a, col=AZ, grosor=3.0, brillo=0.9):
    """Un polígono que se traza con brillo sobre el 3D (para señalar un chip)."""
    if a <= 0:
        return img
    tr = DG.Trazo()
    tr.tinta(col, 1.0)
    pts = list(puntos) + [puntos[0]]
    DG.linea(tr.c, pts, a, grosor)
    return tr.componer(img, brillo, col, 10)


# =========================================================================== título


def titulo() -> TarjetaTitulo:
    t = TarjetaTitulo(NUMERO, guion.leer()[NUMERO].titulo, AZ, BL)
    t.cine = CINE_AP
    return t


# =========================================================================== 2.0


class Sub20(Subescena):
    """Cámara del tranvía; el arresto; el sospechoso; su iPhone en la mesa de evidencias."""

    cine = CINE_F

    def preparar(self) -> None:
        s = self.T.oraciones
        self.seg = Segmentos([s[2], s[6]], CRUCE)
        self.cctv = Plano3D("e02_tranvia_cctv", s[2] + CRUCE / 2 + 0.3, motor=MOTOR["e02_tranvia_cctv"])
        self.ini_mesa = s[6] - CRUCE / 2
        self.mesa = Plano3D("e02_mesa_evidencias", self.d - self.ini_mesa + 0.2, motor=MOTOR["e02_mesa_evidencias"])
        self.planos3d = [self.cctv, self.mesa]
        self.sosp = Foto("2.0_hussein_khavari.jpg")
        self.fondo_sosp = gradiente_vertical([(0.0, mezcla(F["piedra"], NEGRO, 0.80)), (1.0, mezcla(F["verde"], NEGRO, 0.88))])
        self.fondo_sosp += DG._foco(560.0, 520.0, 800.0)[..., None] * F["piedra"] * 0.06

    # ---- cámara del tranvía, como imagen de vigilancia
    def _ver_cctv(self, t: float) -> np.ndarray:
        tc = math.floor(t * 12.5) / 12.5                                  # la grabación va a 12.5 cuadros por segundo
        img = self.cctv.cuadro(tc)
        lum = img @ np.array([0.30, 0.59, 0.11], np.float32)
        lum = np.clip((lum - 0.02) * 1.9, 0, 1) ** 0.8
        chica = cv2.resize(lum, (704, 396), interpolation=cv2.INTER_AREA)
        rng = np.random.default_rng(int(tc * 12.5) + 7)
        chica = chica + rng.normal(0, 0.035, chica.shape).astype(np.float32)
        lum = cv2.resize(cv2.GaussianBlur(chica, (0, 0), 0.6), (W, H), interpolation=cv2.INTER_LINEAR)
        lum[::2] *= 0.94                                                  # líneas de barrido
        out = np.stack([lum * 0.84, lum * 0.95, lum * 0.82], -1).astype(np.float32) * 0.92 + 0.03
        rotulo(out, "CÁMARA DEL TRANVÍA", 70, 86, 30, BL, 0.85, nombre="Inter-Regular.ttf")      # sin fecha ni hora: no las da el guion
        if int(t * 1.6) % 2 == 0:
            tr = DG.Trazo()
            tr.tinta(F["rojo"])
            tr.c.arc(W - 150, 75, 9, 0, math.tau)
            tr.c.fill()
            out = tr.componer(out)
            rotulo(out, "REC", W - 130, 86, 28, BL, 0.85, nombre="Inter-Regular.ttf")
        a = aparece(t, self.m(1) + 0.15, 0.6)
        out *= 1 - 0.45 * a
        out = panel(out, 80, H - 270, 860, H - 90, a, F["blanco"])
        rotulo(out, "ARRESTO", 130, H - 200, 26, mezcla(F["piedra"], F["blanco"], 0.45), a)
        rotulo(out, "3 de diciembre de 2016", 128, H - 136, 56, F["blanco"], a)
        return out

    # ---- el sospechoso
    def _ver_sospechoso(self, t: float) -> np.ndarray:
        img = self.fondo_sosp.copy()
        x0, y0, fw, fh = 120, 230, 1000, 623
        z = 1.0 + 0.035 * lim((t - self.m(2) + 0.5) / 9.0)
        if self.sosp.existe:
            im = self.sosp.im
            cubre = max(fw / im.width, fh / im.height) * z
            bw, bh = fw / cubre, fh / cubre
            bx, by = (im.width - bw) * 0.55, (im.height - bh) * 0.35
            foto = np.asarray(im.resize((fw, fh), Image.LANCZOS, box=caja_dentro((bx, by, bx + bw, by + bh), im.width, im.height)), np.float32) / 255
        else:
            foto = np.full((fh, fw, 3), 0.12, np.float32)
        m = np.zeros((H, W), np.float32)
        m[y0 : y0 + fh, x0 : x0 + fw] = 1
        sombra = cv2.GaussianBlur(np.roll(np.roll(m, 22, 0), 12, 1), (0, 0), 24)
        img *= (1 - 0.6 * sombra)[..., None]
        img[y0 : y0 + fh, x0 : x0 + fw] = foto
        img[y0 - 2 : y0, x0 - 2 : x0 + fw + 2] = F["blanco"] * 0.5
        img[y0 + fh : y0 + fh + 2, x0 - 2 : x0 + fw + 2] = F["blanco"] * 0.5
        img[y0 : y0 + fh, x0 - 2 : x0] = F["blanco"] * 0.5
        img[y0 : y0 + fh, x0 + fw : x0 + fw + 2] = F["blanco"] * 0.5
        x = 1210
        rotulo(img, "Hussein Khavari", x, 360, 64, F["blanco"], aparece(t, self.m(2) + 0.2, 0.8))
        img[392:395, x : x + int(470 * suave(lim((t - self.m(2) - 0.4) / 1.2)))] = F["rojo"]
        filas = (("llega a Alemania", 3, 0.2, True), ("noviembre de 2015", 3, 0.5, False), ("sin documentos", 3, 2.2, False),
                 ("dice ser afgano", 4, 0.2, True), ("y tener 16 años", 4, 0.9, False),
                 ("familia de acogida", 5, 1.2, False))
        y = 470
        for cadena, o, dt, sub in filas:
            a = aparece(t, self.m(o) + dt, 0.6)
            if sub:
                y += 18
                rotulo(img, cadena, x, y, 30, mezcla(F["piedra"], F["blanco"], 0.4), a, nombre="Inter-Regular.ttf")
                y += 44
            else:
                rotulo(img, cadena, x, y, 42, F["blanco"], a)
                y += 58
        return img

    # ---- el iPhone en la mesa de evidencias
    def _ver_mesa(self, t: float) -> np.ndarray:
        tm = t - self.ini_mesa
        img = self.mesa.cuadro(tm)
        tq = cuadro_de(self.mesa, tm)
        cam = V.camara_mesa(tq, self.mesa.n / 30)
        c, giro = V.MESA_TELEFONO
        esq = V.proyectar_esquinas(V.esquinas_telefono(V.IPHONE, c, giro), *cam)
        enciende = aparece(t, self.m(6) + 0.3, 0.5)
        codigo = aparece(t, self.m(7) + 0.2, 0.35)
        pantalla = PT.ios_bloqueo() * (1 - codigo) + PT.ios_codigo(0) * codigo
        return PT.pegar(img, pantalla, esq, 0.85 * enciende, halo=0.12)

    def cuadro(self, t: float) -> np.ndarray:
        partes = (self._ver_cctv, self._ver_sospechoso, self._ver_mesa)
        img = None
        for k, peso in self.seg.pesos(t):
            capa = partes[k](t)
            img = capa * peso if img is None else img + capa * peso
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("cámara", 0.0, sfx.zumbido_cctv(self.m(2) + 0.6, 201), -2, 0.8, 0.8)
        m.agregar("bolsa", self.m(6) + 0.1, sfx.bolsa_evidencia(1.8, 202), -3)
        m.agregar("sala", self.m(6) - 0.3, sfx.zumbido_electronico(d - self.m(6) + 0.3, 203), -16, 1.0, 1.0)
        return m.x[:n]


# =========================================================================== 2.1


class Sub21(Subescena):
    """Se abre un iPhone, se ilumina el chip de memoria flash y adentro hay ceros y unos."""

    cine = CINE_AP

    def preparar(self) -> None:
        s = self.T.oraciones
        self.t_abre = round(s[1] + 0.4, 2)
        self.t_acerca = round(s[3] - 0.3, 2)
        self.t_bits = self.t_acerca + 2.0                       # del chip en 3D a sus celdas
        self.abierto = Plano3D("e02_iphone_abierto", self.t_bits + CRUCE + 0.4, motor=MOTOR["e02_iphone_abierto"],
                               t_abre=self.t_abre, t_acerca=self.t_acerca)
        self.planos3d = [self.abierto]
        self.seg = Segmentos([self.t_bits + CRUCE / 2], CRUCE * 1.2)
        self.fondo = fondo_apple() * 0.7
        self.miniaturas = [Sub25._miniatura(0), Sub25._miniatura(2)]

    def _chip(self, t: float) -> np.ndarray:
        img = self.abierto.cuadro(t)
        tq = cuadro_de(self.abierto, t)
        cam = V.camara_abierto(tq, self.t_acerca, self.abierto.n / 30)
        x, y, _ = V.CHIP_FLASH
        z = 0.0012 + 0.0011 + 0.0010
        w, h = 0.0120 / 2 + 0.0006, 0.0160 / 2 + 0.0006
        esq = [V.proyectar(p, *cam) for p in ((x - w, y + h, z), (x + w, y + h, z), (x + w, y - h, z), (x - w, y - h, z))]
        a = suave(lim((t - self.m(2) - 0.2) / 1.0))
        apaga = 1 - aparece(t, self.t_acerca + 0.8, 0.8)
        img = contorno_brillante(img, esq, a * apaga, AZ, 3.0, 0.9)
        if a * apaga > 0:
            luz = Luces()
            cx = sum(p[0] for p in esq) / 4
            cy = sum(p[1] for p in esq) / 4
            luz.punto(cx, cy, 70, AZ, 0.25 * a * apaga * (0.8 + 0.2 * math.sin(t * 3)), forma="gauss")
            img += luz.resultado()
            b = aparece(t, self.m(2) + 0.6, 0.6) * (1 - aparece(t, self.t_acerca, 0.5))
            img = panel(img, 110, H - 300, 760, H - 110, b)
            rotulo(img, "memoria flash", 150, H - 215, 52, BL, b)
            rotulo(img, "soldada a la placa", 152, H - 150, 32, GRIS_TXT, b, nombre="Inter-Regular.ttf")
        return img

    def _celdas(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        lejos = np.zeros_like(img)
        DG.bits(lejos, 40, 20, 80, 36, 20, t * 0.6, mezcla(AZ, BL, 0.2), semilla=212, opacidad=0.55)
        img += cv2.GaussianBlur(lejos, (0, 0), 3.0) * 0.8
        deriva = (t - self.t_bits) * 6
        cerca = np.zeros_like(img)
        DG.bits(cerca, 123 - int(deriva), 140, 62, 20, 30, t, mezcla(AZ, BL, 0.4), semilla=21, opacidad=1.0)
        img += cerca + cv2.GaussianBlur(cerca, (0, 0), 6) * 0.5
        if t > self.m(4) - 0.4:
            # una foto y un mensaje entran y se deshacen en la rejilla: para el chip son lo mismo
            b = aparece(t, self.m(4) - 0.2, 0.6) * (1 - aparece(t, self.m(4) + 3.2, 1.4))
            for k, (x, nombre) in enumerate(((620, "foto"), (1300, "mensaje"))):
                img = panel(img, x - 170, 330, x + 170, 650, b)
                y0, x0 = 400, x - 120
                img[y0 : y0 + 130, x0 : x0 + 240] = img[y0 : y0 + 130, x0 : x0 + 240] * (1 - b) + self.miniaturas[k] * b
                rotulo(img, nombre, x, 600, 34, BL, b, alinear="centro")
            c = aparece(t, self.m(4) + 2.4, 0.7)
            img = panel(img, 460, 790, 1460, 900, c)
            rotulo(img, "para el chip, todo es igual: ceros y unos", W / 2, 860, 40, BL, c, alinear="centro")
        return lento(img, t - self.t_bits, self.d - self.t_bits, 1.0, 1.06)

    def cuadro(self, t: float) -> np.ndarray:
        partes = (self._chip, self._celdas)
        img = None
        for k, peso in self.seg.pesos(t):
            capa = partes[k](t)
            img = capa * peso if img is None else img + capa * peso
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(d, 211), -2, 1.5, 1.5)
        m.agregar("abre", self.t_abre, sfx.bolsa_evidencia(0.8, 213), -14)
        m.agregar("datos", self.t_bits - 0.3, sfx.datos(d - self.t_bits + 0.3, 212, 12), -10, 1.0, 1.5)
        return m.x[:n]


# =========================================================================== 2.2


class Sub22(Subescena):
    """Extracción física: el cable, la copia bit por bit, lo borrado que sigue ahí, la fuerza bruta;
    el teléfono, a un lado, ni se entera."""

    cine = CINE_AP

    def preparar(self) -> None:
        s = self.T.oraciones
        self.marcas = [round(s[k], 2) for k in (1, 3, 4, 7, 8)]
        self.lab = Plano3D("e02_laboratorio", self.d + 0.2, motor=MOTOR["e02_laboratorio"], marcas=self.marcas)
        self.planos3d = [self.lab]
        self.claves = V.claves_laboratorio(self.marcas)

    def cuadro(self, t: float) -> np.ndarray:
        m = self.m
        img = self.lab.cuadro(t)
        tq = cuadro_de(self.lab, t)
        cam = V.recorrido(tq, self.claves)
        # la pantalla de la laptop: la herramienta del perito
        esq_l = V.proyectar_esquinas(V.esquinas_laptop(*V.LAB_LAPTOP), *cam)
        img = PT.pegar(img, PT.laptop_extraccion(t, self.T.oraciones), esq_l, 0.92, halo=0.10)
        # la del teléfono: arrancado con el programa del perito; al final se apaga
        c, giro = V.LAB_TELEFONO
        esq_t = V.proyectar_esquinas(V.esquinas_telefono(V.IPHONE, (c[0], c[1], c[2] + 0.0016), giro), *cam)
        lineas = int(lim((t - m(1) - 0.6) / 3.0) * 8)
        tel = aparece(t, m(1) + 0.5, 0.4) * (1 - aparece(t, m(8) - 0.2, 0.8))
        img = PT.pegar(img, PT.ios_arranque(max(1, lineas)), esq_t, 0.85 * tel, halo=0.1)
        img = leyenda(img, t, [("Extracción física", 0.3, m(1) + 1.5, False)])
        # lo borrado y la memoria sin cifrar ya los dice la pantalla de la laptop, que llena el cuadro
        img = leyenda(img, t, [("el teléfono ni se enteraba", m(8) + 0.3, self.d - 0.3, False)])
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(d, 221), -10, 1.5, 1.5)
        m.agregar("conector", self.m(1) + 0.2, sfx.candado(224)[: int(0.25 * SR)], -18)
        m.agregar("datos", self.m(2), sfx.datos(self.m(4) - self.m(2) + 0.5, 222), -4, 0.3, 0.6)
        m.agregar("teclado", self.m(7), sfx.teclado(self.m(8) - self.m(7) + 0.5, 223, 2.4), -6, 0.1, 0.5)
        return m.x[:n]


# =========================================================================== 2.3


class Sub23(Subescena):
    """Un procesador dentro del procesador: el Secure Enclave. Al final, el Titan M de Google."""

    cine = CINE_DIAG

    def preparar(self) -> None:
        self.fondo = fondo_apple()
        self.a7 = Foto("2.3_chip_a7.jpg", AZ, 0.10)
        self.titan = Foto("2.3_titan_m.jpg", AZ, 0.08)
        s = self.T.oraciones
        self.seg = Segmentos([s[1] + 1.6, s[6]], 1.0)

    def _foto_a7(self, t):
        z, cx, cy = recorrido(t, self.m(1) + 2.5, 1.0, 1.14, (0.5, 0.5), (0.52, 0.44))
        img = self.a7.ver(z, cx, cy) * 0.82
        a = aparece(t, self.m(1) + 0.1, 0.6)
        img = panel(img, 80, H - 280, 760, H - 90, a)
        rotulo(img, "APPLE A7", 130, H - 200, 26, GRIS_TXT, a)
        rotulo(img, "2013 · iPhone 5S", 128, H - 136, 52, BL, a)
        return img

    def _diagrama(self, t):
        img = self.fondo.copy()
        m = self.m
        tr = DG.Trazo()
        c = tr.c
        dx = 100                                                             # el chip al centro del cuadro
        c.translate(dx, 0)
        p_chip = suave(lim((t - m(1) - 1.4) / 1.2))
        tr.tinta(mezcla(AP["gris"], BL, 0.10), 0.85 * p_chip)
        D.rect_redondeado(c, 540, 220, 640, 640, 38)
        c.fill()
        tr.tinta(BL, 0.85)
        DG.chip(c, 860, 540, 640, 4, 10, p_chip)
        cierre = suave(lim((t - m(3) + 0.3) / 0.8))
        p_in = suave(lim((t - m(1) - 2.4) / 1.2))
        tr.tinta(mezcla(AZ, NEGRO, 0.55), 0.9 * p_in)
        D.rect_redondeado(c, 880, 400, 200, 200, 14)
        c.fill()
        tr.tinta(AZ)
        DG.caja(c, 880, 400, 200, 200, 14, p_in, 5)
        if cierre > 0:                                                       # muro doble: aislado
            tr.tinta(AZ, cierre)
            DG.caja(c, 866, 386, 228, 228, 20, 1.0, 2)
            tr.tinta(BL, cierre)
            DG.candado(c, 980, 486, 56, cerrado=cierre)
        if t > m(4) - 0.3:                                                   # iOS y las apps no pueden entrar
            a = aparece(t, m(4) - 0.3, 0.6)
            tr.tinta(mezcla(AP["gris"], BL, 0.2), 0.9 * a)
            D.rect_redondeado(c, 590, 420, 200, 160, 14)
            c.fill()
            tr.tinta(BL, a)
            DG.caja(c, 590, 420, 200, 160, 14, a, 3)
            choque = suave(lim((t - m(4)) / 1.0))
            DG.flecha(c, (795, 460), (795 + 70 * choque, 460), 1.0 if choque > 0 else 0, 4)
            if choque > 0.95:
                tr.tinta(mezcla(BL, AZ, 0.2), aparece(t, m(4) + 1.0, 0.3, m(5) - 0.2))
                DG.cruz(c, 866, 460, 24, 5)
        if t > m(5) - 0.2:                                                   # solo preguntas y respuestas
            a = aparece(t, m(5) - 0.2, 0.6)
            tr.tinta(AZ, a)
            u = (t * 0.6) % 1.0
            DG.flecha(c, (795, 530), (866, 530), 1.0, 3, 14)
            DG.flecha(c, (866, 565), (795, 565), 1.0, 3, 14)
            c.rectangle(795 + 67 * u - 6, 524, 12, 12)
            c.fill()
        img = DG.componer_relieve(tr, img, brillo=0.35, col_brillo=AZ, sigma_brillo=14)
        rotulo(img, "Procesador principal", 590 + dx, 290, 34, BL, aparece(t, m(1) + 1.8, 0.6))
        rotulo(img, "Secure Enclave", 980 + dx, 680, 38, AZ, aparece(t, m(3), 0.6), alinear="centro")
        rotulo(img, "memoria y sistema propios", 980 + dx, 722, 26, GRIS_TXT, aparece(t, m(2), 0.6), alinear="centro",
               nombre="Inter-Regular.ttf")
        if t > m(4) - 0.3:
            rotulo(img, "iOS y las apps", 690 + dx, 510, 28, BL, aparece(t, m(4) - 0.3, 0.6), alinear="centro")
        if t > m(5) - 0.2:
            rotulo(img, "preguntas y respuestas", 700 + dx, 630, 22, AZ, aparece(t, m(5), 0.6), alinear="centro", nombre="Inter-Regular.ttf")
        return lento(img, t - m(1), m(6) - m(1) + 1.0, 1.0, 1.05)

    def _foto_titan(self, t):
        z, cx, cy = recorrido(t - self.m(6), self.d - self.m(6), 1.0, 1.08)
        img = self.titan.ver(z, cx, cy) * 0.82
        a = aparece(t, self.m(6) + 0.3, 0.6)
        img = panel(img, 80, H - 280, 760, H - 90, a)
        rotulo(img, "GOOGLE TITAN M", 130, H - 200, 26, GRIS_TXT, a)
        rotulo(img, "2018 · teléfonos Pixel", 128, H - 136, 52, BL, a)
        return img

    def cuadro(self, t: float) -> np.ndarray:
        partes = (self._foto_a7, self._diagrama, self._foto_titan)
        img = None
        for k, peso in self.seg.pesos(t):
            capa = partes[k](t)
            img = capa * peso if img is None else img + capa * peso
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(d, 231), -12, 1.5, 1.5)
        m.agregar("candado", self.m(3), sfx.candado(232), -2)
        return m.x[:n]


# =========================================================================== 2.4


class Sub24(Subescena):
    """Un número aleatorio que se graba dentro del silicio: el UID, que nunca sale del chip."""

    cine = CINE_DIAG
    UID = "7F3A 91C4 0B62 E85D 2A17 C9F0 4D3B 86E1"

    def preparar(self) -> None:
        self.fondo = fondo_apple()

    def cuadro(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        m = self.m
        tr = DG.Trazo()
        c = tr.c
        p = aparece(t, 0.2, 1.2)
        tr.tinta(mezcla(AP["gris"], BL, 0.10), 0.9 * p)
        D.rect_redondeado(c, 680, 280, 560, 560, 34)
        c.fill()
        tr.tinta(BL, 0.85)
        DG.chip(c, 960, 560, 560, 4, 9, p)
        hundido = aparece(t, m(2), 1.0)
        if t > m(2):
            tr.tinta(AZ, hundido)
            DG.candado(c, 960, 640, 90, cerrado=hundido)
        if t > m(3) - 0.2:                                                    # programas que rebotan
            for k, (x0, y0) in enumerate(((300, 260), (300, 860), (1620, 260), (1620, 860))):
                u = lim((t - m(3) - 0.2 * k) / 1.2)
                if u <= 0:
                    continue
                destino = np.array([960 + (x0 - 960) * 0.42, 560 + (y0 - 560) * 0.42])
                avance = math.sin(math.pi * min(u, 1.0)) if u < 1 else 0.0
                q = np.array([x0, y0]) + (destino - np.array([x0, y0])) * (u * 2 if u < 0.5 else (1 - u) * 2)
                tr.tinta(BL, 0.8 * (1 - max(0, u - 0.7) / 0.3))
                DG.archivo(c, q[0] - 22, q[1] - 28, 56, 3)
                if 0.45 < u < 0.75:
                    tr.tinta(AZ, avance)
                    DG.cruz(c, destino[0], destino[1], 26, 4)
        if t > m(4) - 0.2:                                                    # por dentro: cifrar y descifrar
            a = aparece(t, m(4) - 0.2, 0.6)
            tr.tinta(AZ, a)
            g = t * 1.4
            for k in range(2):
                c.set_line_width(4)
                c.arc(960, 640, 120, g + k * math.pi, g + k * math.pi + 2.2)
                c.stroke()
        img = DG.componer_relieve(tr, img, brillo=0.4, col_brillo=AZ, sigma_brillo=14)
        graba = lim((t - 0.6) / max(1.0, m(1) - 0.4))
        if t < m(2) + 1.0:                                                    # el número se graba con láser
            rng = np.random.default_rng(int(t * 20))
            cadena = "".join(ch if (ch == " " or i / len(self.UID) < graba) else "0123456789ABCDEF"[rng.integers(16)]
                             for i, ch in enumerate(self.UID))
            rotulo(img, cadena, 960, 470, 40, BL, 1 - hundido, alinear="centro", nombre="Inter-Regular.ttf")
            if graba < 1:
                luz = Luces()
                luz.punto(960 - 330 + 660 * graba, 456, 14, mezcla(AZ, BL, 0.6), 1.6, forma="gauss")
                img += luz.resultado()
        rotulo(img, "UID", 960, 380, 48, AZ, aparece(t, m(1), 0.6), alinear="centro")
        img = panel(img, 560, 935, 1360, 1030, aparece(t, m(2), 0.6))
        rotulo(img, "grabado en el silicio", 960, 995, 32, BL, aparece(t, m(2), 0.6, m(3) - 0.2), alinear="centro")
        rotulo(img, "ningún programa la puede leer", 960, 995, 32, BL, aparece(t, m(3), 0.6, m(4) - 0.2), alinear="centro")
        rotulo(img, "solo se usa por dentro: cifrar y descifrar", 960, 995, 32, BL, aparece(t, m(4), 0.6), alinear="centro")
        return lento(img, t, self.d, 1.0, 1.05)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(d, 241), -14, 1.5, 1.5)
        m.agregar("láser", 0.6, sfx.laser(max(1.2, self.m(1) - 0.2), 242), -3)
        m.agregar("metal", self.m(2), sfx.tono_metalico(243), -4)
        return m.x[:n]


# =========================================================================== 2.5


class Sub25(Subescena):
    """Contraseña + UID → mezcla → clave → archivos que se abren (o se quedan en ruido)."""

    cine = CINE_DIAG

    def preparar(self) -> None:
        self.fondo = fondo_apple()
        self.miniaturas = [self._miniatura(k) for k in range(3)]

    @staticmethod
    def _miniatura(k: int) -> np.ndarray:
        s, c = D.lienzo(240, 130)
        if k == 0:                                                            # foto: cielo, montaña y sol
            D.tinta(c, mezcla(AZ, BL, 0.55))
            c.rectangle(0, 0, 240, 130)
            c.fill()
            D.tinta(c, mezcla(AP["gris"], BL, 0.25))
            D.rellenar(c, [(0, 130), (70, 50), (120, 95), (165, 60), (240, 130)], suave=False)
            D.tinta(c, BL)
            c.arc(185, 35, 16, 0, math.tau)
            c.fill()
        elif k == 1:                                                          # documento: renglones
            D.tinta(c, BL)
            c.rectangle(0, 0, 240, 130)
            c.fill()
            D.tinta(c, mezcla(AP["gris"], BL, 0.4))
            for r in range(5):
                c.rectangle(20, 20 + r * 20, 200 - (r % 3) * 40, 8)
                c.fill()
        else:                                                                 # mensajes: globos
            D.tinta(c, mezcla(AP["gris"], BL, 0.85))
            c.rectangle(0, 0, 240, 130)
            c.fill()
            D.tinta(c, mezcla(AP["gris"], BL, 0.45))
            D.rect_redondeado(c, 14, 14, 130, 36, 16)
            c.fill()
            D.tinta(c, AZ)
            D.rect_redondeado(c, 96, 60, 130, 36, 16)
            c.fill()
            D.tinta(c, mezcla(AP["gris"], BL, 0.45))
            D.rect_redondeado(c, 14, 102, 90, 22, 11)
            c.fill()
        return D.a_rgba(s)[..., :3]

    def cuadro(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        m = self.m
        mal = t > m(5)
        a_pw = aparece(t, 0.2, 0.6)
        img = panel(img, 110, 290, 470, 430, a_pw)
        if m(0) + 1.5 < t < m(2):
            img = panel(img, 110, 510, 470, 640, aparece(t, m(0) + 1.5, 0.5, m(1) + 0.6) * 0.8)
        p2 = suave(lim((t - m(2)) / 1.4))
        img = panel(img, 760, 390, 1060, 640, p2)
        img = panel(img, 190, 540, 390, 740, aparece(t, m(2) - 0.4, 0.8), AZ)
        tr = DG.Trazo()
        c = tr.c
        tr.tinta(BL, 0.9 * a_pw)
        escritos = min(6, int(max(0.0, t - 0.6) * 4))
        for k in range(6):
            c.arc(170 + k * 48, 360, 12, 0, math.tau)
            c.fill() if k < escritos else c.stroke()
        if m(0) + 1.5 < t < m(2):                                            # no hay copia que comparar
            a = aparece(t, m(0) + 1.5, 0.5, m(1) + 0.6)
            tr.tinta(AZ, a)
            DG.cruz(c, 290, 575, 64, 6)
        tr.tinta(BL, 0.85 * aparece(t, m(2) - 0.4, 0.5))
        DG.chip(c, 290, 640, 150, 3, 5, aparece(t, m(2) - 0.4, 0.8))
        tr.tinta(AZ)
        DG.flecha(c, (470, 360), (760, 470), p2, 4, curva=-30)
        DG.flecha(c, (380, 640), (760, 560), p2, 4, curva=30)
        if p2 > 0.5:                                                         # la mezcla gira
            tr.tinta(AZ, p2)
            g = t * 2.2
            for k in range(3):
                c.set_line_width(5)
                c.arc(910, 515, 60, g + k * 2.09, g + k * 2.09 + 1.3)
                c.stroke()
        p3 = suave(lim((t - m(3)) / 1.0))
        tr.tinta(AZ)
        DG.flecha(c, (1060, 515), (1250, 515), p3, 4)
        if p3 > 0.3:
            tr.tinta(mezcla(BL, AZ, 0.35) if not mal else GRIS_TXT, p3)
            DG.llave(c, 1340, 515, 150)
        p4 = suave(lim((t - m(4) + 0.2) / 1.0))
        tr.tinta(AZ)
        DG.flecha(c, (1430, 515), (1540, 515), p4, 4)
        img = DG.componer_relieve(tr, img, brillo=0.3, col_brillo=AZ, sigma_brillo=12)
        rotulo(img, "tu contraseña", 120, 270, 30, BL, a_pw)
        rotulo(img, "copia guardada", 140, 500, 24, GRIS_TXT, aparece(t, m(0) + 1.5, 0.5, m(1) + 0.6), nombre="Inter-Regular.ttf")
        rotulo(img, "UID", 290, 795, 34, AZ, aparece(t, m(2) - 0.2, 0.5), alinear="centro")
        rotulo(img, "mezcla", 910, 372, 34, BL, p2, alinear="centro")
        rotulo(img, "algoritmo de cifrado", 910, 680, 24, GRIS_TXT, p2, alinear="centro", nombre="Inter-Regular.ttf")
        rotulo(img, "clave", 1340, 430, 34, BL, p3, alinear="centro")
        if p4 > 0:                                                           # nítidos o ruido
            ruido = 1.0 if mal else 1 - suave(lim((t - m(4)) / 0.8))
            sombra = np.zeros((H, W), np.float32)
            for k in range(3):
                x, y = 1570, 300 + k * 160
                sombra[y + 10 : y + 140, x + 8 : x + 248] = 1
            img *= (1 - 0.45 * p4 * cv2.GaussianBlur(sombra, (0, 0), 10))[..., None]
            for k in range(3):
                x, y = 1570, 300 + k * 160
                estatica = DG.ruido_visual(130, 240, t, k)[..., None] * 0.8
                bloque = self.miniaturas[k] * (1 - ruido) + estatica * ruido
                img[y : y + 130, x : x + 240] = img[y : y + 130, x : x + 240] * (1 - p4) + bloque * p4
            rotulo(img, "archivos", 1690, 270, 30, BL, p4, alinear="centro")
            img = panel(img, 560, 940, 1360, 1030, p4)
            rotulo(img, "contraseña correcta: se abren" if not mal else "contraseña incorrecta: ruido", 960, 998, 34,
                   BL, p4, alinear="centro")
        return lento(img, t, self.d, 1.0, 1.04)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(d, 251), -14, 1.5, 1.5)
        m.agregar("teclado", 0.6, sfx.teclado(1.6, 252), -8)
        m.agregar("cerradura", self.m(4) + 0.5, sfx.candado(253), -3)
        m.agregar("estática", self.m(5) + 0.4, sfx.estatica(min(2.5, self.d - self.m(5) - 0.6), 254), -6)
        return m.x[:n]


# =========================================================================== 2.6


class Sub26(Subescena):
    """80 milisegundos por intento; lo que suman 10 000, un millón y una contraseña alfanumérica."""

    cine = CINE_DIAG

    def preparar(self) -> None:
        self.fondo = fondo_apple()

    def cuadro(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        m = self.m
        if t < m(4) - 0.3:
            a = aparece(t, 0.3, 0.6, m(4) - 0.6)
            img = panel(img, 720, 230, 1200, 710, a * 0.9, AZ)
            tr = DG.Trazo()
            c = tr.c
            vueltas = (t / 0.08) % 1.0                                      # una vuelta cada 80 ms
            tr.tinta(GRIS_TXT, 0.35 * a)
            c.set_line_width(10)
            c.arc(960, 470, 190, 0, math.tau)
            c.stroke()
            tr.tinta(AZ, a)
            c.arc(960, 470, 190, -math.pi / 2, -math.pi / 2 + math.tau * vueltas)
            c.stroke()
            img = DG.componer_relieve(tr, img, sombra=0.3, brillo=0.6, col_brillo=AZ, sigma_brillo=12)
            rotulo(img, "80 ms", 960, 505, 110, BL, a, alinear="centro", nombre="Inter-Light.ttf")
            rotulo(img, "por intento", 960, 772, 34, GRIS_TXT, a, alinear="centro", nombre="Inter-Regular.ttf")
            rotulo(img, "para una persona: nada", 960, 870, 36, BL, aparece(t, m(2), 0.5, m(4) - 0.6), alinear="centro")
            rotulo(img, "para una máquina: un freno", 960, 930, 36, AZ, aparece(t, m(3), 0.5, m(4) - 0.6), alinear="centro")
        filas = ((4, "4 dígitos", "10 000", "13 minutos"), (5, "6 dígitos", "1 000 000", "22 horas"),
                 (6, "6 caracteres", "minúsculas y números", "más de 5 años y medio"))
        for k, (o, que, cuantas, tiempo) in enumerate(filas):
            if t < m(o) - 0.3:
                continue
            a = aparece(t, m(o) - 0.3, 0.6)
            y = 300 + k * 230
            img = panel(img, 110, y - 70, 1810, y + 130, a * 0.85)
            rotulo(img, que, 160, y, 32, GRIS_TXT, a, nombre="Inter-Regular.ttf")
            rotulo(img, cuantas, 160, y + 84, 66 if k < 2 else 44, BL, a, nombre="Inter-Light.ttf")
            b = aparece(t, m(o) + 1.2, 0.6)
            tr = DG.Trazo()
            tr.tinta(AZ, b)
            DG.flecha(tr.c, (780, y + 58), (980, y + 58), b, 4)
            img = DG.componer_relieve(tr, img, sombra=0.3, brillo=0.5, col_brillo=AZ)
            rotulo(img, tiempo, 1030, y + 82, 60, AZ if k == 2 else BL, b, nombre="Inter-SemiBold.ttf")
        return lento(img, t, self.d, 1.0, 1.03)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        ticks = list(np.arange(0.4, self.m(4) - 0.4, 0.08))
        m.agregar("tics", 0.0, sfx.tics(ticks, d, 261), -8, 0.5, 0.8)
        for k, o in enumerate((4, 5, 6)):
            m.agregar("golpe", self.m(o) + 1.2, sfx.tono_metalico(262 + k), -10)
        return m.x[:n]


# =========================================================================== 2.7


class Sub27(Subescena):
    """En la laptop del laboratorio solo hay datos cifrados; la flecha hacia el teléfono se rompe:
    cada intento tiene que pasar por el chip de ese teléfono."""

    cine = CINE_AP

    def preparar(self) -> None:
        self.lab = Plano3D("e02_laboratorio_cifrado", self.d + 0.2, motor=MOTOR["e02_laboratorio_cifrado"])
        self.planos3d = [self.lab]

    def cuadro(self, t: float) -> np.ndarray:
        m = self.m
        img = self.lab.cuadro(t)
        tq = cuadro_de(self.lab, t)
        cam = V.camara_cifrado(tq, self.lab.n / 30)
        esq_l = V.proyectar_esquinas(V.esquinas_laptop(*V.LAB_LAPTOP), *cam)
        img = PT.pegar(img, PT.laptop_cifrado(t), esq_l, 0.9 * aparece(t, 0.2, 0.6), halo=0.1)
        tel = V.proyectar(V.centro_telefono_lab(), *cam)
        lap = (sum(p[0] for p in esq_l) / 4, sum(p[1] for p in esq_l) / 4)
        tr = DG.Trazo()
        rompe = suave(lim((t - m(3) + 0.6) / 0.6))
        p = suave(lim((t - m(2)) / 1.2))
        a0 = np.array(lap, float) + (np.array(tel, float) - np.array(lap, float)) * 0.22
        a1 = np.array(tel, float) + (np.array(lap, float) - np.array(tel, float)) * 0.2
        tr.tinta(BL, 0.9)
        if rompe <= 0:
            DG.flecha(tr.c, a0, a1, p, 8, 30, curva=-50)
        else:                                                                 # la flecha se parte en dos
            medio = (a0 + a1) / 2
            n_ = np.array([-(a1 - a0)[1], (a1 - a0)[0]])
            n_ = n_ / (np.linalg.norm(n_) + 1e-9)
            DG.linea(tr.c, [a0, medio - (medio - a0) * 0.18 + n_ * 34 * rompe], 1.0, 8)
            DG.flecha(tr.c, medio + (a1 - medio) * 0.18 - n_ * 34 * rompe, a1 + n_ * 46 * rompe, 1.0, 8, 30)
        if t > m(4) - 0.2:                                                   # cada intento, por el chip
            a = aparece(t, m(4) - 0.2, 0.6)
            tr.tinta(AZ, a)
            r = 95
            u = (t * 0.7) % 1.0
            tr.c.set_line_width(4)
            tr.c.arc(tel[0], tel[1], r, 0, math.tau)
            tr.c.stroke()
            ang = u * math.tau
            tr.c.arc(tel[0] + math.cos(ang) * r, tel[1] + math.sin(ang) * r, 10, 0, math.tau)
            tr.c.fill()
        img = DG.componer_relieve(tr, img, sombra=0.4, brillo=0.35, col_brillo=AZ)
        arriba = dict(x=110, y=210)                                   # el teléfono queda abajo: los rótulos, arriba
        img = leyenda(img, t, [("la copia ya no sirve", m(2) + 0.2, m(4) - 0.3, False),
                               ("en el laboratorio solo hay datos cifrados", m(3) + 0.2, m(4) - 0.3, True)], **arriba)
        img = leyenda(img, t, [("el UID nunca sale del chip", m(1) + 0.1, m(2) - 0.1, False)], **arriba)
        img = leyenda(img, t, [("cada intento pasa por ese chip", m(4) + 0.1, self.d, False),
                               ("en ese teléfono", m(4) + 0.6, self.d, True)], **arriba)
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(d, 271), -14, 1.5, 1.5)
        m.agregar("error", self.m(3) - 0.4, sfx.error_suave(272), -2)
        return m.x[:n]


# =========================================================================== 2.8


class Sub28(Subescena):
    """El teléfono sobre la mesa: cada error lo hace vibrar y alarga la espera, hasta «iPhone no
    disponible»; reiniciar no borra la cuenta; con la opción activada, al décimo borra todo."""

    cine = CINE_AP
    ESPERAS = ((2, "1 minuto"), (3, "5 minutos"), (4, "15 minutos"), (5, "1 hora"), (6, "3 horas"), (7, "8 horas"))

    def preparar(self) -> None:
        self.golpes = [round(x, 3) for x in self._intentos()]
        self.tel = Plano3D("e02_telefono_errores", self.d + 0.2, motor=MOTOR["e02_telefono_errores"], golpes=self.golpes)
        self.planos3d = [self.tel]

    def _intentos(self) -> list[float]:
        m = self.m
        return [m(1) + 0.3, m(1) + 0.9, m(1) + 1.5] + [m(o) + 0.1 for o in range(2, 9)]

    def _espera(self, t: float) -> str:
        return next((cad for o, cad in reversed(self.ESPERAS) if t >= self.m(o)), "")

    def _pantalla(self, t: float) -> np.ndarray:
        m = self.m
        hechos = sum(1 for ti in self.golpes if t >= ti)
        if t >= m(10) + 0.4:
            return PT.ios_borrando(lim((t - m(10) - 0.8) / 2.5))
        if t >= self.golpes[-1]:
            return PT.ios_codigo(0, aviso="iPhone no disponible", sub="")
        espera = self._espera(t)
        if espera:
            return PT.ios_codigo(0, aviso="iPhone no disponible", sub=f"Vuelve a intentarlo en {espera}")
        if hechos < 3 and t > m(0) + 0.6:                                    # se escriben seis dígitos, error, de nuevo
            sig = self.golpes[hechos]
            return PT.ios_codigo(int(lim(1 - (sig - t) / 0.5) * 6))
        return PT.ios_codigo(0)

    def cuadro(self, t: float) -> np.ndarray:
        m = self.m
        img = self.tel.cuadro(t)
        tq = cuadro_de(self.tel, t)
        cam = V.camara_errores(tq, self.tel.n / 30)
        c, giro = V.LAB_TELEFONO
        desp = V.vibracion(tq, self.golpes)
        esq = V.proyectar_esquinas(V.esquinas_telefono(V.IPHONE, (c[0], c[1], c[2] + 0.0016), giro, desp), *cam)
        img = PT.pegar(img, self._pantalla(t), esq, 0.9 * aparece(t, 0.15, 0.4), halo=0.12)
        hechos = sum(1 for ti in self.golpes if t >= ti)
        a = aparece(t, self.golpes[0] - 0.1, 0.3)
        img = panel(img, W - 560, 130, W - 100, 360, a)
        rotulo(img, "ERRORES", W - 510, 196, 24, GRIS_TXT, a)
        rotulo(img, f"{hechos}", W - 512, 300, 92, BL if hechos < 10 else AZ, a, nombre="Inter-Light.ttf")
        espera = self._espera(t)
        if espera and t < self.golpes[-1]:
            rotulo(img, "espera", W - 360, 250, 26, GRIS_TXT, a, nombre="Inter-Regular.ttf")
            rotulo(img, espera, W - 360, 300, 40, AZ, a)
        img = leyenda(img, t, [("del primero al tercero: nada", m(1) + 0.2, m(2) - 0.1, False)])
        img = leyenda(img, t, [("reiniciar no borra la cuenta", m(9) + 0.1, m(10) - 0.2, False),
                               ("la cuenta la guarda el chip", m(9) + 0.6, m(10) - 0.2, True)])
        img = leyenda(img, t, [("al décimo error, borra todo", m(10) + 0.3, self.d, False),
                               ("si el dueño activó la opción", m(10) + 0.7, self.d, True)])
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        for k, ti in enumerate(self._intentos()):
            m.agregar("vibración", ti, sfx.vibracion(280 + k), -3 if k >= 3 else -8)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(d, 291), -16, 1.5, 1.5)
        return m.x[:n]


# =========================================================================== 2.9


class Sub29(Subescena):
    """Android: antes, una sola clave para toda la memoria; si se reiniciaba de noche, no arrancaba
    sin el PIN y la alarma no sonaba."""

    cine = CINE_AN

    def preparar(self) -> None:
        self.noche = Plano3D("e02_android_noche", self.d + 0.2, motor=MOTOR["e02_android_noche"])
        self.planos3d = [self.noche]

    def cuadro(self, t: float) -> np.ndarray:
        m = self.m
        img = self.noche.cuadro(t)
        tq = cuadro_de(self.noche, t)
        cam = V.camara_noche(tq, self.noche.n / 30)
        c, giro = V.NOCHE_TELEFONO
        esq = V.proyectar_esquinas(V.esquinas_telefono(V.ANDROID, c, giro), *cam)
        img = PT.pegar(img, PT.android_inicio(), esq, 0.75 * aparece(t, 0.2, 0.8), halo=0.2)
        verde, claro = AN["verde"], mezcla(AN["blanco"], AN["gris"], 0.35)
        a0 = aparece(t, 0.3, 0.6, m(2) - 0.3)
        img = panel(img, 80, 120, 860, 470, a0, verde)
        rotulo(img, "FBE", 130, 230, 64, verde, a0, nombre="Inter-Bold.ttf")
        rotulo(img, "cifrado basado en archivos", 132, 290, 32, AN["blanco"], a0, nombre="Inter-Regular.ttf")
        rotulo(img, "Android 7 · 2016", 132, 370, 36, AN["blanco"], a0 * aparece(t, m(1), 0.6))
        rotulo(img, "obligatorio desde Android 10", 132, 420, 28, claro, a0 * aparece(t, m(1) + 1.2, 0.6), nombre="Inter-Regular.ttf")
        b = aparece(t, m(2), 0.6, m(4) - 0.3)
        img = panel(img, 80, 120, 860, 330, b)
        rotulo(img, "antes: una sola clave", 132, 210, 42, AN["blanco"], b)
        rotulo(img, "para toda la memoria", 132, 270, 32, claro, b, nombre="Inter-Regular.ttf")
        if t > m(4) - 0.4:
            a = aparece(t, m(4) - 0.2, 0.6)
            img = panel(img, 80, 120, 860, 520, a)
            rotulo(img, "se reinició de noche", 132, 200, 42, AN["blanco"], a)
            rotulo(img, "la alarma no sonaba", 132, 290, 36, verde, aparece(t, m(4) + 1.4, 0.5))
            rotulo(img, "las llamadas no entraban", 132, 360, 36, verde, aparece(t, m(4) + 2.4, 0.5))
            rotulo(img, "hasta que alguien escribía el PIN", 132, 440, 30, claro, aparece(t, m(4) + 3.2, 0.5),
                   nombre="Inter-Regular.ttf")
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("noche", 0.0, sfx.viento(d, 292, 0.3), -14, 2.0, 2.0)
        m.agregar("alarma", self.m(4) + 1.0, sfx.alarma_cortada(1.1, 293), -4)
        return m.x[:n]


# =========================================================================== 2.10


class Sub210(Subescena):
    """La memoria en dos zonas (una abierta al encender, otra cerrada hasta la contraseña); el
    resumen de Friburgo y, al final, los titulares de FBI contra Apple."""

    cine = CINE_AN

    def preparar(self) -> None:
        self.fondo = fondo_android()
        self.titulares = Foto("3.2_titulares_2016.jpg")
        s = self.T.oraciones
        self.seg = Segmentos([s[7] - 0.2], 0.8)

    def _zonas(self, t):
        img = self.fondo.copy()
        m = self.m
        a = aparece(t, 0.2, 0.8, m(6) - 0.2)
        div = suave(lim((t - m(0) - 0.6) / 0.8))
        abre = aparece(t, m(1), 0.8)
        cierra = aparece(t, m(4), 0.8)
        img = panel(img, 262, 222, 940, 738, a * aparece(t, m(1) - 0.2, 0.6), AN["verde"])
        img = panel(img, 980, 222, 1658, 738, a * aparece(t, m(3) - 0.2, 0.6))
        tr = DG.Trazo()
        c = tr.c
        tr.tinta(AN["blanco"], 0.85 * a)
        DG.caja(c, 240, 200, 1440, 560, 28, a, 4)
        c.set_line_width(4)
        c.move_to(960, 200)
        c.line_to(960, 200 + 560 * div)
        c.stroke()
        tr.tinta(AN["verde"], abre * a)
        DG.candado(c, 600, 400, 90, cerrado=0.0)
        tr.tinta(AN["blanco"], aparece(t, m(3), 0.6) * a)
        DG.candado(c, 1320, 420, 90, cerrado=cierra)
        if t > m(5) - 0.2:                                                   # una llave por archivo
            b = aparece(t, m(5) - 0.2, 0.6) * a
            for k in range(6):
                x, y = 1040 + (k % 3) * 200, 520 + (k // 3) * 110
                tr.tinta(AN["blanco"], b)
                DG.archivo(c, x, y, 70, 3)
                tr.tinta(AN["verde"], b)
                DG.llave(c, x + 100, y + 40, 60)
        img = DG.componer_relieve(tr, img, brillo=0.25, col_brillo=AN["verde"], sigma_brillo=14)
        rotulo(img, "Zona 1 · se abre sola al encender", 600, 560, 30, AN["verde"], abre * a, alinear="centro")
        rotulo(img, "alarma · marcador de llamadas", 600, 610, 26, AN["blanco"], aparece(t, m(2), 0.6) * a, alinear="centro",
               nombre="Inter-Regular.ttf")
        rotulo(img, "Zona 2 · todo lo personal", 1320, 300, 30, AN["blanco"], aparece(t, m(3), 0.6) * a, alinear="centro")
        rotulo(img, "cerrada hasta que escribes la contraseña", 1320, 345, 24, mezcla(AN["blanco"], AN["gris"], 0.35),
               aparece(t, m(4), 0.6) * a, alinear="centro", nombre="Inter-Regular.ttf")
        if t > m(6) - 0.4:                                                  # lo que tenía la policía de Friburgo
            b = aparece(t, m(6) - 0.2, 0.6)
            img = panel(img, 420, 330, 1500, 720, b)
            for k, linea in enumerate(("un iPhone", "un sospechoso que no hablaba", "un chip diseñado para impedirlo")):
                rotulo(img, linea, 960, 450 + k * 95, 50, AN["blanco"] if k < 2 else AZ, b * aparece(t, m(6) + 1.2 * k, 0.5),
                       alinear="centro")
        return lento(img, t, m(7), 1.0, 1.04)

    def _titulares(self, t):
        if not self.titulares.existe:
            img = self.fondo.copy()
            rotulo(img, "FBI contra Apple · 2016", 960, 560, 72, AN["blanco"], 1.0, alinear="centro")
            return img
        z, cx, cy = recorrido(t - self.m(7), self.d - self.m(7), 1.0, 1.08, (0.5, 0.3), (0.5, 0.4))
        img = self.titulares.ver(z, cx, cy)
        a = aparece(t, self.m(7) + 0.6, 0.6)
        img = panel(img * (1 - 0.3 * a), 80, H - 270, 900, H - 90, a)
        rotulo(img, "2016", 130, H - 196, 30, GRIS_TXT, a)
        rotulo(img, "FBI contra Apple", 128, H - 134, 56, BL, a)
        return img

    def cuadro(self, t: float) -> np.ndarray:
        partes = (self._zonas, self._titulares)
        img = None
        for k, peso in self.seg.pesos(t):
            capa = partes[k](t)
            img = capa * peso if img is None else img + capa * peso
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(self.m(7), 2101), -14, 1.5, 1.0)
        m.agregar("candado", self.m(4) + 0.4, sfx.candado(2102), -6)
        m.agregar("whoosh", self.m(7) - 0.6, sfx.whoosh(1.1, 2103), -2)
        return m.x[:n]


# =========================================================================== registro

SUBESCENAS = {"2.0": Sub20, "2.1": Sub21, "2.2": Sub22, "2.3": Sub23, "2.4": Sub24, "2.5": Sub25, "2.6": Sub26,
              "2.7": Sub27, "2.8": Sub28, "2.9": Sub29, "2.10": Sub210}

# Fotogramas clave para revisar antes del render completo: (archivo, clip, tiempo en el clip)
REVISION = [
    ("1_mesa_evidencias.png", "2.0", lambda T: T.oraciones[7] + 1.0),
    ("2_laboratorio_copia.png", "2.2", lambda T: T.oraciones[3] + 0.6),
    ("3_contrasena_uid.png", "2.5", lambda T: T.oraciones[4] + 1.8),
    ("4_iphone_no_disponible.png", "2.8", lambda T: T.oraciones[5] + 0.8),
]


def clips() -> list[str]:
    return ["titulo"] + [s.id for s in guion.leer()[NUMERO].subescenas]


def crear(id_: str) -> Subescena:
    if id_ == "titulo":
        return titulo()
    return SUBESCENAS[id_](id_, tiempos(id_))
