"""Escena 7 — Cuando el aparato no quiere hablar.

7.0  Los datos del caso Dabate estaban en servidores fáciles de pedir; en el mundo IoT eso es la
     excepción. La mesa de evidencias del laboratorio (3D): dos teléfonos y, junto a ellos, aparatos
     IoT que no se parecen en nada. Al final, un registro circular que se sobrescribe.
7.1  Tres caminos para sacar los datos: la nube, la app del teléfono, el chip.
7.2  Dos técnicas; JTAG (Joint Test Action Group, 1985). La placa de un aparato en 3D: la cámara llega
     a los puntos de prueba, que se encienden. Un puerto JTAG en una placa real. Diagrama: la máquina
     habla con el procesador y lee o escribe la memoria. Estándar desde 1990.
7.3  Foto real de un perito soldando (NIST). Los cables de cobre soldados a los puntos (3D). La
     memoria completa se copia a un archivo; el aparato no se destruye; el USB no importa.
7.4  Chip-Off: cuándo se usa; foto real del aire caliente; la boquilla y las pinzas que levantan el
     chip (3D); desgastar la placa por debajo (corte); el chip en el programador (3D); destruye el
     aparato y no hay segunda oportunidad.
7.5  El volcado hexadecimal: archivos que aparecen, el mapa de memoria de cada fabricante, el
     rompecabezas, la pausa; y el mapa de Arkansas hasta Bentonville.
7.6  Noviembre de 2015: el patio de los Bates de noche (3D), la casa, James Bates, Victor Collins (su
     foto, quieta y sin efectos), la tina vacía, la bocina Echo (foto real y 3D en la cocina).
7.7  Cómo escucha el Echo; el anillo azul que se enciende (3D); el audio que viaja a la nube de
     Amazon; la orden judicial; el titular; Bates da su permiso.
7.8  El medidor de agua inteligente y sus lecturas; la gráfica con el pico de 140 galones entre la una
     y las tres; el patio vacío (3D); el titular de los cargos retirados.

Paletas: laboratorio (verde de placa, cobre, negro, verde de terminal) de 7.0 a 7.5; Arkansas (rojo,
azul y blanco de su bandera) del final de 7.5 a 7.8. Las víctimas no se modelan ni se tiñen: la foto
de Victor Collins va quieta y el acabado de cine se suaviza mientras está en pantalla.
"""

from __future__ import annotations

import functools
import math
import re

import cairo
import cv2
import numpy as np

import atmosfera as A
import guion
from escenas import graficos_e07 as G
from escenas import sonidos_e07 as S
from escenas.base import SR, Foto, Segmentos, Subescena, TarjetaTitulo, aparece, recorrido, tiempos
from escenas.plano3d import Plano3D
from graficos import H, W, fuente, lim, suave, texto_alfa
from paletas import ARKANSAS, CONNECTICUT, LABORATORIO, mezcla, rgb
from tres_d import datos_e07 as DT

import sfx

NUMERO = 7
LAB, ARK, CT = rgb(LABORATORIO), rgb(ARKANSAS), rgb(CONNECTICUT)
NEGRO = np.zeros(3, np.float32)
BLANCO = np.array([0.94, 0.95, 0.93], np.float32)
GRIS = mezcla(BLANCO, NEGRO, 0.42)
VERDE = LAB["terminal"]
COBRE = LAB["cobre"]
PLACA = LAB["placa"]
AZUL = ARK["azul"]
ROJO = ARK["rojo"]
AZUL_CLARO = mezcla(ARK["azul"], BLANCO, 0.55)
CRUCE = 0.9

# Todos los planos en Eevee: el laboratorio es un primer plano con el fondo desenfocado y el patio de
# los Bates no tiene calle mojada (direccion_visual.md §5; Cycles costaría 20 a 30 veces más).
MOTOR = {"e07_mesa": "eevee", "e07_placa": "eevee", "e07_soldar": "eevee", "e07_aire": "eevee",
         "e07_lector": "eevee", "e07_echo_repisa": "eevee", "e07_echo_anillo": "eevee",
         "e07_patio_llegada": "eevee", "e07_patio_tina": "eevee", "e07_patio_piso": "eevee"}

CINE_LAB = dict(sombras=mezcla(PLACA, NEGRO, 0.55), luces=BLANCO, mezcla=0.12, saturacion=0.95, contraste=0.06,
                halo=0.12, grano=0.012, vineta=0.32)
CINE_ARK = dict(sombras=mezcla(AZUL, NEGRO, 0.35), luces=mezcla(BLANCO, ARK["rojo"], 0.04), mezcla=0.12,
                saturacion=0.92, contraste=0.06, halo=0.12, grano=0.012, vineta=0.34)
# Mientras está la foto de una víctima: sin corrección de color ni halo (solo el grano mínimo)
CINE_NEUTRO = dict(sombras=NEGRO, luces=BLANCO, mezcla=0.0, saturacion=1.0, contraste=0.0, halo=0.0, grano=0.006,
                   vineta=0.18)


# =========================================================================== utilidades


def plano(nombre: str, duracion: float, **params) -> Plano3D:
    return Plano3D(nombre, duracion, motor=MOTOR[nombre], **params)


def fondo_lab() -> np.ndarray:
    return G.fondo(mezcla(LAB["negro"], NEGRO, 0.4), mezcla(PLACA, NEGRO, 0.62), semilla=7)


def fondo_ark() -> np.ndarray:
    return G.fondo(mezcla(AZUL, NEGRO, 0.72), mezcla(AZUL, NEGRO, 0.35), semilla=8)


def instante(sub: Subescena, k: int, palabra: str, fin: float | None = None) -> float:
    """Momento aproximado en que se dice `palabra` en la oración k (por caracteres antes de ella)."""
    oracion = guion.subescena(sub.id).oraciones[k]
    palabras = oracion.split()
    limpio = [re.sub(r"[^\wáéíóúñü]", "", p.lower()) for p in palabras]
    i = next(j for j, p in enumerate(limpio) if p.startswith(palabra))
    antes = len(" ".join(palabras[:i]))
    a = sub.m(k)
    if fin is None:
        fin = sub.m(k + 1) - 0.35 if k + 1 < len(sub.T.oraciones) else sub.T.fin_voz
    return a + (fin - a) * antes / max(1, len(oracion))


def componer(partes, seg: Segmentos, t: float, oscuros=()) -> np.ndarray:
    """Encadena los tramos con fundidos. Si uno de los dos tramos de un cruce está en `oscuros`, el
    fundido pasa por negro (uno se apaga y luego el otro aparece) en vez de encimar las dos imágenes:
    así la foto de una víctima nunca queda sobre otra imagen."""
    pesos = seg.pesos(t)
    if len(pesos) == 2 and any(k in oscuros for k, _ in pesos):
        (k0, _), (k1, x) = pesos
        pesos = [(k, p) for k, p in ((k0, suave(1 - 2 * x)), (k1, suave(2 * x - 1))) if p > 0] or [(k1, 0.0)]
    img = None
    for k, peso in pesos:
        capa = partes[k](t)
        img = capa * peso if img is None else img + capa * peso
    return img


def en_foto(foto: Foto, zoom: float, cx: float, cy: float, px: float, py: float) -> tuple[float, float]:
    """Dónde cae en pantalla el punto (px, py) (fracciones de la foto) con `Foto.ver(zoom, cx, cy)`."""
    cubre = max(W / foto.w, H / foto.h) * zoom
    bw, bh = W / cubre, H / cubre
    x0 = min(max(cx * foto.w - bw / 2, 0), foto.w - bw)
    y0 = min(max(cy * foto.h - bh / 2, 0), foto.h - bh)
    return (px * foto.w - x0) * cubre, (py * foto.h - y0) * cubre


def anillo_foco(img, x, y, r, col, a):
    """Círculo fino que señala algo en una foto, con un poco de brillo."""
    if a <= 0:
        return
    lz = G.Lienzo()
    lz.tinta(col, 0.9 * a)
    lz.c.set_line_width(3)
    lz.c.arc(x, y, r * (1.08 - 0.08 * suave(a)), 0, math.tau)
    lz.c.stroke()
    lz.componer(img, sombra=0.4, brillo=0.5, col_brillo=col, sigma_brillo=10)


def pie_de_foto(img, cadena, a, col=BLANCO, x=120, y=H - 120, sub=None):
    G.rotulo(img, cadena, x, y, 36, col, a)
    if sub:
        G.rotulo(img, sub, x, y + 44, 26, mezcla(col, NEGRO, 0.35), a, nombre="Inter-Regular.ttf")


class Plano:
    """Un plano 3D dentro de una subescena: dónde empieza, su clip y cómo se proyectan sus puntos."""

    def __init__(self, nombre, ini, fin, camara=None, **params):
        self.ini = ini
        self.clip = plano(nombre, fin - ini + 0.25, **params)
        self.camara = camara                       # t_plano -> (pos, mira, lente)

    def cuadro(self, t):
        return self.clip.cuadro(max(0.0, t - self.ini))

    def punto(self, t, p):
        if self.camara is None:
            return None
        pos, mira, lente = self.camara(max(0.0, t - self.ini))
        return DT.proyectar(p, pos, mira, lente)


# =========================================================================== título


def titulo() -> TarjetaTitulo:
    t = TarjetaTitulo(NUMERO, guion.leer()[NUMERO].titulo, COBRE, BLANCO)
    t.cine = CINE_LAB
    return t


# =========================================================================== 7.0


class Sub70(Subescena):
    """Servidores fáciles de pedir (caso Dabate); la mesa de evidencias IoT (3D); poca memoria."""

    cine = CINE_LAB

    def preparar(self) -> None:
        o = self.T.oraciones
        self.fondo_dabate = G.fondo(mezcla(CT["azul"], NEGRO, 0.86), mezcla(CT["azul"], NEGRO, 0.6), semilla=5)
        self.t_pedir = instante(self, 0, "pedir")
        self.t_correo = instante(self, 0, "correo")
        self.t_facebook = instante(self, 0, "facebook")
        self.t_fitbit = instante(self, 0, "fitbit")
        ini, fin = o[1] - CRUCE / 2, o[6] + CRUCE / 2
        rel = lambda x: float(round(x - ini, 2))                               # noqa: E731
        self.t_camara, self.t_reloj, self.t_sensor = instante(self, 5, "cámara"), instante(self, 5, "reloj"), instante(self, 5, "sensor")
        marcas = {"telefonos": rel(o[2]), "iot": rel(o[3]), "camara": rel(self.t_camara), "reloj": rel(self.t_reloj),
                  "sensor": rel(self.t_sensor), "fin": rel(fin)}
        self.mesa = Plano("e07_mesa", ini, fin, lambda t: DT.cam_mesa(t, marcas), marcas=marcas)
        self.planos3d = [self.mesa.clip]
        self.seg = Segmentos([o[1], o[6]], CRUCE)
        self.t_sistema = instante(self, 4, "sistema")
        self.t_formato = instante(self, 4, "formato")
        self.t_guardar = instante(self, 4, "guardar")
        self._congelado = None

    # ---- caso Dabate: servidores fáciles de pedir
    def _dabate(self, t: float) -> np.ndarray:
        img = self.fondo_dabate.copy()
        beige = CT["beige"]
        G.antetitulo(img, "Caso Dabate", 140, 170, mezcla(beige, NEGRO, 0.2), aparece(t, 0.3, 0.8))
        G.rotulo(img, "Los datos estaban en servidores", 138, 228, 44, BLANCO, aparece(t, 0.6, 0.8))
        from escenas import diagramas as DG
        lz = G.Lienzo()
        c = lz.c
        a_doc = aparece(t, self.t_pedir - 0.6, 0.6)
        lz.tinta(beige, a_doc)
        G.orden_judicial(c, 300, 500, 190)
        origen = (470, 600)
        # los tres servidores en columna a la derecha; la orden llega y los datos vuelven por el mismo camino
        servidores = ((self.t_correo, "Correo", 360), (self.t_facebook, "Facebook", 610), (self.t_fitbit, "Fitbit", 860))
        for k, (tk, nombre, y) in enumerate(servidores):
            a = aparece(t, tk - 0.2, 0.5)
            if a <= 0:
                continue
            x = 1180
            lz.tinta(mezcla(CT["azul"], NEGRO, 0.35), a * 0.85)
            G.D.rect_redondeado(c, x - 110, y - 100, 220, 200, 22)
            c.fill()
            lz.tinta(BLANCO, a)
            G.servidor(c, x, y, 90, 140)
            destino = (x - 125, y)
            curva = (y - origen[1]) * -0.18
            lz.tinta(beige, a * a_doc * 0.8)
            DG.flecha(c, origen, destino, lim((t - tk) / 0.7), 3, 16, curva=curva)
            if t > tk + 0.7:
                n_ = np.array([-(destino[1] - origen[1]), destino[0] - origen[0]], float)
                n_ /= np.linalg.norm(n_)
                medio = (np.array(origen) + np.array(destino)) / 2 + n_ * curva
                for j in range(3):
                    f = ((t - tk) * 0.6 + j / 3) % 1.0
                    u = 1 - f                                        # de regreso: del servidor a la orden
                    q = (1 - u) ** 2 * np.array(origen) + 2 * (1 - u) * u * medio + u * u * np.array(destino)
                    lz.tinta(CT["azul_patrulla"], a * 0.95 * math.sin(f * math.pi))
                    c.rectangle(q[0] - 7, q[1] - 7, 14, 14)
                    c.fill()
        img = lz.componer(img, sombra=0.6, brillo=0.3, col_brillo=CT["azul_patrulla"], sigma_brillo=16)
        G.rotulo(img, "orden judicial", 372, 745, 30, beige, a_doc, alinear="centro", nombre="Inter-Regular.ttf")
        for tk, nombre, y in servidores:
            G.rotulo(img, nombre, 1330, y + 14, 46, BLANCO, aparece(t, tk, 0.5))
        G.rotulo(img, "fáciles de pedir", 1332, 990, 32, beige, aparece(t, self.t_fitbit + 0.6, 0.6), nombre="Inter-Regular.ttf")
        return img

    # ---- la mesa de evidencias (3D)
    def _mesa(self, t: float) -> np.ndarray:
        img = self.mesa.cuadro(t)
        o = self.T.oraciones
        A_ = DT.APARATOS
        # teléfonos: dos sistemas
        a_tel = aparece(t, o[2] + 0.6, 0.8, o[3] - 0.2)
        if a_tel > 0:
            for nombre, rot, lado in (("iphone", "iOS", "izq"), ("android", "Android", "der")):
                x, y, _ = A_[nombre]
                G.rotulo_en(img, self.mesa.punto(t, (x, y + 0.03, DT.ALTO_APARATO[nombre])), rot, BLANCO, VERDE, a_tel,
                            lado=lado, alto=120, largo=60, tam=40)
            G.panel(img, 100, 820, 760, 980, a_tel)
            G.rotulo(img, "Teléfonos: dos sistemas", 140, 880, 42, BLANCO, a_tel)
            G.rotulo(img, "las herramientas forenses los conocen", 140, 935, 30, mezcla(BLANCO, NEGRO, 0.25), a_tel,
                     nombre="Inter-Regular.ttf")
        # cada fabricante, a su manera
        for tk, cadena, nombre, lado in ((self.t_sistema, "su propio sistema", "camara", "der"),
                                         (self.t_formato, "su propio formato", "reloj", "der"),
                                         (self.t_guardar, "su forma de guardar", "bocina", "der")):
            a = aparece(t, tk - 0.1, 0.7, o[5] - 0.3)
            x, y, _ = A_[nombre]
            G.rotulo_en(img, self.mesa.punto(t, (x, y, DT.ALTO_APARATO[nombre])), cadena, BLANCO, COBRE, a, lado=lado,
                        alto=110, largo=50, tam=34)
        # tres aparatos que no se parecen en nada
        for tk, cadena, nombre in ((self.t_camara, "cámara barata", "camara"), (self.t_reloj, "reloj inteligente", "reloj"),
                                   (self.t_sensor, "sensor de una fábrica", "sensor")):
            a = aparece(t, tk + 0.25, 0.7, tk + 3.4)
            x, y, _ = A_[nombre]
            G.rotulo_en(img, self.mesa.punto(t, (x, y, DT.ALTO_APARATO[nombre])), cadena, BLANCO, VERDE, a, lado="der",
                        alto=130, largo=60, tam=40)
        return img

    # ---- poca memoria: un registro circular que se sobrescribe
    def _registro(self, t: float) -> np.ndarray:
        if self._congelado is None:
            ultimo = self.mesa.cuadro(self.T.oraciones[6] + CRUCE / 2)
            self._congelado = G.desenfocar(ultimo, 22, 0.55)
        img = self._congelado.copy()
        t0 = self.T.oraciones[6]
        cx, cy, r = 1180, 560, 250
        n = 16
        vel = 16 / 3.2                                                  # ranuras por segundo
        escritas = max(0.0, (t - t0 - 0.8) * vel)
        lz = G.Lienzo()
        c = lz.c
        a = aparece(t, t0 + 0.1, 0.6)
        for k in range(n):
            a0 = -math.pi / 2 + k * math.tau / n + 0.05
            a1 = a0 + math.tau / n - 0.10
            lleno = escritas > k
            edad = ((escritas - k) % n) if lleno else n          # cuántas ranuras se escribieron después
            vuelta = math.floor((escritas - k) / n) if lleno else -1
            recien = lleno and edad < 1.0
            if recien and vuelta >= 1:                            # este dato acaba de borrar a uno viejo
                col, fuerza = COBRE, 1.0
            elif lleno:
                col, fuerza = VERDE, 0.25 + 0.75 * (1 - edad / n)
            else:
                col, fuerza = mezcla(BLANCO, NEGRO, 0.7), 0.35
            lz.tinta(col, a * fuerza)
            c.set_line_width(46)
            c.set_line_cap(cairo.LINE_CAP_BUTT)                 # ranuras de bordes rectos
            c.new_sub_path()
            c.arc(cx, cy, r, a0, a1)
            c.stroke()
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        # la aguja de escritura
        ang = -math.pi / 2 + (escritas % n) * math.tau / n
        lz.tinta(BLANCO, a)
        c.set_line_width(4)
        c.move_to(cx + math.cos(ang) * (r - 60), cy + math.sin(ang) * (r - 60))
        c.line_to(cx + math.cos(ang) * (r + 60), cy + math.sin(ang) * (r + 60))
        c.stroke()
        img = lz.componer(img, sombra=0.5, brillo=0.35, col_brillo=VERDE, sigma_brillo=14)
        G.rotulo(img, "registro", cx, cy - 6, 48, BLANCO, a, alinear="centro")
        G.rotulo(img, "memoria pequeña", cx, cy + 46, 30, mezcla(BLANCO, NEGRO, 0.3), a, alinear="centro", nombre="Inter-Regular.ttf")
        a2 = aparece(t, t0 + 2.2, 0.7)
        G.antetitulo(img, "IoT", 140, 420, VERDE, a)
        G.rotulo(img, "Poca memoria", 138, 480, 56, BLANCO, a)
        G.rotulo(img, "lo nuevo borra lo viejo", 140, 545, 36, COBRE, a2, nombre="Inter-Regular.ttf")
        G.rotulo(img, "cada pocas horas", 140, 595, 36, mezcla(BLANCO, NEGRO, 0.25), a2, nombre="Inter-Regular.ttf")
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return componer((self._dabate, self._mesa, self._registro), self.seg, t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        o = self.T.oraciones
        m.agregar("datos", self.t_correo, sfx.datos(o[1] - self.t_correo, 701, 14.0), -10, 0.3, 0.8)
        m.agregar("laboratorio", o[1] - 0.6, S.zumbido_lab(d - o[1] + 0.6, 702), 0, 1.2, 1.5)
        for k, tk in enumerate((self.t_camara, self.t_reloj, self.t_sensor)):
            m.agregar(f"aparato{k}", tk + 0.25, sfx.clic_contador(703 + k), -14)
        m.agregar("registro", o[6] + 0.8, sfx.clics([o[6] + 0.8 + k / 5.0 for k in range(int((d - o[6] - 1.4) * 5))], d, 706)[_n(o[6] + 0.8):], -12)
        return m.x[:n]


def _n(seg: float) -> int:
    return int(round(seg * SR))


# =========================================================================== 7.1


class Sub71(Subescena):
    """Tres caminos para sacar los datos de un aparato IoT: la nube, la app, el chip."""

    cine = CINE_LAB

    def preparar(self) -> None:
        self.fondo = fondo_lab()

    def cuadro(self, t: float) -> np.ndarray:
        from escenas import diagramas as DG
        img = self.fondo.copy()
        o = self.T.oraciones
        origen = (470, 560)
        caminos = (
            (o[1], (1180, 290), "La nube del fabricante", "con una orden judicial", "nube"),
            (o[2], (1180, 560), "La app del teléfono", "guarda una copia", "app"),
            (o[3], (1180, 830), "El chip", "directo a la memoria", "chip"),
        )
        final = suave(lim((t - o[3] - 0.6) / 0.8))
        lz = G.Lienzo()
        c = lz.c
        a0 = aparece(t, 0.2, 0.7)
        lz.tinta(mezcla(PLACA, NEGRO, 0.35), a0 * 0.9)
        G.D.rect_redondeado(c, origen[0] - 150, origen[1] - 150, 300, 300, 30)
        c.fill()
        lz.tinta(BLANCO, a0)
        G.camarita(c, origen[0], origen[1] - 10, 170, 4)
        for k, (tk, (x, y), _, _, icono) in enumerate(caminos):
            a = aparece(t, tk - 0.1, 0.5)
            if a <= 0:
                continue
            tenue = 1 - 0.65 * final if icono != "chip" else 1.0
            col = COBRE if icono == "chip" else VERDE
            lz.tinta(col, a * tenue)
            DG.flecha(c, (origen[0] + 165, origen[1] + (y - origen[1]) * 0.25), (x - 170, y), lim((t - tk) / 0.8), 5, 22,
                      curva=(y - origen[1]) * -0.25)
            lz.tinta(mezcla(PLACA, NEGRO, 0.3), a * 0.9 * tenue)
            G.D.rect_redondeado(c, x - 140, y - 105, 280, 210, 26)
            c.fill()
            lz.tinta(BLANCO, a * tenue)
            if icono == "nube":
                G.nube_contorno(c, x, y - 4, 180, BLANCO, mezcla(PLACA, NEGRO, 0.3), a * tenue, 4)
            elif icono == "app":
                DG.telefono(c, x, y, 150, 4)
                for j in range(3):
                    c.rectangle(x - 22, y - 40 + j * 28, 44, 16)
                c.fill()
            else:
                DG.chip(c, x, y, 120, 4, 6)
            lz.tinta(col, a * tenue)
            c.arc(x - 170, y - 105, 26, 0, math.tau)
            c.fill()
        img = lz.componer(img, sombra=0.6, brillo=0.3 + 0.4 * final, col_brillo=COBRE if final > 0 else VERDE, sigma_brillo=14)
        for k, (tk, (x, y), nombre, detalle, icono) in enumerate(caminos):
            a = aparece(t, tk + 0.2, 0.6) * ((1 - 0.65 * final) if icono != "chip" else 1.0)
            G.rotulo(img, str(k + 1), x - 170, y - 93, 32, NEGRO, a, alinear="centro", sombra=0)
            G.rotulo(img, nombre, x + 175, y - 8, 46, BLANCO, a)
            G.rotulo(img, detalle, x + 177, y + 42, 30, mezcla(BLANCO, NEGRO, 0.3), a, nombre="Inter-Regular.ttf")
        G.rotulo(img, "aparato IoT", origen[0], origen[1] + 200, 32, mezcla(BLANCO, NEGRO, 0.25), a0, alinear="centro",
                 nombre="Inter-Regular.ttf")
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        o = self.T.oraciones
        m.agregar("laboratorio", 0, S.zumbido_lab(d, 711), -6, 1.0, 1.0)
        for k in range(3):
            m.agregar(f"camino{k}", o[k + 1] - 0.1, sfx.whoosh(0.8, 712 + k, 200 + 60 * k, 2600), -2)
        return m.x[:n]


# =========================================================================== 7.2


class Sub72(Subescena):
    """Dos técnicas; JTAG; la placa con sus puntos de prueba (3D); la foto real; el diagrama."""

    cine = CINE_LAB

    def preparar(self) -> None:
        o = self.T.oraciones
        self.fondo = fondo_lab()
        self.ini3d = o[2] - CRUCE / 2
        self.t_foto = o[3] + 2.4
        fin3d = self.t_foto + CRUCE / 2
        marcas = {"puertos": float(round(o[3] + 0.3 - self.ini3d, 2))}
        self.placa = Plano("e07_placa", self.ini3d, fin3d, lambda t: DT.cam_placa(t, fin3d - self.ini3d, marcas), marcas=marcas)
        self.planos3d = [self.placa.clip]
        self.t_diagrama = o[4] + 0.6
        self.seg = Segmentos([o[2], self.t_foto, self.t_diagrama], CRUCE)
        self.foto = Foto("7.2_puertos_jtag.jpg", tinte=PLACA, fuerza=0.06)

    def _tecnicas(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        o = self.T.oraciones
        abre = suave(lim((t - o[1] + 0.1) / 1.0))                 # JTAG pasa al centro
        lz = G.Lienzo()
        c = lz.c
        a0 = aparece(t, 0.15, 0.6)
        cajas = ((560 + (960 - 560) * abre, 420 - 60 * abre, "JTAG", VERDE, 1.0),
                 (1360 + 400 * abre, 420, "Chip-Off", COBRE, 1 - abre))
        for x, y, nombre, col, a in cajas:
            if a * a0 <= 0.01:
                continue
            lz.tinta(mezcla(PLACA, NEGRO, 0.35), 0.9 * a * a0)
            G.D.rect_redondeado(c, x - 230, y - 110, 460, 220, 28)
            c.fill()
            lz.tinta(col, a * a0)
            c.set_line_width(3)
            G.D.rect_redondeado(c, x - 230, y - 110, 460, 220, 28)
            c.stroke()
        img = lz.componer(img, sombra=0.6, brillo=0.25, col_brillo=VERDE)
        for x, y, nombre, col, a in cajas:
            G.rotulo(img, nombre, x, y + 30, 92, BLANCO, a * a0, alinear="centro", nombre="Inter-SemiBold.ttf")
        G.antetitulo(img, "El tercer camino: el chip", 960, 210, COBRE, a0 * (1 - abre), alinear="centro")
        # Joint Test Action Group: cada palabra con su inicial resaltada
        palabras = ("Joint", "Test", "Action", "Group")
        tam = 64
        ancho_total = sum(fuente("Inter-SemiBold.ttf", tam).getlength(p) for p in palabras) + 34 * 3
        x = 960 - ancho_total / 2
        t_grupo = instante(self, 1, "joint")
        for k, p in enumerate(palabras):
            a = aparece(t, t_grupo + 0.18 * k, 0.5)
            G.rotulo(img, p[0], x, 650, tam, VERDE, a)
            G.rotulo(img, p[1:], x + fuente("Inter-SemiBold.ttf", tam).getlength(p[0]), 650, tam, BLANCO, a)
            x += fuente("Inter-SemiBold.ttf", tam).getlength(p) + 34
        a85 = aparece(t, instante(self, 1, "1985") - 0.1, 0.6)
        G.rotulo(img, "1985", 960, 780, 120, COBRE, a85, alinear="centro", nombre="Inter-Light.ttf")
        G.rotulo(img, "un grupo de ingenieros", 960, 545, 34, mezcla(BLANCO, NEGRO, 0.25), aparece(t, instante(self, 1, "grupo"), 0.6),
                 alinear="centro", nombre="Inter-Regular.ttf")
        return img

    def _placa(self, t: float) -> np.ndarray:
        img = self.placa.cuadro(t)
        o = self.T.oraciones
        a_q = aparece(t, o[2] + 0.8, 0.8, o[3] - 0.2)
        G.panel(img, 100, 830, 900, 990, a_q)
        G.antetitulo(img, "En la fábrica", 140, 885, COBRE, a_q)
        G.rotulo(img, "¿funciona cada soldadura, cada chip?", 140, 945, 40, BLANCO, a_q)
        a = aparece(t, o[3] + 1.0, 0.8)
        x, y = DT.JTAG[2]
        G.rotulo_en(img, self.placa.punto(t, DT.en_placa(x, y)), "puertos de prueba", BLANCO, VERDE, a, lado="der",
                    alto=150, largo=80, tam=44)
        return img

    def _foto(self, t: float) -> np.ndarray:
        u = t - self.t_foto + CRUCE / 2
        z, cx, cy = recorrido(u, self.t_diagrama - self.t_foto + CRUCE, 1.25, 1.75, (0.32, 0.78), (0.24, 0.86))
        img = self.foto.ver(z, cx, cy) if self.foto.existe else self.fondo.copy()
        if self.foto.existe:
            x, y = en_foto(self.foto, z, cx, cy, 0.215, 0.925)
            anillo_foco(img, x, y, 120 * z / 1.5, VERDE, aparece(t, self.t_foto + 0.6, 0.6))
            G.panel(img, 0, 0, 900, 190, aparece(t, self.t_foto, 0.6), 0.5)
            pie_de_foto(img, "Un puerto JTAG en una placa real", aparece(t, self.t_foto + 0.2, 0.6), y=95,
                        sub="router con su conector de prueba")
        return img

    def _diagrama(self, t: float) -> np.ndarray:
        from escenas import diagramas as DG
        img = self.fondo.copy()
        o = self.T.oraciones
        t0 = self.t_diagrama - CRUCE / 2
        lz = G.Lienzo()
        c = lz.c
        a_pc = aparece(t, t0, 0.6)
        lz.tinta(BLANCO, a_pc)
        DG.computadora(c, 300, 500, 200, 4, lim((t - t0) / 0.8))
        # interfaz JTAG
        a_if = aparece(t, t0 + 0.6, 0.6)
        lz.tinta(mezcla(PLACA, NEGRO, 0.3), a_if)
        G.D.rect_redondeado(c, 560, 470, 170, 90, 14)
        c.fill()
        lz.tinta(VERDE, a_if)
        c.set_line_width(3)
        G.D.rect_redondeado(c, 560, 470, 170, 90, 14)
        c.stroke()
        lz.tinta(BLANCO, a_if * 0.8)
        DG.linea(c, [(470, 515), (560, 515)], lim((t - t0 - 0.6) / 0.5), 4)
        # cuatro señales hacia el procesador
        a_l = lim((t - t0 - 1.0) / 1.0)
        for k, nombre in enumerate(DT.SENALES[:4]):
            y = 455 + k * 40
            lz.tinta(VERDE, 0.9 * a_l)
            DG.linea(c, [(730, 515), (800, 515), (840, y), (1010, y)], a_l, 3)
        # procesador y memoria
        a_cpu = aparece(t, t0 + 0.9, 0.6)
        lz.tinta(mezcla(PLACA, NEGRO, 0.2), a_cpu)
        G.D.rect_redondeado(c, 1010, 400, 220, 230, 18)
        c.fill()
        lz.tinta(BLANCO, a_cpu)
        DG.chip(c, 1120, 515, 200, 3, 8, lim((t - t0 - 0.9) / 0.8))
        a_mem = aparece(t, t0 + 1.8, 0.6)
        lz.tinta(mezcla(PLACA, NEGRO, 0.2), a_mem)
        G.D.rect_redondeado(c, 1420, 380, 300, 270, 18)
        c.fill()
        lz.tinta(BLANCO, a_mem)
        c.set_line_width(3)
        G.D.rect_redondeado(c, 1420, 380, 300, 270, 18)
        c.stroke()
        for i in range(6):
            for j in range(8):
                c.rectangle(1450 + j * 33, 410 + i * 37, 24, 26)
        c.stroke()
        # leer y escribir: pulsos que van y vienen
        t_rw = instante(self, 4, "lea")
        a_rw = aparece(t, t_rw, 0.5)
        lz.tinta(VERDE, a_rw)
        DG.flecha(c, (1240, 480), (1410, 480), lim((t - t_rw) / 0.6), 4, 18)
        lz.tinta(COBRE, a_rw)
        DG.flecha(c, (1410, 560), (1240, 560), lim((t - t_rw - 0.5) / 0.6), 4, 18)
        celda = int(max(0.0, t - t_rw) * 9) % 48
        if a_rw > 0:
            lz.tinta(VERDE, 0.9 * a_rw)
            c.rectangle(1450 + (celda % 8) * 33, 410 + (celda // 8) * 37, 24, 26)
            c.fill()
        img = lz.componer(img, sombra=0.6, brillo=0.3, col_brillo=VERDE, sigma_brillo=12)
        G.rotulo(img, "computadora del perito", 300, 690, 30, mezcla(BLANCO, NEGRO, 0.25), a_pc, alinear="centro", nombre="Inter-Regular.ttf")
        G.rotulo(img, "interfaz JTAG", 645, 600, 28, VERDE, a_if, alinear="centro")
        for k, nombre in enumerate(DT.SENALES[:4]):
            G.rotulo(img, nombre, 925, 452 + k * 40, 22, mezcla(BLANCO, NEGRO, 0.2), a_l, alinear="centro", sombra=0.2)
        G.rotulo(img, "procesador", 1120, 680, 34, BLANCO, a_cpu, alinear="centro")
        G.rotulo(img, "memoria", 1570, 700, 34, BLANCO, a_mem, alinear="centro")
        G.rotulo(img, "leer", 1325, 462, 28, VERDE, a_rw, alinear="centro")
        G.rotulo(img, "escribir", 1325, 605, 28, COBRE, a_rw, alinear="centro")
        a90 = aparece(t, o[5], 0.6)
        G.panel(img, 560, 800, 1360, 960, a90)
        G.rotulo(img, "Estándar internacional desde 1990", 960, 868, 44, BLANCO, a90, alinear="centro")
        G.rotulo(img, "IEEE 1149.1", 960, 925, 30, VERDE, a90, alinear="centro", nombre="Inter-Regular.ttf")
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return componer((self._tecnicas, self._placa, self._foto, self._diagrama), self.seg, t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        o = self.T.oraciones
        m.agregar("laboratorio", 0, S.zumbido_lab(d, 721), -4, 1.0, 1.0)
        for k in range(5):
            m.agregar(f"chispa{k}", o[3] + 0.3 + 0.35 * k, S.chispa(722 + k), -6 - k)
        m.agregar("datos", instante(self, 4, "lea"), sfx.datos(o[5] - instante(self, 4, "lea"), 728, 12.0), -10, 0.3, 0.8)
        return m.x[:n]


# =========================================================================== 7.3


class Sub73(Subescena):
    """Foto real (NIST); la soldadura de los cables (3D); el volcado a un archivo; el USB no importa."""

    cine = CINE_LAB

    def preparar(self) -> None:
        o = self.T.oraciones
        self.fondo = fondo_lab()
        self.foto = Foto("7.3_soldadura_jtag.jpg", tinte=PLACA, fuerza=0.05)
        self.t_3d = o[1] + 1.0
        self.t_diag = o[3] - 0.2
        self.t_toque = instante(self, 2, "suelda") + 0.3
        ini, fin = self.t_3d - CRUCE / 2, self.t_diag + CRUCE / 2
        dur = fin - ini + 0.25
        t_toque = float(round(self.t_toque - ini, 2))
        self.soldar = Plano("e07_soldar", ini, fin, lambda t: DT.cam_soldar(t, math.ceil(dur * 2) / 2), t_toque=t_toque)
        self.planos3d = [self.soldar.clip]
        self.seg = Segmentos([self.t_3d, self.t_diag], CRUCE)
        self.humo = A.Humo(731)

    def _foto(self, t: float) -> np.ndarray:
        z, cx, cy = recorrido(t, self.t_3d + 1.0, 1.02, 1.12, (0.45, 0.45), (0.5, 0.5))
        img = self.foto.ver(z, cx, cy) if self.foto.existe else self.fondo.copy()
        a = aparece(t, 0.5, 0.7)
        G.panel(img, 0, H - 200, 980, H, a, 0.5)
        pie_de_foto(img, "Un perito suelda cables a una placa", a, y=H - 120, sub="laboratorio del NIST, Estados Unidos")
        return img

    def _soldar(self, t: float) -> np.ndarray:
        img = self.soldar.cuadro(t)
        o = self.T.oraciones
        # sin etiquetas: los puntos están ahí, pero nada dice qué son
        a = aparece(t, self.t_3d + 0.3, 0.7, o[2] - 0.2)
        x, y = DT.JTAG[0]
        G.rotulo_en(img, self.soldar.punto(t, DT.en_placa(x, y)), "sin ninguna etiqueta", BLANCO, COBRE, a, lado="der",
                    alto=140, largo=60, tam=40)
        # humo del fundente mientras la punta toca la pastilla
        x, y = DT.JTAG[3]
        p = self.soldar.punto(t, DT.en_placa(x, y, DT.GROSOR + 1.5))
        humo = suave(lim((t - self.t_toque + 0.1) / 0.4)) * (1 - suave(lim((t - self.t_toque - 2.4) / 1.2)))
        if p is not None and humo > 0:
            alfa = self.humo.alfa(t, [(p[0], p[1], 34.0, 420.0)], vel=60.0, viento=26.0, densidad=0.5 * humo)
            img = img * (1 - alfa[..., None] * 0.6) + alfa[..., None] * np.array([0.72, 0.74, 0.76], np.float32) * 0.6
        a2 = aparece(t, instante(self, 2, "interfaz") - 0.2, 0.7)
        G.panel(img, 100, 860, 760, 990, a2)
        G.rotulo(img, "cables muy delgados", 140, 915, 40, BLANCO, a2)
        G.rotulo(img, "hacia la interfaz JTAG", 140, 962, 30, COBRE, a2, nombre="Inter-Regular.ttf")
        return img

    def _volcado(self, t: float) -> np.ndarray:
        from escenas import diagramas as DG
        img = self.fondo.copy()
        o = self.T.oraciones
        t0 = self.t_diag - CRUCE / 2
        lz = G.Lienzo()
        c = lz.c
        # el aparato (placa con su procesador y memoria) y la conexión directa
        a = aparece(t, t0, 0.6)
        lz.tinta(mezcla(PLACA, NEGRO, 0.55), a)
        G.D.rect_redondeado(c, 180, 330, 560, 420, 26)
        c.fill()
        lz.tinta(PLACA, a)
        c.set_line_width(3)
        G.D.rect_redondeado(c, 180, 330, 560, 420, 26)
        c.stroke()
        lz.tinta(BLANCO, a)
        DG.chip(c, 360, 540, 150, 3, 6)
        c.set_line_width(3)
        G.D.rect_redondeado(c, 520, 470, 150, 140, 12)
        c.stroke()
        for i in range(4):
            c.move_to(540, 500 + i * 28)
            c.line_to(650, 500 + i * 28)
        c.stroke()
        # puerto USB en el canto del aparato
        lz.tinta(BLANCO, a * 0.9)
        G.D.rect_redondeado(c, 150, 640, 60, 34, 8)
        c.stroke()
        # pista directa del procesador a la interfaz
        lz.tinta(VERDE, a)
        DG.linea(c, [(435, 480), (560, 400), (840, 400)], lim((t - t0 - 0.3) / 0.8), 5)
        # el archivo que se llena
        t_copia = o[3] + 0.4
        progreso = lim((t - t_copia) / max(1.0, o[4] - t_copia - 0.4))
        a_f = aparece(t, t_copia - 0.3, 0.5)
        lz.tinta(mezcla(PLACA, NEGRO, 0.6), a_f)
        G.D.rect_redondeado(c, 1270, 300, 430, 470, 24)
        c.fill()
        lz.tinta(BLANCO, a_f)
        DG.archivo(c, 1410, 360, 200, 4)
        lz.tinta(VERDE, a_f)
        c.rectangle(1330, 640, 310 * progreso, 16)
        c.fill()
        lz.tinta(BLANCO, a_f * 0.4)
        c.set_line_width(2)
        c.rectangle(1330, 640, 310, 16)
        c.stroke()
        # bytes en camino
        if t > t_copia:
            for j in range(10):
                f = ((t - t_copia) * 0.9 + j / 10) % 1.0
                px = 860 + (1260 - 860) * f
                lz.tinta(VERDE, 0.9 * math.sin(f * math.pi) * (progreso < 1))
                c.rectangle(px - 9, 393 + 8 * math.sin(j * 1.7), 18, 14)
                c.fill()
        # el USB bloqueado o dañado
        t_usb = instante(self, 5, "usb") - 0.2
        a_usb = aparece(t, t_usb, 0.5)
        lz.tinta(ROJO, a_usb)
        G.tacha(c, 180, 657, 70, lim((t - t_usb) / 0.6), 7)
        img = lz.componer(img, sombra=0.6, brillo=0.3, col_brillo=VERDE, sigma_brillo=12)
        G.rotulo(img, "procesador", 360, 655, 26, mezcla(BLANCO, NEGRO, 0.25), a, alinear="centro", nombre="Inter-Regular.ttf")
        G.rotulo(img, "memoria", 595, 655, 26, mezcla(BLANCO, NEGRO, 0.25), a, alinear="centro", nombre="Inter-Regular.ttf")
        G.rotulo(img, "JTAG: directo al procesador", 690, 380, 30, VERDE, aparece(t, t0 + 0.8, 0.6), alinear="centro")
        G.rotulo(img, "volcado.bin", 1485, 610, 36, BLANCO, a_f, alinear="centro")
        bytes_ = int(progreso * 8_589_934_592)
        G.rotulo(img, f"{bytes_:,} bytes".replace(",", " "), 1485, 715, 28, VERDE, a_f, alinear="centro", nombre="Inter-Regular.ttf")
        G.rotulo(img, "byte por byte", 1485, 270, 30, mezcla(BLANCO, NEGRO, 0.25), a_f, alinear="centro", nombre="Inter-Regular.ttf")
        G.rotulo(img, "ejemplo: una memoria de 8 GB", 1485, 760, 26, mezcla(BLANCO, NEGRO, 0.3), a_f, alinear="centro",
                 nombre="Inter-Regular.ttf")
        a_ok = aparece(t, o[4], 0.6)
        lz2 = G.Lienzo()
        lz2.tinta(VERDE, a_ok)
        G.palomita(lz2.c, 230, 880, 60, lim((t - o[4]) / 0.5), 7)
        img = lz2.componer(img, sombra=0.4, brillo=0.5, col_brillo=VERDE)
        G.rotulo(img, "El aparato no se destruye", 290, 898, 44, BLANCO, a_ok)
        G.rotulo(img, "USB bloqueado o dañado: no importa", 180, 760, 30, mezcla(ROJO, BLANCO, 0.45), a_usb, nombre="Inter-Regular.ttf")
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return componer((self._foto, self._soldar, self._volcado), self.seg, t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        o = self.T.oraciones
        m.agregar("laboratorio", 0, S.zumbido_lab(d, 731), -4, 1.0, 1.0)
        m.agregar("cautín", self.t_toque, S.cautin(2.6, 732), 0)
        m.agregar("datos", o[3] + 0.4, sfx.datos(o[4] - o[3], 733, 20.0), -8, 0.2, 0.6)
        return m.x[:n]


# =========================================================================== 7.4


class Sub74(Subescena):
    """Chip-Off: cuándo se usa; la foto real; aire caliente y pinzas (3D); desgastar por debajo; el
    programador (3D); destruye el aparato; no hay segunda oportunidad."""

    cine = CINE_LAB

    def preparar(self) -> None:
        o = self.T.oraciones
        self.fondo = fondo_lab()
        self.foto = Foto("7.4_chip_off.jpg", tinte=PLACA, fuerza=0.05)
        self.t_foto = o[2] - 0.3
        self.t_aire = o[3] - 0.2
        self.t_corte = o[4] + 0.7                       # el chip ya subió con las pinzas antes de cortar
        self.t_lector = o[5] - 0.1
        self.t_fin = o[6] - 0.1
        t_pinzas = instante(self, 3, "pinzas")
        ini, fin = self.t_aire - CRUCE / 2, self.t_corte + CRUCE / 2
        dur_a = math.ceil((fin - ini + 0.25) * 2) / 2
        self.aire = Plano("e07_aire", ini, fin, lambda t: DT.cam_aire(t, dur_a),
                          t_pinzas=float(round(t_pinzas - 1.3 - ini, 2)), t_levanta=float(round(t_pinzas - 0.2 - ini, 2)))
        self.t_levanta = t_pinzas - 0.2
        ini2, fin2 = self.t_lector - CRUCE / 2, self.t_fin + CRUCE / 2
        dur_l = math.ceil((fin2 - ini2 + 0.25) * 2) / 2
        self.lector = Plano("e07_lector", ini2, fin2, lambda t: DT.cam_lector(t, dur_l), t_lee=1.2)
        self.planos3d = [self.aire.clip, self.lector.clip]
        self.seg = Segmentos([self.t_foto, self.t_aire, self.t_corte, self.t_lector, self.t_fin], CRUCE)
        self.razones = [(instante(self, 1, w), w2) for w, w2 in (("puertos", "sin puertos de prueba"), ("quemado", "quemado"),
                                                                    ("mojado", "mojado"), ("destrozado", "destrozado"))]
        rng = np.random.default_rng(741)
        self.calor = rng.standard_normal((H // 8, W // 8)).astype(np.float32)

    def _titulo(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        a = aparece(t, 0.1, 0.6)
        G.rotulo(img, "Chip-Off", 960, 330, 120, BLANCO, a, alinear="centro")
        lz = G.Lienzo()
        c = lz.c
        for k, (tk, nombre) in enumerate(self.razones):
            ak = aparece(t, tk - 0.15, 0.5)
            x = 330 + k * 420
            lz.tinta(mezcla(PLACA, NEGRO, 0.3), 0.9 * ak)
            G.D.rect_redondeado(c, x - 180, 470, 360, 300, 24)
            c.fill()
            lz.tinta(COBRE if k else VERDE, ak)
            c.set_line_width(4)
            cx, cy = x, 590
            if k == 0:
                G.D.rect_redondeado(c, cx - 90, cy - 60, 180, 120, 10)
                c.stroke()
                G.tacha(c, cx + 60, cy - 40, 50, lim((t - tk) / 0.5), 6)
            elif k == 1:                                      # llama
                c.move_to(cx, cy - 80)
                c.curve_to(cx + 70, cy - 10, cx + 50, cy + 70, cx, cy + 70)
                c.curve_to(cx - 50, cy + 70, cx - 70, cy - 10, cx, cy - 80)
                c.stroke()
            elif k == 2:                                      # gota
                c.move_to(cx, cy - 80)
                c.curve_to(cx + 60, cy, cx + 60, cy + 70, cx, cy + 70)
                c.curve_to(cx - 60, cy + 70, cx - 60, cy, cx, cy - 80)
                c.stroke()
            else:                                             # placa rota
                c.move_to(cx - 90, cy - 60)
                c.line_to(cx - 5, cy - 60)
                c.line_to(cx + 15, cy - 10)
                c.line_to(cx - 10, cy + 20)
                c.line_to(cx + 10, cy + 60)
                c.line_to(cx - 90, cy + 60)
                c.close_path()
                c.stroke()
                c.move_to(cx + 30, cy - 60)
                c.line_to(cx + 90, cy - 60)
                c.line_to(cx + 90, cy + 60)
                c.line_to(cx + 35, cy + 60)
                c.line_to(cx + 15, cy + 20)
                c.line_to(cx + 40, cy - 10)
                c.close_path()
                c.stroke()
        img = lz.componer(img, sombra=0.6, brillo=0.25, col_brillo=COBRE)
        for k, (tk, nombre) in enumerate(self.razones):
            G.rotulo(img, nombre, 330 + k * 420, 730, 32 if k == 0 else 38, BLANCO, aparece(t, tk, 0.5), alinear="centro")
        return img

    def _foto(self, t: float) -> np.ndarray:
        z, cx, cy = recorrido(t - self.t_foto + CRUCE / 2, self.t_aire - self.t_foto + CRUCE, 1.05, 1.22, (0.5, 0.5), (0.47, 0.55))
        img = self.foto.ver(z, cx, cy) if self.foto.existe else self.fondo.copy()
        a = aparece(t, self.t_foto + 0.3, 0.6)
        G.panel(img, 0, H - 200, 980, H, a, 0.5)
        pie_de_foto(img, "Aire caliente sobre un chip", a, y=H - 120, sub="la soldadura se derrite")
        return img

    def _aire(self, t: float) -> np.ndarray:
        img = self.aire.cuadro(t)
        # el aire caliente hace temblar lo que se ve sobre la boquilla mientras calienta
        calor = 1 - suave(lim((t - (self.t_levanta - 1.7)) / 0.6))      # hasta que se aparta la boquilla
        p = self.aire.punto(t, DT.en_placa(DT.CHIPS["U2"][0], DT.CHIPS["U2"][1], DT.GROSOR + 14.0))
        if calor > 0 and p is not None:
            x, y = p
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            zona = np.exp(-(((xx - x) / 260) ** 2) - (((yy - y + 60) / 300) ** 2)) * calor
            ruido = cv2.resize(self.calor, (W, H), interpolation=cv2.INTER_CUBIC)
            ruido = np.roll(ruido, int(t * 240) % H, axis=0)
            mx = (xx + ruido * 2.4 * zona).astype(np.float32)
            my = (yy + np.roll(ruido, 37, axis=1) * 3.2 * zona).astype(np.float32)
            img = cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        a = aparece(t, self.t_aire + 0.3, 0.6, self.t_corte - 0.4)
        G.panel(img, 100, 860, 760, 990, a)
        G.rotulo(img, "aire caliente", 140, 915, 42, BLANCO, a)
        G.rotulo(img, "y pinzas para despegarlo", 140, 962, 30, COBRE, aparece(t, self.t_levanta - 0.6, 0.5, self.t_corte - 0.4),
                 nombre="Inter-Regular.ttf")
        return img

    def _corte(self, t: float) -> np.ndarray:
        """Corte de la placa: se desgasta por debajo hasta dejar expuestas las bolitas del chip."""
        img = self.fondo.copy()
        t0 = self.t_corte - CRUCE / 2
        o = self.T.oraciones
        desgaste = suave(lim((t - t0 - 1.2) / max(1.0, o[5] - t0 - 2.2)))
        x0, x1, ytop = 460, 1460, 520
        capas = ((ytop, 34, PLACA), (ytop + 34, 20, COBRE), (ytop + 54, 70, mezcla(COBRE, PLACA, 0.6) * 0.8),
                 (ytop + 124, 20, COBRE), (ytop + 144, 34, PLACA))
        fondo_corte = ytop + 178
        frente = fondo_corte - (fondo_corte - ytop + 6) * desgaste       # hasta dónde llegó el desgaste
        lz = G.Lienzo()
        c = lz.c
        a = aparece(t, t0, 0.6)
        # chip encima, con sus bolitas entre el chip y la placa
        lz.tinta(mezcla(LAB["negro"], BLANCO, 0.08), a)
        G.D.rect_redondeado(c, 780, ytop - 110, 360, 84, 8)
        c.fill()
        for k in range(9):
            bx = 810 + k * 37.5
            expuesta = frente < ytop + 2
            lz.tinta(mezcla(BLANCO, COBRE, 0.25) if not expuesta else VERDE, a)
            c.arc(bx, ytop - 13, 13, 0, math.tau)
            c.fill()
        for (y, h, col) in capas:
            alto_vivo = max(0.0, min(h, frente - y))
            if alto_vivo <= 0:
                continue
            lz.tinta(col, a)
            c.rectangle(x0, y, x1 - x0, alto_vivo)
            c.fill()
        # la lija/fresa que sube por debajo
        lz.tinta(GRIS, a * (desgaste < 0.999))
        c.rectangle(x0 + 120, frente + 4, x1 - x0 - 240, 40)
        c.fill()
        lz.tinta(BLANCO, a * 0.5 * (desgaste < 0.999))
        for k in range(16):
            xx = x0 + 130 + k * 47 + (t * 180) % 47
            c.move_to(xx, frente + 8)
            c.line_to(xx - 18, frente + 40)
        c.set_line_width(2)
        c.stroke()
        img = lz.componer(img, sombra=0.6, brillo=0.3 * desgaste, col_brillo=VERDE)
        G.rotulo(img, "chip", 960, ytop - 140, 36, BLANCO, a, alinear="centro")
        G.rotulo(img, "placa", x0 - 30, ytop + 100, 34, BLANCO, a, alinear="der")
        G.rotulo(img, "se desgasta por debajo", 960, 840, 40, COBRE, aparece(t, t0 + 0.8, 0.6), alinear="centro")
        G.rotulo(img, "hasta dejar expuestos los contactos", 960, 895, 34, VERDE, aparece(t, t0 + 1.2 + desgaste * 0, 0.6) * suave(lim((desgaste - 0.8) / 0.2)),
                 alinear="centro", nombre="Inter-Regular.ttf")
        G.antetitulo(img, "Otra forma", 960, 230, COBRE, a, alinear="centro")
        return img

    def _lector(self, t: float) -> np.ndarray:
        img = self.lector.cuadro(t)
        a = aparece(t, self.t_lector + 0.5, 0.7)
        G.rotulo_en(img, self.lector.punto(t, (0.0, 0.0, 0.034)), "adaptador", BLANCO, VERDE, a, lado="der", alto=130, largo=50, tam=38)
        t_prog = instante(self, 5, "programador")
        a2 = aparece(t, t_prog, 0.7)
        G.rotulo_en(img, self.lector.punto(t, (0.040, -0.030, 0.024)), "programador", BLANCO, COBRE, a2, lado="der",
                    alto=90, largo=50, tam=38, sub="habla directo con chips de memoria")
        return img

    def _final(self, t: float) -> np.ndarray:
        from escenas import diagramas as DG
        img = self.fondo.copy()
        o = self.T.oraciones
        t0 = self.t_fin - CRUCE / 2
        lz = G.Lienzo()
        c = lz.c
        a = aparece(t, t0, 0.6)
        # la placa con el hueco donde estaba el chip
        lz.tinta(mezcla(PLACA, NEGRO, 0.3), a)
        G.D.rect_redondeado(c, 220, 340, 600, 400, 20)
        c.fill()
        lz.tinta(mezcla(LAB["negro"], BLANCO, 0.06), a)
        DG.caja(c, 280, 400, 180, 180, 10, 1.0, 3, relleno=mezcla(LAB["negro"], BLANCO, 0.06))
        lz.tinta(BLANCO, a * 0.6)
        c.set_line_width(3)
        c.set_dash([10, 8])
        c.rectangle(560, 420, 170, 190)
        c.stroke()
        c.set_dash([])
        for i in range(5):
            for j in range(5):
                c.new_sub_path()
                c.arc(590 + i * 28, 455 + j * 30, 6, 0, math.tau)
        c.fill()
        lz.tinta(ROJO, aparece(t, o[6] + 0.3, 0.5))
        G.tacha(c, 520, 540, 300, lim((t - o[6] - 0.3) / 0.7), 10)
        # no hay segunda oportunidad: el chip y el calor
        t2 = o[7]
        a2 = aparece(t, t2, 0.6)
        lz.tinta(mezcla(LAB["negro"], BLANCO, 0.1), a2)
        G.D.rect_redondeado(c, 1250, 420, 260, 220, 16)
        c.fill()
        temp = lim((t - t2 - 0.3) / 2.0)
        lz.tinta(mezcla(VERDE, ROJO, temp), a2)
        c.set_line_width(5)
        G.D.rect_redondeado(c, 1250, 420, 260, 220, 16)
        c.stroke()
        lz.tinta(mezcla(COBRE, ROJO, 0.5), a2)
        c.rectangle(1580, 640 - 220 * temp, 26, 220 * temp)
        c.fill()
        lz.tinta(BLANCO, a2 * 0.7)
        c.set_line_width(3)
        G.D.rect_redondeado(c, 1574, 410, 38, 236, 18)
        c.stroke()
        if temp > 0.85:
            lz.tinta(ROJO, a2)
            DG.linea(c, [(1320, 420), (1345, 480), (1325, 530), (1360, 600), (1350, 640)], (temp - 0.85) / 0.15, 4)
        img = lz.componer(img, sombra=0.6, brillo=0.3, col_brillo=mezcla(VERDE, ROJO, temp))
        G.rotulo(img, "el aparato queda destruido", 520, 830, 40, BLANCO, aparece(t, o[6] + 0.3, 0.6), alinear="centro")
        G.rotulo(img, "no se puede volver a armar", 520, 885, 32, mezcla(ROJO, BLANCO, 0.4), aparece(t, o[6] + 0.8, 0.6),
                 alinear="centro", nombre="Inter-Regular.ttf")
        G.rotulo(img, "una sola oportunidad", 1430, 830, 40, BLANCO, aparece(t, t2 + 1.0, 0.6), alinear="centro")
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return componer((self._titulo, self._foto, self._aire, self._corte, self._lector, self._final), self.seg, t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("laboratorio", 0, S.zumbido_lab(d, 741), -5, 1.0, 1.0)
        m.agregar("aire caliente", self.t_foto + 0.3, S.aire_caliente(self.t_levanta - self.t_foto - 0.6, 742), -2, 0.4, 0.6)
        m.agregar("pinzas", self.t_levanta - 0.25, S.clic_pinzas(743), 0)
        m.agregar("lijado", self.t_corte + 1.2, sfx.filtro(S.aire_caliente(3.0, 744), "bandpass", (1500, 6000), 2), -10, 0.3, 0.5)
        m.agregar("lectura", self.t_lector + 1.0, S.lectura(self.t_fin - self.t_lector - 0.8, 745), -6)
        return m.x[:n]


# =========================================================================== 7.5


@functools.lru_cache(maxsize=1)
def _atlas_hex(tam: int = 26) -> tuple:
    """Máscaras de "00".."FF" y de los caracteres imprimibles para pintar el volcado en rejilla."""
    hx = tuple(texto_alfa(f"{k:02X}", "Inter-Regular.ttf", tam, margen=0) for k in range(256))
    asc = tuple(texto_alfa(chr(k) if 33 <= k < 127 else "·", "Inter-Regular.ttf", tam, margen=0) for k in range(256))
    return hx, asc


def _pegar(img, m, x, y, col, a):
    h, w = m.shape
    if a <= 0 or y < 0 or y + h > H or x < 0 or x + w > W:
        return
    img[y : y + h, x : x + w] += m[..., None] * (np.asarray(col, np.float32) * a)


class Sub75(Subescena):
    """El volcado hexadecimal; archivos que aparecen; el mapa de memoria; el rompecabezas; la pausa;
    Bentonville."""

    @property
    def cine(self):
        x = suave(lim((getattr(self, "_t", 0.0) - self.T.oraciones[5] + 0.3) / 1.2))
        return {k: (mezcla(CINE_LAB[k], CINE_ARK[k], x) if isinstance(CINE_LAB[k], np.ndarray) else CINE_LAB[k] * (1 - x) + CINE_ARK[k] * x)
                for k in CINE_LAB}

    def preparar(self) -> None:
        o = self.T.oraciones
        self.fondo = G.fondo(mezcla(LAB["negro"], NEGRO, 0.5), mezcla(PLACA, NEGRO, 0.78), semilla=9, reticula=0.0)
        rng = np.random.default_rng(751)
        self.datos = rng.integers(0, 256, (400, 16)).astype(np.uint8)
        self.datos[rng.random((400, 16)) < 0.35] = 0
        self.datos[40:42] = 0xFF
        # firmas de archivos conocidas, escondidas justo donde el volcado se va a detener
        self.seg = Segmentos([o[2] - 0.2, o[3] - 0.1, o[4] - 0.3, o[5] - 0.1], CRUCE)
        f = int(self._scroll(o[2] - 0.2))
        filas = (f + 5, f + 10, f + 16)
        firmas = (b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01", b"SQLite format 3\x00", b"evt=07 v=01 t=1A")
        for fila, b in zip(filas, firmas):
            self.datos[fila % len(self.datos)] = np.frombuffer(b, np.uint8)
        self.hallazgos = tuple(zip(filas, ("imagen JPEG", "base de datos", "registro de eventos")))
        self.fondo_ark = fondo_ark()

    def _scroll(self, t: float) -> float:
        """Filas desplazadas: corre rápido, frena cuando aparecen los recuadros y se para en la pausa."""
        tq = self.quieto(t)
        o = self.T.oraciones
        frena = o[1] - 0.6
        if tq < frena:
            return tq * 6.0
        return frena * 6.0 + 14 - 14 * math.exp(-(tq - frena) / 1.0) + (tq - frena) * 0.4

    def _volcado(self, t: float, cuadros: bool = True) -> np.ndarray:
        img = self.fondo.copy()
        hx, asc = _atlas_hex()
        o = self.T.oraciones
        fila0 = self._scroll(t)
        f0 = int(fila0)
        frac = fila0 - f0
        x_off, x_hex, x_asc = 110, 330, 1120
        alto = 38
        bits = aparece(t, 0.0, 0.3) * (1 - suave(lim((t - 2.6) / 1.2)))
        hexa = suave(lim((t - 2.2) / 1.2))
        a_hal = [aparece(t, o[1] + 0.2 + 0.7 * k, 0.4) for k in range(3)]
        for r in range(-1, 26):
            fila = f0 + r
            y = int(160 + r * alto - frac * alto)
            if y < 120 or y > H - 80:
                continue
            fade = min(1.0, (y - 120) / 120, (H - 80 - y) / 120)
            datos = self.datos[fila % len(self.datos)]
            if hexa > 0:
                _pegar(img, texto_alfa(f"{(fila * 16) & 0xFFFFFFFF:08X}", "Inter-Regular.ttf", 26, margen=0), x_off, y,
                       mezcla(VERDE, NEGRO, 0.55), hexa * fade)
                for j, b in enumerate(datos):
                    _pegar(img, hx[b], x_hex + j * 46 + (12 if j >= 8 else 0), y, VERDE, hexa * fade * (0.55 if b == 0 else 0.95))
                    _pegar(img, asc[b], x_asc + j * 22, y, mezcla(VERDE, BLANCO, 0.2), hexa * fade * 0.6)
            if bits > 0:
                for j in range(64):
                    v = (int(datos[j // 4]) >> (j % 4 * 2)) & 1
                    _pegar(img, texto_alfa(str(v), "Inter-Regular.ttf", 26, margen=0), 110 + j * 25, y, VERDE, bits * fade * 0.8)
        if cuadros:
            lz = G.Lienzo()
            for k, (fila, nombre) in enumerate(self.hallazgos):
                y = 160 + (fila - fila0) * alto
                if a_hal[k] <= 0 or not (120 < y < H - 120):
                    continue
                col = (COBRE, VERDE, BLANCO)[k]
                lz.tinta(col, a_hal[k])
                lz.c.set_line_width(3)
                G.D.rect_redondeado(lz.c, x_hex - 14, y - 8, 46 * 16 + 30, alto, 6)
                lz.c.stroke()
            img = lz.componer(img, sombra=0.3, brillo=0.45, col_brillo=VERDE, sigma_brillo=10)
            for k, (fila, nombre) in enumerate(self.hallazgos):
                y = 160 + (fila - fila0) * alto
                if a_hal[k] > 0 and 120 < y < H - 120:
                    G.rotulo(img, nombre, x_asc + 16 * 22 + 40, y + 24, 32, (COBRE, VERDE, BLANCO)[k], a_hal[k])
        G.panel(img, 0, 0, W, 110, 1.0, 0.3)
        G.rotulo(img, "volcado.bin", 150, 72, 32, BLANCO, aparece(t, 0.2, 0.6))
        G.rotulo(img, "sin etiquetas", 1770, 72, 28, mezcla(BLANCO, NEGRO, 0.35), aparece(t, 0.8, 0.6), alinear="der",
                 nombre="Inter-Regular.ttf")
        return img

    def _mapa_memoria(self, t: float) -> np.ndarray:
        img = G.desenfocar(self._volcado(t, cuadros=False), 18, 0.55)
        o = self.T.oraciones
        t0 = o[2] - 0.2
        tramos = (("arranque", 0.15, VERDE), ("sistema", 0.20, VERDE), ("?", 0.16, GRIS), ("registros", 0.17, COBRE),
                  ("?", 0.13, GRIS), ("datos", 0.19, VERDE))
        x, y, ancho, alto = 220, 470, 1480, 150
        lz = G.Lienzo()
        c = lz.c
        acum = 0.0
        for k, (nombre, frac, col) in enumerate(tramos):
            a = aparece(t, t0 + 0.25 * k, 0.5)
            lz.tinta(mezcla(col, NEGRO, 0.55 if nombre != "?" else 0.75), a)
            G.D.rect_redondeado(c, x + acum * ancho + 4, y, frac * ancho - 8, alto, 14)
            c.fill()
            lz.tinta(col, a)
            c.set_line_width(3)
            G.D.rect_redondeado(c, x + acum * ancho + 4, y, frac * ancho - 8, alto, 14)
            c.stroke()
            acum += frac
        img = lz.componer(img, sombra=0.6, brillo=0.25, col_brillo=VERDE)
        acum = 0.0
        for k, (nombre, frac, col) in enumerate(tramos):
            G.rotulo(img, nombre, x + (acum + frac / 2) * ancho, y + alto / 2 + (24 if nombre == "?" else 12),
                     64 if nombre == "?" else 32, BLANCO, aparece(t, t0 + 0.25 * k + 0.2, 0.5), alinear="centro")
            acum += frac
        a = aparece(t, t0 + 0.2, 0.6)
        G.antetitulo(img, "Mapa de memoria", x, 380, COBRE, a)
        G.rotulo(img, "cada fabricante organiza la suya", x, 720, 40, BLANCO, aparece(t, t0 + 1.4, 0.6))
        return img

    def _rompecabezas(self, t: float) -> np.ndarray:
        img = G.desenfocar(self._volcado(t, cuadros=False), 18, 0.6)
        o = self.T.oraciones
        t0 = o[3] - 0.1
        tq = self.quieto(t)
        lz = G.Lienzo()
        c = lz.c
        rng = np.random.default_rng(752)
        n_c, n_f, lado = 7, 4, 120
        x0, y0 = 960 - n_c * lado / 2, 300
        faltan = {(1, 2), (4, 1), (5, 3), (2, 0)}
        for i in range(n_f):
            for j in range(n_c):
                k = i * n_c + j
                tk = t0 + 0.05 * k
                a = aparece(tq, tk, 0.4)
                if (j, i) in faltan:
                    lz.tinta(BLANCO, a * 0.35)
                    c.set_line_width(2)
                    c.set_dash([8, 8])
                    c.rectangle(x0 + j * lado + 6, y0 + i * lado + 6, lado - 12, lado - 12)
                    c.stroke()
                    c.set_dash([])
                    continue
                col = mezcla(VERDE, COBRE, float(rng.random()) * 0.6)
                dx = (rng.random() - 0.5) * 30 * (1 - suave(lim((tq - tk) / 1.4)))
                lz.tinta(mezcla(col, NEGRO, 0.45), a)
                px, py = x0 + j * lado + dx, y0 + i * lado
                c.rectangle(px + 6, py + 6, lado - 12, lado - 12)
                c.fill()
                lz.tinta(col, a)
                c.set_line_width(2)
                c.rectangle(px + 6, py + 6, lado - 12, lado - 12)
                c.stroke()
                if j < n_c - 1:                                           # pestaña del rompecabezas
                    lz.tinta(mezcla(col, NEGRO, 0.45), a)
                    c.arc(px + lado, py + lado / 2, 16, 0, math.tau)
                    c.fill()
        img = lz.componer(img, sombra=0.6, brillo=0.2, col_brillo=VERDE)
        G.rotulo(img, "Sin estándares en IoT", 960, 880, 48, BLANCO, aparece(tq, t0 + 0.4, 0.6), alinear="centro")
        G.rotulo(img, "cada aparato nuevo, un rompecabezas nuevo", 960, 940, 34, COBRE,
                 aparece(tq, instante(self, 3, "rompecabezas") - 0.6, 0.6), alinear="centro", nombre="Inter-Regular.ttf")
        return img

    def _significado(self, t: float) -> np.ndarray:
        img = G.desenfocar(self._volcado(t, cuadros=False), 18, 0.62)
        o = self.T.oraciones
        t0 = o[4] - 0.3
        a = aparece(t, t0, 0.6)
        G.panel(img, 420, 380, 1500, 700, a)
        G.rotulo(img, "evt=07   v=01   t=1A", 960, 500, 64, VERDE, a, alinear="centro", nombre="Inter-Light.ttf")
        G.rotulo(img, "¿qué significa?", 960, 620, 54, BLANCO, aparece(t, instante(self, 4, "significa") - 0.3, 0.6), alinear="centro")
        return img

    def _arkansas(self, t: float) -> np.ndarray:
        img = self.fondo_ark.copy()
        t0 = self.T.oraciones[5] - 0.1
        u = suave(lim((t - t0) / 2.6))
        # proyección: de Estados Unidos entero a Arkansas
        lon0, lat0, k0 = -96.0, 38.0, 26.0
        lon1, lat1, k1 = -92.2, 34.8, 210.0
        lon_c, lat_c = lon0 + (lon1 - lon0) * u, lat0 + (lat1 - lat0) * u
        k = k0 * (k1 / k0) ** u
        cl = math.cos(math.radians(36))

        def P(lon, lat):
            return (960 + (lon - lon_c) * k * cl, 560 - (lat - lat_c) * k)
        lz = G.Lienzo()
        c = lz.c
        a = aparece(t, t0 - 0.4, 0.6)
        lz.tinta(mezcla(AZUL, BLANCO, 0.12), a * (1 - 0.5 * u))
        G.D.rellenar(c, [P(*q) for q in G.EEUU], suave=False)
        lz.tinta(mezcla(AZUL, BLANCO, 0.35), a)
        G.D.rellenar(c, [P(*q) for q in G.ARKANSAS], suave=False)
        lz.tinta(BLANCO, a * 0.8)
        c.set_line_width(3)
        pts = [P(*q) for q in G.ARKANSAS]
        c.move_to(*pts[0])
        for q in pts[1:]:
            c.line_to(*q)
        c.close_path()
        c.stroke()
        bx, by = P(*G.BENTONVILLE)
        ab = aparece(t, t0 + 1.4, 0.6)
        lz.tinta(ROJO, ab)
        c.arc(bx, by, 10, 0, math.tau)
        c.fill()
        anillo = (t * 0.7) % 1.0
        lz.tinta(ROJO, ab * (1 - anillo))
        c.set_line_width(3)
        c.arc(bx, by, 14 + 50 * anillo, 0, math.tau)
        c.stroke()
        img = lz.componer(img, sombra=0.6, brillo=0.4, col_brillo=ROJO)
        G.rotulo(img, "Bentonville", bx + 30, by + 14, 46, BLANCO, ab)
        G.rotulo(img, "Arkansas", bx + 32, by + 64, 30, mezcla(BLANCO, AZUL, 0.3), ab, nombre="Inter-Regular.ttf")
        return img

    def cuadro(self, t: float) -> np.ndarray:
        self._t = t
        return componer((self._volcado, self._mapa_memoria, self._rompecabezas, self._significado, self._arkansas), self.seg, t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        o = self.T.oraciones
        pausa = self.T.pausas[0] if self.T.pausas else (o[4] - 1.0, o[4])
        m.agregar("datos", 0.0, sfx.datos(pausa[0], 751, 30.0), -4, 0.3, 0.6)
        m.agregar("laboratorio", 0, S.zumbido_lab(pausa[0] + 0.5, 752), -8, 1.0, 0.8)
        for k in range(3):
            m.agregar(f"hallazgo{k}", o[1] + 0.2 + 0.7 * k, sfx.clic_contador(753 + k), -6)
        m.agregar("transición", o[5] - 0.4, sfx.whoosh(1.0, 756, 140, 2400), -4)
        m.agregar("noche", o[5] + 0.2, S.noche_fria(d - o[5], 757), -10, 1.0, 0.5)
        return m.x[:n]


# =========================================================================== 7.6


class Sub76(Subescena):
    """Noviembre de 2015: el patio (3D), la casa, James Bates, Victor Collins, la tina vacía, el Echo."""

    @property
    def cine(self):
        t = getattr(self, "_t", 0.0)
        x = campana_victima(t, self.t_collins, self.t_tina, 0.9)
        return {k: (mezcla(CINE_ARK[k], CINE_NEUTRO[k], x) if isinstance(CINE_ARK[k], np.ndarray) else CINE_ARK[k] * (1 - x) + CINE_NEUTRO[k] * x)
                for k in CINE_ARK}

    def preparar(self) -> None:
        o = self.T.oraciones
        self.fondo = fondo_ark()
        self.t_casa = o[1] + 0.4
        self.t_bates = instante(self, 1, "james") - 0.2
        self.t_collins = o[2] + 0.2
        self.t_tina = instante(self, 2, "jacuzzi") - 0.9
        self.t_echo_foto = o[3]
        self.t_echo = instante(self, 3, "bocina") + 1.2
        self.patio = Plano("e07_patio_llegada", 0.0, self.t_casa + CRUCE / 2,
                           lambda t: DT.cam_patio(t, math.ceil((self.t_casa + CRUCE / 2 + 0.25) * 2) / 2, "llegada"))
        ini_t, fin_t = self.t_tina - CRUCE / 2, self.t_echo_foto + CRUCE / 2
        dur_t = math.ceil((fin_t - ini_t + 0.25) * 2) / 2
        self.tina = Plano("e07_patio_tina", ini_t, fin_t, lambda t: DT.cam_patio(t, dur_t, "tina"))
        ini_e, fin_e = self.t_echo - CRUCE / 2, self.d
        dur_e = math.ceil((fin_e - ini_e + 0.25) * 2) / 2
        self.echo = Plano("e07_echo_repisa", ini_e, fin_e, lambda t: DT.cam_echo(t, dur_e, "repisa"))
        self.planos3d = [self.patio.clip, self.tina.clip, self.echo.clip]
        self.seg = Segmentos([self.t_casa, self.t_collins, self.t_tina, self.t_echo_foto, self.t_echo], CRUCE)
        self.f_casa = Foto("7.6_casa_bates.jpg", tinte=AZUL, fuerza=0.06)
        self.f_bates = Foto("7.6_james_bates.jpg")
        self.f_collins = Foto("7.6_victor_collins.jpg")                     # víctima: sin tinte ni efectos
        self.f_echo = Foto("7.6_amazon_echo.jpg")

    def _patio(self, t: float) -> np.ndarray:
        img = self.patio.cuadro(t)
        G.antetitulo(img, "Bentonville, Arkansas", 120, H - 200, mezcla(BLANCO, AZUL, 0.25), aparece(t, 0.3, 0.7))
        G.rotulo(img, "Noviembre de 2015", 118, H - 140, 56, BLANCO, aparece(t, 0.5, 0.7))
        return img

    def _casa(self, t: float) -> np.ndarray:
        """La casa y, cuando se dice su nombre, James Bates a su lado."""
        img = self.fondo.copy()
        z = 1.0 + 0.04 * lim((t - self.t_casa + 0.5) / 5.0)
        G.tarjeta_foto(img, self.f_casa, 150, 200, 720, 683, z=z, cx=0.5, cy=0.5, a=aparece(t, self.t_casa - 0.4, 0.5))
        G.antetitulo(img, "La casa", 150, 170, mezcla(BLANCO, AZUL, 0.3), aparece(t, self.t_casa, 0.7))
        ab = aparece(t, self.t_bates, 0.7)
        if ab > 0 and self.f_bates.existe:
            fw = 380
            fh = round(fw * self.f_bates.h / self.f_bates.w)
            G.tarjeta_foto(img, self.f_bates, 1010 + int(30 * (1 - suave(ab))), 200, fw, fh,
                           z=1.0 + 0.03 * lim((t - self.t_bates) / 5.0), cy=0.45, a=ab)
        G.rotulo(img, "James Bates", 1460, 520, 64, BLANCO, aparece(t, self.t_bates + 0.3, 0.7))
        G.rotulo(img, "dueño de la casa", 1462, 582, 32, mezcla(BLANCO, AZUL, 0.3), aparece(t, self.t_bates + 0.7, 0.7),
                 nombre="Inter-Regular.ttf")
        img[608:611, 1462 : 1462 + int(300 * suave(lim((t - self.t_bates - 0.6) / 1.2)))] = ROJO
        G.rotulo(img, "amigos reunidos para ver un partido", 152, 945, 32, mezcla(BLANCO, AZUL, 0.25),
                 aparece(t, self.t_casa + 0.6, 0.6), nombre="Inter-Regular.ttf")
        return img

    def _retrato(self, t: float, foto: Foto, nombre: str, detalle: str, t0: float, victima: bool) -> np.ndarray:
        if victima:
            img = G.fondo(mezcla(AZUL, NEGRO, 0.85), mezcla(AZUL, NEGRO, 0.7), semilla=10, reticula=0.0)
        else:
            img = self.fondo.copy()
        fw = 470
        fh = round(fw * foto.h / foto.w) if foto.existe else 680
        x0, y0 = 330, (H - fh) // 2
        z = 1.0 + (0.025 if victima else 0.035) * lim((t - t0) / 6.0)       # acercamiento muy lento
        G.tarjeta_foto(img, foto, x0, y0, fw, fh, z=z, cx=0.5, cy=0.45, a=1.0, sombra=0.5)
        a = aparece(t, t0 + 0.3, 0.8)
        G.rotulo(img, nombre, 960, 520, 66, BLANCO, a, sombra=0)
        G.rotulo(img, detalle, 962, 585, 32, mezcla(BLANCO, AZUL, 0.3), aparece(t, t0 + 0.8, 0.8), nombre="Inter-Regular.ttf", sombra=0)
        largo = int(380 * suave(lim((t - t0 - 0.5) / 1.4)))
        img[612:615, 962 : 962 + largo] = mezcla(BLANCO, AZUL, 0.4) if victima else ROJO
        return img

    def _collins(self, t):
        return self._retrato(t, self.f_collins, "Victor Collins", "uno de sus amigos", self.t_collins, True)

    def _tina(self, t: float) -> np.ndarray:
        return self.tina.cuadro(t)

    def _echo_foto(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        a = aparece(t, self.t_echo_foto - 0.4, 0.5)
        G.tarjeta_foto(img, self.f_echo, 560, 120, 300, None, z=1.0 + 0.03 * lim((t - self.t_echo_foto) / 3.0), a=a,
                       borde=(0.85, 0.85, 0.85))
        G.rotulo(img, "Amazon Echo", 1000, 520, 66, BLANCO, aparece(t, self.t_echo_foto + 0.1, 0.6))
        G.rotulo(img, "bocina inteligente", 1002, 585, 32, mezcla(BLANCO, AZUL, 0.3), aparece(t, self.t_echo_foto + 0.4, 0.6),
                 nombre="Inter-Regular.ttf")
        return img

    def _echo(self, t: float) -> np.ndarray:
        img = self.echo.cuadro(t)
        a = aparece(t, self.t_echo + 0.5, 0.8)
        G.antetitulo(img, "La cocina de Bates", 120, H - 140, mezcla(BLANCO, AZUL, 0.25), a)
        return img

    def cuadro(self, t: float) -> np.ndarray:
        self._t = t
        return componer((self._patio, self._casa, self._collins, self._tina, self._echo_foto, self._echo), self.seg, t, oscuros=(2,))

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("noche", 0, S.noche_fria(d, 761), -4, 1.0, 1.0)
        # las burbujas solo con el patio a la vista; bajan mientras están las fotos
        m.agregar("burbujas", 0.0, S.burbujas(self.t_casa + 1.0, 762), -3, 0.8, 1.0)
        m.agregar("burbujas2", self.t_tina - 0.3, S.burbujas(self.t_echo_foto - self.t_tina + 1.0, 763), -4, 1.0, 1.0)
        return m.x[:n]


def campana_victima(t: float, a: float, b: float, rampa: float) -> float:
    """1 mientras está en pantalla la foto de la víctima (de a a b), con rampas suaves."""
    return suave(lim((t - a + rampa / 2) / rampa)) * (1 - suave(lim((t - b + rampa / 2) / rampa)))


# =========================================================================== 7.7


class Sub77(Subescena):
    """Cómo escucha el Echo; el anillo azul (3D); el audio va a la nube; la orden; el titular; el permiso."""

    cine = CINE_ARK

    def preparar(self) -> None:
        o = self.T.oraciones
        self.fondo = fondo_ark()
        self.t_anillo = o[3] - 0.3
        self.t_nube = o[4] - 0.3
        self.t_titular = o[6] + 0.2
        self.t_permiso = o[8] - 0.3
        self.t_luz = instante(self, 3, "enciende")
        ini, fin = self.t_anillo - CRUCE / 2, self.t_nube + CRUCE / 2
        dur = math.ceil((fin - ini + 0.25) * 2) / 2
        self.echo = Plano("e07_echo_anillo", ini, fin, lambda t: DT.cam_echo(t, dur, "anillo"),
                          encendido=float(round(self.t_luz - ini, 2)))
        self.planos3d = [self.echo.clip]
        self.seg = Segmentos([self.t_anillo, self.t_nube, self.t_titular, self.t_permiso], CRUCE)
        self.titular = Foto("7.7_titular_amazon.jpg")
        self.t_alexa = instante(self, 1, "alexa")

    def _escucha(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        o = self.T.oraciones
        lz = G.Lienzo()
        c = lz.c
        a = aparece(t, 0.2, 0.6)
        lz.tinta(BLANCO, a)
        G.bocina(c, 520, 560, 360, 4)
        # el sonido de la casa entra: ondas desde la izquierda
        for k in range(4):
            f = (t * 0.6 + k / 4) % 1.0
            lz.tinta(AZUL_CLARO, a * (1 - f) * 0.8)
            c.set_line_width(3)
            c.arc(520, 560, 220 + 260 * f, math.pi * 0.75, math.pi * 1.25)
            c.stroke()
        # adentro: escucha unos instantes y los descarta
        a_v = aparece(t, o[1], 0.6)
        lz.tinta(mezcla(AZUL, NEGRO, 0.3), a_v)
        G.D.rect_redondeado(c, 820, 430, 560, 260, 24)
        c.fill()
        lz.tinta(AZUL_CLARO, a_v)
        G.waveform(c, 860, 560, 480, 150, t, 771, 56)
        no_graba = aparece(t, o[2], 0.5)
        # el detector busca solo una palabra
        a_al = aparece(t, self.t_alexa - 0.2, 0.5)
        lz.tinta(BLANCO, a_al)
        G.lupa(c, 1550, 520, 120, 4)
        # botón de grabar apagado
        lz.tinta(mezcla(ROJO, NEGRO, 0.6), no_graba)
        c.arc(1110, 790, 26, 0, math.tau)
        c.fill()
        img = lz.componer(img, sombra=0.6, brillo=0.3, col_brillo=AZUL_CLARO)
        G.rotulo(img, "escucha todo el tiempo", 1100, 400, 34, BLANCO, a_v, alinear="centro")
        G.rotulo(img, "«Alexa»", 1550, 690, 46, BLANCO, a_al, alinear="centro")
        G.rotulo(img, "solo busca una palabra", 1550, 740, 28, mezcla(BLANCO, AZUL, 0.3), a_al, alinear="centro",
                 nombre="Inter-Regular.ttf")
        G.rotulo(img, "mientras no la oye, no graba", 1150, 802, 34, mezcla(BLANCO, ROJO, 0.3), no_graba)
        G.rotulo(img, "bocina Echo", 520, 820, 30, mezcla(BLANCO, AZUL, 0.3), a, alinear="centro", nombre="Inter-Regular.ttf")
        return img

    def _anillo(self, t: float) -> np.ndarray:
        img = self.echo.cuadro(t)
        o = self.T.oraciones
        a = aparece(t, self.t_luz + 0.9, 0.5)
        if a > 0:
            seg = max(0.0, t - self.t_luz - 0.9)
            G.panel(img, 100, 880, 520, 990, a)
            if int(t * 2) % 2 == 0:
                lz = G.Lienzo()
                lz.tinta(ROJO, a)
                lz.c.arc(150, 935, 14, 0, math.tau)
                lz.c.fill()
                img = lz.componer(img, sombra=0, brillo=0.5, col_brillo=ROJO)
            G.rotulo(img, f"graba  0:{min(int(seg), 9):02d}", 180, 950, 42, BLANCO, a, nombre="Inter-Light.ttf")
        del o
        return img

    def _nube(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        o = self.T.oraciones
        t0 = self.t_nube - CRUCE / 2
        lz = G.Lienzo()
        c = lz.c
        a = aparece(t, t0, 0.6)
        en_nube = suave(lim((t - o[4] - 0.5) / 1.6))
        lz.tinta(BLANCO, a * (1 - 0.5 * suave(lim((t - o[5] - 0.6) / 1.0))))
        G.bocina(c, 320, 600, 300, 4, anillo=1.0, col_anillo=AZUL_CLARO)
        # el clip de audio viaja a la nube
        lz.tinta(AZUL_CLARO, a * (1 - en_nube * 0.8))
        px = 400 + (1180 - 400) * en_nube
        py = 470 - math.sin(en_nube * math.pi) * 120
        G.D.rect_redondeado(c, px - 60, py - 30, 120, 60, 10)
        c.fill()
        G.nube_contorno(c, 1300, 420, 560, BLANCO, mezcla(AZUL, BLANCO, 0.10), a, 5)
        # adentro: se interpreta la orden y se guarda la grabación
        t_int = instante(self, 4, "interpreta")
        t_gua = instante(self, 4, "guarda")
        a_i = aparece(t, t_int, 0.5)
        lz.tinta(BLANCO, a_i)
        G.D.rect_redondeado(c, 1005, 350, 240, 90, 18)
        c.stroke()
        a_g = aparece(t, t_gua, 0.5)
        lz.tinta(AZUL_CLARO, a_g)
        for k in range(3):
            c.save()
            c.translate(1470, 360 + k * 34)
            c.scale(1.0, 0.32)
            c.arc(0, 0, 80, 0, math.tau)
            c.restore()
            c.stroke()
        c.move_to(1390, 360)
        c.line_to(1390, 428)
        c.move_to(1550, 360)
        c.line_to(1550, 428)
        c.stroke()
        # la policía y la orden judicial: a Amazon, no a la bocina
        t_pol = o[5]
        a_p = aparece(t, t_pol, 0.6)
        lz.tinta(BLANCO, a_p)
        G.insignia(c, 1300, 860, 120, 4)
        G.orden_judicial(c, 1430, 790, 140, 3)
        from escenas import diagramas as DG
        t_or = instante(self, 5, "orden")
        lz.tinta(ROJO, aparece(t, t_or, 0.4))
        DG.flecha(c, (1420, 780), (1380, 620), lim((t - t_or) / 0.7), 5, 22, curva=30)
        img = lz.componer(img, sombra=0.6, brillo=0.3, col_brillo=AZUL_CLARO)
        G.rotulo(img, "servidores de Amazon", 1300, 150, 48, BLANCO, a, alinear="centro")
        G.rotulo(img, "«apaga la luz»", 1125, 405, 28, BLANCO, a_i, alinear="centro", nombre="Inter-Regular.ttf")
        G.rotulo(img, "interpreta la orden", 1125, 492, 30, BLANCO, a_i, alinear="centro")
        G.rotulo(img, "guarda la grabación", 1470, 492, 30, BLANCO, a_g, alinear="centro")
        G.rotulo(img, "policía", 1300, 965, 34, BLANCO, a_p, alinear="centro")
        G.rotulo(img, "orden judicial", 1500, 965, 34, BLANCO, a_p, alinear="centro")
        return img

    def _titular(self, t: float) -> np.ndarray:
        img = G.fondo(mezcla(AZUL, NEGRO, 0.8), mezcla(AZUL, NEGRO, 0.55), semilla=11, reticula=0.0)
        G.documento(img, self.titular, t - self.t_titular + CRUCE / 2, self.t_permiso - self.t_titular + CRUCE, ancho=1220,
                    z0=0.98, z1=1.10, cy0=0.45, cy1=0.6)
        a = aparece(t, self.T.oraciones[7], 0.6)
        G.panel(img, 0, H - 150, W, H, a, 0.5)
        G.rotulo(img, "Engadget, 24 de febrero de 2017", 120, H - 62, 30, BLANCO, a, nombre="Inter-Regular.ttf")
        return img

    def _permiso(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        t0 = self.t_permiso - CRUCE / 2
        o = self.T.oraciones
        lz = G.Lienzo()
        c = lz.c
        a = aparece(t, t0, 0.6)
        G.nube_contorno(c, 560, 520, 420, BLANCO, mezcla(AZUL, NEGRO, 0.2), a, 4)
        t_ent = instante(self, 8, "entrega")
        viaje = suave(lim((t - t_ent) / 1.6))
        for k in range(3):
            lz.tinta(AZUL_CLARO, aparece(t, t_ent, 0.4) * (1 - 0.6 * viaje))
            px = 700 + (1220 - 700) * suave(lim((t - t_ent - 0.15 * k) / 1.5))
            G.D.rect_redondeado(c, px - 50, 470 + k * 34 - 14, 100, 28, 8)
            c.fill()
        lz.tinta(BLANCO, aparece(t, t_ent + 0.4, 0.6))
        G.insignia(c, 1360, 520, 170, 4)
        t_bates = instante(self, 8, "bates")
        lz.tinta(AZUL_CLARO, aparece(t, t_bates, 0.5))
        G.palomita(c, 960, 800, 60, lim((t - t_bates) / 0.5), 7)
        img = lz.componer(img, sombra=0.6, brillo=0.3, col_brillo=AZUL_CLARO)
        G.rotulo(img, "Amazon", 560, 680, 38, BLANCO, a, alinear="centro")
        G.rotulo(img, "fiscalía", 1360, 680, 38, BLANCO, aparece(t, t_ent + 0.4, 0.6), alinear="centro")
        G.rotulo(img, "Bates da su permiso", 1020, 818, 42, BLANCO, aparece(t, t_bates, 0.6))
        del o
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return componer((self._escucha, self._anillo, self._nube, self._titular, self._permiso), self.seg, t, oscuros=(3,))

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        o = self.T.oraciones
        m.agregar("casa", 0, S.noche_fria(d, 771), -10, 1.0, 1.0)
        m.agregar("alexa", self.t_luz, S.tono_alexa(772), 0)
        m.agregar("a la nube", o[4] + 0.4, sfx.whoosh(1.4, 773, 200, 3000, -0.6, 0.6), -4)
        m.agregar("papel", self.t_titular + 0.2, sfx.bolsa_evidencia(0.8, 774), -10)
        return m.x[:n]


# =========================================================================== 7.8


class Sub78(Subescena):
    """El medidor de agua inteligente; la gráfica con el pico; el patio vacío (3D); los cargos retirados."""

    cine = CINE_ARK

    def preparar(self) -> None:
        o = self.T.oraciones
        self.fondo = fondo_ark()
        self.t_grafica = o[3] - 0.3
        self.t_patio = o[4] - 0.2
        self.t_titular = o[5] - 0.3
        ini, fin = self.t_patio - CRUCE / 2, self.t_titular + CRUCE / 2
        dur = math.ceil((fin - ini + 0.25) * 2) / 2
        self.patio = Plano("e07_patio_piso", ini, fin, lambda t: DT.cam_patio(t, dur, "piso"))
        self.planos3d = [self.patio.clip]
        self.seg = Segmentos([self.t_grafica, self.t_patio, self.t_titular], CRUCE)
        self.titular = Foto("7.8_titular_cargos.jpg")

    def _medidor(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        o = self.T.oraciones
        lz = G.Lienzo()
        c = lz.c
        a = aparece(t, 0.2, 0.6)
        lz.tinta(BLANCO, a)
        G.casa(c, 300, 470, 260, 4)
        # el tubo y el agua que corre
        lz.tinta(mezcla(AZUL, BLANCO, 0.25), a)
        c.rectangle(440, 600, 1000, 38)
        c.fill()
        flujo = aparece(t, o[1], 0.6)
        lz.tinta(AZUL_CLARO, flujo)
        for k in range(16):
            x = 450 + ((k * 62 + t * 160) % 980)
            c.rectangle(x, 613, 30, 12)
        c.fill()
        lz.tinta(BLANCO, a)
        G.medidor(c, 760, 560, 170, 4)
        # la carátula gira mientras pasa agua (sin cifra)
        ang = -math.pi / 2 + (t - o[1]) * 2.2 * flujo
        lz.tinta(AZUL_CLARO, a)
        c.set_line_width(4)
        c.move_to(760, 560)
        c.line_to(760 + 52 * math.cos(ang), 560 + 52 * math.sin(ang))
        c.stroke()
        # lecturas por intervalos: casillas iguales que se van llenando (ilustración, sin valores)
        t_int = instante(self, 1, "intervalos")
        a_b = aparece(t, t_int - 0.3, 0.6)
        for k in range(8):
            vis = suave(lim((t - t_int - 0.25 * k) / 0.4))
            lz.tinta(BLANCO, a_b * 0.5)
            c.set_line_width(2)
            c.rectangle(560 + k * 52, 820, 38, 40)
            c.stroke()
            lz.tinta(AZUL_CLARO, a_b * vis)
            c.rectangle(564 + k * 52, 824, 30, 32)
            c.fill()
        # la lectura viaja a la compañía de agua
        a_r = aparece(t, o[2], 0.6)
        lz.tinta(BLANCO, a_r)
        G.antena(c, 790, 470, 100, t * 0.8, 3)
        G.edificio(c, 1540, 470, 300, 4)
        if t > o[2] + 0.5:
            for k in range(4):
                f = ((t - o[2]) * 0.6 + k / 4) % 1.0
                lz.tinta(AZUL_CLARO, a_r * math.sin(f * math.pi))
                c.arc(840 + (1360 - 840) * f, 400 - math.sin(f * math.pi) * 120, 8, 0, math.tau)
                c.fill()
        img = lz.componer(img, sombra=0.6, brillo=0.3, col_brillo=AZUL_CLARO)
        G.rotulo(img, "medidor de agua inteligente", 760, 760, 34, BLANCO, a, alinear="centro")
        G.rotulo(img, "consumo por intervalos", 760, 920, 30, mezcla(BLANCO, AZUL, 0.3), a_b, alinear="centro", nombre="Inter-Regular.ttf")
        G.rotulo(img, "compañía de agua", 1540, 720, 34, BLANCO, a_r, alinear="centro")
        G.rotulo(img, "nadie tiene que ir a leerlo", 1540, 775, 28, mezcla(BLANCO, AZUL, 0.3), aparece(t, o[2] + 1.6, 0.6),
                 alinear="centro", nombre="Inter-Regular.ttf")
        return img

    def _grafica(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        t0 = self.t_grafica - CRUCE / 2
        o = self.T.oraciones
        # Solo lo documentado: 140 galones entre la 1 y las 3 a. m. Las demás horas son una línea base
        # tenue, sin valores (no hay cifras del caso para ellas).
        horas = ["20", "21", "22", "23", "0", "1", "2", "3", "4", "5", "6", "7"]
        x0, y0, ancho, alto = 280, 830, 1360, 470
        paso = ancho / len(horas)
        lz = G.Lienzo()
        c = lz.c
        a = aparece(t, t0, 0.6)
        lz.tinta(BLANCO, a * 0.6)
        c.set_line_width(2)
        c.move_to(x0, y0)
        c.line_to(x0 + ancho, y0)
        c.stroke()
        for k in range(len(horas) + 1):
            c.move_to(x0 + k * paso, y0)
            c.line_to(x0 + k * paso, y0 + 10)
        c.stroke()
        t_pico = instante(self, 3, "140")
        crece = suave(lim((t - t_pico + 0.3) / 0.9))
        lz.tinta(ROJO, a)
        G.D.rect_redondeado(c, x0 + 5 * paso + 10, y0 - alto * crece, 2 * paso - 20, alto * crece, 8)
        c.fill()
        img = lz.componer(img, sombra=0.6, brillo=0.35, col_brillo=ROJO)
        for k, hr in enumerate(horas):
            G.rotulo(img, hr, x0 + k * paso, y0 + 52, 30, mezcla(BLANCO, AZUL, 0.25), a, alinear="centro", nombre="Inter-Regular.ttf")
        G.rotulo(img, "hora", x0 + ancho + 20, y0 + 52, 28, mezcla(BLANCO, AZUL, 0.35), a, nombre="Inter-Regular.ttf")
        a_p = aparece(t, t_pico, 0.6)
        G.rotulo(img, "140 galones", x0 + 6 * paso, y0 - alto - 40, 62, BLANCO, a_p, alinear="centro")
        G.rotulo(img, "unos 530 litros", x0 + 8.4 * paso, y0 - alto + 90, 44, mezcla(BLANCO, ROJO, 0.15), aparece(t, t_pico + 0.8, 0.6))
        G.rotulo(img, "entre la 1 y las 3 de la madrugada", x0 + 8.4 * paso, y0 - alto + 150, 34, mezcla(BLANCO, AZUL, 0.2),
                 aparece(t, t_pico + 1.4, 0.6), nombre="Inter-Regular.ttf")
        G.antetitulo(img, "Medidor de agua de la casa de Bates", x0, 190, mezcla(BLANCO, AZUL, 0.2), a, tam=28)
        del o
        return img

    def _patio(self, t: float) -> np.ndarray:
        img = self.patio.cuadro(t)
        a = aparece(t, self.t_patio + 0.6, 0.7)
        G.panel(img, 100, 860, 900, 990, a)
        G.antetitulo(img, "Para la fiscalía", 140, 912, mezcla(BLANCO, AZUL, 0.3), a)
        G.rotulo(img, "alguien había limpiado el patio", 140, 965, 40, BLANCO, a)
        return img

    def _titular(self, t: float) -> np.ndarray:
        img = G.fondo(mezcla(AZUL, NEGRO, 0.8), mezcla(AZUL, NEGRO, 0.55), semilla=12, reticula=0.0)
        G.documento(img, self.titular, t - self.t_titular + CRUCE / 2, self.d - self.t_titular + CRUCE, ancho=980,
                    z0=0.98, z1=1.12, cy0=0.4, cy1=0.62, giro=1.0)
        o = self.T.oraciones
        a = aparece(t, o[5] + 0.4, 0.6)
        G.panel(img, 0, H - 170, W, H, a, 0.5)
        G.rotulo(img, "29 de noviembre de 2017 · cargos retirados", 120, H - 80, 40, BLANCO, a)
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return componer((self._medidor, self._grafica, self._patio, self._titular), self.seg, t, oscuros=(3,))

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        o = self.T.oraciones
        m.agregar("agua", o[1] - 0.2, S.agua_tuberia(self.t_grafica - o[1] + 0.6, 781), 0, 1.0, 1.2)
        m.agregar("datos", o[2] + 0.5, sfx.datos(3.0, 782, 10.0), -12, 0.2, 0.5)
        m.agregar("noche", self.t_patio - 0.5, S.noche_fria(self.t_titular - self.t_patio + 1.5, 783), -4, 1.0, 1.0)
        m.agregar("mazo", o[5] + 0.4, S.mazo(784), 0)
        return m.x[:n]


# =========================================================================== registro

SUBESCENAS = {"7.0": Sub70, "7.1": Sub71, "7.2": Sub72, "7.3": Sub73, "7.4": Sub74, "7.5": Sub75, "7.6": Sub76,
              "7.7": Sub77, "7.8": Sub78}

# Fotogramas clave para revisar antes del render completo: (archivo, clip, tiempo en el clip)
REVISION = [
    ("1_mesa_aparatos.png", "7.0", lambda T: T.oraciones[5] + 2.9),
    ("2_puertos_jtag.png", "7.2", lambda T: T.oraciones[3] + 1.9),
    ("3_chip_off_pinzas.png", "7.4", lambda T: T.oraciones[4] + 0.1),
    ("4_echo_anillo.png", "7.7", lambda T: T.oraciones[3] + 2.6),
]


def clips() -> list[str]:
    return ["titulo"] + [s.id for s in guion.leer()[NUMERO].subescenas]


def crear(id_: str) -> Subescena:
    if id_ == "titulo":
        return titulo()
    return SUBESCENAS[id_](id_, tiempos(id_))
