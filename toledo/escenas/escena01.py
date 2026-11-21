"""Escena 1 — El testigo en el bolsillo (Friburgo, madrugada del 16 de octubre de 2016).

Animación 3D realista hecha en Blender (véase direccion_visual.md, sección 4); los planos se
construyen en `tres_d/planos.py`. Solo el mapa, los rótulos y el contador son gráficos.

1.0  Mapa de Alemania con Friburgo; el casco viejo de madrugada, vacío y mojado; María (su foto,
     sin efectos); desde la otra orilla del Dreisam, la luz de una bicicleta que avanza por la
     ciclovía a las 2:37, pasa bajo el puente y ya no sale: «María nunca llega».
1.1  La misma orilla al amanecer, gris y con neblina, cerrada con cinta de la policía y marcadores
     de evidencia; «0 testigos, 0 cámaras»; las tres pistas; un tranvía iluminado de madrugada,
     quieto en la pausa.
1.2  El costado de alguien que camina junto al río: el teléfono late con luz dentro del bolsillo
     y un contador de pasos avanza solo.

Paleta de Friburgo: verde de la Selva Negra, rojo y blanco del escudo, gris piedra, azul río.
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image

import cv2

import dibujo as D
import guion
import sfx
from escenas.base import SR, Foto, Segmentos, Subescena, TarjetaTitulo, aparece, texto, tiempos
from escenas.plano3d import Plano3D
from graficos import H, W, Luces, caja_dentro, fbm, gradiente_vertical, lim, suave, texto_alfa
from paletas import FRIBURGO, mezcla, rgb

# Motor mixto (direccion_visual.md §5): Cycles donde se nota (la calle mojada de noche refleja los
# faroles en el empedrado), Eevee donde los dos se ven casi iguales y Cycles tardaría 30 veces más.
MOTOR = {"calle_madrugada": "cycles", "tranvia_noche": "cycles",
         "dreisam_noche": "eevee", "orilla_amanecer": "eevee", "bolsillo": "eevee"}

NUMERO = 1
P = rgb(FRIBURGO)
NEGRO = np.zeros(3, np.float32)
FRIBURGO_LONLAT = (7.85, 47.99)
# El 3D ya trae su curva de color (AgX): el acabado encima es leve.
CINE = dict(sombras=mezcla(P["verde"], NEGRO, 0.45), luces=P["blanco"], mezcla=0.12, saturacion=0.95,
            contraste=0.06, halo=0.12, grano=0.012, vineta=0.32)
CRUCE = 0.9                     # fundido entre planos (s)


# =========================================================================== utilidades


def panel_esmerilado(img: np.ndarray, x0: int, y0: int, x1: int, y1: int, a: float, oscuro: float = 0.42) -> None:
    """Recuadro de vidrio esmerilado: lo de atrás se desenfoca y oscurece; borde fino de luz arriba."""
    if a <= 0:
        return
    zona = img[y0:y1, x0:x1]
    borrosa = cv2.GaussianBlur(zona, (0, 0), 16) * (1 - oscuro)
    img[y0:y1, x0:x1] = zona * (1 - a) + borrosa * a
    img[y0 : y0 + 2, x0:x1] = img[y0 : y0 + 2, x0:x1] * (1 - 0.35 * a) + P["blanco"] * 0.35 * a

# Contorno aproximado de Alemania (lon, lat), en el sentido del reloj desde Aquisgrán.
ALEMANIA = [
    (6.0, 50.75), (6.2, 51.4), (5.95, 51.85), (6.8, 52.1), (7.05, 52.25), (6.7, 52.5), (7.05, 52.65),
    (7.2, 53.25), (7.3, 53.7), (8.0, 53.7), (8.5, 53.55), (8.65, 53.9), (9.0, 54.0), (8.6, 54.4),
    (8.65, 54.9), (9.4, 54.85), (10.0, 54.6), (10.9, 54.4), (10.85, 53.95), (11.5, 54.05),
    (12.3, 54.3), (13.2, 54.6), (14.2, 53.9), (14.4, 53.3), (14.6, 52.6), (14.75, 52.1),
    (14.95, 51.4), (15.0, 51.0), (14.3, 50.9), (13.5, 50.65), (12.4, 50.3), (12.1, 50.25),
    (12.5, 49.75), (13.0, 49.3), (13.85, 48.75), (13.4, 48.35), (13.0, 47.8), (13.0, 47.47),
    (12.2, 47.6), (11.2, 47.4), (10.2, 47.3), (9.6, 47.55), (9.0, 47.7), (8.6, 47.65), (7.6, 47.58),
    (7.55, 48.0), (7.9, 48.6), (8.2, 48.98), (7.0, 49.15), (6.35, 49.45), (6.5, 49.8), (6.1, 50.1),
    (6.4, 50.3),
]
RIN = [(9.2, 47.66), (8.6, 47.62), (7.6, 47.58), (7.55, 48.0), (7.8, 48.5), (8.2, 49.0), (8.45, 49.5),
       (8.3, 49.95), (7.6, 50.05), (7.6, 50.35), (7.2, 50.75), (6.8, 51.2), (6.6, 51.8), (6.1, 51.85)]


# =========================================================================== título


def titulo() -> TarjetaTitulo:
    t = TarjetaTitulo(NUMERO, guion.leer()[NUMERO].titulo, P["rojo"], P["blanco"])
    t.cine = CINE
    return t


# =========================================================================== 1.0


class Sub10(Subescena):
    """Friburgo de noche; María; el camino junto al Dreisam; el río de noche."""

    cine = CINE

    def preparar(self) -> None:
        self.mapa = self._mapa()
        s = self.T.oraciones
        self.maria = Foto("1.0_maria_ladenburger.jpg")          # sin tinte ni efectos
        self.tarjeta = self._fondo_tarjeta()
        self.seg = Segmentos([s[1], s[2], s[4]], CRUCE)
        # el casco viejo de madrugada, de s1 a s2
        self.ini_calle = s[1] - CRUCE / 2
        self.calle = Plano3D("calle_madrugada", s[2] + CRUCE / 2 - self.ini_calle + 0.2, motor=MOTOR["calle_madrugada"])
        # el Dreisam: la bicicleta llega al puente (y = 49 m) justo antes de «María nunca llega»
        self.ini_rio = s[4] - CRUCE / 2
        llega = s[6] - 0.3 - self.ini_rio - 0.3
        vel = round((52.0 - 3.0 + 18.0) / max(4.0, llega) * 20) / 20
        self.rio = Plano3D("dreisam_noche", self.d - self.ini_rio + 0.2, motor=MOTOR["dreisam_noche"], bici_inicio=0.3, bici_vel=vel, bici_y0=-18.0)
        self.planos3d = [self.calle, self.rio]

    # ---- mapa
    def _proy(self, lon, lat):
        k = 219.0
        return (1920 + (lon - 10.45) * k * math.cos(math.radians(51)), 1080 - (lat - 51.2) * k)

    def _mapa(self) -> Image.Image:
        w, h = 3840, 2160
        fondo = gradiente_vertical([(0.0, mezcla(P["rio"], NEGRO, 0.86)), (1.0, mezcla(P["verde"], NEGRO, 0.9))], w, h)
        fondo *= (0.85 + 0.3 * fbm(h // 8, w // 8, 32, 4, 0.5, 5).repeat(8, 0).repeat(8, 1))[..., None]
        s, c = D.lienzo(w, h)
        pts = [self._proy(*q) for q in ALEMANIA]
        D.tinta(c, mezcla(P["verde"], NEGRO, 0.25))
        D.rellenar(c, pts, suave=False)
        D.tinta(c, mezcla(P["piedra"], P["blanco"], 0.3), 0.85)
        c.set_line_width(4)
        c.move_to(*pts[0])
        for q in pts[1:]:
            c.line_to(*q)
        c.close_path()
        c.stroke()
        D.tinta(c, P["rio"], 0.9)
        c.set_line_width(5)
        D.camino(c, [self._proy(*q) for q in RIN], cerrado=False)
        c.stroke()
        capa = D.a_rgba(s)
        # profundidad: el país proyecta una sombra suave sobre el fondo y su borde brilla un poco
        alfa = capa[..., 3]
        sombra = cv2.GaussianBlur(np.roll(np.roll(alfa, 28, 0), 18, 1), (0, 0), 26) * 0.65
        halo = np.clip(cv2.GaussianBlur(alfa, (0, 0), 34) - alfa, 0, 1) * 0.35
        fondo = fondo * (1 - sombra)[..., None] + halo[..., None] * P["rio"]
        img = fondo * (1 - capa[..., 3:]) + capa[..., :3]
        a = texto_alfa("ALEMANIA", "Inter-SemiBold.ttf", 120, 0.45)
        cx, cy = self._proy(10.4, 51.0)
        y0, x0 = int(cy - a.shape[0] / 2), int(cx - a.shape[1] / 2)
        img[y0 : y0 + a.shape[0], x0 : x0 + a.shape[1]] += a[..., None] * 0.10
        return Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))

    def _ver_mapa(self, t: float) -> np.ndarray:
        fx, fy = self._proy(*FRIBURGO_LONLAT)
        u = suave(lim(t / (self.m(1) + 0.8)))
        z = 1.0 + 1.4 * u
        cx, cy = 1920 + (fx - 1920) * u * 0.92, 1080 + (fy - 1080) * u * 0.92
        bw, bh = 3840 / z, 2160 / z
        # Friburgo queda muy abajo en el mapa: al final del acercamiento el encuadre se saldría unos
        # píxeles por el borde inferior; se detiene en el borde (la marca se calcula con x0, y0).
        x0 = min(max(cx - bw / 2, 0.0), 3840 - bw)
        y0 = min(max(cy - bh / 2, 0.0), 2160 - bh)
        img = np.asarray(self.mapa.resize((W, H), Image.BILINEAR, box=caja_dentro((x0, y0, x0 + bw, y0 + bh), 3840, 2160)), np.float32) / 255
        sx, sy = (fx - x0) * W / bw, (fy - y0) * H / bh
        luz = Luces()
        pulso = 0.5 + 0.5 * math.sin(t * 3.2)
        luz.punto(sx, sy, 26, P["rojo"], 0.6 + 0.4 * pulso, forma="gauss")
        img += luz.resultado()
        anillo = (t * 0.7) % 1.0
        s, c = D.lienzo(W, H)
        D.tinta(c, P["rojo"], 0.8 * (1 - anillo))
        c.set_line_width(3)
        c.arc(sx, sy, 12 + 60 * anillo, 0, math.tau)
        c.stroke()
        D.tinta(c, P["rojo"])
        c.arc(sx, sy, 9, 0, math.tau)
        c.fill()
        capa = D.a_rgba(s)
        img = img * (1 - capa[..., 3:]) + capa[..., :3]
        texto(img, "Friburgo", sx + 30, sy + 14, 44, P["blanco"], opacidad=aparece(t, 0.6, 0.8))
        return img

    # ---- María (foto quieta con acercamiento muy lento; si falta, una tarjeta sobria)
    def _fondo_tarjeta(self) -> np.ndarray:
        return gradiente_vertical([(0.0, mezcla(P["verde"], NEGRO, 0.55)), (1.0, mezcla(P["verde"], NEGRO, 0.85))])

    def _ver_maria(self, t: float) -> np.ndarray:
        img = self.tarjeta.copy()
        x0, y0, fw, fh = 300, 170, 560, 740
        if self.maria.existe and self.maria.im.width > self.maria.im.height:
            # La foto que eligió su familia es apaisada: el marco toma su forma para mostrarla
            # entera, sin recortarle la cara ni agrandarla de más.
            fw = 760
            fh = round(fw * self.maria.im.height / self.maria.im.width)
            x0, y0 = 160, (H - fh) // 2
        if self.maria.existe:
            z = 1.0 + 0.03 * lim((t - self.m(2)) / 8.0)
            im = self.maria.im
            cubre = max(fw / im.width, fh / im.height) * z
            bw, bh = fw / cubre, fh / cubre
            bx, by = (im.width - bw) / 2, (im.height - bh) * 0.3
            foto = np.asarray(im.resize((fw, fh), Image.BICUBIC, box=caja_dentro((bx, by, bx + bw, by + bh), im.width, im.height)), np.float32) / 255
            img[y0 : y0 + fh, x0 : x0 + fw] = foto
        else:
            s, c = D.lienzo(W, H)
            D.tinta(c, P["blanco"], 0.05)
            c.rectangle(x0, y0, fw, fh)
            c.fill()
            D.tinta(c, P["piedra"], 0.22)
            c.arc(x0 + fw / 2, y0 + fh * 0.40, fw * 0.17, 0, math.tau)
            c.fill()
            c.move_to(x0 + fw * 0.16, y0 + fh)
            c.curve_to(x0 + fw * 0.18, y0 + fh * 0.66, x0 + fw * 0.82, y0 + fh * 0.66, x0 + fw * 0.84, y0 + fh)
            c.close_path()
            c.fill()
            capa = D.a_rgba(s)
            img = img * (1 - capa[..., 3:]) + capa[..., :3]
        img[y0 - 2 : y0, x0 - 2 : x0 + fw + 2] = P["blanco"] * 0.5
        img[y0 + fh : y0 + fh + 2, x0 - 2 : x0 + fw + 2] = P["blanco"] * 0.5
        img[y0 : y0 + fh, x0 - 2 : x0] = P["blanco"] * 0.5
        img[y0 : y0 + fh, x0 + fw : x0 + fw + 2] = P["blanco"] * 0.5
        texto(img, "María Ladenburger", 960, 500, 66, P["blanco"], opacidad=aparece(t, self.m(2) + 0.3, 0.9), sombra=0)
        texto(img, "19 años · estudiante de medicina", 962, 570, 34, mezcla(P["piedra"], P["blanco"], 0.4),
              nombre="Inter-Regular.ttf", opacidad=aparece(t, self.m(2) + 0.9, 0.9), sombra=0)
        img[600:603, 962 : 962 + int(380 * suave(lim((t - self.m(2) - 0.5) / 1.2)))] = P["rojo"]
        return img

    # ---- planos 3D
    def _ver_calle(self, t: float) -> np.ndarray:
        img = self.calle.cuadro(t - self.ini_calle)
        texto(img, "MADRUGADA", 120, H - 200, 26, mezcla(P["piedra"], P["blanco"], 0.4), interletra=0.3,
              opacidad=aparece(t, self.m(1) + 0.3))
        texto(img, "16 de octubre de 2016", 118, H - 140, 56, P["blanco"], opacidad=aparece(t, self.m(1) + 0.5))
        return img

    def _ver_rio(self, t: float) -> np.ndarray:
        img = self.rio.cuadro(t - self.ini_rio)
        a = aparece(t, self.m(4) + 0.2, 0.7, self.m(5) - 0.2)
        texto(img, "2:37", 118, H - 150, 132, P["blanco"], nombre="Inter-Light.ttf", opacidad=a)
        texto(img, "a. m.", 404, H - 150, 40, mezcla(P["piedra"], P["blanco"], 0.4), opacidad=a)
        texto(img, "Río Dreisam", W - 120, H - 140, 40, P["blanco"], alinear="der",
              opacidad=aparece(t, self.m(5) + 0.4, 0.8, self.m(6)))
        apaga = 1 - 0.9 * suave(lim((t - self.m(6) - 0.4) / max(0.5, self.d - self.m(6) - 0.6)))
        return img * apaga

    def cuadro(self, t: float) -> np.ndarray:
        partes = (self._ver_mapa, self._ver_calle, self._ver_maria, self._ver_rio)
        img = None
        for k, peso in self.seg.pesos(t):
            capa = partes[k](t)
            img = capa * peso if img is None else img + capa * peso
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("viento", 0.0, sfx.viento(d + 0.5, 101, 0.9), 0, 1.5, 1.5)
        m.agregar("bicicleta", self.m(4) + 0.3, sfx.rueda_bici(4.5, 102), -8, 0.6, 2.0)    # lejos: en la otra orilla
        m.agregar("río", self.m(4) + 0.8, sfx.agua_rio(d - self.m(4), 103), -3, 1.5, 2.0)
        return m.x[:n]


# =========================================================================== 1.1


class Sub11(Subescena):
    """La orilla del Dreisam al amanecer; cero testigos, cero cámaras; las pistas; el tranvía."""

    cine = CINE

    def preparar(self) -> None:
        o = self.T.oraciones
        palabras = guion.subescena(self.id).oraciones[4].split()
        fin4 = self.T.pausas[0][0] if self.T.pausas else self.T.fin_voz

        def en(palabra: str) -> float:  # instante aproximado en que se dice `palabra` en la oración 4
            i = next(k for k, p in enumerate(palabras) if p.lower().startswith(palabra))
            return o[4] + (fin4 - o[4]) * i / len(palabras)

        self.t_cabello, self.t_bufanda, self.t_videos = en("cabello"), en("bufanda"), en("videos")
        corte = self.t_videos + 0.4
        self.seg = Segmentos([corte], 1.2)
        self.orilla = Plano3D("orilla_amanecer", corte + 0.6 + 0.2, motor=MOTOR["orilla_amanecer"])
        self.ini_tranvia = corte - 0.6                     # se congela en la pausa: el plano corre con `quieto`
        self.tranvia = Plano3D("tranvia_noche", self.quieto(self.d) - self.quieto(self.ini_tranvia) + 0.2, motor=MOTOR["tranvia_noche"])
        self.planos3d = [self.orilla, self.tranvia]

    def _ver_orilla(self, t: float) -> np.ndarray:
        return self.orilla.cuadro(t)

    def _ver_tranvia(self, t: float) -> np.ndarray:
        return self.tranvia.cuadro(self.quieto(t) - self.quieto(self.ini_tranvia))

    def _pistas(self, img: np.ndarray, t: float) -> None:
        """Las tres pistas que tiene la policía, con un dibujo de línea cada una."""
        items = ((self.t_cabello, "un cabello", "cabello"), (self.t_bufanda, "una bufanda", "bufanda"),
                 (self.t_videos, "cámaras de los tranvías", "camara"))
        fin = self.T.pausas[0][1] if self.T.pausas else self.d
        panel = aparece(t, self.t_cabello - 0.3, 0.6, fin - 0.4, 0.5)
        if panel <= 0:
            return
        panel_esmerilado(img, 60, 300, 780, 790, panel)
        for k, (tk, rotulo, icono) in enumerate(items):
            a = aparece(t, tk, 0.5, fin - 0.4, 0.5)
            if a <= 0:
                continue
            y = 400 + k * 140
            s, c = D.lienzo(160, 120)
            D.tinta(c, P["blanco"], 0.9)
            c.set_line_width(4)
            if icono == "cabello":
                c.move_to(20, 90)
                c.curve_to(50, 10, 90, 110, 140, 30)
                c.stroke()
            elif icono == "bufanda":
                c.move_to(30, 30)
                c.curve_to(80, 50, 110, 20, 140, 40)
                c.line_to(130, 70)
                c.curve_to(100, 50, 70, 80, 40, 60)
                c.close_path()
                c.stroke()
                c.move_to(60, 62)
                c.line_to(52, 105)
                c.move_to(78, 66)
                c.line_to(76, 108)
                c.stroke()
            else:
                D.rect_redondeado(c, 26, 38, 88, 56, 8)
                c.stroke()
                c.arc(70, 66, 17, 0, math.tau)
                c.stroke()
                c.move_to(114, 54)
                c.line_to(140, 42)
                c.line_to(140, 90)
                c.line_to(114, 78)
                c.stroke()
            capa = D.a_rgba(s)
            zona = img[y - 75 : y + 45, 110:270]
            zona *= 1 - capa[..., 3:] * a
            zona += capa[..., :3] * a
            texto(img, rotulo, 300, y, 44, P["blanco"], opacidad=a)

    def cuadro(self, t: float) -> np.ndarray:
        partes = (self._ver_orilla, self._ver_tranvia)
        img = None
        for k, peso in self.seg.pesos(t):
            capa = partes[k](t)
            img = capa * peso if img is None else img + capa * peso
        a2 = aparece(t, self.m(2) + 0.2, 0.6, self.m(4) - 0.3)
        a3 = aparece(t, self.m(3) + 0.2, 0.6, self.m(4) - 0.3)
        panel_esmerilado(img, 60, 180, 720, 360, max(a2, a3))
        texto(img, "Testigos: 0", 120, 250, 50, P["blanco"], opacidad=a2)
        texto(img, "Cámaras en la orilla: 0", 120, 320, 50, P["blanco"], opacidad=a3)
        self._pistas(img, t)
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("viento", 0.0, sfx.viento(d + 0.5, 111, 0.7), 0, 1.5, 1.5)
        m.agregar("sirena lejana", 1.2, sfx.sirena_lejana(min(14.0, d - 1.2), 112), -14, 3.0, 4.0)
        m.agregar("río", 0.0, sfx.agua_rio(d, 113, 0.6), -8, 2.0, 2.0)
        return m.x[:n]


# =========================================================================== 1.2


class Sub12(Subescena):
    """Alguien camina solo en la niebla; un contador de pasos avanza por su cuenta y late."""

    fundido_salida = 1.2
    cine = CINE

    def preparar(self) -> None:
        self.latidos = sfx.tiempos_latido(self.d, 52.0, 14, 0.4)
        r = np.random.default_rng(31)
        t, pasos = self.m(2) + 0.25, []
        while t < self.d - 0.6:
            pasos.append(t)
            t += 0.53 + r.normal(0, 0.035)
        self.pasos = np.array(pasos)
        # el que camina ya venía caminando: hacia atrás, al mismo paso que cuenta el teléfono
        antes = list(np.arange(self.pasos[0] - 0.53, 0.15, -0.53))[::-1] if len(self.pasos) else []
        todos = [round(float(x), 3) for x in antes + list(self.pasos)]
        self.bolsillo = Plano3D("bolsillo", self.d + 0.2, motor=MOTOR["bolsillo"], latidos=[round(float(x), 3) for x in self.latidos], pasos=todos)
        self.planos3d = [self.bolsillo]

    def _pulso(self, t: float) -> float:
        v = 0.0
        for tb in self.latidos:
            for dt, amp in ((0.0, 1.0), (0.28, 0.6)):
                x = t - tb - dt
                if 0 <= x < 0.7:
                    v += amp * math.exp(-x / 0.16) * (1 - math.exp(-x / 0.02))
        return min(v, 1.2)

    def cuadro(self, t: float) -> np.ndarray:
        img = self.bolsillo.cuadro(t)
        if t > self.m(2) - 0.3:
            cuenta = int(np.searchsorted(self.pasos, t, side="right"))
            a = aparece(t, self.m(2) - 0.2, 0.6)
            panel_esmerilado(img, 100, 330, 520, 640, a)
            pulso = self._pulso(t)
            s_, c = D.lienzo(W, H)                                         # el teléfono que late
            D.tinta(c, P["blanco"], a * (0.55 + 0.45 * min(pulso, 1.0)))
            c.set_line_width(3)
            D.rect_redondeado(c, 145, 372, 34, 62, 7)
            c.stroke()
            capa = D.a_rgba(s_)
            brillo = cv2.GaussianBlur(capa[..., 3], (0, 0), 10) * pulso * a
            img = img * (1 - capa[..., 3:]) + capa[..., :3] + brillo[..., None] * mezcla(P["rio"], P["blanco"], 0.5) * 0.8
            texto(img, "PASOS", 200, 418, 28, mezcla(P["piedra"], P["blanco"], 0.5), interletra=0.3, opacidad=a)
            texto(img, f"{cuenta:,}".replace(",", " "), 140, 560, 132, P["blanco"], nombre="Inter-Light.ttf", opacidad=a)
            ultimo = self.pasos[cuenta - 1] if cuenta else -9
            destello = math.exp(-(t - ultimo) / 0.12) if t >= ultimo else 0
            img[590:594, 144 : 144 + int(330 * a)] = P["rojo"] * (0.6 + 0.4 * destello)
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("latido", 0.0, sfx.latido(d, 14, tiempos=self.latidos), 0, 0.5, 1.0)
        m.agregar("pasos", 0.0, sfx.clics(list(self.pasos), d, 120), -4)
        return m.x[:n]


# =========================================================================== registro

SUBESCENAS = {"1.0": Sub10, "1.1": Sub11, "1.2": Sub12}

# Fotogramas clave para revisar antes del render completo: (archivo, clip, tiempo en el clip)
REVISION = [
    ("1_calle_madrugada.png", "1.0", lambda T: T.oraciones[1] + 1.4),
    ("2_dreisam_2_37.png", "1.0", lambda T: T.oraciones[4] + 1.6),
    ("3_orilla_testigos.png", "1.1", lambda T: T.oraciones[3] + 1.2),
    ("4_bolsillo_pasos.png", "1.2", lambda T: T.oraciones[2] + 1.5),
]


def clips() -> list[str]:
    return ["titulo"] + [s.id for s in guion.leer()[NUMERO].subescenas]


def crear(id_: str) -> Subescena:
    if id_ == "titulo":
        return titulo()
    return SUBESCENAS[id_](id_, tiempos(id_))
