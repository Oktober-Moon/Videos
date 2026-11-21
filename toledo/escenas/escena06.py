"""Escena 6 — La casa declara (caso Dabate: lo que registraron los aparatos de la casa).

6.0  La dirección IP: la casa, su módem y su número; los servicios que lo anotan; la orden
     judicial; la compañía de internet que dice a qué domicilio pertenecía.
6.1  Línea de tiempo del correo: lo que dijo Richard (desde la carretera) contra lo que registró la
     computadora de la casa (9:01, 9:04, 9:18, 9:20).
6.2  La alarma: panel y sensores; un contacto magnético real (foto); imán e interruptor; la puerta
     que se abre (3D); el panel que anota el cambio y lo manda a la central.
6.3  Línea de tiempo de la alarma y de Facebook: nada antes de las 9:23; pánico a las 10:11; las
     llamadas al 911; los videos de las 9:40 a 9:46, cuando según Richard Connie ya estaba muerta.
6.4  El Fitbit One (3D y la foto real); por dentro, acelerómetro y altímetro; memoria, Bluetooth,
     la app y los servidores de Fitbit.
6.5  La gráfica de la mañana: salida a las 8:46, regreso a las 9:23, 1,217 pies hasta las 10:05
     contra 125 pies del garaje al sótano; la línea de las nueve que dio Richard.
6.6  Todos los aparatos en la misma línea: la historia del intruso ya no cabe; la orden de arresto
     (2017), el veredicto y la sentencia (2022); «el asesinato del Fitbit».

Las líneas de tiempo son el corazón de la escena: arriba, punteado, lo que dijo Richard; abajo, en
líneas firmes, lo que registró cada aparato. Paleta de Connecticut (`paletas.CONNECTICUT`).
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image

import dibujo as D
import guion
import sfx
from escenas import dabate_e05 as K
from escenas import diagramas as DG
from escenas.base import SR, Foto, Segmentos, Subescena, TarjetaTitulo, aparece, recorrido, texto, tiempos
from escenas.escena05 import mezclar, momento
from escenas.plano3d import Plano3D
from graficos import H, W, caja_dentro, gradiente_vertical, lim, suave
from paletas import mezcla

NUMERO = 6
MOTOR = {"e06_modem": "eevee", "e06_sensor_puerta": "eevee", "e06_fitbit_mesa": "eevee"}
P = K.P
CINE = K.CINE
CRUCE = K.CRUCE
IP = "203.0.113.24"            # dirección de ejemplo (rango reservado para documentación): no es la real


def titulo() -> TarjetaTitulo:
    t = TarjetaTitulo(NUMERO, guion.leer()[NUMERO].titulo, P["azul_patrulla"], K.CLARO)
    t.cine = CINE
    return t


def viaje(c, pts, u, col, a, r=7.0):
    """Un paquete de datos (punto con estela) que recorre la polilínea `pts` según `u` (0..1)."""
    if a <= 0 or u <= 0 or u >= 1:
        return
    pts = [np.asarray(p, float) for p in pts]
    largos = [np.linalg.norm(b - p) for p, b in zip(pts, pts[1:])]
    total = sum(largos)
    for k, (dv, aa) in enumerate(((0.0, 1.0), (0.025, 0.5), (0.05, 0.25))):
        falta = max(0.0, u - dv) * total
        q = pts[0]
        for p0, p1, l in zip(pts, pts[1:], largos):
            if falta <= l:
                q = p0 + (p1 - p0) * falta / max(l, 1e-9)
                break
            falta -= l
            q = p1
        D.tinta(c, col, a * aa)
        c.new_sub_path()
        c.arc(q[0], q[1], r * (1 - 0.25 * k), 0, math.tau)
        c.fill()


# =========================================================================== 6.0


class Sub60(Subescena):
    """La dirección IP: de la casa al módem, del módem a los servicios, y de vuelta a un domicilio."""

    cine = CINE

    def preparar(self) -> None:
        self.fondo = K.fondo()
        self.casa = K.CasaDiagrama((540, 640), 0.6)
        m = lambda k, p: momento(self.T, self.id, k, p)   # noqa: E731
        o = self.T.oraciones
        self.t_ip = m(0, "dirección")
        self.t_num = m(1, "número")
        self.t_postal = m(1, "dirección")
        self.t_aparatos = o[2] + 0.2
        self.t_modem = m(2, "módem")
        self.t_mismo = m(2, "usan")
        self.t_servicios = [m(3, "correo"), m(3, "facebook"), m(3, "banco")]
        self.t_anota = m(3, "anota")
        self.t_orden = m(4, "orden")
        self.t_lista = m(4, "lista")
        self.t_compania = m(5, "compañía")
        self.t_domicilio = m(5, "domicilio")
        self.t_amarra = o[6] + 0.3
        self.nube = (1060, 600)
        self.isp = (1060, 905)
        self.poli = (1060, 235)
        self.tarjetas = [("correo", "sobre", 205), ("Facebook", "video", 445), ("banco", "escudo", 685)]
        # primero, el módem real de la casa (3D); después, el diagrama
        self.corte = o[1] - 0.1
        self.seg = Segmentos([self.corte], CRUCE)
        self.modem = Plano3D("e06_modem", self.corte + CRUCE / 2 + 0.2, motor=MOTOR["e06_modem"])
        self.planos3d = [self.modem]

    def _ver_modem(self, t: float) -> np.ndarray:
        img = self.modem.cuadro(t)
        a = aparece(t, 0.6, 0.8)
        texto(img, "EL MÓDEM DE LA CASA", 120, H - 200, 26, K.BEIGE, interletra=0.3, opacidad=a)
        texto(img, "la dirección IP", 118, H - 140, 56, K.CLARO, opacidad=aparece(t, self.t_ip, 0.7))
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return mezclar((self._ver_modem, self._ver_diagrama), self.seg.pesos(t), t)

    def _ver_diagrama(self, t: float) -> np.ndarray:
        o = self.T.oraciones
        img = self.fondo.copy()
        L = K.Lienzo()
        c = L.c
        a0 = aparece(t, self.corte - 0.5, 0.8)
        L.texto("LA DIRECCIÓN IP", 110, 140, 34, K.CLARO, a0, interletra=0.12)
        L.texto("el número de una casa en internet", 112, 182, 26, K.TENUE, a0, nombre="Inter-Regular.ttf")
        # la casa
        self.casa.dibujar(L, suave(lim((t - self.corte + 0.3) / 2.2)), K.BEIGE, a0)
        mx, my = self.casa.p("modem")
        self.casa.aparato(L, "modem", "modem", aparece(t, self.t_aparatos - 0.4, 0.6), K.CLARO, 46)
        aparatos = (("laptop", "laptop"), ("telefono", "telefono"), ("tableta", "telefono"))
        for k, (nom, ic) in enumerate(aparatos):
            self.casa.aparato(L, nom, ic, aparece(t, self.t_aparatos + 0.3 * k, 0.5), K.CLARO, 38)
        # la compañía de internet y el número que le da a la casa
        b = aparece(t, o[1] + 0.1, 0.6)
        L.tinta(K.CLARO, b)
        K.icono(c, "edificio", *self.isp, 80, 3)
        L.texto("compañía de internet", self.isp[0], self.isp[1] + 80, 26, K.BEIGE, b, "centro", "Inter-Regular.ttf")
        techo = self.casa.p((880, 300))
        u = suave(lim((t - self.t_num) / 1.6))
        if t > self.t_num:
            tx = self.isp[0] + (techo[0] - self.isp[0]) * u
            ty = self.isp[1] - 60 + (techo[1] - 70 - self.isp[1] + 60) * u - 120 * math.sin(math.pi * u)
            K.caja_suave(L, tx - 150, ty - 34, 300, 60, aparece(t, self.t_num, 0.4), K.REG, K.OSCURO, 12)
            L.texto(f"IP  {IP}", tx, ty + 8, 28, K.CLARO, aparece(t, self.t_num, 0.4), "centro")
            L.texto("número de ejemplo", tx, ty + 56, 20, K.TENUE, aparece(t, self.t_num + 1.2, 0.5), "centro",
                    "Inter-Regular.ttf")
        L.texto("como una dirección postal", techo[0], techo[1] - 128, 24, K.TENUE, aparece(t, self.t_postal, 0.6),
                "centro", "Inter-Regular.ttf")
        # todos los aparatos salen por el mismo módem con el mismo número
        cc = aparece(t, self.t_modem - 0.2, 0.6)
        if cc > 0:
            for k, (nom, _) in enumerate(aparatos):
                px, py = self.casa.p(nom)
                L.tinta(K.REG, 0.7 * cc)
                DG.linea(c, [(px, py + 18), (px, my - 4), (mx - 10, my - 4)] if nom != "tableta" else
                         [(px, py + 24), (px, my - 30), (mx - 20, my - 14)], 1.0, 2)
            salida = [(mx + 30, my), (self.casa.p((1170, 742))[0], my), (self.nube[0] - 80, self.nube[1] + 10)]
            L.tinta(K.REG, cc)
            DG.linea(c, salida, suave(lim((t - self.t_modem) / 1.0)), 3)
            for k in range(3):
                u = ((t - self.t_modem) * 0.45 + k / 3) % 1.0
                viaje(c, salida, u, K.REG, cc)
            L.tinta(K.CLARO, cc)
            K.icono(c, "nube", *self.nube, 110, 3)
            L.texto("internet", self.nube[0], self.nube[1] + 92, 26, K.BEIGE, cc, "centro", "Inter-Regular.ttf")
            d = aparece(t, self.t_mismo, 0.5)
            L.texto(IP, (salida[1][0] + salida[2][0]) / 2, my + 44, 24, K.REG, d, "centro")
        # los servicios en línea, que anotan el número
        for k, ((nombre, ic, y), ts) in enumerate(zip(self.tarjetas, self.t_servicios)):
            e = aparece(t, ts, 0.5)
            if e <= 0:
                continue
            x0 = 1300
            resalta = aparece(t, self.t_lista, 0.4) if k == 0 else 0.0
            K.caja_suave(L, x0, y - 85, 520, 190, e, mezcla(K.REG, K.CLARO, resalta * 0.5), K.OSCURO, 14)
            L.tinta(K.CLARO, e)
            K.icono(c, ic, x0 + 52, y - 42, 42, 2.5)
            L.texto(nombre, x0 + 100, y - 28, 32, K.CLARO, e)
            L.tinta(K.REG, 0.5 * e)
            DG.linea(c, [(self.nube[0] + 70, self.nube[1]), (x0 - 6, y)], suave(lim((t - ts) / 0.6)), 2)
            f = aparece(t, self.t_anota + 0.25 * k, 0.5)
            # el registro de cada servicio: la hora (sin cifras, la narración aquí no da ninguna) y el número
            que = ("correo enviado", "video publicado", "inicio de sesión")[k]
            yy = y + 22
            L.tinta(K.CLARO, f * (1 - 0.6 * (k > 0) * aparece(t, self.t_orden, 0.6)))
            K.icono(c, "reloj", x0 + 58, yy - 9, 30, 2.5)
            L.texto("hora", x0 + 84, yy, 22, K.CLARO, f * (1 - 0.6 * (k > 0) * aparece(t, self.t_orden, 0.6)),
                    nombre="Inter-Regular.ttf")
            L.texto(f"{IP}   {que}", x0 + 150, yy, 22, K.TENUE, f, nombre="Inter-Regular.ttf")
        # la policía, con una orden judicial, pide la lista
        g = aparece(t, self.t_orden - 0.3, 0.5)
        if g > 0:
            L.tinta(K.CLARO, g)
            K.icono(c, "escudo", *self.poli, 70, 3)
            L.texto("policía", self.poli[0], self.poli[1] + 70, 26, K.BEIGE, g, "centro", "Inter-Regular.ttf")
            camino = [(self.poli[0] + 50, self.poli[1] - 10), (1290, 140)]
            u = suave(lim((t - self.t_orden) / 1.2))
            if 0 < u < 1:
                x = camino[0][0] + (camino[1][0] - camino[0][0]) * u
                y = camino[0][1] + (camino[1][1] - camino[0][1]) * u
                L.tinta(K.CLARO, g)
                K.icono(c, "documento", x, y, 50, 2.5)
            L.texto("orden judicial", self.poli[0] + 120, self.poli[1] - 70, 24, K.BEIGE,
                    aparece(t, self.t_orden, 0.5, self.t_compania), "centro", "Inter-Regular.ttf")
            v = suave(lim((t - self.t_lista) / 1.2))
            if 0 < v < 1:
                L.tinta(K.REG, g)
                K.icono(c, "documento", 1290 + (self.poli[0] + 60 - 1290) * v, 140 + (self.poli[1] - 140) * v, 50, 2.5)
        # la compañía de internet dice a qué domicilio pertenecía el número
        h = aparece(t, self.t_compania, 0.5)
        if h > 0:
            L.tinta(K.BEIGE, 0.7 * h)
            c.set_dash([8, 8])
            DG.linea(c, [(self.poli[0] + 40, self.poli[1] + 90), (1215, 420), (1215, 790), (self.isp[0] + 50, self.isp[1] - 50)],
                     suave(lim((t - self.t_compania) / 1.0)), 2)
            c.set_dash([])
        dom = aparece(t, self.t_domicilio, 0.6)
        if dom > 0:
            puerta = self.casa.p((1235, 772))
            L.tinta(K.ROJO, dom)
            DG.flecha(c, (self.isp[0] - 60, self.isp[1] - 10), (puerta[0] + 6, puerta[1] + 10),
                      suave(lim((t - self.t_domicilio) / 1.0)), 3, 16, curva=-40)
            L.texto("este domicilio", (self.isp[0] + puerta[0]) / 2 - 10, self.isp[1] + 34, 26, K.ROJO, dom, "centro")
        # la acción en internet queda amarrada a la casa
        am = aparece(t, self.t_amarra, 0.8)
        if am > 0:
            pulso = 0.75 + 0.25 * math.sin((t - self.t_amarra) * 4.0)
            L.tinta(K.ROJO, am * pulso)
            DG.linea(c, [(1340, 227), (1200, 260), self.casa.p((1100, 520)), self.casa.p((880, 640))],
                     suave(lim((t - self.t_amarra) / 1.2)), 4)
        return L.componer(img, 0.4, 0.45)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        o = self.T.oraciones
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(d, 601), -6, 1.5, 1.5)
        m.agregar("parpadeo", 0.3, sfx.datos(self.corte, 609, 6), -16, 0.5, 0.8)
        m.agregar("módem", self.t_modem, sfx.datos(o[3] - self.t_modem + 0.5, 602, 10), -12, 0.5, 1.0)
        for k, ts in enumerate(self.t_servicios):
            m.agregar(f"servicio{k}", ts, K.notificacion(603 + k), -10)
        m.agregar("orden", self.t_orden, K.papel(1.0, 606), -6)
        m.agregar("lista", self.t_lista, K.papel(0.8, 607), -8)
        m.agregar("domicilio", self.t_domicilio, K.clic_mouse(608), -8)
        return m.x[:n]


# =========================================================================== 6.1


class Sub61(Subescena):
    """El correo: lo que dijo Richard contra lo que registró la computadora de la casa."""

    cine = CINE

    def preparar(self) -> None:
        self.fondo = K.fondo()
        self.lt = K.LineaTiempo("8:55", "9:25", filas={"richard": 330, "computadora": 650}, eje=880)
        o = self.T.oraciones
        self.marcas = [(o[2] + 0.3, "9:01"), (o[3] + 0.3, "9:04"), (o[4] + 0.3, "9:18"), (o[5] + 0.5, "9:20")]
        self.t_choque = momento(self.T, self.id, 3, "desde")

    def cuadro(self, t: float) -> np.ndarray:
        o = self.T.oraciones
        img = self.fondo.copy()
        lt = self.lt
        L = K.Lienzo()
        c = L.c
        a = aparece(t, 0.2, 0.8)
        L.texto("EL CORREO AL JEFE", 110, 140, 30, K.CLARO, a, interletra=0.12)
        L.texto("23 de diciembre de 2015", 112, 180, 24, K.TENUE, a, nombre="Inter-Regular.ttf")
        lt.eje(L, a, paso=5, arriba=230)
        # lo que dijo Richard
        lt.fila(L, "richard", aparece(t, o[0] + 0.2, 0.6), punteada_=True, p=lim((t - o[0]) / 1.0))
        r = aparece(t, momento(self.T, self.id, 0, "carretera") - 0.3, 0.6)
        lt.marca(L, "richard", "9:04", r, "el correo, desde la carretera", "con su teléfono", K.BEIGE, arriba=True,
                 ic="auto", punteada_=True, hora=False, alto=10)
        # lo que registró la computadora
        lt.fila(L, "computadora", aparece(t, o[1] + 0.1, 0.6), p=lim((t - o[1]) / 1.0))
        rot = {"9:01": ("inicio de sesión", "", True, "laptop"), "9:04": ("correo al jefe", "desde la IP de la casa", False, "sobre"),
               "9:18": ("horario de clases del YMCA", "", True, None), "9:20": ("página de ESPN", "", False, None)}
        for tk, h in self.marcas:
            rotulo, det, arriba, ic = rot[h]
            lt.marca(L, "computadora", h, aparece(t, tk, 0.5), rotulo, det, K.REG, arriba=arriba, ic=ic,
                     alto=40 if h == "9:18" else 0)
        # el choque: misma hora, otro lugar
        ch = aparece(t, self.t_choque, 0.6)
        if ch > 0:
            x = lt.x("9:04")
            L.tinta(K.ROJO, ch)
            c.set_dash([6, 6])
            DG.linea(c, [(x, lt.y("richard") + 14), (x, lt.y("computadora") - 14)], suave(lim((t - self.t_choque) / 0.8)), 3)
            c.set_dash([])
            ym = (lt.y("richard") + lt.y("computadora")) / 2
            c.new_sub_path()
            c.arc(x, ym, 24, 0, math.tau)
            D.tinta(c, K.OSCURO, ch)
            c.fill_preserve()
            L.tinta(K.ROJO, ch)
            c.set_line_width(3)
            c.stroke()
            DG.cruz(c, x, ym, 18, 3.5)
            L.texto("el correo salió de la casa", x + 44, ym + 10, 28, K.ROJO, ch)
        return L.componer(img, 0.4, 0.45)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(d, 611), -8, 1.5, 1.5)
        for k, (tk, _) in enumerate(self.marcas):
            m.agregar(f"clic{k}", tk, K.clic_mouse(612 + k), -2)
        m.agregar("teclado", self.marcas[0][0] + 0.2, sfx.teclado(1.4, 616, 0.8), -12, 0.1, 0.4)
        m.agregar("choque", self.t_choque, sfx.error_suave(617), -8)
        return m.x[:n]


# =========================================================================== 6.2


class Sub62(Subescena):
    """La alarma: panel y sensores; un contacto real; imán e interruptor; la puerta que se abre."""

    cine = CINE

    def preparar(self) -> None:
        o = self.T.oraciones
        self.fondo = K.fondo()
        self.casa = K.CasaDiagrama((900, 610), 0.95)
        self.casa_b = K.CasaDiagrama((700, 620), 0.8)
        self.c_foto = o[2] + 0.42 * (o[3] - o[2])
        self.seg = Segmentos([o[2], self.c_foto, o[3] - 0.2, o[4]], CRUCE)
        self.foto = Foto("6.2_sensor_puerta.jpg")
        self.ini_3d = o[3] - 0.2 - CRUCE / 2
        self.t_abre = o[3] + 0.6
        self.puerta = Plano3D("e06_sensor_puerta", o[4] + CRUCE / 2 - self.ini_3d + 0.2, motor=MOTOR["e06_sensor_puerta"],
                              t_abre=round(self.t_abre - self.ini_3d, 2))
        self.planos3d = [self.puerta]
        n = len(K.CasaDiagrama.SENSORES)
        a, b = momento(self.T, self.id, 1, "sensores"), o[2] - 0.5
        self.t_sens = {nom: a + (b - a) * k / max(1, n - 1) for k, nom in enumerate(K.CasaDiagrama.SENSORES)}
        self.t_panel = momento(self.T, self.id, 1, "panel")
        self.t_iman = momento(self.T, self.id, 2, "imán")
        self.t_interruptor = momento(self.T, self.id, 2, "interruptor", fin=None)
        self.t_anota = momento(self.T, self.id, 4, "anota")
        self.t_central = momento(self.T, self.id, 4, "manda")

    # ---- panel y sensores
    def _ver_sistema(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        L = K.Lienzo()
        a = aparece(t, 0.2, 0.7)
        L.texto("LA ALARMA", 110, 140, 34, K.CLARO, a, interletra=0.12)
        self.casa.dibujar(L, suave(lim((t - 0.2) / 2.0)), K.BEIGE, a)
        pa = aparece(t, self.t_panel, 0.5)
        self.casa.aparato(L, "panel", "escudo", pa, K.ROJO, 44)
        px, py = self.casa.p("panel")
        L.texto("panel central", px, py + 62, 26, K.CLARO, pa, "centro")
        for nom, ti in self.t_sens.items():
            self.casa.sensor(L, nom, t, ti, K.REG)
            u = suave(lim((t - ti - 0.2) / 0.8))
            if u > 0:
                sx, sy = self.casa.p(nom)
                L.tinta(K.REG, 0.35 * u)
                L.c.set_dash([4, 6])
                DG.linea(L.c, [(sx, sy), (px, py)], u, 1.5)
                L.c.set_dash([])
        L.texto("sensores en puertas y ventanas", 960, 1000, 34, K.CLARO, aparece(t, min(self.t_sens.values()) + 0.4, 0.6), "centro")
        return L.componer(img, 0.4, 0.45)

    # ---- un contacto magnético real
    def _ver_foto(self, t: float) -> np.ndarray:
        o = self.T.oraciones
        z, cx, cy = recorrido(t - o[2] + CRUCE, self.c_foto - o[2] + 2 * CRUCE, 1.02, 1.12, (0.5, 0.5), (0.55, 0.52))
        img = self.foto.ver(z, cx, cy) if self.foto.existe else self.fondo.copy()
        K.panel_esmerilado(img, 80, H - 230, 900, H - 80, aparece(t, o[2] + 0.2, 0.6))
        texto(img, "contacto magnético", 120, H - 150, 52, K.CLARO, opacidad=aparece(t, o[2] + 0.3, 0.6))
        texto(img, "un sensor de puerta común", 122, H - 100, 30, K.BEIGE, nombre="Inter-Regular.ttf",
              opacidad=aparece(t, o[2] + 0.6, 0.6))
        return img

    # ---- imán e interruptor (diagrama de frente)
    def _contacto(self, L: K.Lienzo, t: float, abre: float, a: float, x_marco=1160, y0=330, escala=1.0):
        """Puerta y marco de frente: el imán en la puerta, el interruptor (un contacto de lengüetas) en el
        marco. `abre` (0..1) aleja la puerta y abre las lengüetas."""
        c = L.c
        dx = -260 * suave(abre)
        # marco
        L.tinta(K.BEIGE, 0.9 * a)
        c.set_line_width(3)
        c.rectangle(x_marco, y0 - 120, 110, 720)
        c.stroke()
        # puerta
        L.tinta(K.BEIGE, 0.6 * a)
        c.rectangle(x_marco - 560 + dx, y0 - 120, 548, 720)
        c.stroke()
        # imán en la puerta y sus líneas de campo
        ix0, iy0 = x_marco - 70 + dx, y0
        K.caja_suave(L, ix0, iy0, 50, 130, a, K.ROJO, K.OSCURO, 10)
        L.texto("N", ix0 + 25, iy0 + 45, 24, K.ROJO, a, "centro")
        L.texto("S", ix0 + 25, iy0 + 110, 24, K.ROJO, a, "centro")
        campo = (1 - suave(abre)) * a
        for k in range(3):
            r = 60 + 30 * k
            L.tinta(K.ROJO, 0.35 * campo)
            c.new_sub_path()
            c.arc(ix0 + 50, iy0 + 65, r, -math.pi / 2.6, math.pi / 2.6)
            c.stroke()
        # interruptor en el marco: cápsula con dos lengüetas
        sx0, sy0 = x_marco + 20, y0 - 20
        K.caja_suave(L, sx0, sy0, 70, 170, a, K.REG, K.OSCURO, 12)
        L.tinta(K.CLARO, 0.6 * a)
        c.set_line_width(2)
        D.rect_redondeado(c, sx0 + 22, sy0 + 25, 26, 120, 12)
        c.stroke()
        L.tinta(K.CLARO, a)
        c.set_line_width(4)
        c.move_to(sx0 + 35, sy0 + 30)
        c.line_to(sx0 + 35, sy0 + 82)
        c.stroke()
        sep = 10 * suave(abre)
        c.move_to(sx0 + 35, sy0 + 140)
        c.line_to(sx0 + 35 + sep * 0.2, sy0 + 88 + sep)
        c.stroke()
        # rótulos
        L.texto("imán", ix0 - 30, iy0 + 72, 36, K.CLARO, a * aparece(t, self.t_iman, 0.5), "der")
        L.texto("en la puerta", ix0 - 30, iy0 + 110, 26, K.BEIGE, a * aparece(t, self.t_iman, 0.5), "der", "Inter-Regular.ttf")
        L.texto("interruptor", sx0 + 100, sy0 + 82, 36, K.CLARO, a * aparece(t, self.t_interruptor, 0.5))
        L.texto("en el marco", sx0 + 100, sy0 + 120, 26, K.BEIGE, a * aparece(t, self.t_interruptor, 0.5), nombre="Inter-Regular.ttf")
        estado = "abierto" if abre > 0.5 else "cerrado"
        L.texto(f"circuito {estado}", sx0 + 100, sy0 + 190, 28, K.ROJO if abre > 0.5 else K.REG, a)

    def _ver_contacto(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        L = K.Lienzo()
        self._contacto(L, t, 0.0, aparece(t, self.c_foto - 0.2, 0.6))
        return L.componer(img, 0.35, 0.45)

    # ---- la puerta que se abre (3D) con el contacto en un recuadro
    def _ver_puerta(self, t: float) -> np.ndarray:
        o = self.T.oraciones
        img = self.puerta.cuadro(t - self.ini_3d)
        a = aparece(t, o[3] + 0.2, 0.5)
        abre = suave(lim((t - self.t_abre) / 1.6))
        K.panel_esmerilado(img, W - 560, 90, W - 90, 380, a, 0.55)
        L = K.Lienzo()
        c = L.c
        x0, y0 = W - 470, 150
        L.texto("el interruptor", x0 - 20, y0 - 10, 26, K.BEIGE, a, nombre="Inter-Regular.ttf")
        L.tinta(K.CLARO, 0.7 * a)
        c.set_line_width(2)
        D.rect_redondeado(c, x0, y0 + 40, 300, 60, 30)
        c.stroke()
        L.tinta(K.CLARO, a)
        c.set_line_width(5)
        c.move_to(x0 + 20, y0 + 70)
        c.line_to(x0 + 150, y0 + 70)
        c.stroke()
        c.move_to(x0 + 280, y0 + 70)
        ang = math.radians(9) * abre
        c.line_to(x0 + 280 - 128 * math.cos(ang), y0 + 70 - 128 * math.sin(ang))
        c.stroke()
        col = K.ROJO if abre > 0.5 else K.REG
        L.texto("circuito abierto" if abre > 0.5 else "circuito cerrado", x0 - 20, y0 + 180, 34, col, a)
        L.tinta(col, a)
        c.new_sub_path()
        c.arc(x0 + 285, y0 + 168, 10, 0, math.tau)
        c.fill()
        return L.componer(img, 0.4, 0.0)

    # ---- el panel anota y avisa a la central
    def _ver_central(self, t: float) -> np.ndarray:
        o = self.T.oraciones
        img = self.fondo.copy()
        L = K.Lienzo()
        c = L.c
        a = aparece(t, o[4] - 0.3, 0.6)
        casa = self.casa_b
        casa.dibujar(L, 1.0, K.BEIGE, a)
        casa.aparato(L, "panel", "escudo", a, K.ROJO, 40)
        casa.sensor(L, "puerta_cochera", t, o[4] - 0.3, K.ROJO, a)
        sx, sy = casa.p("puerta_cochera")
        px, py = casa.p("panel")
        u = suave(lim((t - self.t_anota + 0.6) / 0.9))
        if 0 < u:
            L.tinta(K.ROJO, a)
            DG.linea(c, [(sx, sy), (px, py)], u, 2)
        b = aparece(t, self.t_anota, 0.5)
        tx, ty = 930, 250
        L.tinta(K.ROJO, 0.7 * b)
        DG.linea(c, [(px + 8, py - 30), (tx + 40, ty + 104)], suave(lim((t - self.t_anota) / 0.6)), 2)
        K.caja_suave(L, tx, ty, 380, 104, b, K.ROJO, K.OSCURO, 12)
        L.tinta(K.CLARO, b)
        K.icono(c, "reloj", tx + 40, ty + 52, 36, 2.5)
        L.texto("puerta abierta", tx + 78, ty + 48, 30, K.CLARO, b)
        L.texto("con su hora exacta", tx + 78, ty + 84, 24, K.BEIGE, b, nombre="Inter-Regular.ttf")
        cen = (1620, 420)
        e = aparece(t, self.t_central - 0.2, 0.5)
        L.tinta(K.CLARO, e)
        K.icono(c, "edificio", *cen, 110, 3)
        L.texto("central de la", cen[0], cen[1] + 100, 28, K.CLARO, e, "centro")
        L.texto("empresa de seguridad", cen[0], cen[1] + 136, 28, K.CLARO, e, "centro")
        ruta = [(px + 30, py), (casa.p((1420, 668))[0], py), (cen[0] - 80, cen[1] + 10)]
        L.tinta(K.REG, 0.8 * e)
        DG.linea(c, ruta, suave(lim((t - self.t_central) / 0.9)), 3)
        for k in range(2):
            viaje(c, ruta, ((t - self.t_central - 0.5) * 0.6 + k * 0.5) % 1.0 if t > self.t_central + 0.5 else 0, K.REG, e)
        return L.componer(img, 0.4, 0.45)

    def cuadro(self, t: float) -> np.ndarray:
        return mezclar((self._ver_sistema, self._ver_foto, self._ver_contacto, self._ver_puerta, self._ver_central),
                       self.seg.pesos(t), t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(d, 621), -10, 1.5, 1.5)
        m.agregar("panel", self.t_panel, K.pitido(2900, 0.08), -10)
        m.agregar("sensores", 0.0, sfx.tics(sorted(self.t_sens.values()), d, 622), -14)
        m.agregar("cuarto", self.ini_3d, K.cuarto(self.T.oraciones[4] - self.ini_3d + 1.0, 623), -8, 0.6, 0.8)
        m.agregar("clic", self.t_abre + 0.15, K.clic_magnetico(624), 0)
        for k in range(2):
            m.agregar(f"pitido{k}", self.t_anota + 0.15 * k, K.pitido(2700, 0.07), -8)
        m.agregar("datos", self.t_central + 0.4, sfx.datos(1.6, 625, 14), -12, 0.1, 0.5)
        return m.x[:n]


# =========================================================================== 6.3


class Sub63(Subescena):
    """La alarma y Facebook contra la versión de Richard."""

    cine = CINE

    def preparar(self) -> None:
        o = self.T.oraciones
        self.fondo = K.fondo()
        self.lt = K.LineaTiempo("8:30", "10:30", filas={"richard": 250, "alarma": 470, "facebook": 745}, eje=915)
        m = lambda k, p: momento(self.T, self.id, k, p)   # noqa: E731
        self.t_alerta = m(0, "alerta")
        self.t_nada = m(1, "ninguna")
        self.t_923 = m(2, "9:23")
        self.t_1011 = o[3] + 0.3
        self.t_1016 = o[4] + 0.3
        self.t_1020 = o[5] + 0.3
        self.t_fb = o[6] + 0.1
        self.t_videos = m(7, "videos")
        self.t_mensaje = m(7, "mensaje")
        self.t_muerta = o[8] + 0.2
        self.t_45 = m(8, "45")

    def cuadro(self, t: float) -> np.ndarray:
        o = self.T.oraciones
        img = self.fondo.copy()
        lt = self.lt
        L = K.Lienzo()
        c = L.c
        a = aparece(t, 0.2, 0.8)
        L.texto("LA ALARMA Y FACEBOOK", 110, 96, 30, K.CLARO, a, interletra=0.12)
        lt.eje(L, a, paso=30, arriba=200)
        # lo que dijo Richard
        lt.fila(L, "richard", a, punteada_=True)
        # la alerta que, según él, lo hizo regresar: no tiene hora en ningún registro, así que se marca
        # como un tramo punteado sobre la misma ventana en la que la alarma no anotó nada
        al = aparece(t, self.t_alerta - 0.2, 0.5)
        if al > 0:
            xa, xb, yr = lt.x("8:30"), lt.x("9:23"), lt.y("richard")
            K.punteada(L, [(xa, yr - 18), (xa, yr - 32), (xb, yr - 32), (xb, yr - 18)], K.BEIGE, al, 2.0, (6, 6))
            L.tinta(K.BEIGE, al)
            K.icono(c, "campana", xa + 22, yr - 60, 30, 2.5)
            L.texto("una alerta lo hizo regresar", xa + 50, yr - 50, 26, K.CLARO, al, "izq", "Inter-Regular.ttf")
        # la alarma: nada hasta las 9:23
        lt.fila(L, "alarma", aparece(t, o[1] + 0.1, 0.6))
        n = aparece(t, self.t_nada - 0.2, 0.6)
        lt.tramo(L, "alarma", "8:30", "9:23", n, K.TENUE, 24, rayado=True, p=suave(lim((t - self.t_nada + 0.2) / 1.2)))
        L.texto("ninguna actividad", (lt.x("8:30") + lt.x("9:23")) / 2, lt.y("alarma") - 26, 26, K.BEIGE, n, "centro",
                "Inter-Regular.ttf")
        lt.marca(L, "alarma", "9:23", aparece(t, self.t_923, 0.5), "puerta del garaje", "Connie vuelve del gimnasio",
                 K.REG, arriba=False, ic="puerta")
        lt.marca(L, "alarma", "10:11", aparece(t, self.t_1011, 0.5), "alarma de pánico", "desde el llavero de Richard",
                 K.ROJO, arriba=True, ic="llavero")
        # la llamada de Richard: el guion dice «cuatro minutos después», no una hora
        eventos = [("10:16", "la empresa llama al 911")] + \
            ([("10:20", "Richard llama al 911", "+4 min")] if t > self.t_1020 else [])
        lt.grupo(L, "alarma", eventos, aparece(t, self.t_1016, 0.5) * (1 if t > self.t_1016 else 0), K.REG, arriba=False,
                 alto=4, ancla=1505)
        # Facebook
        f = aparece(t, self.t_fb, 0.6)
        lt.fila(L, "facebook", f)
        v = aparece(t, self.t_videos - 0.3, 0.5)
        lt.tramo(L, "facebook", "9:40", "9:46", v, K.REG, 30, p=suave(lim((t - self.t_videos + 0.3) / 0.8)))
        xm = (lt.x("9:40") + lt.x("9:46")) / 2
        y = lt.y("facebook")
        if v > 0:
            L.tinta(K.REG, v)
            K.icono(c, "video", xm - 26, y - 46, 34, 2.5)
            L.tinta(K.REG, v * aparece(t, self.t_mensaje, 0.4))
            K.icono(c, "mensaje", xm + 26, y - 46, 34, 2.5)
            L.texto("9:40 – 9:46", xm, y + 56, 30, K.CLARO, v, "centro")
            L.texto("videos y un mensaje, desde la casa", xm, y + 92, 26, K.REG, v, "centro", "Inter-Regular.ttf")
        # según Richard, Connie ya estaba muerta
        mu = aparece(t, self.t_muerta, 0.6)
        if mu > 0:
            lt.tramo(L, "richard", "9:00", "9:46", mu * 0.8, K.ROJO, 18, rayado=True, punteada_=True,
                     p=suave(lim((t - self.t_muerta) / 1.0)))
            lt.marca(L, "richard", "9:00", mu, "Connie ya había muerto", "según Richard", K.ROJO, arriba=False,
                     punteada_=True, alto=6)
            q = aparece(t, self.t_45 - 0.3, 0.5)
            x0, x1 = lt.x("9:00"), lt.x("9:40")
            yr = lt.y("richard")
            L.tinta(K.ROJO, q)
            c.set_dash([6, 6])
            DG.linea(c, [(x1, y - 16), (x1, yr + 16)], suave(lim((t - self.t_45 + 0.3) / 0.8)), 2.5)
            c.set_dash([])
            DG.linea(c, [(x0, yr - 40), (x0, yr - 50), (x1, yr - 50), (x1, yr - 40)], 1.0, 2.5)
            L.texto("casi 45 minutos", (x0 + x1) / 2, yr - 64, 28, K.ROJO, q, "centro")
        img = L.componer(img, 0.4, 0.45)
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(d, 631), -10, 1.5, 1.5)
        m.agregar("alerta", self.t_alerta, K.notificacion(632), -12)
        for k, tk in enumerate((self.t_923, self.t_1016, self.t_1020)):
            m.agregar(f"marca{k}", tk, K.clic_mouse(633 + k), -4)
        for k in range(3):
            m.agregar(f"pitido{k}", self.t_923 + 0.1 + 0.16 * k, K.pitido(2900, 0.07), -10)
        m.agregar("pánico", self.t_1011, K.alarma_casa(1.6, 636, lejos=0.85), -14, 0.05, 0.6)
        for k, tk in enumerate((self.t_videos, self.t_mensaje)):
            m.agregar(f"notificación{k}", tk, K.notificacion(637 + k), -6)
        return m.x[:n]


# =========================================================================== 6.4


class Sub64(Subescena):
    """El Fitbit One: en la mesa (3D), la foto real y lo que tiene adentro; de la memoria a la nube."""

    cine = CINE

    def preparar(self) -> None:
        o = self.T.oraciones
        self.fondo = K.fondo()
        self.c1 = momento(self.T, self.id, 1, "aparato")
        self.seg = Segmentos([self.c1, o[3]], CRUCE)
        self.mesa = Plano3D("e06_fitbit_mesa", self.c1 + CRUCE / 2 + 0.2, motor=MOTOR["e06_fitbit_mesa"])
        self.planos3d = [self.mesa]
        self.foto = Foto("6.4_fitbit_one.jpg")
        m = lambda k, p: momento(self.T, self.id, k, p)   # noqa: E731
        self.t_acel = m(3, "acelerómetro")
        self.t_alti = m(3, "altímetro")
        self.t_iphone = m(3, "igual")
        self.t_sin = o[4] + 0.2
        self.t_mem = o[5] + 0.1
        self.t_tel = m(6, "teléfono")
        self.t_bt = m(6, "bluetooth")
        self.t_app = o[7] + 0.1
        self.t_nube = m(7, "servidores")
        self.t_pierde = m(8, "pierda")
        self.t_cintura = m(2, "cintura")

    def _ver_mesa(self, t: float) -> np.ndarray:
        o = self.T.oraciones
        img = self.mesa.cuadro(t)
        a = aparece(t, o[1] + 0.2, 0.7)
        texto(img, "Fitbit One", 120, H - 140, 64, K.CLARO, opacidad=a)
        return img

    def _ver_foto(self, t: float) -> np.ndarray:
        o = self.T.oraciones
        z, cx, cy = recorrido(t - self.c1 + CRUCE, o[3] - self.c1 + 2 * CRUCE, 1.0, 1.25, (0.5, 0.5), (0.6, 0.6))
        img = self.foto.ver(z, cx, cy) if self.foto.existe else self.fondo.copy()
        a = aparece(t, self.c1, 0.6)
        K.panel_esmerilado(img, 80, H - 250, 980, H - 70, a)
        texto(img, "del tamaño de un llavero", 120, H - 170, 50, K.CLARO, opacidad=a)
        texto(img, "se engancha en la ropa", 122, H - 112, 32, K.BEIGE, nombre="Inter-Regular.ttf",
              opacidad=aparece(t, self.c1 + 1.0, 0.6, self.t_cintura - 0.2))
        texto(img, "Connie lo llevaba en la cintura", 122, H - 112, 32, K.BEIGE, nombre="Inter-Regular.ttf",
              opacidad=aparece(t, self.t_cintura, 0.6))
        # la cifra de la pantalla es de la foto de archivo, no de Connie: se dice en pantalla
        K.panel_esmerilado(img, W - 640, 48, W - 70, 112, a, 0.55)
        texto(img, "foto de un Fitbit One (no es el de Connie)", W - 100, 90, 24, K.CLARO, alinear="der",
              nombre="Inter-Regular.ttf", opacidad=a * 0.85)
        return img

    def _ver_dentro(self, t: float) -> np.ndarray:
        o = self.T.oraciones
        img = self.fondo.copy()
        L = K.Lienzo()
        c = L.c
        a = aparece(t, o[3] - 0.3, 0.6)
        pierde = aparece(t, self.t_pierde, 0.8)
        # el aparato, en grande
        fx, fy, fw, fh = 140, 370, 640, 330
        K.caja_suave(L, fx, fy, fw, fh, a * (1 - 0.75 * pierde), K.CLARO, K.OSCURO, fh / 2, punteada=pierde > 0.5, grosor=3)
        L.texto("Fitbit One", fx + fw / 2, fy - 30, 34, K.CLARO, a * (1 - 0.6 * pierde), "centro")
        for k, (tk, ic, nombre, que) in enumerate(((self.t_acel, "pasos", "acelerómetro", "cuenta pasos"),
                                                   (self.t_alti, "escalera", "altímetro", "cuenta pisos"))):
            b = aparece(t, tk, 0.5) * (1 - 0.75 * pierde)
            x = fx + 150 + k * 260
            K.caja_suave(L, x - 90, fy + 34, 180, 104, b, K.REG, K.OSCURO, 12)
            L.tinta(K.REG, b)
            K.icono(c, ic, x, fy + 84, 46, 2.5)
            L.texto(nombre, x, fy + 176, 26, K.CLARO, b, "centro")
            L.texto(que, x, fy + 206, 22, K.TENUE, b, "centro", "Inter-Regular.ttf")
        L.texto("igual que el iPhone de Friburgo", fx + fw / 2, fy + fh + 60, 26, K.BEIGE,
                aparece(t, self.t_iphone, 0.6, self.t_sin - 0.2), "centro", "Inter-Regular.ttf")
        # sin internet propio
        s = aparece(t, self.t_sin, 0.5) * (1 - aparece(t, self.t_mem, 0.5))
        if s > 0:
            L.tinta(K.TENUE, s)
            K.icono(c, "nube", fx + fw / 2, fy - 130, 80, 3)
            L.tinta(K.ROJO, s)
            DG.cruz(c, fx + fw / 2, fy - 130, 50, 4)
            L.texto("sin conexión propia a internet", fx + fw / 2, fy - 200, 28, K.CLARO, s, "centro")
        # la memoria, minuto a minuto
        mem = aparece(t, self.t_mem, 0.5)
        if mem > 0:
            n = int(32 * suave(lim((t - self.t_mem) / 3.0)))
            rng = np.random.default_rng(64)
            alturas = rng.uniform(0.15, 1.0, 32)
            for k in range(n):
                hh = 34 * alturas[k]
                L.tinta(K.REG, mem * (1 - 0.6 * pierde))
                c.rectangle(fx + 70 + k * 15.5, fy + fh - 34 - hh, 10, hh)
                c.fill()
            L.texto("memoria: minuto a minuto", fx + fw / 2, fy + fh + 60, 26, K.BEIGE, mem, "centro", "Inter-Regular.ttf")
        # Bluetooth al teléfono o la computadora, y de ahí a la nube
        tel = (1060, 530)
        nube = (1600, 530)
        b = aparece(t, self.t_tel - 0.2, 0.5)
        L.tinta(K.CLARO, b)
        K.icono(c, "telefono", tel[0] - 40, tel[1], 110, 3)
        K.icono(c, "laptop", tel[0] + 60, tel[1] + 20, 70, 3)
        L.texto("teléfono o computadora", tel[0], tel[1] + 110, 26, K.CLARO, b, "centro")
        L.texto("con la app de Fitbit", tel[0], tel[1] + 144, 22, K.TENUE, b, "centro", "Inter-Regular.ttf")
        bt = aparece(t, self.t_bt - 0.3, 0.5)
        if bt > 0:
            ruta = [(fx + fw + 20, fy + fh / 2), (tel[0] - 90, tel[1])]
            L.tinta(K.REG, 0.6 * bt)
            c.set_dash([6, 8])
            DG.linea(c, ruta, 1.0, 2.5)
            c.set_dash([])
            L.tinta(K.REG, bt)
            K.icono(c, "bluetooth", (ruta[0][0] + ruta[1][0]) / 2, tel[1] - 50, 46, 3)
            L.texto("Bluetooth", (ruta[0][0] + ruta[1][0]) / 2, tel[1] + 6 + 40, 24, K.REG, bt, "centro")
            for k in range(3):
                u = ((t - self.t_bt) * 0.7 + k / 3) % 1.0 if t > self.t_bt else 0
                viaje(c, ruta, u, K.REG, bt * (1 - pierde), 6)
        nb = aparece(t, self.t_app, 0.5)
        if nb > 0:
            ruta = [(tel[0] + 110, tel[1]), (nube[0] - 110, nube[1])]
            L.tinta(K.REG, 0.6 * nb)
            DG.linea(c, ruta, suave(lim((t - self.t_app) / 0.8)), 2.5)
            for k in range(3):
                u = ((t - self.t_nube) * 0.6 + k / 3) % 1.0 if t > self.t_nube else 0
                viaje(c, ruta, u, K.REG, nb, 6)
            L.tinta(K.CLARO, nb)
            K.icono(c, "nube", *nube, 160, 3.5)
            L.texto("servidores de Fitbit", nube[0], nube[1] + 130, 28, K.CLARO, nb, "centro")
            g = aparece(t, self.t_nube + 0.5, 0.6)
            rng = np.random.default_rng(64)
            alturas = rng.uniform(0.15, 1.0, 32)
            for k in range(16):
                hh = 26 * alturas[k]
                L.tinta(K.REG, g)
                c.rectangle(nube[0] - 70 + k * 9, nube[1] + 30 - hh, 5, hh)
                c.fill()
        L.texto("los datos quedan guardados", nube[0], nube[1] - 140, 28, K.ROJO, pierde, "centro")
        return L.componer(img, 0.4, 0.45)

    def cuadro(self, t: float) -> np.ndarray:
        return mezclar((self._ver_mesa, self._ver_foto, self._ver_dentro), self.seg.pesos(t), t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        o = self.T.oraciones
        m = sfx.Mezcla(d)
        m.agregar("cuarto", 0.0, K.cuarto(o[3] + 0.5, 641), -6, 0.8, 1.0)
        m.agregar("zumbido", o[3] - 0.5, sfx.zumbido_electronico(d - o[3] + 0.5, 642), -10, 1.0, 1.5)
        m.agregar("bluetooth", self.t_bt, K.sincronizacion(1.6, 643), -4)
        m.agregar("nube", self.t_nube, K.sincronizacion(1.6, 644), -6)
        m.agregar("memoria", self.t_mem, sfx.tics([self.t_mem + 0.094 * k for k in range(32)], 3.5, 645), -16)
        return m.x[:n]


# =========================================================================== 6.5


class Sub65(Subescena):
    """Lo que registró el Fitbit, solo con los datos que da la narración: salida a las 8:46, regreso a
    las 9:23 tras nueve minutos de manejo, 1,217 pies caminados hasta el último movimiento de las 10:05,
    contra los 125 pies del garaje al sótano; y la hora en que, según Richard, ya había muerto.
    Sin curva ni conteos intermedios: la forma de una gráfica inventada se leería como prueba."""

    cine = CINE

    def preparar(self) -> None:
        o = self.T.oraciones
        self.fondo = K.fondo()
        self.lt = K.LineaTiempo("8:30", "10:30", filas={"fitbit": 560}, eje=760)
        m = lambda k, p: momento(self.T, self.id, k, p)   # noqa: E731
        self.t_846 = m(0, "8:46")
        self.t_923 = m(1, "marcó")
        self.t_manejo = m(1, "nueve")
        self.t_tramo = o[2] + 0.2
        self.t_pies = m(2, "1,217")
        self.t_metros = m(2, "unos")
        self.t_comp = o[3] + 0.2
        self.t_125 = m(3, "125")
        self.t_1005 = o[4] + 0.2
        self.t_nueve = o[5] + 0.2

    def cuadro(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        lt = self.lt
        L = K.Lienzo()
        c = L.c
        a = aparece(t, 0.2, 0.8)
        L.texto("EL FITBIT DE CONNIE", 110, 140, 30, K.CLARO, a, interletra=0.12)
        L.texto("lo que quedó guardado esa mañana", 112, 180, 24, K.TENUE, a, nombre="Inter-Regular.ttf")
        lt.eje(L, a, paso=30, arriba=440)
        lt.fila(L, "fitbit", a)
        y = lt.y("fitbit")
        # fuera de casa: de la salida a las 8:46 al regreso de las 9:23
        f = aparece(t, self.t_923 - 0.2, 0.5)
        lt.tramo(L, "fitbit", "8:46", "9:23", f * 0.7, K.TENUE, 22, rayado=True)
        L.texto("fuera de casa", (lt.x("8:46") + lt.x("9:23")) / 2, y - 26, 24, K.TENUE, f, "centro", "Inter-Regular.ttf")
        mj = aparece(t, self.t_manejo - 0.2, 0.5)
        if mj > 0:
            L.tinta(K.BEIGE, mj)
            K.icono(c, "auto", lt.x("9:23") - 46, y + 46, 30, 2.5)
            L.texto("9 minutos de manejo", lt.x("9:23") - 72, y + 58, 22, K.BEIGE, mj, "der", "Inter-Regular.ttf")
        lt.marca(L, "fitbit", "8:46", aparece(t, self.t_846, 0.5), "sale al gimnasio", "", K.REG, arriba=True, alto=40)
        lt.marca(L, "fitbit", "9:23", aparece(t, self.t_923, 0.5), "vuelve a casa", "", K.REG, arriba=False, alto=60)
        # de las 9:23 a las 10:05: el total que caminó, sin forma inventada en medio
        p = suave(lim((t - self.t_tramo) / 2.5))
        ca = aparece(t, self.t_tramo, 0.4)
        lt.tramo(L, "fitbit", "9:23", "10:05", ca, K.REG, 30, p=p)
        x0, x1 = lt.x("9:23"), lt.x("10:05")
        b = aparece(t, self.t_pies, 0.5)
        if b > 0:
            L.tinta(K.REG, b)
            DG.linea(c, [(x0, y - 40), (x0, y - 50), (x1, y - 50), (x1, y - 40)], 1.0, 2.5)
            L.texto("caminó 1,217 pies", (x0 + x1) / 2, y - 112, 44, K.CLARO, b, "centro")
            L.texto("unos 370 metros", (x0 + x1) / 2, y - 70, 26, K.BEIGE, aparece(t, self.t_metros, 0.5), "centro",
                    "Inter-Regular.ttf")
        lt.marca(L, "fitbit", "10:05", aparece(t, self.t_1005, 0.5), "último movimiento", "", K.ROJO, arriba=False, alto=60)
        # comparación: lo que caminó contra la distancia del garaje al sótano (las dos cifras del guion)
        cm = aparece(t, self.t_comp, 0.6, self.t_nueve - 0.6, 0.5)
        if cm > 0:
            bx, by = 1150, 222
            K.caja_suave(L, bx - 30, by - 60, 690, 220, cm, K.BEIGE, K.OSCURO, 14)
            largo = 480
            L.texto("caminó en la casa", bx, by - 12, 24, K.CLARO, cm, nombre="Inter-Regular.ttf")
            L.tinta(K.REG, cm)
            c.rectangle(bx, by + 2, largo * suave(lim((t - self.t_comp) / 0.8)), 24)
            c.fill()
            L.texto("1,217 pies", bx + largo + 12, by + 24, 24, K.CLARO, cm)
            e = aparece(t, self.t_125, 0.6) * cm
            L.texto("del garaje al sótano", bx, by + 70, 24, K.CLARO, e, nombre="Inter-Regular.ttf")
            L.tinta(K.ROJO, e)
            c.rectangle(bx, by + 84, largo * 125 / 1217 * suave(lim((t - self.t_125) / 0.6)), 24)
            c.fill()
            L.texto("no más de 125 pies (38 m)", bx + largo * 125 / 1217 + 14, by + 106, 24, K.CLARO, e)
        # las nueve, según Richard
        nv = aparece(t, self.t_nueve, 0.6)
        if nv > 0:
            x = lt.x("9:00")
            L.tinta(K.ROJO, 0.08 * nv)
            c.rectangle(x, 330, x1 - x, lt.eje_y - 330)
            c.fill()
            L.tinta(K.BEIGE, nv)
            c.set_dash([10, 8])
            DG.linea(c, [(x, lt.eje_y), (x, 330)], suave(lim((t - self.t_nueve) / 0.8)), 3)
            c.set_dash([])
            L.texto("9:00", x, 290, 34, K.CLARO, nv, "centro")
            L.texto("muerta, según Richard", x, 320, 24, K.BEIGE, nv, "centro", "Inter-Regular.ttf")
        return L.componer(img, 0.4, 0.45)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(d, 651), -10, 1.5, 1.5)
        rng = np.random.default_rng(652)
        pasos, x = [], self.t_tramo + 0.2
        fin = self.t_tramo + 2.5
        while x < fin:
            pasos.append(x)
            x += 0.55 + rng.normal(0, 0.05) + (0.6 if rng.random() < 0.12 else 0)
        m.agregar("pasos", 0.0, K.pasos_madera(pasos, fin + 0.5, 653), -2)          # y se detienen
        m.agregar("última", self.t_1005, K.pitido(1400, 0.15), -14)
        m.agregar("grave", self.t_nueve - 0.5, K.tono_grave(d - self.t_nueve + 0.5, 654), -6, 1.0, 1.0)
        return m.x[:n]


# =========================================================================== 6.6


class Sub66(Subescena):
    """Todo en la misma línea: el intruso no cabe. La orden de arresto, el veredicto y la sentencia."""

    cine = CINE
    fundido_salida = 1.4

    def preparar(self) -> None:
        o = self.T.oraciones
        self.fondo = K.fondo()
        self.lt = K.LineaTiempo("8:30", "10:30", filas={"richard": 225, "computadora": 375, "alarma": 520,
                                                         "facebook": 665, "fitbit": 810}, eje=910)
        self.seg = Segmentos([o[2], o[4], o[5], o[6]], CRUCE)
        self.juicio = Foto("6.6_dabate_juicio.jpg")
        self.titular = Foto("6.6_titular_fitbit.jpg")
        self.richard = Foto("5.0_richard_dabate.jpg")
        m = lambda k, p: momento(self.T, self.id, k, p)   # noqa: E731
        self.t_caber = m(0, "intruso")
        self.t_viva = m(1, "viva")
        self.t_casa = m(1, "Richard")
        self.t_cinco = o[3] + 0.1
        self.cargos = [m(4, "asesinato"), m(4, "alteración"), m(4, "declaraciones")]
        self.t_65 = m(5, "65")
        self.gris = gradiente_vertical([(0.0, mezcla(P["azul"], K.NEGRO, 0.75)), (1.0, mezcla(P["azul"], K.NEGRO, 0.9))])

    def _ver_linea(self, t: float) -> np.ndarray:
        img = self.fondo.copy()
        lt = self.lt
        L = K.Lienzo()
        c = L.c
        a = aparece(t, 0.1, 0.6)
        lt.eje(L, a, paso=30, arriba=180)
        L.texto("TODOS LOS APARATOS, EN LA MISMA LÍNEA", 110, 120, 28, K.CLARO, a, interletra=0.1)
        for k, fila in enumerate(("computadora", "alarma", "facebook", "fitbit")):
            lt.fila(L, fila, aparece(t, 0.2 + 0.25 * k, 0.5))
        lt.fila(L, "richard", a, punteada_=True)
        r = aparece(t, 0.5, 0.6)
        for h in ("9:01", "9:04", "9:18", "9:20"):
            lt.punto(L, "computadora", h, r, K.REG)
        lt.tramo(L, "alarma", "8:30", "9:23", r, K.TENUE, 20, rayado=True)
        for h in ("9:23", "10:16", "10:20"):
            lt.punto(L, "alarma", h, r, K.REG)
        lt.punto(L, "alarma", "10:11", r, K.ROJO)
        lt.tramo(L, "facebook", "9:40", "9:46", r, K.REG, 26)
        lt.punto(L, "fitbit", "8:46", r, K.REG)
        lt.tramo(L, "fitbit", "9:23", "10:05", r, K.REG, 26)
        lt.punto(L, "fitbit", "10:05", r, K.ROJO)
        for clave, h, rot in (("computadora", "9:04", "correo"), ("alarma", "10:11", "pánico"),
                              ("facebook", "9:43", "videos"), ("fitbit", "9:44", "camina 1,217 pies")):
            L.texto(rot, lt.x(h), lt.y(clave) - 26, 22, K.TENUE, r, "centro", "Inter-Regular.ttf")
        # la historia del intruso: un bloque punteado que ya no cabe
        b = aparece(t, 0.4, 0.6)
        x0, x1 = lt.x("9:00"), lt.x("10:11")          # de la muerte que él declara a la alarma de pánico
        y = lt.y("richard")
        choque = aparece(t, self.t_caber, 0.5)
        rompe = suave(lim((t - self.t_caber - 1.0) / 1.2))
        if b > 0:
            col = mezcla(K.BEIGE, K.ROJO, choque)
            K.caja_suave(L, x0, y - 34, x1 - x0, 68, b * (1 - 0.7 * rompe), col, K.OSCURO, 10, punteada=True, grosor=2.5)
            L.texto("el intruso, según Richard", (x0 + x1) / 2, y + 10, 28, col, b * (1 - rompe), "centro")
            for h in ("9:18", "9:23", "9:40", "10:05"):                    # donde choca con lo registrado
                xx = lt.x(h)
                L.tinta(K.ROJO, choque * (1 - rompe * 0.5))
                c.set_dash([5, 6])
                DG.linea(c, [(xx, y + 36), (xx, lt.y("fitbit"))], 1.0, 2)
                c.set_dash([])
            L.texto("no cabe", (x0 + x1) / 2, y + 12, 34, K.ROJO, choque * rompe, "centro")
        # Connie viva; Richard en la casa
        v = aparece(t, self.t_viva, 0.6)
        if v > 0:
            for clave in ("facebook", "fitbit"):
                L.tinta(K.REG, 0.18 * v)
                c.rectangle(lt.x("9:23"), lt.y(clave) - 30, lt.x("10:05") - lt.x("9:23"), 60)
                c.fill()
            L.texto("Connie, viva", lt.x("10:05") + 26, lt.y("fitbit") + 10, 30, K.CLARO, v)
        h = aparece(t, self.t_casa, 0.6)
        if h > 0:
            L.tinta(K.REG, 0.18 * h)
            c.rectangle(lt.x("9:01") - 12, lt.y("computadora") - 30, lt.x("9:20") - lt.x("9:01") + 24, 60)
            c.fill()
            L.texto("Richard, en la casa", lt.x("9:20") + 30, lt.y("computadora") + 10, 30, K.CLARO, h)
        return L.componer(img, 0.4, 0.45)

    def _ver_juicio(self, t: float) -> np.ndarray:
        o = self.T.oraciones
        z, cx, cy = recorrido(t - o[2] + CRUCE, o[4] - o[2] + 2 * CRUCE, 1.02, 1.1, (0.42, 0.42), (0.36, 0.38))
        img = self.juicio.ver(z, cx, cy) if self.juicio.existe else self.gris.copy()
        a = aparece(t, o[2] + 0.2, 0.6)
        K.panel_esmerilado(img, 80, H - 260, 1000, H - 70, a, 0.55)
        texto(img, "ABRIL DE 2017", 120, H - 190, 26, K.BEIGE, interletra=0.3, opacidad=a * (1 - aparece(t, self.t_cinco, 0.5)))
        texto(img, "orden de arresto de 50 páginas", 118, H - 120, 50, K.CLARO, opacidad=a * (1 - aparece(t, self.t_cinco, 0.5)))
        b = aparece(t, self.t_cinco, 0.5)
        texto(img, "EL JUICIO", 120, H - 190, 26, K.BEIGE, interletra=0.3, opacidad=b)
        texto(img, "cinco años después: 2022", 118, H - 120, 50, K.CLARO, opacidad=b)
        return img

    def _ver_titular(self, t: float) -> np.ndarray:
        o = self.T.oraciones
        img = self.gris.copy()
        if self.titular.existe:
            fw = 980
            fh = int(fw * self.titular.h / self.titular.w)
            x0, y0 = 110, (H - fh) // 2
            K.sombra_marco(img, x0, y0, fw, fh, 1.0, 0.7)
            K.foto_en_marco(img, self.titular, x0, y0, fw, fh, 1.0 + 0.03 * lim((t - o[4]) / 6), 0.5, 0.4, borde=0.2)
        L = K.Lienzo()
        a = aparece(t, o[4] + 0.2, 0.6)
        L.texto("10 DE MAYO DE 2022", 1200, 300, 26, K.BEIGE, a, interletra=0.3)
        L.texto("Culpable de:", 1200, 380, 48, K.CLARO, a)
        for k, (tk, rot) in enumerate(zip(self.cargos, ("asesinato", "alteración de pruebas", "declaraciones falsas"))):
            b = aparece(t, tk, 0.5)
            L.tinta(K.ROJO, b)
            L.c.new_sub_path()
            L.c.arc(1214, 456 + k * 70, 7, 0, math.tau)
            L.c.fill()
            L.texto(rot, 1240, 470 + k * 70, 40, K.CLARO, b, nombre="Inter-Regular.ttf")
        return L.componer(img, 0.3, 0.0)

    def _ver_sentencia(self, t: float) -> np.ndarray:
        o = self.T.oraciones
        if self.richard.existe:
            img = self.richard.ver(1.05 + 0.04 * lim((t - o[5]) / 6), 0.42, 0.42) * 0.5
            # el lado derecho se oscurece para que se lea la sentencia
            rampa = np.clip((np.arange(W, dtype=np.float32) - W * 0.5) / (W * 0.25), 0, 1) ** 1.2
            img *= (1 - 0.72 * rampa)[None, :, None]
        else:
            img = self.gris.copy()
        a = aparece(t, o[5] + 0.2, 0.6)
        texto(img, "18 DE AGOSTO DE 2022", W - 120, 380, 28, K.BEIGE, alinear="der", interletra=0.3, opacidad=a)
        b = aparece(t, self.t_65, 0.5)
        texto(img, "65 años", W - 120, 560, 160, K.CLARO, alinear="der", nombre="Inter-Light.ttf", opacidad=b)
        texto(img, "de prisión", W - 124, 640, 56, K.CLARO, alinear="der", opacidad=b)
        return img

    def _ver_prensa(self, t: float) -> np.ndarray:
        """El titular en grande: la cámara se acerca a «'Fitbit murder'» y lo subraya."""
        o = self.T.oraciones
        img = self.gris.copy()
        if self.titular.existe:
            iw, ih = self.titular.w, self.titular.h
            u = suave(lim((t - o[6] + 0.6) / 2.6))
            s0 = 980 / iw
            s = s0 + (1.25 * 1880 / iw - s0) * u
            # de la tarjeta entera a la frase centrada (en la foto: «'Fitbit murder'» va de x 650 a 1545, y ≈ 370)
            x_ini, y_ini = 110.0, (H - ih * s0) / 2
            fx, fy = 1100 / 1880 * iw, 372 / 1327 * ih
            x_fin, y_fin = W / 2 - fx * s, H * 0.42 - fy * s
            x0 = x_ini + (x_fin - x_ini) * u
            y0 = y_ini + (y_fin - y_ini) * u
            fw, fh = iw * s, ih * s
            # recorte visible, muestreado de la foto con la escala actual
            xa, ya = max(0, int(x0)), max(0, int(y0))
            xb, yb = min(W, int(x0 + fw)), min(H, int(y0 + fh))
            if xb > xa and yb > ya:
                caja = ((xa - x0) / s, (ya - y0) / s, (xb - x0) / s, (yb - y0) / s)
                sub = np.asarray(self.titular.im.resize((xb - xa, yb - ya), Image.BICUBIC,
                                                       box=caja_dentro(caja, self.titular.w, self.titular.h)), np.float32) / 255
                img[ya:yb, xa:xb] = sub
            hx0, hx1 = x0 + 650 / 1880 * iw * s, x0 + 1545 / 1880 * iw * s
            hy = y0 + 428 / 1327 * ih * s
            ancho = (hx1 - hx0) * suave(lim((t - o[6] - 1.4) / 1.0))
            if ancho > 1:
                L = K.Lienzo()
                L.tinta(K.ROJO, 0.95)
                L.c.rectangle(hx0, hy, ancho, 12 * s / s0 * 0.5)
                L.c.fill()
                img = L.componer(img, 0.2, 0.0)
        a = aparece(t, o[6] + 1.6, 0.8)
        banda = np.clip((np.arange(H, dtype=np.float32) - (H - 300)) / 200, 0, 1)[:, None, None]
        img *= 1 - 0.85 * banda * a
        texto(img, "«el asesinato del Fitbit»", W / 2, H - 100, 64, K.CLARO, alinear="centro", opacidad=a)
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return mezclar((self._ver_linea, self._ver_juicio, self._ver_titular, self._ver_sentencia, self._ver_prensa),
                       self.seg.pesos(t), t)

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        o = self.T.oraciones
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, sfx.zumbido_electronico(o[2] + 0.5, 661), -10, 1.0, 1.0)
        m.agregar("choque", self.t_caber, sfx.error_suave(662), -10)
        m.agregar("sala", o[2] - 0.4, sfx.viento(d - o[2] + 0.4, 663, 0.25), -18, 1.5, 1.5)
        m.agregar("papel", o[2] + 0.3, K.papel(1.2, 664), -8)
        m.agregar("mazo", o[4] + 0.3, K.mazo(665), 0)
        m.agregar("mazo2", self.t_65 - 0.1, K.mazo(666), 0)
        return m.x[:n]


# =========================================================================== registro

SUBESCENAS = {"6.0": Sub60, "6.1": Sub61, "6.2": Sub62, "6.3": Sub63, "6.4": Sub64, "6.5": Sub65, "6.6": Sub66}

# Fotogramas clave para revisar antes del render completo: (archivo, clip, tiempo en el clip)
REVISION = [
    ("1_correo_9_04.png", "6.1", lambda T: T.oraciones[5] + 1.5),
    ("2_alarma_facebook.png", "6.3", lambda T: T.fin_voz - 0.3),
    ("3_fitbit_mesa.png", "6.4", lambda T: T.oraciones[1] + 0.8),
    ("4_grafica_1217_pies.png", "6.5", lambda T: T.oraciones[5] + 1.5),
]


def clips() -> list[str]:
    return ["titulo"] + [s.id for s in guion.leer()[NUMERO].subescenas]


def crear(id_: str) -> Subescena:
    if id_ == "titulo":
        return titulo()
    return SUBESCENAS[id_](id_, tiempos(id_))
