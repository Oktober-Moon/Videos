"""Escena 5 — Un hombre amarrado a una silla (Ellington, Connecticut, 23 de diciembre de 2015).

5.0  Del teléfono de Friburgo a una casa llena de sensores; el mapa de Connecticut con Ellington; la
     casa de los Dabate en la mañana gris (3D), la alarma de pánico y las luces de la patrulla;
     Richard (su foto); la cocina vacía con la silla plegable tumbada y los cinchos cortados (3D);
     Connie (su foto, quieta, sin efectos ni sonidos encima).
5.1  La versión de Richard, paso a paso, sobre la casa tranquila vista desde la calle (3D); el
     intruso: una silueta borrosa a contraluz al fondo del pasillo de arriba (3D).
5.2  La escalera al sótano, vacía (3D); según Richard, «las nueve»; abajo, el resplandor de un
     soplete en las paredes. En la pausa, la imagen se queda quieta.
5.3  Lo que notan los investigadores; la solicitud del seguro de vida por 475,000 dólares (3D);
     «sospechoso no es prueba»; el teclado de la alarma: la casa lo había registrado (3D).

La violencia nunca se muestra: solo la casa vacía, luces y sombras. Connie Dabate no se hace como
personaje 3D. Paleta de Connecticut (`paletas.CONNECTICUT`).
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image

import cv2

import dibujo as D
import guion
import sfx
from escenas import dabate_e05 as K
from escenas import diagramas as DG
from escenas.base import SR, Foto, Segmentos, Subescena, TarjetaTitulo, aparece, texto, tiempos
from escenas.plano3d import Plano3D
from graficos import H, W, Luces, caja_dentro, fbm, gradiente_vertical, lim, suave, texto_alfa
from paletas import mezcla

NUMERO = 5
MOTOR = {"e05_casa_manana": "eevee", "e05_casa_calle": "eevee", "e05_cocina_silla": "eevee",
         "e05_intruso": "eevee", "e05_escalera_sotano": "eevee", "e05_documento": "eevee",
         "e05_teclado_alarma": "eevee"}
P = K.P
CINE = K.CINE
CRUCE = K.CRUCE


def momento(T, id_: str, k: int, palabra: str, fin: float | None = None) -> float:
    """Instante aproximado en que se dice `palabra` dentro de la oración k (por número de palabras)."""
    palabras = guion.subescena(id_).oraciones[k].split()
    i = next((j for j, p in enumerate(palabras) if p.lower().strip("«»,.:;").startswith(palabra)), 0)
    a = T.oraciones[k]
    b = fin if fin is not None else (T.oraciones[k + 1] if k + 1 < len(T.oraciones) else T.fin_voz)
    return a + (b - a) * i / max(1, len(palabras))


def mezclar(partes, pesos, t):
    img = None
    for k, peso in pesos:
        capa = partes[k](t)
        img = capa * peso if img is None else img + capa * peso
    return img


# =========================================================================== título


def titulo() -> TarjetaTitulo:
    t = TarjetaTitulo(NUMERO, guion.leer()[NUMERO].titulo, P["rojo_patrulla"], K.CLARO)
    t.cine = CINE
    return t


# =========================================================================== mapa de Connecticut

# Contorno aproximado de Connecticut (lon, lat), en el sentido del reloj desde la esquina noroeste.
CONNECTICUT = [
    (-73.487, 42.049), (-73.05, 42.04), (-72.81, 42.036), (-72.81, 42.0), (-72.76, 42.0), (-72.755, 42.035),
    (-72.53, 42.032), (-72.1, 42.028), (-71.80, 42.023), (-71.797, 41.73), (-71.79, 41.52), (-71.84, 41.40),
    (-71.86, 41.32), (-71.95, 41.33), (-72.06, 41.31), (-72.10, 41.33), (-72.20, 41.30), (-72.35, 41.27),
    (-72.45, 41.27), (-72.53, 41.26), (-72.68, 41.25), (-72.82, 41.26), (-72.92, 41.27), (-73.03, 41.21),
    (-73.12, 41.16), (-73.19, 41.15), (-73.30, 41.12), (-73.40, 41.08), (-73.54, 41.04), (-73.62, 41.00),
    (-73.657, 40.985), (-73.727, 41.10), (-73.48, 41.21), (-73.55, 41.29), (-73.52, 41.66),
]
RIO_CONNECTICUT = [(-72.60, 42.03), (-72.63, 41.93), (-72.66, 41.765), (-72.65, 41.71), (-72.645, 41.56),
                   (-72.55, 41.50), (-72.50, 41.45), (-72.42, 41.36), (-72.35, 41.28)]
# El estrecho de Long Island (desde la costa de Rhode Island y Connecticut hacia el sur) y Long Island.
MAR = [(-70.5, 41.47), (-71.12, 41.47), (-71.45, 41.38), (-71.86, 41.32)] +       CONNECTICUT[13:31] + [(-73.78, 40.88), (-74.0, 40.75), (-74.6, 40.5), (-74.6, 39.6), (-70.5, 39.6)]
LONG_ISLAND = [(-74.05, 40.58), (-73.78, 40.80), (-73.6, 40.90), (-73.4, 40.91), (-73.1, 40.93), (-72.85, 40.96),
               (-72.6, 40.98), (-72.4, 41.05), (-72.25, 41.12), (-72.05, 41.09), (-71.86, 41.07), (-72.0, 40.98),
               (-72.4, 40.85), (-72.8, 40.75), (-73.2, 40.65), (-73.6, 40.58)]
ELLINGTON = (-72.47, 41.904)
HARTFORD = (-72.68, 41.765)


class MapaConnecticut:
    """Connecticut en un lienzo grande (4K) que la cámara recorre acercándose a Ellington: el estado
    en relieve sobre los vecinos (Nueva York, Massachusetts, Rhode Island), el estrecho de Long
    Island al sur y el río Connecticut."""

    def __init__(self):
        self.k = 1500.0
        self.img = self._dibujar()

    def proy(self, lon, lat):
        return (1920 + (lon + 72.75) * self.k * math.cos(math.radians(41.5)), 1080 - (lat - 41.55) * self.k)

    def _poligono(self, c, puntos):
        pts = [self.proy(*q) for q in puntos]
        c.move_to(*pts[0])
        for q in pts[1:]:
            c.line_to(*q)
        c.close_path()
        return pts

    def _dibujar(self) -> Image.Image:
        w, h = 3840, 2160
        tierra = mezcla(P["azul"], K.NEGRO, 0.86)
        mar = mezcla(P["azul"], K.NEGRO, 0.70)
        fondo = np.broadcast_to(tierra, (h, w, 3)).copy()
        fondo *= (0.86 + 0.28 * fbm(h // 8, w // 8, 32, 4, 0.5, 51).repeat(8, 0).repeat(8, 1))[..., None]
        s, c = D.lienzo(w, h)
        D.tinta(c, mar)
        self._poligono(c, MAR)
        c.fill()
        D.tinta(c, tierra * 1.05)
        self._poligono(c, LONG_ISLAND)
        c.fill()
        capa = D.a_rgba(s)
        fondo = fondo * (1 - capa[..., 3:]) + capa[..., :3]
        s, c = D.lienzo(w, h)
        D.tinta(c, mezcla(P["azul"], P["beige"], 0.22))
        self._poligono(c, CONNECTICUT)
        c.fill()
        D.tinta(c, mezcla(P["beige"], K.NEGRO, 0.1), 0.85)
        c.set_line_width(5)
        self._poligono(c, CONNECTICUT)
        c.stroke()
        D.tinta(c, mezcla(P["azul_patrulla"], np.ones(3), 0.3), 0.85)
        c.set_line_width(6)
        D.camino(c, [self.proy(*q) for q in RIO_CONNECTICUT], cerrado=False)
        c.stroke()
        capa = D.a_rgba(s)
        alfa = capa[..., 3]
        sombra = cv2.GaussianBlur(np.roll(np.roll(alfa, 30, 0), 20, 1), (0, 0), 28) * 0.6
        halo = np.clip(cv2.GaussianBlur(alfa, (0, 0), 36) - alfa, 0, 1) * 0.3
        fondo = fondo * (1 - sombra)[..., None] + halo[..., None] * P["azul_patrulla"]
        img = fondo * (1 - capa[..., 3:]) + capa[..., :3]

        def rotulo(cadena, lon, lat, tam, fuerza, interletra=0.3):
            a = texto_alfa(cadena, "Inter-SemiBold.ttf", tam, interletra)
            cx, cy = self.proy(lon, lat)
            y0, x0 = int(cy - a.shape[0] / 2), int(cx - a.shape[1] / 2)
            y1, x1 = min(h, y0 + a.shape[0]), min(w, x0 + a.shape[1])
            img[max(0, y0):y1, max(0, x0):x1] += a[max(0, -y0):y1 - y0, max(0, -x0):x1 - x0, None] * fuerza * P["beige"]
        rotulo("CONNECTICUT", -72.72, 41.56, 104, 0.12)
        rotulo("MASSACHUSETTS", -72.3, 42.16, 46, 0.22)
        rotulo("NUEVA YORK", -73.98, 41.62, 46, 0.22)
        rotulo("RHODE ISLAND", -71.58, 41.72, 40, 0.22)
        rotulo("Long Island Sound", -72.85, 41.08, 40, 0.18, 0.05)
        return Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))

    def ver(self, t: float, u: float) -> np.ndarray:
        """`u` (0..1): de todo el estado a un acercamiento sobre Ellington."""
        fx, fy = self.proy(*ELLINGTON)
        z = 1.0 + 0.9 * u
        cx, cy = 1920 + (fx - 1920) * u * 0.7, 1080 + (fy - 1080) * u * 0.7
        bw, bh = 3840 / z, 2160 / z
        x0, y0 = cx - bw / 2, cy - bh / 2
        img = np.asarray(self.img.resize((W, H), Image.BILINEAR, box=caja_dentro((x0, y0, x0 + bw, y0 + bh), self.img.width, self.img.height)), np.float32) / 255

        def pant(lon, lat):
            px, py = self.proy(lon, lat)
            return (px - x0) * W / bw, (py - y0) * H / bh
        hx, hy = pant(*HARTFORD)
        sx, sy = pant(*ELLINGTON)
        luz = Luces()
        pulso = 0.5 + 0.5 * math.sin(t * 3.2)
        luz.punto(sx, sy, 26, P["rojo_patrulla"], 0.6 + 0.4 * pulso, forma="gauss")
        img += luz.resultado()
        s, c = D.lienzo(W, H)
        anillo = (t * 0.7) % 1.0
        D.tinta(c, P["rojo_patrulla"], 0.8 * (1 - anillo))
        c.set_line_width(3)
        c.arc(sx, sy, 12 + 60 * anillo, 0, math.tau)
        c.stroke()
        D.tinta(c, K.ROJO)
        c.arc(sx, sy, 9, 0, math.tau)
        c.fill()
        D.tinta(c, K.BEIGE, 0.7)
        c.arc(hx, hy, 5, 0, math.tau)
        c.fill()
        capa = D.a_rgba(s)
        img = img * (1 - capa[..., 3:]) + capa[..., :3]
        texto(img, "Ellington", sx + 30, sy + 14, 48, K.CLARO, opacidad=aparece(t, 0.5, 0.8))
        texto(img, "Hartford", hx - 18, hy + 10, 30, K.TENUE, alinear="der", nombre="Inter-Regular.ttf",
              opacidad=aparece(t, 0.9, 0.8))
        return img


# =========================================================================== 5.0


class Sub50(Subescena):
    """Del teléfono a la casa; Connecticut; la casa en la mañana; la alarma; Richard; la cocina; Connie."""

    cine = CINE

    def preparar(self) -> None:
        s = self.T.oraciones
        self.seg = Segmentos([s[2], s[4], s[6], s[7]], CRUCE)
        self.fondo = K.fondo()
        self.casa = K.CasaDiagrama((960, 610), 1.0)
        n = len(K.CasaDiagrama.SENSORES)
        a, b = s[1] + 1.0, s[2] - 0.6
        self.t_sensores = {nom: a + (b - a) * k / max(1, n - 1) for k, nom in enumerate(K.CasaDiagrama.SENSORES)}
        self.mapa = MapaConnecticut()
        self.ini_casa = s[4] - CRUCE / 2
        self.t_alarma = momento(self.T, self.id, 4, "alarma")
        self.t_patrulla = s[5] + 0.4
        self.t_richard = momento(self.T, self.id, 5, "encuentra") + 0.5
        self.exterior = Plano3D("e05_casa_manana", s[6] + CRUCE / 2 - self.ini_casa + 0.2, motor=MOTOR["e05_casa_manana"],
                                t_patrulla=round(self.t_patrulla - self.ini_casa, 2))
        self.ini_cocina = s[6] - CRUCE / 2
        self.cocina = Plano3D("e05_cocina_silla", s[7] + CRUCE / 2 - self.ini_cocina + 0.2, motor=MOTOR["e05_cocina_silla"])
        self.planos3d = [self.exterior, self.cocina]
        self.richard = Foto("5.0_richard_dabate.jpg")
        self.connie = Foto("5.0_connie_dabate.jpg")                       # sin tinte ni efectos
        self.tarjeta = gradiente_vertical([(0.0, mezcla(P["azul"], K.NEGRO, 0.70)), (1.0, mezcla(P["azul"], K.NEGRO, 0.9))])

    # ---- del teléfono a la casa
    def _ver_sensores(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        s = self.T.oraciones
        L = K.Lienzo()
        c = L.c
        # el teléfono de Friburgo, con su sensor que late
        a_tel = aparece(t, 0.2, 0.8) * (1 - suave(lim((t - s[1] - 0.2) / 1.0)))
        if a_tel > 0:
            esc = 1.0 - 0.25 * suave(lim((t - s[1]) / 1.2))
            L.tinta(K.CLARO, a_tel)
            DG.telefono(c, 960, 540, 470 * esc, 4)
            L.tinta(K.REG, a_tel)
            DG.chip(c, 960, 600, 70 * esc, 2.5, 5)
            u = (t * 0.9) % 1.0
            L.tinta(K.REG, a_tel * (1 - u) * 0.8)
            c.set_line_width(3)
            c.new_sub_path()
            c.arc(960, 600, 40 + 120 * u, 0, math.tau)
            c.stroke()
            L.texto("un teléfono", 960, 880, 40, K.CLARO, a_tel * aparece(t, 0.8, 0.8), "centro")
            L.texto("sensores que nadie mira", 960, 930, 28, K.TENUE, a_tel * aparece(t, 1.4, 0.8), "centro", "Inter-Regular.ttf")
        # la casa entera, que se traza y se llena de sensores
        p = suave(lim((t - s[1] + 0.1) / 2.4))
        self.casa.dibujar(L, p, K.BEIGE, 1.0)
        for nom, ti in self.t_sensores.items():
            self.casa.sensor(L, nom, t, ti, K.ROJO if nom in ("puerta_cochera", "puerta_principal") else K.REG)
        for nom, ic, d in (("panel", "escudo", 0.0), ("laptop", "laptop", 0.4), ("modem", "modem", 0.8), ("telefono", "telefono", 1.2)):
            self.casa.aparato(L, nom, ic, aparece(t, s[1] + 1.4 + d, 0.6), K.CLARO, 34)
        L.texto("una casa llena de sensores", 960, 1000, 40, K.CLARO, aparece(t, s[1] + 1.6, 0.8), "centro")
        return L.componer(img, 0.4, 0.45)

    # ---- mapa y fecha
    def _ver_mapa(self, t: float) -> np.ndarray:
        s = self.T.oraciones
        u = suave(lim((t - s[2] + 0.4) / (s[4] - s[2] + 0.4)))
        img = self.mapa.ver(t - s[2] + 0.5, u)
        a = aparece(t, s[2] + 0.2, 0.7)
        texto(img, "ESTADOS UNIDOS", 120, 150, 28, K.TENUE, interletra=0.3, opacidad=a)
        b = aparece(t, s[3] + 0.1, 0.7)
        K.panel_esmerilado(img, 80, H - 300, 860, H - 90, b)
        texto(img, "23 de diciembre de 2015", 120, H - 190, 58, K.CLARO, opacidad=b)
        texto(img, "dos días antes de Navidad", 122, H - 130, 32, K.BEIGE, nombre="Inter-Regular.ttf",
              opacidad=aparece(t, momento(self.T, self.id, 3, "dos"), 0.7))
        return img

    # ---- la casa en la mañana, la alarma, la patrulla y Richard
    def _ver_exterior(self, t: float) -> np.ndarray:
        s = self.T.oraciones
        img = self.exterior.cuadro(t - self.ini_casa)        # la patrulla y sus destellos están en el 3D
        a = aparece(t, s[4] - 0.2, 0.7, s[5] + 0.6)
        texto(img, "ELLINGTON, CONNECTICUT", 120, H - 200, 26, K.BEIGE, interletra=0.3, opacidad=a)
        texto(img, "La casa de los Dabate", 118, H - 140, 52, K.CLARO, opacidad=a)
        texto(img, "recreación", W - 110, H - 70, 22, K.TENUE, alinear="der", nombre="Inter-Regular.ttf", opacidad=a)
        al = aparece(t, self.t_alarma - 0.1, 0.4, s[5] + 0.4)
        if al > 0:
            K.panel_esmerilado(img, W - 640, 120, W - 110, 330, al)
            pulso = 0.6 + 0.4 * (0.5 + 0.5 * math.cos((t - self.t_alarma) * math.tau * 1.6))
            L = K.Lienzo()
            L.tinta(K.ROJO, al * pulso)
            L.c.new_sub_path()
            L.c.arc(W - 590, 196, 13, 0, math.tau)
            L.c.fill()
            L.texto("ALARMA DE PÁNICO", W - 560, 208, 34, K.CLARO, al, nombre="Inter-SemiBold.ttf", interletra=0.06)
            L.texto("poco después de las 10 a. m.", W - 590, 282, 36, K.CLARO, al, nombre="Inter-Light.ttf")
            img = L.componer(img, 0.6, 0.0, 12)
        r = aparece(t, self.t_richard, 0.8)          # cuando la patrulla ya se detuvo junto a la cochera
        if r > 0 and self.richard.existe:
            x0, y0, fw, fh = 1290, 150, 520, 660
            K.sombra_marco(img, x0, y0, fw, fh, r)
            K.foto_en_marco(img, self.richard, x0, y0, fw, fh, 1.25 + 0.05 * lim((t - s[5]) / 8), 0.415, 0.42, a=r)
            K.panel_esmerilado(img, x0, y0 + fh + 18, x0 + fw, y0 + fh + 150, r)
            texto(img, "Richard Dabate", x0 + 30, y0 + fh + 82, 46, K.CLARO, opacidad=r)
            texto(img, "el esposo", x0 + 32, y0 + fh + 126, 28, K.BEIGE, nombre="Inter-Regular.ttf", opacidad=r)
        return img

    # ---- la cocina vacía
    def _ver_cocina(self, t: float) -> np.ndarray:
        s = self.T.oraciones
        img = self.cocina.cuadro(t - self.ini_cocina)
        a = aparece(t, s[6] + 0.4, 0.8, s[7] - 0.4)
        texto(img, "LA COCINA", 120, H - 200, 26, K.BEIGE, interletra=0.3, opacidad=a)
        texto(img, "una silla plegable y cinchos de plástico", 118, H - 140, 44, K.CLARO, opacidad=a)
        return img

    # ---- Connie: su foto, quieta, con un acercamiento muy lento
    def _ver_connie(self, t: float) -> np.ndarray:
        s = self.T.oraciones
        img = self.tarjeta.copy()
        fh = 760
        fw = round(fh * self.connie.w / self.connie.h) if self.connie.existe else 470
        x0, y0 = 300, (H - fh) // 2
        if self.connie.existe:
            K.sombra_marco(img, x0, y0, fw, fh, 1.0)
            K.foto_en_marco(img, self.connie, x0, y0, fw, fh, 1.0 + 0.03 * lim((t - s[7]) / 9.0), 0.5, 0.45)
        texto(img, "Connie Dabate", 960, 500, 68, K.CLARO, opacidad=aparece(t, s[7] + 0.5, 0.9), sombra=0)
        texto(img, "su esposa", 962, 570, 34, K.BEIGE, nombre="Inter-Regular.ttf", opacidad=aparece(t, s[7] + 1.1, 0.9), sombra=0)
        img[600:603, 962 : 962 + int(380 * suave(lim((t - s[7] - 0.7) / 1.2)))] = K.BEIGE
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return mezclar((self._ver_sensores, self._ver_mapa, self._ver_exterior, self._ver_cocina, self._ver_connie),
                       self.seg.pesos(t), t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        s = self.T.oraciones
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(s[2] + 1.0, 501), -6, 1.0, 1.0)
        pips = sorted(self.t_sensores.values())
        m.agregar("sensores", 0.0, sfx.tics(pips, s[2] + 0.5, 502), -10)
        m.agregar("afuera", s[4] - 0.5, K.manana_afuera(s[6] - s[4] + 1.5, 503), -2, 1.0, 1.0)
        m.agregar("alarma", self.t_alarma, K.alarma_casa(3.2, 504, lejos=0.7), -8, 0.05, 1.2)
        m.agregar("sirena", s[5] - 2.0, K.sirena_americana(s[6] - s[5] + 2.6, 505), -6, 1.0, 1.2)
        m.agregar("cocina", s[6] - 0.4, K.cuarto(s[7] - s[6] + 0.9, 506), -6, 0.8, 0.9)
        return m.x[:n]                                                        # con Connie: silencio


# =========================================================================== 5.1


class Sub51(Subescena):
    """La versión de Richard sobre la casa tranquila; el intruso al fondo del pasillo."""

    cine = CINE

    def preparar(self) -> None:
        s = self.T.oraciones
        corte = s[4] - 0.1
        self.seg = Segmentos([corte], 1.0)
        self.calle = Plano3D("e05_casa_calle", corte + 0.5 + 0.2, motor=MOTOR["e05_casa_calle"])
        self.ini_intruso = corte - 0.5
        self.intruso = Plano3D("e05_intruso", self.d - self.ini_intruso + 0.2, motor=MOTOR["e05_intruso"])
        self.planos3d = [self.calle, self.intruso]
        m = lambda k, p: momento(self.T, self.id, k, p)   # noqa: E731
        self.pasos = [(m(1, "dejó") + 0.2, "autobus", "deja a sus hijos en la parada"),
                      (m(1, "salió"), "auto", "sale hacia el trabajo"),
                      (m(2, "alerta") - 0.3, "campana", "una alerta de la alarma"),
                      (m(3, "le"), "sobre", "manda un correo a su jefe"),
                      (m(3, "regresó"), "casa", "regresa a casa"),
                      (s[4] - 0.6, "silueta", "arriba, un intruso")]
        self.t_masc = m(4, "máscara")
        self.t_voz = m(4, "voz")
        self.t_grande = m(4, "grande")

    def _panel(self, img, t, a):
        if a <= 0:
            return img
        x0, y0, x1 = 90, 150, 780
        alto = 150 + 98 * sum(1 for tk, *_ in self.pasos if t > tk - 0.3)
        K.panel_esmerilado(img, x0, y0, x1, y0 + alto, a, 0.5)
        L = K.Lienzo()
        L.texto("LA VERSIÓN DE RICHARD", x0 + 40, y0 + 70, 30, K.CLARO, a, interletra=0.12)
        L.texto("lo que contó a la policía", x0 + 40, y0 + 110, 26, K.TENUE, a, nombre="Inter-Regular.ttf")
        ultimo = None
        for k, (tk, ic, rot) in enumerate(self.pasos):
            b = aparece(t, tk, 0.5) * a
            if b <= 0:
                continue
            y = y0 + 190 + k * 98
            K.caja_suave(L, x0 + 34, y - 40, 76, 76, b, K.BEIGE, K.OSCURO, 14, punteada=True, grosor=2)
            L.tinta(K.CLARO, b)
            K.icono(L.c, ic, x0 + 72, y - 2, 40, 2.5)
            L.texto(rot, x0 + 138, y + 10, 34, K.CLARO, b, nombre="Inter-Regular.ttf")
            if ultimo is not None:
                K.punteada(L, [(x0 + 72, ultimo + 40), (x0 + 72, y - 42)], K.BEIGE, 0.6 * b, 2, (5, 6))
            ultimo = y
        return L.componer(img, 0.25, 0.3)

    def _ver_calle(self, t: float) -> np.ndarray:
        img = self.calle.cuadro(t)
        return self._panel(img, t, aparece(t, self.m(0) + 0.2, 0.7))

    def _ver_intruso(self, t: float) -> np.ndarray:
        img = self.intruso.cuadro(t - self.ini_intruso)
        L = K.Lienzo()
        a = aparece(t, self.m(4) + 0.3, 0.7)
        K.caja_suave(L, 90, 120, 360, 64, a * 0.9, K.BEIGE, K.OSCURO, 10, punteada=True, grosor=2)
        L.texto("SEGÚN RICHARD", 120, 164, 28, K.CLARO, a, interletra=0.14)
        for k, (tk, rot) in enumerate(((self.t_grande, "un hombre grande"), (self.t_masc, "máscara y traje de camuflaje"),
                                       (self.t_voz, "voz «como la de Vin Diesel»"))):
            L.texto(rot, 120, H - 230 + k * 62, 40 if k == 0 else 34, K.CLARO if k == 0 else K.BEIGE,
                    aparece(t, tk, 0.7), nombre="Inter-SemiBold.ttf" if k == 0 else "Inter-Regular.ttf")
        return L.componer(img, 0.2, 0.0)

    def cuadro(self, t: float) -> np.ndarray:
        return mezclar((self._ver_calle, self._ver_intruso), self.seg.pesos(t), t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        corte = self.m(4)
        m.agregar("afuera", 0.0, K.manana_afuera(corte + 1.0, 511), -2, 1.0, 1.0)
        for k, (tk, *_r) in enumerate(self.pasos):
            m.agregar(f"paso{k}", tk, K.clic_mouse(512 + k), -16)
        m.agregar("grave", corte - 0.8, K.tono_grave(d - corte + 0.8, 513), 0, 1.5, 1.2)
        return m.x[:n]


# =========================================================================== 5.2


class Sub52(Subescena):
    """La escalera al sótano, vacía; las nueve según Richard; el resplandor del soplete; pausa quieta."""

    cine = CINE
    fundido_salida = 1.0

    def quieto(self, t: float) -> float:
        """El «(pausa)» del guion va al final: ahí la imagen se queda quieta. (La narración generada
        recorta el silencio final y el detector de pausas se queda con una coma de la última oración;
        por eso la pausa se toma desde que termina la voz.)"""
        return min(t, self.T.fin_voz)

    def preparar(self) -> None:
        # el resplandor dura lo que la última oración y se apaga al terminar: queda la escalera vacía, quieta
        self.t_soplete = momento(self.T, self.id, 2, "soplete") + 0.1
        self.t_fin = max(self.t_soplete + 2.0, self.T.fin_voz - 1.3)
        self.escalera = Plano3D("e05_escalera_sotano", self.quieto(self.d) + 0.2, motor=MOTOR["e05_escalera_sotano"],
                                t_soplete=round(self.quieto(self.t_soplete), 2), t_fin=round(self.quieto(self.t_fin), 2))
        self.planos3d = [self.escalera]
        self.t_nueve = momento(self.T, self.id, 1, "nueve")

    def cuadro(self, t: float) -> np.ndarray:
        s = self.T.oraciones
        img = self.escalera.cuadro(self.quieto(t))
        L = K.Lienzo()
        a = aparece(t, 0.4, 0.7)
        K.caja_suave(L, 90, 120, 360, 64, a * 0.9, K.BEIGE, K.OSCURO, 10, punteada=True, grosor=2)
        L.texto("SEGÚN RICHARD", 120, 164, 28, K.CLARO, a, interletra=0.14)
        L.texto("Connie vuelve del gimnasio", 120, H - 160, 40, K.CLARO, aparece(t, s[0] + 0.3, 0.7, s[1] + 0.2))
        b = aparece(t, self.t_nueve - 0.2, 0.7)
        L.texto("el sótano", 120, H - 230, 30, K.BEIGE, aparece(t, s[1] + 0.8, 0.7, self.t_nueve - 0.3),
                nombre="Inter-Regular.ttf")
        L.texto("≈ 9:00", 120, H - 140, 120, K.CLARO, b, nombre="Inter-Light.ttf")
        L.texto("a. m., según Richard", 560, H - 140, 34, K.BEIGE, b, nombre="Inter-Regular.ttf")
        return L.componer(img, 0.2, 0.0)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("cuarto", 0.0, K.cuarto(d, 521), -4, 1.0, 1.5)
        m.agregar("grave", 0.5, K.tono_grave(d - 0.5, 522), -3, 2.0, 2.0)
        m.agregar("soplete", self.t_soplete - 0.2, K.soplete(min(5.0, self.t_fin - self.t_soplete + 0.8), 523), -10, 0.0, 0.8)
        return m.x[:n]


# =========================================================================== 5.3


class Sub53(Subescena):
    """Lo que notan los investigadores; el seguro de vida; sospechoso no es prueba; el teclado de la alarma."""

    cine = CINE

    def preparar(self) -> None:
        s = self.T.oraciones
        self.seg = Segmentos([s[6], s[7], s[9]], CRUCE)
        self.fondo = K.fondo()
        self.ini_doc = s[6] - CRUCE / 2
        self.doc = Plano3D("e05_documento", s[7] + CRUCE / 2 - self.ini_doc + 0.2, motor=MOTOR["e05_documento"])
        self.ini_tec = s[9] - CRUCE / 2
        self.teclado = Plano3D("e05_teclado_alarma", self.d - self.ini_tec + 0.2, motor=MOTOR["e05_teclado_alarma"])
        self.planos3d = [self.doc, self.teclado]
        m = lambda k, p: momento(self.T, self.id, k, p)   # noqa: E731
        self.items = [(s[1] + 0.2, "Heridas que no lo incapacitaban", "quizá hechas por él mismo"),
                      (s[2] + 0.1, "Problemas de dinero", None),
                      (m(3, "amante"), "Una amante embarazada: Sarah Ganzer", "unas diez semanas"),
                      (s[4] + 0.2, "primero: «una madre sustituta»", "sub"),
                      (s[5] + 0.2, "después: «una amiga de la preparatoria»", "sub"),
                      (s[7] - 0.1, "Un seguro de vida: 475,000 dólares", "cinco días después")]

    def _ver_lista(self, t: float) -> np.ndarray:
        s = self.T.oraciones
        img = self.fondo.copy()
        L = K.Lienzo()
        a = aparece(t, 0.2, 0.7)
        L.texto("LO QUE NOTAN LOS INVESTIGADORES", 200, 170, 30, K.BEIGE, a, interletra=0.12)
        L.tinta(K.BEIGE, 0.5 * a)
        DG.linea(L.c, [(200, 196), (200 + 900 * suave(lim((t - 0.4) / 1.2)), 196)], 1.0, 2)
        sosp = aparece(t, s[7] + 0.1, 0.6)
        prueba = aparece(t, s[8] + 0.1, 0.8)
        # se proyecta en un salón: el texto va siempre en blanco y apenas se atenúa; la sospecha la dice
        # el color de las viñetas, no el de las letras
        y = 300
        for k, (tk, rot, sub) in enumerate(self.items):
            b = aparece(t, tk, 0.5) * (1 - 0.2 * prueba)
            es_sub = sub == "sub"
            if b > 0:
                x = 290 if es_sub else 200
                if es_sub:
                    L.tinta(K.BEIGE, b)
                    DG.linea(L.c, [(x - 40, y - 12), (x - 16, y - 12)], 1.0, 2)
                else:
                    L.tinta(mezcla(K.BEIGE, K.ROJO, sosp), b)
                    L.c.new_sub_path()
                    L.c.arc(x + 8, y - 13, 7 + 2 * sosp, 0, math.tau)
                    L.c.fill()
                L.texto(rot, x + 40 if not es_sub else x, y, 40 if not es_sub else 32, K.CLARO if not es_sub else K.BEIGE,
                        b, nombre="Inter-SemiBold.ttf" if not es_sub else "Inter-Regular.ttf")
                if sub and not es_sub:
                    L.texto(sub, x + 40, y + 42, 28, K.BEIGE, b * 0.9, nombre="Inter-Regular.ttf")
            y += (66 if es_sub else (104 if sub else 82))
        L.texto("sospechoso", 1430, 560, 64, K.CLARO, prueba, "centro", "Inter-Light.ttf")
        L.texto("no es prueba", 1430, 640, 64, K.CLARO, prueba, "centro", "Inter-SemiBold.ttf")
        L.tinta(K.ROJO, prueba)
        DG.linea(L.c, [(1250, 680), (1250 + 360 * suave(lim((t - s[8] - 0.4) / 1.0)), 680)], 1.0, 3)
        return L.componer(img, 0.3, 0.35)

    def _ver_doc(self, t: float) -> np.ndarray:
        s = self.T.oraciones
        img = self.doc.cuadro(t - self.ini_doc)
        a = aparece(t, s[6] + 0.3, 0.7)
        texto(img, "CINCO DÍAS DESPUÉS", 120, H - 200, 26, K.BEIGE, interletra=0.3, opacidad=a)
        texto(img, "Richard pide cobrar el seguro de vida", 118, H - 140, 46, K.CLARO, opacidad=a)
        return img

    def _ver_teclado(self, t: float) -> np.ndarray:
        s = self.T.oraciones
        img = self.teclado.cuadro(t - self.ini_tec)
        a = aparece(t, s[9] + 1.0, 0.8)
        texto(img, "minuto a minuto", 120, H - 140, 52, K.CLARO, opacidad=a)
        b = aparece(t, s[10] + 0.1, 0.8)
        texto(img, "la casa lo había registrado", 120, H - 80, 34, K.BEIGE, nombre="Inter-Regular.ttf", opacidad=b)
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return mezclar((self._ver_lista, self._ver_doc, self._ver_lista, self._ver_teclado), self.seg.pesos(t), t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        s = self.T.oraciones
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(s[9] + 0.5, 531), -8, 1.5, 1.0)
        m.agregar("marcas", 0.0, sfx.tics([tk for tk, *_ in self.items], s[9], 532), -12)
        m.agregar("papel", s[6] - 0.2, K.papel(1.4, 533), -4)
        m.agregar("cuarto", s[9] - 0.4, K.cuarto(d - s[9] + 0.4, 534), -6, 0.8, 1.0)
        for k in range(3):
            m.agregar(f"pitido{k}", s[10] + 0.2 + 0.18 * k, K.pitido(2900, 0.07), -10)
        return m.x[:n]


# =========================================================================== registro

SUBESCENAS = {"5.0": Sub50, "5.1": Sub51, "5.2": Sub52, "5.3": Sub53}

# Fotogramas clave para revisar antes del render completo: (archivo, clip, tiempo en el clip)
REVISION = [
    ("1_casa_patrulla.png", "5.0", lambda T: T.oraciones[5] + 3.38),
    ("2_intruso.png", "5.1", lambda T: T.oraciones[4] + 3.0),
    ("3_escalera_soplete.png", "5.2", lambda T: T.oraciones[3] + 1.0),
    ("4_seguro_de_vida.png", "5.3", lambda T: T.oraciones[6] + 2.5),
]


def clips() -> list[str]:
    return ["titulo"] + [s.id for s in guion.leer()[NUMERO].subescenas]


def crear(id_: str) -> Subescena:
    if id_ == "titulo":
        return titulo()
    return SUBESCENAS[id_](id_, tiempos(id_))
