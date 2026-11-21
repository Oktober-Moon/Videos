"""Escena 8 — Las 10:05 (cierre del video).

8.0  Un teléfono cuenta pasos y una bocina espera oír su nombre; el Dreisam al atardecer (3D, el mismo
     río de la escena 1); la cocina vacía en Connecticut con la luz de la mañana (3D); la última marca
     del Fitbit de Connie Dabate a las 10:05; doce personas de un jurado; corte a negro y silencio.

Lento y sobrio: movimientos de cámara mínimos, pocos textos, fundidos largos. La paleta es la del
cierre (`paletas.cierre`): de la de Friburgo a la de Connecticut, terminando en negro.
"""

from __future__ import annotations

import math

import numpy as np

import guion
import sfx
from escenas import graficos_e07 as G
from escenas.base import SR, Segmentos, Subescena, TarjetaTitulo, aparece, tiempos
from escenas.plano3d import Plano3D
from graficos import H, lim, suave
from paletas import CONNECTICUT, FRIBURGO, cierre, mezcla, rgb

NUMERO = 8
F, CT = rgb(FRIBURGO), rgb(CONNECTICUT)
NEGRO = np.zeros(3, np.float32)
CRUCE = 1.2
MOTOR = {"e08_dreisam_atardecer": "eevee", "e08_cocina": "eevee"}
_P = cierre(0.45)
CINE = dict(sombras=mezcla(_P["fondo"], NEGRO, 0.4), luces=_P["claro"], mezcla=0.10, saturacion=0.92, contraste=0.05,
            halo=0.12, grano=0.012, vineta=0.36)


def titulo() -> TarjetaTitulo:
    p = cierre(0.3)
    t = TarjetaTitulo(NUMERO, guion.leer()[NUMERO].titulo, p["acento"], p["claro"])
    t.cine = CINE
    return t


class Sub80(Subescena):
    """Pasos que se cuentan solos; el río; la cocina vacía; la última marca a las 10:05; negro."""

    fundido_entrada = 0.8
    fundido_salida = 1.0
    cine = CINE

    def preparar(self) -> None:
        o = self.T.oraciones
        self.t_rio = o[1] - 0.5
        self.t_cocina = o[2] - 0.3
        self.t_grafica = o[4] - 0.5
        self.rio = Plano3D("e08_dreisam_atardecer", self.t_cocina + CRUCE / 2 - (self.t_rio - CRUCE / 2) + 0.25,
                           motor=MOTOR["e08_dreisam_atardecer"])
        self.cocina = Plano3D("e08_cocina", self.t_grafica + CRUCE / 2 - (self.t_cocina - CRUCE / 2) + 0.25,
                              motor=MOTOR["e08_cocina"])
        self.planos3d = [self.rio, self.cocina]
        self.seg = Segmentos([self.t_rio, self.t_cocina, self.t_grafica], CRUCE)
        self.pasos = [0.9 + 0.56 * k + 0.03 * math.sin(k * 1.7) for k in range(int((self.t_rio + 1.0) / 0.56))]   # ritmo de caminar
        palabras = guion.subescena(self.id).oraciones[0].split()
        i = next(k for k, p in enumerate(palabras) if p.lower().startswith("bocina"))
        self.t_bocina = o[0] + (o[1] - 0.4 - o[0]) * len(" ".join(palabras[:i])) / len(guion.subescena(self.id).oraciones[0])
        palabras = guion.subescena(self.id).oraciones[5].split()
        i = next(k for k, p in enumerate(palabras) if p.lower().startswith("doce"))
        self.t_doce = o[5] + (self.T.fin_voz - o[5]) * len(" ".join(palabras[:i])) / len(guion.subescena(self.id).oraciones[5])
        self.fondo = G.fondo(mezcla(F["verde"], NEGRO, 0.86), mezcla(F["verde"], NEGRO, 0.62), semilla=21, reticula=0.0)

    # ---- un teléfono que cuenta pasos y una bocina que espera
    def _pasos(self, t: float) -> np.ndarray:
        """El teléfono cuenta pasos (sin cifra: cada paso enciende una huella) y, a un lado, una bocina
        con su anillo apagado que respira apenas."""
        from escenas import diagramas as DG
        img = self.fondo.copy()
        p = cierre(0.0)
        lz = G.Lienzo()
        c = lz.c
        a = aparece(t, 0.3, 1.0)
        lz.tinta(mezcla(F["verde"], NEGRO, 0.7), a)
        G.D.rect_redondeado(c, 960 - 175, 540 - 355, 350, 710, 52)
        c.fill()
        lz.tinta(p["claro"], a * 0.85)
        DG.telefono(c, 960, 540, 720, 4)
        dados = sum(1 for x in self.pasos if x <= t)
        ultimo = max([x for x in self.pasos if x <= t], default=-9)
        late = math.exp(-(t - ultimo) / 0.25) if t >= ultimo else 0.0
        for k, (dx, dy) in enumerate(((-38, 30), (38, -30))):             # dos huellas que se turnan
            activa = dados % 2 == k
            lz.tinta(p["claro"] if activa else mezcla(p["claro"], NEGRO, 0.6), a * (0.55 + 0.45 * late if activa else 0.35))
            hx, hy = 960 + dx, 560 + dy
            G.D.elipse(c, hx, hy, 24, 44, 0.12 * (1 if k else -1))
            for j_, (ox, oy, r) in enumerate(((-14, -58, 8), (0, -64, 7), (13, -60, 6), (23, -51, 5))):
                c.arc(hx + (ox if k else -ox), hy + oy, r, 0, math.tau)
                c.fill()
        ab = aparece(t, self.t_bocina, 1.2)
        lz.tinta(p["claro"], ab * 0.6)
        G.bocina(c, 1480, 600, 300, 3, anillo=ab * (0.35 + 0.25 * math.sin(t * 1.6)), col_anillo=p["acento"])
        img = lz.componer(img, sombra=0.6, brillo=0.3, col_brillo=p["acento"], sigma_brillo=18)
        G.antetitulo(img, "Pasos", 960, 430, p["claro"], a * 0.9, alinear="centro", tam=30)
        G.rotulo(img, "contando", 960, 700, 40, p["claro"], a * 0.85, alinear="centro", nombre="Inter-Regular.ttf")
        return img

    def _rio(self, t: float) -> np.ndarray:
        return self.rio.cuadro(t - (self.t_rio - CRUCE / 2))

    def _cocina(self, t: float) -> np.ndarray:
        img = self.cocina.cuadro(t - (self.t_cocina - CRUCE / 2))
        p = cierre(0.6)
        a = aparece(t, self.t_cocina + 1.2, 1.2, self.t_grafica - 0.6, 0.8)
        G.panel(img, 0, H - 270, 900, H - 70, a, 0.45)
        G.antetitulo(img, "Ellington, Connecticut", 120, H - 195, mezcla(p["claro"], NEGRO, 0.05), a, tam=30)
        G.rotulo(img, "23 de diciembre de 2015", 118, H - 120, 64, p["claro"], a)
        return img

    # ---- la última marca del Fitbit: una línea de tiempo con las horas del guion, sin cifras inventadas
    def _grafica(self, t: float) -> np.ndarray:
        o = self.T.oraciones
        p = cierre(0.5)
        claro = mezcla(p["claro"], np.ones(3, np.float32), 0.35)
        acento = mezcla(p["acento"], np.ones(3, np.float32), 0.45)
        img = G.fondo(mezcla(CT["azul"], NEGRO, 0.88), mezcla(CT["azul"], NEGRO, 0.70), semilla=22, reticula=0.0)
        t0 = self.t_grafica - CRUCE / 2
        x0, x1, y = 200, 1720, 560

        def X(h, m):                                          # de las 8:30 a las 10:15
            return x0 + (x1 - x0) * ((h - 8) * 60 + m - 30) / 105.0
        a = aparece(t, t0, 0.8)
        lz = G.Lienzo()
        c = lz.c
        lz.tinta(claro, a * 0.45)
        c.set_line_width(3)
        c.move_to(x0, y)
        c.line_to(x1, y)
        c.stroke()
        marcas = ((8, 46, "8:46", "sale al gimnasio"), (9, 23, "9:23", "vuelve a casa"))
        for h, m, _, _ in marcas:
            lz.tinta(claro, a * 0.85)
            c.arc(X(h, m), y, 9, 0, math.tau)
            c.fill()
        # el movimiento de 9:23 a 10:05 se traza y se detiene
        avance = suave(lim((t - t0 - 0.4) / max(1.0, o[4] + 1.4 - t0 - 0.4)))
        xa, xb = X(9, 23), X(10, 5)
        lz.tinta(acento, a)
        c.set_line_width(9)
        c.move_to(xa, y)
        c.line_to(xa + (xb - xa) * avance, y)
        c.stroke()
        quieto = suave(lim((t - (o[4] + 1.4)) / 0.6))
        if quieto > 0:
            pulso = 0.5 + 0.5 * math.sin((t - o[4]) * 2.0)
            lz.tinta(claro, a * quieto)
            c.arc(xb, y, 16 + 3 * pulso, 0, math.tau)
            c.fill()
        # doce personas de un jurado
        for k in range(12):
            ak = aparece(t, self.t_doce + 0.12 * k, 0.5)
            lz.tinta(claro, ak * 0.9)
            c.arc(960 - 11 * 46 + k * 92, 880, 18, 0, math.tau)
            c.fill()
        img = lz.componer(img, sombra=0.5, brillo=0.45, col_brillo=acento, sigma_brillo=16)
        G.antetitulo(img, "Fitbit de Connie Dabate", x0, 250, claro, a, tam=34)
        for h, m, hora, que in marcas:
            G.rotulo(img, hora, X(h, m), y - 40, 52, claro, a, alinear="centro")
            G.rotulo(img, que, X(h, m), y + 70, 34, mezcla(claro, NEGRO, 0.15), a, alinear="centro", nombre="Inter-Regular.ttf")
        G.rotulo(img, "10:05", xb, y - 50, 120, claro, aparece(t, o[4] + 1.4, 0.8), alinear="centro", nombre="Inter-Light.ttf")
        G.rotulo(img, "último movimiento", xb, y + 70, 34, claro, aparece(t, o[4] + 1.6, 0.8), alinear="centro",
                 nombre="Inter-Regular.ttf")
        G.rotulo(img, "seis años y medio después", 960, 800, 42, claro, aparece(t, o[5] + 0.3, 0.8), alinear="centro",
                 nombre="Inter-Regular.ttf")
        # todo se apaga despacio hasta el negro
        apaga = 1.0 - suave(lim((t - (self.T.fin_voz - 1.4)) / 2.2))
        return img * apaga

    def cuadro(self, t: float) -> np.ndarray:
        img = None
        for k, peso in self.seg.pesos(t):
            capa = (self._pasos, self._rio, self._cocina, self._grafica)[k](t)
            img = capa * peso if img is None else img + capa * peso
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        silencio = self.T.fin_voz - 1.0                       # al final, silencio total
        m.agregar("viento", 0.0, sfx.viento(silencio, 801, 0.6), 0, 2.0, 2.5)
        return m.x[:n]


SUBESCENAS = {"8.0": Sub80}

REVISION = [
    ("1_pasos.png", "8.0", lambda T: T.oraciones[0] + 6.5),
    ("2_dreisam_atardecer.png", "8.0", lambda T: T.oraciones[1] + 1.0),
    ("3_cocina_vacia.png", "8.0", lambda T: T.oraciones[3] + 0.6),
    ("4_las_10_05.png", "8.0", lambda T: T.oraciones[5] + 2.5),
]


def clips() -> list[str]:
    return ["titulo"] + [s.id for s in guion.leer()[NUMERO].subescenas]


def crear(id_: str) -> Subescena:
    if id_ == "titulo":
        return titulo()
    return SUBESCENAS[id_](id_, tiempos(id_))
