"""Escena 3 — 900,000 dólares por nada (San Bernardino, el iPhone 5C de Farook y el FBI contra Apple).

3.0  California y San Bernardino; los atacantes (sus fotos); el Inland Regional Center de noche,
     vacío, con patrullas a lo lejos (3D); el iPhone 5C (foto) y, apagado, en su bolsa de evidencia (3D).
3.1  La contraseña de iCloud cambiada; el último respaldo; la captura de ajustes; las tres
     condiciones del respaldo; la sesión que deja de valer; Apple contra el FBI; respaldos apagados.
3.2  La orden de la jueza; Tim Cook y su carta; los titulares; la línea de tiempo hasta «No dice cómo».
3.3  Cinco años sin saber; el Washington Post y Azimuth; los cinco pasos; el puerto Lightning (foto y
     3D: el cable que entra); la conversación con el accesorio aunque esté bloqueado.
3.4  Bibliotecas de código abierto; la de Mozilla dentro del iPhone; el error que se hereda.
3.5  Mark Dowd; el código que se revisa línea por línea; el error guardado y nunca publicado.
3.6  Los compartimentos; David Wang (silueta: no hay foto confirmada); tres puertas; «Cóndor».
3.7  La fuerza bruta sin borrado; una docena de iPhone 5C (3D) que se abren todos.
3.8  A6 contra A7: sin Secure Enclave, iOS controla los intentos; el UID sigue en el hardware.
3.9  900,000 dólares; nada útil; Mozilla corrige; el Modo USB restringido; GrayKey.
3.10 El primer desbloqueo deja las claves en la memoria de trabajo.
3.11 BFU y AFU; la bolsa de Faraday con el teléfono encendido y cargando (3D).
3.12 Detroit 2024: teléfonos de evidencia que se reinician solos (3D); Jiska Classen y sus tres pasos.
3.13 La cadena de arranque: bootrom, cargador e iOS, cada eslabón con la firma de Apple.
3.14 checkm8: el primer eslabón se agrieta; del 4S al X; el Secure Enclave sigue en pie.

Paletas: San Bernardino (azul FBI, dorado, arena) de 3.0 a 3.7 y en 3.9; mundo Apple (gris espacial,
blanco, azul) en 3.8 y de 3.10 a 3.14. La violencia nunca se muestra.
"""

from __future__ import annotations

import functools
import math

import numpy as np
from PIL import Image

import dibujo as D
import guion
from escenas import diagramas as DG
from escenas import piezas_e03 as P
from escenas import sonidos_e03 as S
from escenas.base import SR, Foto, Segmentos, Subescena, TarjetaTitulo, aparece, recorrido, tiempos
from escenas.piezas_e03 import AP, MANZANA, NEGRO, ROJO, SANB, SB, Capa, antetitulo, rotulo
from escenas.plano3d import Plano3D
from graficos import H, W, Luces, lim, suave
from paletas import mezcla

import sfx

NUMERO = 3
TAU = math.tau
CRUCE = 0.9
# Todos los planos en Eevee: no hay agua ni calle mojada que pida Cycles (direccion_visual.md §5).
MOTOR = {"e03_centro_noche": "eevee", "e03_iphone_evidencia": "eevee", "e03_puerto_lightning": "eevee",
         "e03_docena_5c": "eevee", "e03_bolsa_faraday": "eevee", "e03_sala_evidencias": "eevee"}

# El 3D ya trae su curva de color (AgX): el acabado encima es leve, como en la escena 1.
CINE_SB = dict(sombras=mezcla(SB["azul_fbi"], NEGRO, 0.35), luces=SB["arena"], mezcla=0.12, saturacion=0.95,
               contraste=0.06, halo=0.12, grano=0.012, vineta=0.32)
CINE_AP = dict(sombras=mezcla(AP["gris"], NEGRO, 0.3), luces=AP["blanco"], mezcla=0.08, saturacion=0.97,
               contraste=0.05, halo=0.12, grano=0.011, vineta=0.3)


# =========================================================================== utilidades


@functools.lru_cache(maxsize=4)
def _degradado(alto: int, abajo: bool) -> np.ndarray:
    y = np.arange(H, dtype=np.float32)
    v = np.clip((y - (H - alto)) / alto, 0, 1) if abajo else np.clip((alto - y) / alto, 0, 1)
    v = (v ** 1.5)[:, None, None]
    v.setflags(write=False)
    return v


def oscurecer(img: np.ndarray, abajo: bool = True, alto: int = 380, fuerza: float = 0.65) -> np.ndarray:
    """Oscurece el borde de abajo (o de arriba) para que los rótulos se lean sobre fotos y 3D."""
    img *= 1 - _degradado(alto, abajo) * fuerza
    return img


def leyenda(img, ante, principal, a=1.0, tema=SANB, x=120, y=H - 140, tam=56, detalle=None, a_detalle=None):
    """Rótulo de lugar o de objeto abajo a la izquierda: antetítulo chico y texto grande."""
    if a <= 0:
        return
    if ante:
        antetitulo(img, ante, x + 2, y - 62, tema.tenue if tema is SANB else mezcla(tema.claro, tema.oscuro, 0.35), a)
    rotulo(img, principal, x, y, tam, tema.claro, a)
    if detalle:
        rotulo(img, detalle, x + 2, y + 52, 30, tema.tenue, a if a_detalle is None else a_detalle, nombre="Inter-Regular.ttf")


class Sub3(Subescena):
    """Subescena de la escena 3: compone sus tramos de imagen con fundidos."""

    tema = SANB
    cine = CINE_SB

    def __init__(self, id_: str, t):
        super().__init__(id_, t)
        self.o = repartir_oraciones(id_, t)

    def m(self, k: int) -> float:
        return self.o[k]

    def mezclar(self, t: float, partes) -> np.ndarray:
        img = None
        for k, peso in self.seg.pesos(t):
            capa = partes[k](t)
            img = capa * peso if img is None else img + capa * peso
        return img

    def fondo(self) -> np.ndarray:
        return P.fondo(self.tema)

    def en(self, k: int, palabra: str, n: int = 1) -> float:
        return P.en_palabra(self, k, palabra, n)

    def fin(self, k: int) -> float:
        """Fin aproximado de la oración k (inicio de la siguiente, o fin de la voz)."""
        return self.o[k + 1] if k + 1 < len(self.o) else self.T.fin_voz


def repartir_oraciones(id_: str, T) -> list[float]:
    """Inicios de oración sin choques. Los de `base.tiempos` buscan el silencio más cercano a donde
    caería cada oración por número de palabras, y a veces toman la pausa de una coma o pegan dos
    oraciones cortas («Apple se niega a obedecer.») en el mismo silencio: su imagen no saldría.
    Donde dos inicios quedan a menos de 0.24 s por palabra, se reparten por palabras entre el
    último inicio confiable y el siguiente. (Se probó tomar solo los silencios largos como fines
    de oración: con la voz procesada no se distinguen bien de las comas.)"""
    pal = guion.subescena(id_).palabras
    o = [float(x) for x in T.oraciones]
    n = len(o)
    k = 0
    while k < n - 1:
        if o[k + 1] - o[k] < 0.24 * pal[k]:
            j = k + 1
            while j < n and o[j] - o[k] < 0.24 * sum(pal[k:j]):
                j += 1
            fin_j = o[j] if j < n else T.fin_voz
            total = sum(pal[k:j]) or 1
            acum = 0
            for q in range(k + 1, j):
                acum += pal[q - 1]
                o[q] = o[k] + (fin_j - o[k]) * acum / total
            k = j
        else:
            k += 1
    return o


def puntos_codigo(img, cx, cy, t, a, tema, escala=1.0):
    """Seis puntos de un código que se llenan y se vacían sin parar: probar contraseñas a máquina
    sin mostrar números de intentos, que la voz no dice."""
    if a <= 0:
        return
    cp = Capa()
    lleno = int((max(0.0, t) * 40) % 7)
    for k in range(6):
        x = cx + (k - 2.5) * 46 * escala
        cp.tinta(tema.acento if k < lleno else tema.claro, a)
        cp.c.set_line_width(3 * escala)
        cp.c.arc(x, cy, 13 * escala, 0, TAU)
        if k < lleno:
            cp.c.fill()
        else:
            cp.c.stroke()
    cp.componer(img, sombra=0.25, brillo=0.4, col_brillo=tema.acento)


def persona_en(img, im, x, y, w, h, t, t0, a=1.0, z1=1.05, cy=0.38, borde=None, tema=SANB):
    """Foto de una persona en su recuadro, con un acercamiento lento desde que aparece."""
    z = 1.0 + (z1 - 1.0) * suave(lim((t - t0) / 9.0))
    P.ventana(img, im, x, y, w, h, a=a, zoom=z, cx=0.5, cy=cy, radio=10, borde=borde if borde is not None else tema.claro)


def silueta_en(img, x, y, w, h, a, tema=SANB):
    """Recuadro con una silueta neutra, para una persona sin foto confirmada."""
    if a <= 0:
        return
    P.ventana(img, None, x, y, w, h, a=a, radio=10, borde=tema.claro, fondo_vacio=mezcla(tema.panel, tema.claro, 0.08))
    cp = Capa()
    cp.tinta(mezcla(tema.tenue, tema.panel, 0.35), a)
    P.icono_persona(cp.c, x + w / 2, y + h * 0.58, w * 0.62)
    cp.componer(img, sombra=0)


def foto_tintada(ruta: str, tema: Tema = None, fuerza: float = 0.10) -> Image.Image | None:  # noqa: F821
    """Foto de persona con el tinte ligero de la paleta del lugar (tratamiento normal de personas)."""
    im = P.cargar(ruta)
    if im is None:
        return None
    tema = tema or SANB
    a = np.asarray(im, np.float32) / 255.0
    lin = a ** 2.2
    lum = (lin * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    tono = np.asarray(tema.acento if tema is MANZANA else SB["arena"], np.float32) ** 2.2
    lin = lin * (1 - fuerza) + lum * tono * 1.4 * fuerza
    return Image.fromarray((np.clip(lin, 0, 1) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8))


# =========================================================================== título


def titulo() -> TarjetaTitulo:
    t = TarjetaTitulo(NUMERO, guion.leer()[NUMERO].titulo, SB["dorado"], P.SANB.claro)
    t.cine = CINE_SB
    return t


# =========================================================================== 3.0


class Sub30(Sub3):
    """California; los atacantes; el edificio de noche y vacío; el iPhone 5C, apagado."""

    def preparar(self) -> None:
        o = self.o
        self.mapa = P.MapaCalifornia()
        self.farook = foto_tintada("3.0_farook.png")
        self.malik = foto_tintada("3.0_malik.jpg")
        self.iphone = Foto("3.0_iphone_5c.jpg")
        self.t_malik = self.en(1, "tashfeen")
        self.t_fiesta = self.en(1, "fiesta")
        self.c_foto = o[4]
        self.c_evid = o[5] + 1.2                         # el iPhone real, y luego el de la mesa del FBI
        self.seg = Segmentos([o[1], o[2], self.c_foto, self.c_evid], CRUCE)
        self.ini_centro = o[2] - CRUCE / 2
        self.centro = Plano3D("e03_centro_noche", self.c_foto + CRUCE / 2 - self.ini_centro + 0.2, motor=MOTOR["e03_centro_noche"])
        self.ini_evid = self.c_evid - CRUCE / 2
        self.evid = Plano3D("e03_iphone_evidencia", self.d - self.ini_evid + 0.2, motor=MOTOR["e03_iphone_evidencia"])
        self.planos3d = [self.centro, self.evid]

    def _mapa(self, t):
        u = suave(lim(t / (self.m(1) + 0.6)))
        img, sx, sy, _ = self.mapa.ver(u, P.SAN_BERNARDINO_LL, 3.0)
        luz = Luces()
        luz.punto(sx, sy, 24, SB["dorado"], 0.55 + 0.35 * math.sin(t * 3.2), forma="gauss")
        img += luz.resultado()
        cp = Capa()
        anillo = (t * 0.7) % 1.0
        cp.tinta(SB["dorado"], 0.8 * (1 - anillo))
        cp.c.set_line_width(3)
        cp.c.arc(sx, sy, 12 + 60 * anillo, 0, TAU)
        cp.c.stroke()
        cp.tinta(SB["dorado"])
        cp.c.arc(sx, sy, 9, 0, TAU)
        cp.c.fill()
        img = cp.componer(img, sombra=0.3)
        rotulo(img, "San Bernardino", sx + 28, sy + 12, 44, SANB.claro, aparece(t, 0.4, 0.8))
        lx, ly = self.mapa.proy(*P.LOS_ANGELES_LL)
        oscurecer(img, True, 360, 0.55)
        leyenda(img, "California", "2 de diciembre de 2015", aparece(t, 0.3, 0.8))
        return img

    def _atacantes(self, t):
        img = self.fondo()
        w, h = 400, 480
        x1, x2, y = 520, 1000, 200
        a1 = aparece(t, self.m(1) + 0.1, 0.7)
        a2 = aparece(t, self.t_malik - 0.2, 0.7)
        if self.farook is not None:
            persona_en(img, self.farook, x1, y, w, h, t, self.m(1), a1, cy=0.42)
        else:
            silueta_en(img, x1, y, w, h, a1)
        if self.malik is not None:
            persona_en(img, self.malik, x2, y, w, h, t, self.t_malik, a2, cy=0.45)
        else:
            silueta_en(img, x2, y, w, h, a2)
        rotulo(img, "Syed Rizwan Farook", x1 + w / 2, y + h + 66, 38, SANB.claro, a1, "centro")
        rotulo(img, "Tashfeen Malik", x2 + w / 2, y + h + 66, 38, SANB.claro, a2, "centro")
        a3 = aparece(t, self.t_fiesta, 0.8)
        rotulo(img, "fiesta de fin de año de sus compañeros de trabajo", W / 2, 930, 30, SANB.tenue, a3, "centro",
               nombre="Inter-Regular.ttf")
        return img

    def _centro(self, t):
        img = self.centro.cuadro(t - self.ini_centro)
        oscurecer(img, True, 380, 0.6)
        leyenda(img, "San Bernardino · de noche", "Inland Regional Center", aparece(t, self.m(2) + 0.2, 0.8))
        rotulo(img, "14 víctimas", W - 120, H - 140, 52, SANB.claro, aparece(t, self.m(2) + 0.5, 0.8), "der")
        return img

    def _iphone(self, t):
        z, cx, cy = recorrido(t - self.c_foto, self.c_evid - self.c_foto + 1.0, 1.0, 1.07, (0.5, 0.52), (0.46, 0.55))
        img = self.iphone.ver(z, cx, cy) if self.iphone.existe else self.fondo()
        oscurecer(img, True, 420, 0.7)
        leyenda(img, "", "iPhone 5C", aparece(t, self.c_foto + 0.3, 0.7))
        return img

    def _evidencia(self, t):
        img = self.evid.cuadro(t - self.ini_evid)
        oscurecer(img, True, 380, 0.55)
        leyenda(img, "propiedad del condado", "teléfono de trabajo", aparece(t, self.c_evid + 0.2, 0.7, self.m(6) - 0.1, 0.5))
        a = aparece(t, self.m(6) + 0.4, 0.7)
        cp = Capa()
        cp.tinta(SANB.claro, a)
        P.icono_power(cp.c, 150, H - 158, 46, 5)
        cp.componer(img, sombra=0.3)
        antetitulo(img, "en manos del FBI", 122, H - 222, SANB.tenue, a)
        rotulo(img, "apagado", 196, H - 140, 56, SANB.claro, a)
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return self.mezclar(t, (self._mapa, self._atacantes, self._centro, self._iphone, self._evidencia))

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("viento", 0.0, sfx.viento(d + 0.5, 300, 0.5), -8, 1.5, 1.5)
        m.agregar("sirenas", self.m(2) - 0.5, S.sirena_eeuu(self.c_foto - self.m(2) + 3.0, 301), -6, 2.0, 2.5)
        m.agregar("helicóptero", self.m(3), S.helicoptero(self.c_foto - self.m(3) + 3.0, 302), -9, 2.0, 2.5)
        m.agregar("bolsa", self.c_evid + 0.2, sfx.bolsa_evidencia(1.6, 303), -6)
        return m.x[:n]


# =========================================================================== 3.1


class Sub31(Sub3):
    """La contraseña de iCloud que se cambió; cómo funciona el respaldo; la sesión que deja de valer;
    Apple contra el FBI; los respaldos que Farook había apagado."""

    def preparar(self) -> None:
        o = self.o
        self.captura = P.cargar("3.1_icloud_ajustes.png")
        self.t_cambia = self.en(0, "cambia")
        self.t_pedido = self.en(0, "pedido")
        self.t_corriente = self.en(4, "corriente")
        self.t_wifi = self.en(4, "wifi")
        self.t_bloq = self.en(4, "bloqueada")
        self.seg = Segmentos([o[3], o[4], o[5], o[8]], CRUCE)

    # ---- A: la cuenta, la nube y la línea de tiempo
    def _cuenta(self, t):
        img = self.fondo()
        m = self.m
        T = SANB
        a0 = aparece(t, 0.3, 0.8)
        rotulo(img, "4 días después del ataque", 160, 170, 36, T.acento, a0)
        cp = Capa()
        c = cp.c
        P.tarjeta(c, 160, 300, 640, 330, 22, T.panel, a0, borde=T.claro)
        cp.tinta(T.claro, a0)
        P.icono_nube(c, 250, 380, 110, relleno=False, g=6)
        P.tarjeta(c, 200, 500, 560, 86, 14, mezcla(T.panel, NEGRO, 0.4), a0, borde=T.tenue)
        cambio = lim((t - self.t_cambia) / 1.6)
        borrar = int(8 * lim(cambio / 0.4))
        escribir = int(9 * lim((cambio - 0.45) / 0.55))
        puntos = (8 - borrar) if cambio < 0.45 else escribir
        cp.tinta(T.acento if cambio >= 0.45 else T.claro, a0)
        for k in range(puntos):
            c.arc(250 + k * 42, 543, 10, 0, TAU)
            c.fill()
        img = cp.componer(img, sombra=0.5, brillo=0.25, col_brillo=T.acento if cambio > 0 else T.claro)
        rotulo(img, "Cuenta de iCloud", 330, 395, 42, T.claro, a0)
        rotulo(img, "del teléfono", 332, 440, 28, T.tenue, a0, nombre="Inter-Regular.ttf")
        rotulo(img, "contraseña", 204, 488, 22, T.tenue, a0, nombre="Inter-Regular.ttf")
        a_c = aparece(t, self.t_cambia + 1.4, 0.6)
        rotulo(img, "cambiada por un técnico del condado", 200, 680, 30, T.acento, a_c)
        rotulo(img, "a pedido del FBI", 200, 724, 28, T.tenue, aparece(t, max(self.t_pedido, self.t_cambia + 1.8), 0.6),
               nombre="Inter-Regular.ttf")
        # la nube con los respaldos
        a1 = aparece(t, m(1) - 0.2, 0.8)
        if a1 > 0:
            cp = Capa()
            cp.tinta(T.claro, a1)
            P.icono_nube(cp.c, 1380, 400, 360, g=7)
            for k in range(3):
                cp.tinta(T.acento if k == 2 else T.claro, a1 * (0.55 + 0.15 * k))
                DG.archivo(cp.c, 1290 + k * 52, 380 + k * 14, 86, 4)
            img = cp.componer(img, sombra=0.4, brillo=0.3, col_brillo=T.claro)
            rotulo(img, "respaldos en la nube", 1380, 560, 32, T.claro, a1, "centro")
        # línea de tiempo: el último respaldo, el ataque y el cambio de contraseña
        a2 = aparece(t, m(2) - 0.2, 0.8)
        if a2 > 0:
            def x_dia(d):
                return 300 + d * 26.0
            cp = Capa()
            c = cp.c
            p = suave(lim((t - m(2) + 0.2) / 1.2))
            cp.tinta(T.tenue, a2)
            DG.linea(c, [(x_dia(-4), 880), (x_dia(52), 880)], p, 3)
            marcas = ((0, T.acento), (44, T.claro), (48, T.claro))
            for d, col in marcas:
                cp.tinta(col, a2 * p)
                c.arc(x_dia(d), 880, 11, 0, TAU)
                c.fill()
            b = aparece(t, m(2) + 1.6, 0.8)
            cp.tinta(T.acento, 0.85 * b)
            c.set_line_width(3)
            c.move_to(x_dia(0), 840)
            c.line_to(x_dia(0), 826)
            c.line_to(x_dia(44), 826)
            c.line_to(x_dia(44), 840)
            c.stroke()
            img = cp.componer(img, sombra=0.3, brillo=0.3, col_brillo=T.acento)
            rotulo(img, "19 oct", x_dia(0), 930, 30, T.acento, a2 * p, "centro")
            rotulo(img, "último respaldo", x_dia(0), 966, 24, T.tenue, a2 * p, "centro", nombre="Inter-Regular.ttf")
            rotulo(img, "2 dic", x_dia(44), 930, 30, T.claro, a2 * p, "centro")
            rotulo(img, "ataque", x_dia(44), 966, 24, T.tenue, a2 * p, "centro", nombre="Inter-Regular.ttf")
            rotulo(img, "4 días después", x_dia(48) + 30, 930, 24, T.claro, a2 * p, "izq", nombre="Inter-Regular.ttf")
            rotulo(img, "contraseña cambiada", x_dia(48) + 30, 966, 24, T.tenue, a2 * p, "izq", nombre="Inter-Regular.ttf")
            rotulo(img, "casi 7 semanas sin respaldo", x_dia(22), 806, 30, T.acento, b, "centro")
        return img

    # ---- B: la captura real de ajustes
    def _captura(self, t):
        img = self.fondo()
        T = SANB
        u = t - self.m(3)
        a = aparece(t, self.m(3) - 0.3, 0.8)
        h = 860
        w = int(h * (self.captura.width / self.captura.height)) if self.captura is not None else 640
        z = 1.0 + 0.10 * suave(lim(u / 7.0))
        P.ventana(img, self.captura, 1000, 110, w, h, a=a, zoom=z, cx=0.5, cy=0.28, radio=22, borde=T.claro)
        antetitulo(img, "ajustes del iPhone", 200, 440, T.tenue, a)
        rotulo(img, "Respaldo de iCloud", 196, 510, 58, T.claro, a)
        rotulo(img, "automático", 198, 572, 40, T.acento, aparece(t, self.m(3) + 1.6, 0.7))
        return img

    # ---- C: las tres condiciones; la sesión; el bloqueo
    def _condiciones(self, t):
        img = self.fondo()
        m = self.m
        T = SANB
        cp = Capa()
        c = cp.c
        a_t = aparece(t, m(4) - 0.2, 0.7)
        tiempos_ = (self.t_corriente, self.t_wifi, self.t_bloq)
        todas = aparece(t, self.t_bloq + 1.0, 0.6)
        for k, (tk, x) in enumerate(zip(tiempos_, (560, 960, 1360))):
            # las tres casillas están desde el principio, apagadas; cada una se enciende al nombrarla
            a = a_t * (0.22 + 0.78 * aparece(t, tk - 0.3, 0.5))
            if a <= 0:
                continue
            col = T.acento if todas > 0.5 else T.claro
            P.tarjeta(c, x - 120, 300, 240, 240, 40, T.panel, a_t, borde=col, a_borde=0.6 * a / max(a_t, 1e-3), grosor=2.5)
            cp.tinta(col, a)
            if k == 0:
                P.icono_enchufe(c, x, 420, 150, 9)
            elif k == 1:
                P.icono_wifi(c, x, 410, 170, 12)
            else:
                DG.candado(c, x, 430, 120, cerrado=1.0)
        if todas > 0:
            cp.tinta(T.claro, 0.85 * todas)
            DG.telefono(c, 700, 790, 170, 4)
            P.icono_nube(c, 1230, 780, 170, g=5)
            u = (t * 0.6) % 1.0
            DG.flecha(c, (780, 790), (1120, 790), todas, 4, curva=-50)
            cp.tinta(T.acento, todas)
            q = np.array([780 + 340 * u, 790 - 50 * 4 * u * (1 - u) * 0.5 * 2])
            c.arc(q[0], q[1], 8, 0, TAU)
            c.fill()
        img = cp.componer(img, sombra=0.45, brillo=0.35 * (0.4 + 0.6 * todas), col_brillo=T.acento if todas > 0.5 else T.claro)
        rotulo(img, "tres condiciones al mismo tiempo", W / 2, 210, 40, T.claro, a_t, "centro")
        for tk, x, txt in zip(tiempos_, (560, 960, 1360), ("conectado a la corriente", "en una red wifi", "pantalla bloqueada")):
            rotulo(img, txt, x, 600, 28, T.claro, aparece(t, tk - 0.1, 0.5), "centro", nombre="Inter-Regular.ttf")
        rotulo(img, "el respaldo sube solo", 965, 900, 32, T.acento, todas, "centro")
        return img

    def _sesion(self, t):
        img = self.fondo()
        m = self.m
        T = SANB
        cp = Capa()
        c = cp.c
        a = aparece(t, m(5) - 0.4, 0.7)
        cp.tinta(T.claro, a)
        px, py, pw, ph = DG.telefono(c, 520, 560, 500, 5, pantalla=mezcla(T.panel, NEGRO, 0.3))
        P.icono_nube(c, 1420, 520, 420, g=7)
        # el pase de la sesión viaja del teléfono a la nube
        viaje = suave(lim((t - m(5) - 0.8) / 1.6))
        vencida = aparece(t, m(6) + 0.6, 0.5)
        x = 660 + (1400 - 660) * viaje
        y_p = 560 - 20 * viaje
        col_pase = mezcla(T.acento, T.tenue, vencida)
        P.tarjeta(c, x - 70, y_p - 43, 140, 86, 12, mezcla(T.panel, col_pase, 0.25), a, borde=col_pase, a_borde=0.9, grosor=3)
        cp.tinta(col_pase, a)
        DG.llave(c, x, y_p, 90)
        if vencida > 0:
            cp.tinta(ROJO, vencida)
            DG.cruz(c, x, y_p, 70, 8)
        # la contraseña cambia del lado de la nube
        if t > m(6) - 0.2:
            b = aparece(t, m(6) - 0.2, 0.5)
            P.tarjeta(c, 1290, 740, 260, 70, 12, mezcla(T.panel, NEGRO, 0.4), b, borde=T.acento)
            cp.tinta(T.acento, b)
            for k in range(int(6 * lim((t - m(6)) / 0.9))):
                c.arc(1325 + k * 38, 775, 9, 0, TAU)
                c.fill()
        # el respaldo intenta subir y choca a medio camino
        if t > m(7) - 0.2:
            b = aparece(t, m(7) - 0.2, 0.5)
            u = ((t - m(7)) * 0.7) % 1.0
            cp.tinta(T.claro, 0.8 * b)
            DG.linea(c, [(660, 420), (960, 420)], 1.0, 4)
            cp.tinta(ROJO, b)
            c.set_line_width(6)
            c.move_to(975, 380)
            c.line_to(975, 460)
            c.stroke()
            cp.tinta(T.claro, b * (1 - u))
            c.arc(660 + 300 * u, 420, 8, 0, TAU)
            c.fill()
            cp.tinta(T.acento, b)
            P.tarjeta(c, px + 18, py + ph * 0.36, pw - 36, 110, 14, mezcla(T.panel, T.claro, 0.12), b, borde=T.acento)
        img = cp.componer(img, sombra=0.45, brillo=0.3, col_brillo=T.acento)
        rotulo(img, "sesión", x, y_p - 58, 26, col_pase, a * (1 - 0.3 * vencida), "centro")
        rotulo(img, "iCloud", 1420, 700, 40, T.claro, a, "centro")
        rotulo(img, "el teléfono se identifica con la sesión", W / 2, 230, 36, T.claro, aparece(t, m(5), 0.6, m(6) - 0.3), "centro")
        rotulo(img, "contraseña cambiada desde fuera", 1420, 860, 28, T.acento, aparece(t, m(6), 0.6), "centro")
        rotulo(img, "la sesión deja de valer", W / 2, 230, 36, T.claro, aparece(t, m(6) + 0.6, 0.6, m(7) - 0.3), "centro")
        if t > m(7) - 0.2:
            b = aparece(t, m(7) - 0.2, 0.5)
            rotulo(img, "Escribe la", 520, py + ph * 0.36 + 48, 22, T.claro, b, "centro", nombre="Inter-Regular.ttf")
            rotulo(img, "contraseña nueva", 520, py + ph * 0.36 + 82, 22, T.acento, b, "centro")
            rotulo(img, "no sube nada hasta escribirla en el teléfono", W / 2, 230, 36, T.claro, aparece(t, m(7) + 0.3, 0.6), "centro")
        return img

    # ---- D: Apple contra el FBI; los respaldos apagados
    def _versiones(self, t):
        img = self.fondo()
        m = self.m
        T = SANB
        cp = Capa()
        c = cp.c
        aA = aparece(t, m(8) - 0.3, 0.7)
        aF = aparece(t, m(9) - 0.3, 0.7)
        cp.tinta(T.tenue, 0.5 * max(aA, aF))
        c.set_line_width(2)
        c.move_to(W / 2, 200)
        c.line_to(W / 2, 760)
        c.stroke()
        # Apple: con la contraseña original, quizá se habría respaldado en una red conocida
        if aA > 0:
            cp.tinta(T.claro, aA)
            DG.telefono(c, 260, 500, 230, 4)
            P.icono_wifi(c, 480, 490, 120, 8)
            P.icono_nube(c, 760, 480, 190, g=5)
            c.save()
            c.set_dash([14, 12])
            cp.tinta(T.acento, aA)
            DG.flecha(c, (330, 430), (680, 430), suave(lim((t - m(8) - 1.5) / 1.2)), 4, curva=-60)
            c.restore()
        if aF > 0:
            cp.tinta(T.claro, aF)
            DG.telefono(c, 1220, 500, 230, 4)
            P.icono_power(c, 1220, 500, 70, 6)
            P.icono_wifi(c, 1500, 490, 120, 8)
            cp.tinta(T.acento, aF)
            DG.candado(c, 1545, 540, 56)
            x = aparece(t, m(9) + 2.0, 0.5)
            cp.tinta(ROJO, x)
            DG.cruz(c, 1700, 490, 80, 9)
        # los respaldos que Farook había apagado
        aR = aparece(t, m(10) - 0.2, 0.6)
        if aR > 0:
            for k in range(3):
                x0 = 560 + k * 300
                apaga = suave(lim((t - m(10) - 0.5 - 0.35 * k) / 0.35))
                col = mezcla(T.acento, T.tenue, apaga)
                P.tarjeta(c, x0, 880, 92, 50, 25, mezcla(T.panel, col, 0.5), aR, borde=col, a_borde=0.8, grosor=2)
                cp.tinta(T.claro, aR)
                c.arc(x0 + 25 + 42 * (1 - apaga), 905, 20, 0, TAU)
                c.fill()
                cp.tinta(T.tenue, 0.6 * aR)
                D.rect_redondeado(c, x0 + 110, 896, 140 - 30 * (k % 2), 16, 8)
                c.fill()
        img = cp.componer(img, sombra=0.45, brillo=0.3, col_brillo=T.acento)
        antetitulo(img, "Apple dijo", 160, 210, T.acento, aA)
        rotulo(img, "con la contraseña original…", 160, 262, 34, T.claro, aA)
        rotulo(img, "quizá se respaldaba solo", 520, 690, 32, T.acento, aparece(t, m(8) + 2.6, 0.6), "centro")
        rotulo(img, "en una red wifi conocida", 520, 732, 28, T.tenue, aparece(t, m(8) + 2.9, 0.6), "centro", nombre="Inter-Regular.ttf")
        antetitulo(img, "El FBI respondió", 1120, 210, T.acento, aF)
        rotulo(img, "recién encendido…", 1120, 262, 34, T.claro, aF)
        rotulo(img, "no entra a ningún wifi", 1460, 690, 32, T.claro, aparece(t, m(9) + 2.0, 0.6), "centro")
        rotulo(img, "sin su contraseña", 1460, 732, 28, T.tenue, aparece(t, m(9) + 2.3, 0.6), "centro", nombre="Inter-Regular.ttf")
        rotulo(img, "Farook había apagado varios respaldos", W / 2, 1010, 32, T.claro, aparece(t, m(10) + 0.2, 0.6), "centro")
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return self.mezclar(t, (self._cuenta, self._captura, self._condiciones, self._sesion, self._versiones))

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, S.zumbido(d, 3101), -14, 1.5, 1.5)
        m.agregar("teclado", self.t_cambia, sfx.teclado(1.6, 3102), -8)
        m.agregar("aviso", self.t_bloq + 1.0, S.notificacion(3103), -6)
        m.agregar("error", self.m(6) + 0.6, sfx.error_suave(3104), -4)
        m.agregar("error", self.m(7) + 0.5, sfx.error_suave(3105), -6)
        for k in range(3):
            m.agregar("interruptor", self.m(10) + 0.5 + 0.35 * k, S.desbloqueo(3106 + k), -8)
        return m.x[:n]


# =========================================================================== 3.2


class Sub32(Sub3):
    """La orden de la jueza; Tim Cook y su carta; los titulares; la línea de tiempo hasta «No dice cómo»."""

    def preparar(self) -> None:
        o = self.o
        self.cook = foto_tintada("3.2_tim_cook.jpg")
        self.carta = P.cargar("3.2_carta_tim_cook.png")
        self.titulares = P.cargar("3.2_titulares_2016.jpg")
        self.t_borrado = self.en(0, "borrado")
        self.t_esperas = self.en(0, "esperas")
        self.t_probar = self.en(0, "probar")
        self.seg = Segmentos([o[1], o[2], o[3], o[4]], CRUCE)

    def _orden(self, t):
        img = self.fondo()
        T = SANB
        a = aparece(t, 0.3, 0.8)
        cp = Capa()
        c = cp.c
        P.tarjeta(c, 220, 330, 300, 300, 150, T.panel, a, borde=T.acento, a_borde=0.6, grosor=2.5)
        cp.tinta(T.acento, a)
        P.icono_balanza(c, 370, 480, 190, 7)
        b = aparece(t, 1.4, 0.7)
        P.tarjeta(c, 640, 300, 1060, 400, 24, T.panel, b, borde=T.claro)
        for k, tk in enumerate((self.t_borrado, self.t_esperas)):
            ak = aparece(t, tk - 0.1, 0.4)
            cp.tinta(ROJO, ak)
            DG.cruz(c, 720, 500 + k * 90, 36, 7)
        img = cp.componer(img, sombra=0.5, brillo=0.25, col_brillo=T.acento)
        antetitulo(img, "febrero de 2016", 220, 260, T.acento, a)
        rotulo(img, "una jueza ordena a Apple:", 690, 380, 40, T.claro, b)
        rotulo(img, "un iOS especial para este teléfono", 690, 432, 32, T.acento, aparece(t, 2.4, 0.6))
        rotulo(img, "sin borrado al décimo intento", 770, 512, 36, T.claro, b * (0.2 + 0.8 * aparece(t, self.t_borrado - 0.1, 0.4)))
        rotulo(img, "sin esperas entre intentos", 770, 602, 36, T.claro, b * (0.2 + 0.8 * aparece(t, self.t_esperas - 0.1, 0.4)))
        # contraseñas a máquina
        c_ = aparece(t, self.t_probar - 0.2, 0.6)
        if c_ > 0:
            puntos_codigo(img, W / 2, 830, t - self.t_probar, c_, T)
            rotulo(img, "contraseñas probadas a máquina", W / 2, 925, 30, T.tenue, c_, "centro", nombre="Inter-Regular.ttf")
        return img

    def _cook(self, t):
        img = self.fondo()
        T = SANB
        a = aparece(t, self.m(1) - 0.3, 0.7)
        persona_en(img, self.cook, 300, 170, 520, 700, t, self.m(1), a, cy=0.3)
        rotulo(img, "Tim Cook", 940, 470, 72, T.claro, a)
        rotulo(img, "director de Apple", 944, 534, 34, T.tenue, a, nombre="Inter-Regular.ttf")
        rotulo(img, "publica una carta abierta", 944, 620, 38, T.acento, aparece(t, self.m(1) + 1.6, 0.6))
        return img

    def _carta(self, t):
        img = self.fondo()
        T = SANB
        a = aparece(t, self.m(2) - 0.3, 0.7)
        h = 900
        w = int(h * self.carta.width / self.carta.height) if self.carta is not None else 800
        z = 1.0 + 0.16 * suave(lim((t - self.m(2)) / 6.0))
        P.ventana(img, self.carta, 1000, 90, w, h, a=a, zoom=z, cx=0.42, cy=0.18, radio=8, borde=T.claro)
        antetitulo(img, "carta abierta de Tim Cook", 160, 400, T.tenue, a)
        rotulo(img, "«una llave maestra»", 156, 480, 58, T.claro, aparece(t, self.m(2) + 0.6, 0.6))
        rotulo(img, "para cualquier iPhone", 160, 540, 38, T.acento, aparece(t, self.m(2) + 1.4, 0.6))
        cp = Capa()
        cp.tinta(T.acento, aparece(t, self.m(2) + 0.6, 0.6))
        DG.llave(cp.c, 290, 680, 240)
        cp.componer(img, sombra=0.4, brillo=0.4, col_brillo=T.acento)
        return img

    def _titulares(self, t):
        img = self.fondo()
        T = SANB
        a = aparece(t, self.m(3) - 0.3, 0.7)
        w = 1400
        h = int(w * self.titulares.height / self.titulares.width) if self.titulares is not None else 850
        z = 1.0 + 0.06 * suave(lim((t - self.m(3)) / 3.0))
        P.ventana(img, self.titulares, (W - w) / 2, 50, w, h, a=a, zoom=z, cx=0.5, cy=0.3, radio=8, borde=T.claro)
        rotulo(img, "Apple se niega a obedecer", W / 2, 1000, 44, T.claro, aparece(t, self.m(3), 0.5), "centro")
        return img

    def _linea(self, t):
        img = self.fondo()
        m = self.m
        T = SANB
        cp = Capa()
        c = cp.c
        a = aparece(t, m(4) - 0.4, 0.7)
        cp.tinta(T.tenue, a)
        DG.linea(c, [(180, 640), (1740, 640)], suave(lim((t - m(4) + 0.4) / 1.0)), 3)
        marcas = ((300, m(4) - 0.4, T.tenue), (1120, m(4), T.acento), (1260, m(4) + 0.6, T.claro), (1560, m(6), T.acento))
        for x, tk, col in marcas:
            ak = aparece(t, tk, 0.5)
            cp.tinta(col, ak)
            c.arc(x, 640, 12, 0, TAU)
            c.fill()
        # alguien ofreció otra forma de entrar
        b = aparece(t, m(5) - 0.2, 0.6)
        if b > 0:
            cp.tinta(T.tenue, b)
            P.icono_persona(c, 1120, 400, 170)
        e = aparece(t, m(6) + 0.3, 0.6)
        if e > 0:
            cp.tinta(T.acento, e)
            DG.candado(c, 1560, 420, 110, cerrado=1.0 - suave(lim((t - m(6) - 0.6) / 0.8)))
        img = cp.componer(img, sombra=0.45, brillo=0.3, col_brillo=T.acento)
        rotulo(img, "febrero", 300, 700, 30, T.tenue, a, "centro")
        rotulo(img, "la orden", 300, 738, 24, T.tenue, a, "centro", nombre="Inter-Regular.ttf")
        rotulo(img, "un día antes", 1120, 700, 30, T.acento, aparece(t, m(4), 0.5), "centro")
        rotulo(img, "el FBI pide pausar", 1120, 738, 24, T.claro, aparece(t, m(4) + 0.3, 0.5), "centro", nombre="Inter-Regular.ttf")
        rotulo(img, "audiencia", 1290, 800, 30, T.claro, aparece(t, m(4) + 0.6, 0.5), "centro")
        rotulo(img, "?", 1120, 330, 80, T.acento, b, "centro", nombre="Inter-Light.ttf")
        rotulo(img, "alguien ofrece otra forma de entrar", 1120, 540, 26, T.claro, b, "centro", nombre="Inter-Regular.ttf")
        rotulo(img, "una semana después", 1560, 700, 30, T.acento, aparece(t, m(6), 0.5), "centro")
        rotulo(img, "retira la demanda", 1560, 738, 24, T.claro, aparece(t, m(6) + 0.3, 0.5), "centro", nombre="Inter-Regular.ttf")
        rotulo(img, "teléfono abierto", 1560, 540, 26, T.acento, e, "centro", nombre="Inter-Regular.ttf")
        rotulo(img, "¿Cómo?", 460, 430, 110, T.acento, aparece(t, m(7) + 0.1, 0.8), "centro", nombre="Inter-Light.ttf")
        rotulo(img, "2016", 180, 600, 30, T.tenue, a)
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return self.mezclar(self.quieto(t),
                            (self._orden, self._cook, self._carta, self._titulares, self._linea))

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, S.zumbido(d, 3201), -16, 1.5, 1.5)
        m.agregar("mazo", 0.5, S.mazo(3202), -2)
        m.agregar("teclado", self.t_probar, sfx.teclado(2.0, 3203, 2.2), -10, 0.1, 0.5)
        m.agregar("papel", self.m(2) - 0.4, S.papel(1.2, 3204), -4)
        m.agregar("papel", self.m(3) - 0.4, S.papel(1.0, 3205), -6)
        m.agregar("mazo", self.m(6) + 0.3, S.mazo(3206), -5)
        return m.x[:n]


# =========================================================================== 3.3


class Sub33(Sub3):
    """Cinco años sin saber; el Washington Post y Azimuth; los cinco pasos; la puerta: el puerto
    Lightning (foto real y 3D) y la conversación con lo que se conecta, aunque esté bloqueado."""

    def preparar(self) -> None:
        o = self.o
        self.articulo = P.cargar("3.3_washington_post_2021.png")
        self.puerto = Foto("3.3_puerto_lightning.jpg")
        self.t_cargador = self.en(4, "cargador")
        self.t_audif = self.en(4, "audífonos")
        self.t_compu = self.en(4, "computadora")
        self.c_3d = o[4] + 0.6
        self.seg = Segmentos([o[1], o[2], o[3], self.c_3d, o[5], o[6]], CRUCE)
        self.ini_3d = self.c_3d - CRUCE / 2
        dur = o[5] + CRUCE / 2 - self.ini_3d + 0.2
        llega = round(min(dur - 1.5, max(2.8, self.en(4, "lightning") + 0.5 - self.ini_3d)) * 10) / 10   # entra al decir «puerto Lightning»
        self.llega = self.ini_3d + llega
        self.lightning = Plano3D("e03_puerto_lightning", dur, motor=MOTOR["e03_puerto_lightning"], llega=llega)
        self.planos3d = [self.lightning]

    def _pasos(self, img, t, activo):
        o = self.o
        ap = [aparece(t, o[2] + 0.4 + 0.45 * k, 0.5) for k in range(5)]
        P.pasos(img, activo, 1.0, SANB, aparicion=ap)

    def _cinco_anos(self, t):
        img = self.fondo()
        T = SANB
        cp = Capa()
        c = cp.c
        a = aparece(t, 0.2, 0.6)
        p = suave(lim(t / 2.4))
        cp.tinta(T.tenue, a)
        DG.linea(c, [(360, 560), (1560, 560)], 1.0, 3)
        for x in (360, 1560):
            c.arc(x, 560, 12, 0, TAU)
            c.fill()
        cp.tinta(T.acento, a)
        c.arc(360 + 1200 * p, 560, 16, 0, TAU)
        c.fill()
        img = cp.componer(img, sombra=0.3, brillo=0.4, col_brillo=T.acento)
        rotulo(img, "2016", 360, 630, 44, T.claro, a, "centro")
        rotulo(img, "2021", 1560, 630, 44, T.claro, a, "centro")
        rotulo(img, "?", 360 + 1200 * p, 500, 70, T.acento, a, "centro", nombre="Inter-Light.ttf")
        rotulo(img, "5 años sin saber quién lo hizo", W / 2, 380, 40, T.claro, aparece(t, 0.6, 0.6), "centro")
        return img

    def _azimuth(self, t):
        img = self.fondo()
        T = SANB
        a = aparece(t, self.m(1) - 0.3, 0.7)
        h = 900
        w = int(h * self.articulo.width / self.articulo.height) if self.articulo is not None else 800
        z = 1.0 + 0.04 * suave(lim((t - self.m(1)) / 8.0))
        P.ventana(img, self.articulo, 1060, 90, w, h, a=a, zoom=z, cx=0.5, cy=0.3, radio=8, borde=T.claro)
        antetitulo(img, "The Washington Post · 2021", 160, 330, T.tenue, a)
        rotulo(img, "Azimuth", 156, 430, 96, T.claro, aparece(t, self.en(1, "azimuth"), 0.6))
        rotulo(img, "Australia · empresa pequeña", 160, 500, 34, T.acento, aparece(t, self.en(1, "australiana"), 0.6))
        rotulo(img, "encuentra fallas de seguridad", 160, 590, 32, T.claro, aparece(t, self.en(1, "encontrar"), 0.6),
               nombre="Inter-Regular.ttf")
        rotulo(img, "y las vende a gobiernos", 160, 636, 32, T.claro, aparece(t, self.en(1, "venderlas"), 0.6), nombre="Inter-Regular.ttf")
        return img

    def _camino(self, t):
        img = self.fondo()
        T = SANB
        o = self.o
        cp = Capa()
        c = cp.c
        xs = [W / 2 + (k - 2) * 330 for k in range(5)]
        for k, x in enumerate(xs):
            ak = aparece(t, o[2] + 0.4 + 0.45 * k, 0.5)
            if k < 4:
                cp.tinta(T.tenue, 0.6 * ak)
                DG.linea(c, [(x + 70, 520), (xs[k + 1] - 70, 520)], suave(lim((t - o[2] - 0.6 - 0.45 * k) / 0.5)), 3)
            P.tarjeta(c, x - 62, 458, 124, 124, 62, T.panel, ak, borde=T.acento if k == 0 else T.claro, a_borde=0.7, grosor=3)
        img = cp.componer(img, sombra=0.45, brillo=0.3, col_brillo=T.acento)
        for k, x in enumerate(xs):
            ak = aparece(t, o[2] + 0.4 + 0.45 * k, 0.5)
            rotulo(img, str(k + 1), x, 545, 60, T.acento if k == 0 else T.claro, ak, "centro", nombre="Inter-Light.ttf")
            rotulo(img, P.PASOS[k], x, 650, 30, T.claro, ak, "centro")
        rotulo(img, "cómo entraron, paso por paso", W / 2, 330, 40, T.claro, aparece(t, o[2], 0.6), "centro")
        return img

    def _puerto(self, t):
        z, cx, cy = recorrido(t - self.m(3), self.c_3d - self.m(3) + 1.0, 1.0, 1.12, (0.5, 0.5), (0.5, 0.5))
        img = self.puerto.ver(z, cx, cy) * 0.92 if self.puerto.existe else self.fondo()
        oscurecer(img, False, 260, 0.7)
        oscurecer(img, True, 300, 0.55)
        self._pasos(img, t, 0)
        leyenda(img, "", "el puerto Lightning", aparece(t, self.m(3) + 0.2, 0.6))
        return img

    def _cable(self, t):
        img = self.lightning.cuadro(t - self.ini_3d)
        oscurecer(img, False, 260, 0.7)
        self._pasos(img, t, 0)
        dentro = aparece(t, self.llega - 0.2, 0.3)
        a = aparece(t, self.en(4, "preguntarle") - 0.3, 0.6)
        if a > 0:
            P.panel_esmerilado(img, 1240, 300, 1800, 860, a, 0.5, filo=SANB.claro)
            rotulo(img, "¿qué eres?", 1520, 380, 46, SANB.acento, a, "centro")
            cp = Capa()
            items = ((self.t_cargador, P.icono_cargador, "un cargador"), (self.t_audif, P.icono_audifonos, "unos audífonos"),
                     (self.t_compu, P.icono_portatil, "una computadora"))
            for k, (tk, fn, _) in enumerate(items):
                cp.tinta(SANB.claro, a * (0.25 + 0.75 * aparece(t, tk - 0.1, 0.4)))   # apagado hasta que se nombra
                fn(cp.c, 1330, 490 + k * 150, 100)
            img = cp.componer(img, sombra=0.3)
            for k, (tk, _, txt) in enumerate(items):
                rotulo(img, txt, 1420, 505 + k * 150, 34, SANB.claro, a * (0.25 + 0.75 * aparece(t, tk - 0.1, 0.4)))
        if dentro > 0 and a <= 0:
            leyenda(img, "", "conectado", dentro)
        return img

    def _bloqueado(self, t):
        img = self.fondo()
        T = SANB
        m = self.m
        cp = Capa()
        c = cp.c
        a = aparece(t, m(5) - 0.4, 0.7)
        cp.tinta(T.claro, a)
        DG.telefono(c, 720, 560, 520, 5, pantalla=mezcla(T.panel, NEGRO, 0.4))
        DG.candado(c, 720, 470, 90)
        cp.tinta(T.claro, a)
        DG.linea(c, [(720, 820), (720, 900), (1000, 920), (1180, 870)], 1.0, 5)
        P.icono_cargador(c, 1260, 820, 150)
        u = (t * 0.9) % 1.0
        for k in range(2):
            uu = (u + k * 0.5) % 1.0
            cp.tinta(T.acento, a * math.sin(math.pi * uu))
            x = 760 + 420 * (uu if k == 0 else 1 - uu)
            c.arc(x, 905 + 10 * math.sin(uu * 6), 9, 0, TAU)
            c.fill()
        carga = aparece(t, self.en(5, "cargarlo") - 0.2, 0.5)
        if carga > 0:
            cp.tinta(T.acento, carga)
            P.icono_rayo(c, 720, 640, 70)
        img = cp.componer(img, sombra=0.45, brillo=0.35, col_brillo=T.acento)
        rotulo(img, "aunque esté bloqueado", 1260, 520, 40, T.claro, aparece(t, m(5) + 0.5, 0.6), "centro")
        rotulo(img, "el teléfono le pregunta qué es", 1260, 575, 28, T.tenue, aparece(t, m(5) + 0.9, 0.6), "centro",
               nombre="Inter-Regular.ttf")
        rotulo(img, "si no, ni siquiera cargaría", 1260, 640, 28, T.acento, carga, "centro")
        self._pasos(img, t, 0)
        return img

    def _escucha(self, t):
        img = self.fondo()
        T = SANB
        m = self.m
        cp = Capa()
        c = cp.c
        a = aparece(t, m(6) - 0.4, 0.7)
        cp.tinta(T.claro, a)
        DG.caja(c, 380, 300, 1160, 560, 40, a, 4)
        cp.tinta(T.claro, a)
        DG.linea(c, [(160, 580), (380, 580)], 1.0, 8)
        b = aparece(t, m(6) + 0.6, 0.6)
        P.tarjeta(c, 470, 470, 380, 220, 22, mezcla(T.panel, T.acento, 0.15), b, borde=T.acento, a_borde=0.9, grosor=3)
        for k in range(3):
            r = 30 + k * 26 + 14 * ((t * 1.2) % 1.0)
            cp.tinta(T.acento, b * (0.8 - 0.22 * k))
            c.set_line_width(4)
            c.arc(470, 580, r, math.radians(140), math.radians(220))
            c.stroke()
        e = aparece(t, m(6) + 1.0, 0.7)                     # el resto del teléfono, cerrado con la contraseña
        P.tarjeta(c, 950, 380, 520, 400, 30, mezcla(T.panel, NEGRO, 0.3), e, borde=T.tenue)
        cp.tinta(T.tenue, e)
        DG.candado(c, 1210, 560, 140)
        img = cp.componer(img, sombra=0.45, brillo=0.35, col_brillo=T.acento)
        rotulo(img, "iPhone", 410, 350, 30, T.tenue, a)
        rotulo(img, "programa que atiende", 660, 560, 30, T.claro, b, "centro")
        rotulo(img, "lo que llega por el cable", 660, 600, 30, T.acento, b, "centro")
        rotulo(img, "todo lo demás espera", 1210, 700, 28, T.tenue, e, "centro", nombre="Inter-Regular.ttf")
        rotulo(img, "la contraseña", 1210, 740, 28, T.claro, e, "centro")
        rotulo(img, "escucha antes de que nadie escriba la contraseña", W / 2, 960, 34, T.claro, aparece(t, m(6) + 1.5, 0.6), "centro")
        self._pasos(img, t, 0)
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return self.mezclar(t, (self._cinco_anos, self._azimuth, self._camino, self._puerto, self._cable, self._bloqueado,
                                self._escucha))

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, S.zumbido(d, 3301), -15, 1.5, 1.5)
        m.agregar("papel", self.m(1) - 0.3, S.papel(1.0, 3302), -6)
        for k in range(5):
            m.agregar("paso", self.m(2) + 0.4 + 0.45 * k, S.desbloqueo(3303 + k), -10)
        m.agregar("conector", self.llega - 0.11, S.conector(3310), 0)
        for k, tk in enumerate((self.t_cargador, self.t_audif, self.t_compu)):
            m.agregar("aviso", tk, S.notificacion(3311 + k), -10)
        m.agregar("datos", self.m(6) + 0.6, sfx.datos(self.d - self.m(6) - 0.8, 3315, 10), -14, 0.5, 1.0)
        return m.x[:n]


# =========================================================================== 3.4


class Sub34(Sub3):
    """Segundo: de quién era el programa. Bibliotecas de código abierto; la de Mozilla, dentro del
    iPhone; si tiene un error, Apple lo hereda."""

    def preparar(self) -> None:
        self.mozilla = P.logo_blanco("3.4_logo_mozilla.png", 74)

    def cuadro(self, t: float) -> np.ndarray:
        img = self.fondo()
        T = SANB
        m = self.m
        cp = Capa()
        c = cp.c
        # un programa armado con piezas: casi nunca todo desde cero
        a1 = aparece(t, m(1) - 0.2, 0.6, m(3) - 0.3)
        gx = 765 - 465 * suave(lim((t - m(2) + 0.4) / 0.9))          # solo, al centro; luego se hace a un lado
        if a1 > 0:
            for i in range(3):
                for j in range(3):
                    reutil = (i + j) % 2 == 0
                    llega = suave(lim((t - m(1) - 0.15 * (i * 3 + j)) / 0.5))
                    x, y = gx + j * 130, 360 + i * 130 - 40 * (1 - llega)
                    P.tarjeta(c, x, y, 116, 116, 16, mezcla(T.panel, T.acento if reutil else T.claro, 0.18 if reutil else 0.06),
                              a1 * llega, borde=T.acento if reutil else T.tenue, a_borde=0.8, grosor=2.5)
        # la biblioteca de código abierto: pública, se usa y se lee
        a2 = aparece(t, m(2) - 0.2, 0.6)
        mueve = suave(lim((t - m(3) - 0.6) / 1.6))
        bx = 960 - 200 * suave(lim((t - m(3) + 0.3) / 0.9))
        if a2 > 0:
            P.tarjeta(c, bx - 160, 330, 320, 260, 24, mezcla(T.panel, T.acento, 0.12), a2, borde=T.acento, a_borde=0.9, grosor=3)
            P.barras_codigo(c, bx - 130, 360, 260, 9, 22, 34, (T.acento, T.claro, T.tenue), a2)
        # el iPhone con su programa de accesorios
        a3 = aparece(t, m(3) + 0.4, 0.7)
        if a3 > 0:
            cp.tinta(T.claro, a3)
            DG.telefono(c, 1460, 560, 640, 5)
            P.tarjeta(c, 1460 - 130, 640, 260, 170, 18, mezcla(T.panel, T.claro, 0.06), a3, borde=T.claro)
            cp.tinta(T.acento, a3)
            DG.flecha(c, (bx + 170, 470), (1300, 690), mueve, 4, curva=-60)
            if mueve > 0:
                xx = bx + (1460 - bx) * mueve
                yy = 460 + (725 - 460) * mueve
                P.tarjeta(c, xx - 70 * (1 - 0.3 * mueve), yy - 50, 140 * (1 - 0.3 * mueve) + 1, 90, 12,
                          mezcla(T.panel, T.acento, 0.3), a3, borde=T.acento, a_borde=1.0, grosor=2)
        img = cp.componer(img, sombra=0.45, brillo=0.35, col_brillo=T.acento)
        # el error que se hereda (con su propio brillo rojo)
        e = aparece(t, m(4) + 0.2, 0.5)
        if e > 0:
            cp = Capa()
            cp.tinta(ROJO, e)
            P.icono_bicho(cp.c, bx + 100, 420, 64)
            if a3 > 0:
                P.icono_bicho(cp.c, 1460 + 30, 715, 44)
            img = cp.componer(img, sombra=0.2, brillo=0.8, col_brillo=ROJO, sigma=10)
        rotulo(img, "casi nunca todo desde cero", gx, 820, 32, T.claro, a1)
        rotulo(img, "piezas reutilizadas", gx, 864, 26, T.acento, a1 * aparece(t, m(1) + 1.6, 0.5), nombre="Inter-Regular.ttf")
        rotulo(img, "biblioteca de código abierto", bx, 660, 32, T.claro, a2, "centro")
        rotulo(img, "pública: cualquiera la usa y la lee", bx, 704, 26, T.tenue, a2 * aparece(t, self.en(2, "cualquiera"), 0.6), "centro",
               nombre="Inter-Regular.ttf")
        if self.mozilla is not None:
            am = aparece(t, self.en(3, "mozilla") - 0.2, 0.6)
            P.poner_mascara(img, self.mozilla, bx - self.mozilla.shape[1] / 2, 220, T.claro, am, brillo=0.25)
            rotulo(img, "la fundación que hace Firefox", bx, 790, 26, T.tenue, am * aparece(t, self.en(3, "firefox"), 0.6), "centro",
                   nombre="Inter-Regular.ttf")
        else:
            rotulo(img, "Mozilla", bx, 280, 60, T.claro, aparece(t, self.en(3, "mozilla"), 0.6), "centro")
        rotulo(img, "programa de accesorios", 1460, 935, 28, T.claro, a3, "centro")
        rotulo(img, "Apple hereda el error", W / 2, 990, 40, ROJO, e, "centro")
        P.pasos(img, 1, aparece(t, 0.1, 0.5), SANB)
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, S.zumbido(d, 3401), -15, 1.5, 1.5)
        m.agregar("teclado", self.m(1), sfx.teclado(self.m(3) - self.m(1), 3402, 1.4), -8, 0.3, 0.8)
        m.agregar("whoosh", self.m(3) + 0.6, sfx.whoosh(1.4, 3403), -8)
        m.agregar("error", self.m(4) + 0.2, sfx.error_suave(3404), -5)
        return m.x[:n]


# =========================================================================== 3.5


class Sub35(Sub3):
    """Tercero: cómo se encontró. Mark Dowd, el código público revisado línea por línea; el error
    guardado; su tipo nunca se publicó; Mozilla no pudo confirmarlo."""

    def preparar(self) -> None:
        self.dowd = foto_tintada("3.5_mark_dowd.jpg")
        self.mozilla = P.logo_blanco("3.4_logo_mozilla.png", 56)

    def cuadro(self, t: float) -> np.ndarray:
        img = self.fondo()
        T = SANB
        m = self.m
        # Mark Dowd: grande al principio, luego se hace a un lado
        a = aparece(t, m(1) - 0.3, 0.7)
        lado = suave(lim((t - m(2) + 0.4) / 1.0))
        w = int(820 - 360 * lado)
        h = int(w * 359 / 634)
        x = int((W - 820) / 2 - (W - 820) / 2 * lado + 140 * lado)
        y = int(230 + 30 * lado)
        persona_en(img, self.dowd, x, y, w, h, t, m(1), a, z1=1.04, cy=0.4)
        rotulo(img, "Mark Dowd", x, y + h + 70, int(56 - 14 * lado), T.claro, a)
        rotulo(img, "fundador de Azimuth · 41 años", x + 2, y + h + 116 - 8 * lado, int(30 - 6 * lado), T.tenue, a, nombre="Inter-Regular.ttf")
        rotulo(img, "lee código ajeno buscando fallas", x + 2, y + h + 162 - 14 * lado, int(30 - 6 * lado), T.acento,
               a * aparece(t, self.en(1, "leer"), 0.6), nombre="Inter-Regular.ttf")
        # el código público, línea por línea
        b = aparece(t, m(2) - 0.2, 0.7)
        if b > 0:
            x0, y0, w0, h0 = 860, 230, 900, 640
            cp = Capa()
            P.tarjeta(cp.c, x0, y0, w0, h0, 20, mezcla(T.panel, NEGRO, 0.35), b, borde=T.claro)
            img = cp.componer(img, sombra=0.5)
            cp = Capa()
            c = cp.c
            c.rectangle(x0 + 10, y0 + 10, w0 - 20, h0 - 20)
            c.clip()
            fila = 30
            corre = max(0.0, min(t, m(3) + 0.2) - m(2))
            desp = (corre * 46) % fila
            k0 = int(corre * 46 / fila)
            for k in range(22):
                yy = y0 + 30 + k * fila - desp
                P.barras_codigo(c, x0 + 60, yy, w0 - 100, 1, fila, 900 + k0 + k, (T.acento, T.claro, T.tenue), b * 0.9)
            img = cp.componer(img, sombra=0, brillo=0.15, col_brillo=T.claro)
            # la línea que se revisa, el error y su borrón
            yl = y0 + 30 + 10 * fila
            hallado = aparece(t, m(3) + 0.3, 0.4)
            borron = aparece(t, m(4) + 0.3, 0.5)
            cp = Capa()
            c = cp.c
            if hallado < 1:
                barrido = (t * 0.8) % 1.0
                cp.tinta(T.acento, b * 0.2 * (1 - hallado))
                c.rectangle(x0 + 20, y0 + 40 + barrido * (h0 - 80) - 14, w0 - 40, 28)
                c.fill()
            cp.tinta(ROJO, hallado * 0.35)
            c.rectangle(x0 + 20, yl - 8, w0 - 40, 30)
            c.fill()
            cp.tinta(ROJO, hallado)
            c.set_line_width(3)
            c.rectangle(x0 + 20, yl - 8, w0 - 40, 30)
            c.stroke()
            P.icono_bicho(c, x0 + w0 - 50, yl + 7, 34)
            if borron > 0:
                cp.tinta(mezcla(NEGRO, T.panel, 0.2), borron)
                c.rectangle(x0 + 60, yl - 4, (w0 - 160) * borron, 22)
                c.fill()
            img = cp.componer(img, sombra=0.2, brillo=0.6 * hallado, col_brillo=ROJO, sigma=10)
            rotulo(img, "código abierto: se puede leer", x0, y0 - 24, 28, T.claro, b, nombre="Inter-Regular.ttf")
            rotulo(img, "un error en la biblioteca, guardado", x0, y0 + h0 + 60, 32, ROJO, hallado * (1 - borron))
            rotulo(img, "el tipo exacto nunca se hizo público", x0, y0 + h0 + 60, 32, T.claro, borron)
        am = aparece(t, m(5) - 0.1, 0.6)
        if am > 0:
            if self.mozilla is not None:
                P.poner_mascara(img, self.mozilla, 140, 800, T.claro, am, brillo=0.2)
            rotulo(img, "dijo que no podía confirmar", 142, 920, 30, T.claro, am, nombre="Inter-Regular.ttf")
            rotulo(img, "que fuera su código", 142, 962, 30, T.claro, am, nombre="Inter-Regular.ttf")
        P.pasos(img, 2, aparece(t, 0.1, 0.5), SANB)
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, S.zumbido(d, 3501), -15, 1.5, 1.5)
        m.agregar("lectura", self.m(2), sfx.datos(self.m(3) - self.m(2) + 0.4, 3502, 8), -12, 0.5, 0.5)
        m.agregar("hallazgo", self.m(3) + 0.3, S.hallazgo(3503), -2)
        m.agregar("papel", self.m(4) + 0.3, S.papel(0.8, 3504), -8)
        return m.x[:n]


# =========================================================================== 3.6


class Sub36(Sub3):
    """Cuarto: la cadena. Compartimentos con permisos distintos; David Wang (sin foto confirmada: va
    una silueta); tres errores que abren tres puertas; el nombre de la cadena, Cóndor."""

    SALAS = ((560, "accesorios"), (960, "sistema"), (1360, "procesador principal"))

    def preparar(self) -> None:
        self.wang = foto_tintada("3.6_david_wang.jpg")

    def _puertas(self, t):
        m = self.m
        return [suave(lim((t - tk) / 0.8)) for tk in (m(3) + 0.5, m(4) + 0.4, m(5) + 0.8)]

    def _codigo_x(self, t, abre):
        """Dónde va el código de Wang: entra por el cable y avanza de sala en sala."""
        paradas = [260, 560, 960, 1360]
        x = paradas[0]
        for k in range(3):
            x = paradas[k] + (paradas[k + 1] - paradas[k]) * abre[k]
            if abre[k] < 1:
                break
        return x

    def cuadro(self, t: float) -> np.ndarray:
        img = self.fondo()
        T = SANB
        m = self.m
        abre = self._puertas(t)
        a = aparece(t, m(1) - 0.2, 0.7)
        tenue_wang = 1 - 0.93 * aparece(t, m(2) - 0.2, 0.6, m(3) - 0.4)
        cp = Capa()
        c = cp.c
        y0, alto = 340, 420
        for k, (x, _) in enumerate(self.SALAS):
            col = T.acento if abre[k] > 0.5 else T.claro
            P.tarjeta(c, x - 190, y0, 380, alto, 28, mezcla(T.panel, col, 0.06 + 0.1 * abre[k]), a * tenue_wang, borde=col,
                      a_borde=0.7, grosor=3)
        cp.tinta(T.claro, a * tenue_wang)
        DG.linea(c, [(120, 550), (360, 550)], 1.0, 8)
        for k, (x, _) in enumerate(self.SALAS):
            px = x - 190
            cp.tinta(T.acento if abre[k] > 0 else T.tenue, a * tenue_wang)
            c.rectangle(px - 6, 505 + 90 * abre[k] * 0.85, 12, 90 * (1 - abre[k] * 0.85))
            c.fill()
            DG.candado(c, px, 470, 40, cerrado=1 - abre[k])
        if t > m(3):
            cp.tinta(T.acento, aparece(t, m(3), 0.5) * tenue_wang)
            c.arc(self._codigo_x(t, abre), 640, 16, 0, TAU)
            c.fill()
        cnd = aparece(t, m(6) + 0.2, 0.8)
        if cnd > 0:
            cp.tinta(T.acento, cnd)
            for k in range(3):
                P.eslabon(c, 760 + k * 200, 880, 190, 70, 0.0, 9)
        img = cp.componer(img, sombra=0.45, brillo=0.35, col_brillo=T.acento)
        for k, (x, nombre) in enumerate(self.SALAS):
            rotulo(img, nombre, x, y0 + 60, 30, T.acento if abre[k] > 0.5 else T.claro, a * tenue_wang, "centro")
        for k, (tk, txt) in enumerate(((m(3) + 0.6, "error 1: el de Mozilla"), (m(4) + 0.5, "error 2: más permisos"),
                                       (m(5) + 0.9, "error 3: control total"))):
            rotulo(img, txt, self.SALAS[k][0], y0 + alto - 40, 26, T.claro, aparece(t, tk, 0.5) * tenue_wang, "centro",
                   nombre="Inter-Regular.ttf")
        rotulo(img, "compartimentos con permisos distintos", W / 2, 270, 34, T.claro, aparece(t, m(1) + 1.0, 0.6) * tenue_wang, "centro")
        rotulo(img, "Cóndor", W / 2, 1010, 72, T.acento, cnd, "centro")
        aw = aparece(t, m(2) - 0.2, 0.6, m(3) - 0.4)
        if aw > 0:
            if self.wang is not None:
                persona_en(img, self.wang, 460, 300, 380, 460, t, m(2), aw)
            else:
                silueta_en(img, 460, 300, 380, 460, aw)
            rotulo(img, "David Wang", 920, 500, 64, T.claro, aw)
            rotulo(img, "colega de Dowd", 924, 560, 32, T.tenue, aw, nombre="Inter-Regular.ttf")
            rotulo(img, "a los 27 años, premiado por hackear un iPhone", 924, 620, 30, T.acento,
                   aw * aparece(t, self.en(2, "premio"), 0.6), nombre="Inter-Regular.ttf")
        P.pasos(img, 3, aparece(t, 0.1, 0.5), SANB)
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, S.zumbido(d, 3601), -15, 1.5, 1.5)
        for k, tk in enumerate((self.m(3) + 0.5, self.m(4) + 0.4, self.m(5) + 0.8)):
            m.agregar("cerradura", tk, sfx.candado(3602 + k), -2)
        m.agregar("cadena", self.m(6) + 0.2, S.eslabones(3, 3606), -4)
        return m.x[:n]


# =========================================================================== 3.7


class Sub37(Sub3):
    """Quinto: la fuerza bruta, sin borrado al décimo intento; una docena de iPhone 5C; funcionó en todos."""

    def preparar(self) -> None:
        o = self.o
        self.t_desact = self.en(1, "desactivaba")
        self.c_3d = o[2] - 0.3
        self.seg = Segmentos([self.c_3d], CRUCE)
        self.ini_3d = self.c_3d - CRUCE / 2
        dur = self.d - self.ini_3d + 0.2
        base = o[3] - self.ini_3d + 0.2
        orden = [0, 7, 3, 10, 5, 1, 8, 4, 11, 2, 6, 9]
        desb = [0.0] * 12
        for j, k in enumerate(orden):
            desb[k] = round(base + 0.16 * j, 2)
        self.docena = Plano3D("e03_docena_5c", dur, motor=MOTOR["e03_docena_5c"], desbloqueos=desb)
        self.planos3d = [self.docena]

    def _fuerza(self, t):
        img = self.fondo()
        T = SANB
        m = self.m
        a = aparece(t, m(1) - 0.2, 0.6)
        puntos_codigo(img, 640, 560, t - m(1) - 0.4, a, T, escala=1.6)
        rotulo(img, "un intento tras otro", 640, 700, 32, T.tenue, a, "centro", nombre="Inter-Regular.ttf")
        cp = Capa()
        c = cp.c
        apaga = suave(lim((t - self.t_desact - 0.2) / 0.5))
        b = aparece(t, self.t_desact - 0.6, 0.5)
        P.tarjeta(c, 1100, 430, 560, 200, 26, T.panel, b, borde=T.claro)
        col = mezcla(T.acento, T.tenue, apaga)
        P.tarjeta(c, 1520, 500, 100, 56, 28, mezcla(T.panel, col, 0.6), b, borde=col, a_borde=0.9, grosor=2)
        cp.tinta(T.claro, b)
        c.arc(1548 + 44 * (1 - apaga), 528, 22, 0, TAU)
        c.fill()
        img = cp.componer(img, sombra=0.45, brillo=0.3, col_brillo=T.acento)
        rotulo(img, "borrado al", 1140, 515, 32, T.claro, b)
        rotulo(img, "décimo intento", 1140, 560, 32, T.claro, b)
        rotulo(img, "desactivado", 1380, 700, 36, T.acento, aparece(t, self.t_desact + 0.5, 0.5), "centro")
        P.pasos(img, 4, aparece(t, 0.1, 0.5), SANB)
        return img

    def _docena(self, t):
        img = self.docena.cuadro(t - self.ini_3d)
        oscurecer(img, False, 240, 0.65)
        oscurecer(img, True, 340, 0.6)
        P.pasos(img, 4, 1.0, SANB)
        leyenda(img, "", "12 iPhone 5C", aparece(t, self.m(2) + 0.2, 0.6), detalle="algunos comprados en eBay",
                a_detalle=aparece(t, self.en(2, "ebay") - 0.2, 0.6))
        rotulo(img, "funcionó en todos", W - 120, H - 140, 52, SANB.acento, aparece(t, self.m(3) + 0.6, 0.6), "der")
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return self.mezclar(t, (self._fuerza, self._docena))

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, S.zumbido(d, 3701), -15, 1.5, 1.5)
        clics = list(np.arange(self.m(1) + 0.4, self.c_3d + 1.0, 0.08))
        m.agregar("ráfaga", 0.0, sfx.tics(clics, d, 3702), -10, 0.3, 0.6)
        m.agregar("interruptor", self.t_desact + 0.2, S.desbloqueo(3703), -6)
        for k in range(12):
            m.agregar("desbloqueo", self.m(3) + 0.2 + 0.16 * k, S.desbloqueo(3710 + k), -12)
        return m.x[:n]


# =========================================================================== 3.8


class Sub38(Sub3):
    """Un detalle de hardware: el 5C usaba el A6, sin Secure Enclave; ahí iOS controlaba los errores
    y el borrado, y quien controla el procesador controla iOS; la mezcla con el UID seguía en el
    hardware: 80 ms por intento, minutos con 4 dígitos, horas con 6."""

    tema = MANZANA
    cine = CINE_AP

    def preparar(self) -> None:
        o = self.o
        self.chips = P.cargar("3.8_chip_a6_vs_a7.jpg")
        self.t_5s = self.en(1, "5s")
        self.t_sin = self.en(1, "sin")
        self.seg = Segmentos([o[2]], CRUCE)

    def _foto(self, t):
        T = MANZANA
        img = self.fondo()
        w = 1360
        h = int(w * self.chips.height / self.chips.width) if self.chips is not None else 765
        x0 = (W - w) / 2
        z = 1.0 + 0.04 * suave(lim(t / (self.m(2) + 1.0)))
        P.ventana(img, self.chips, x0, 120, w, h, a=aparece(t, 0.1, 0.6), zoom=z, radio=12, borde=T.claro)
        y = 120 + h
        rotulo(img, "iPhone 5C", x0 + w * 0.25, y + 80, 44, T.claro, aparece(t, self.m(1) + 0.3, 0.6), "centro")
        rotulo(img, "sin Secure Enclave", x0 + w * 0.25, y + 124, 30, ROJO, aparece(t, self.t_sin, 0.6), "centro")
        rotulo(img, "iPhone 5S", x0 + w * 0.75, y + 80, 44, T.claro, aparece(t, self.t_5s, 0.6), "centro")
        rotulo(img, "con Secure Enclave", x0 + w * 0.75, y + 124, 30, T.acento, aparece(t, self.t_sin + 0.4, 0.6), "centro")
        rotulo(img, "un detalle de hardware", W / 2, 76, 36, T.claro, aparece(t, 0.3, 0.6, self.m(1) - 0.2), "centro")
        return img

    def _diagrama(self, t):
        img = self.fondo()
        T = MANZANA
        m = self.m
        cp = Capa()
        c = cp.c
        a = aparece(t, m(2) - 0.4, 0.7)
        tomado = aparece(t, m(3) + 0.4, 0.6)
        col_chip = mezcla(T.claro, ROJO, tomado)
        cp.tinta(col_chip, 0.9 * a)
        DG.chip(c, 640, 520, 560, 4, 9, a)
        P.tarjeta(c, 440, 330, 400, 270, 22, mezcla(T.panel, col_chip, 0.08), a, borde=col_chip, a_borde=0.8, grosor=2.5)
        for k in range(2):
            y = 420 + k * 90
            tachado = suave(lim((t - m(3) - 0.8 - 0.3 * k) / 0.4))
            if tachado > 0:
                cp.tinta(ROJO, tachado)
                c.set_line_width(4)
                c.move_to(480, y + 2)
                c.line_to(480 + 320 * tachado, y + 2)
                c.stroke()
        u_ = aparece(t, m(4) - 0.2, 0.6)
        if u_ > 0:
            P.tarjeta(c, 420, 630, 440, 130, 18, mezcla(T.panel, T.acento, 0.18), u_, borde=T.acento, a_borde=0.9, grosor=3)
            cp.tinta(T.acento, u_)
            g = t * 1.6
            for k in range(2):
                c.set_line_width(4)
                c.arc(492, 695, 34, g + k * math.pi, g + k * math.pi + 2.0)
                c.stroke()
        r = aparece(t, m(5) - 0.2, 0.6)
        if r > 0:
            vuelta = (t / 0.08) % 1.0
            cp.tinta(T.tenue, 0.4 * r)
            c.set_line_width(10)
            c.arc(1390, 330, 110, 0, TAU)
            c.stroke()
            cp.tinta(T.acento, r)
            c.arc(1390, 330, 110, -math.pi / 2, -math.pi / 2 + TAU * vuelta)
            c.stroke()
        img = cp.componer(img, sombra=0.45, brillo=0.35, col_brillo=T.acento if tomado < 0.5 else ROJO)
        rotulo(img, "procesador del 5C", 640, 290, 34, T.claro, a, "centro")
        rotulo(img, "iOS", 470, 372, 30, T.claro, a)
        rotulo(img, "cuenta de errores", 480, 430, 28, T.claro, a, nombre="Inter-Regular.ttf")
        rotulo(img, "borrado al décimo intento", 480, 520, 28, T.claro, a, nombre="Inter-Regular.ttf")
        rotulo(img, "Azimuth controla el procesador", 640, 930, 32, ROJO, tomado, "centro")
        rotulo(img, "y por lo tanto iOS", 640, 972, 28, T.claro, tomado * aparece(t, m(3) + 1.0, 0.5), "centro", nombre="Inter-Regular.ttf")
        rotulo(img, "mezcla con el UID", 550, 688, 28, T.claro, u_)
        rotulo(img, "en el hardware", 550, 728, 26, T.acento, u_, nombre="Inter-Regular.ttf")
        rotulo(img, "80 ms", 1390, 350, 64, T.claro, r, "centro", nombre="Inter-Light.ttf")
        rotulo(img, "por intento", 1390, 490, 28, T.tenue, r, "centro", nombre="Inter-Regular.ttf")
        for k, (o_, que, cuanto) in enumerate(((6, "4 dígitos", "minutos"), (7, "6 dígitos", "horas"))):
            b = aparece(t, m(o_) - 0.1, 0.5)
            y = 640 + k * 150
            rotulo(img, que, 1180, y, 40, T.claro, b, nombre="Inter-Light.ttf")
            cp = Capa()
            cp.tinta(T.acento, b)
            DG.flecha(cp.c, (1400, y - 14), (1500, y - 14), b, 4)
            img = cp.componer(img, sombra=0.2)
            rotulo(img, cuanto, 1530, y, 48, T.acento, aparece(t, m(o_) + 0.6, 0.5))
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return self.mezclar(t, (self._foto, self._diagrama))

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("grave", 0.2, S.tono_grave(min(6.0, self.m(2)), 3801), -2)
        m.agregar("zumbido", 0.0, S.zumbido(d, 3802), -16, 1.5, 1.5)
        m.agregar("error", self.m(3) + 0.4, sfx.error_suave(3803), -5)
        ticks = list(np.arange(self.m(5), self.d - 0.5, 0.08))
        m.agregar("tics", 0.0, sfx.tics(ticks, d, 3804), -14, 0.3, 0.8)
        return m.x[:n]


# =========================================================================== 3.9


class Sub39(Sub3):
    """900,000 dólares; nada útil; Mozilla corrige el error; el Modo USB restringido; GrayKey."""

    def preparar(self) -> None:
        o = self.o
        self.usb = P.cargar("3.9_modo_usb.png")
        self.graykey = Foto("3.9_graykey.jpg")
        self.mozilla = P.logo_blanco("3.4_logo_mozilla.png", 64)
        self.seg = Segmentos([o[3], o[6]], CRUCE)

    def _dinero(self, t):
        img = self.fondo()
        T = SANB
        m = self.m
        a = aparece(t, 0.1, 0.5, m(1) - 0.1)
        antetitulo(img, "unos", W / 2, 420, T.tenue, a, "centro", tam=28)
        rotulo(img, "900,000 dólares", W / 2, 560, 130, T.acento, a, "centro", nombre="Inter-Light.ttf")
        rotulo(img, "pagó el FBI", W / 2, 650, 36, T.claro, aparece(t, 0.8, 0.6, m(1) - 0.1), "centro")
        b = aparece(t, m(1) - 0.1, 0.5, m(2) - 0.2)
        if b > 0:
            cp = Capa()
            c = cp.c
            cp.tinta(T.claro, b)
            DG.telefono(c, 620, 540, 460, 5)
            for k in range(3):
                cp.tinta(T.tenue, b)
                P.icono_carpeta(c, 1075 + k * 200, 530, 150, 5)
                cp.tinta(T.tenue, 0.6 * b)
                c.set_line_width(3)
                c.move_to(1040 + k * 200, 545)
                c.line_to(1110 + k * 200, 545)
                c.stroke()
            img = cp.componer(img, sombra=0.45)
            rotulo(img, "nada útil", 1300, 700, 52, T.claro, b, "centro")
        e = aparece(t, m(2) - 0.1, 0.6)
        if e > 0:
            if self.mozilla is not None:
                P.poner_mascara(img, self.mozilla, W / 2 - self.mozilla.shape[1] / 2, 380, T.claro, e, brillo=0.2)
            rotulo(img, "corrige el error un mes después", W / 2, 560, 46, T.claro, e, "centro")
            rotulo(img, "sin saber para qué se había usado", W / 2, 620, 32, T.tenue, aparece(t, self.en(2, "sin"), 0.6), "centro",
                   nombre="Inter-Regular.ttf")
        return img

    def _usb(self, t):
        img = self.fondo()
        T = SANB
        m = self.m
        a = aparece(t, m(3) - 0.3, 0.6)
        b = aparece(t, m(4) - 0.2, 0.6)
        z = 1.0 + 0.12 * suave(lim((t - m(4)) / 5.0))
        P.ventana(img, self.usb, 1140, 160, 620, 620, a=b, zoom=z, cx=0.5, cy=0.58, radio=16, borde=T.claro)
        rotulo(img, "Apple aprendió de esa puerta", 160, 260, 40, T.claro, a)
        antetitulo(img, "2018", 162, 380, T.acento, b)
        rotulo(img, "Modo USB restringido", 158, 448, 58, T.claro, b)
        cp = Capa()
        c = cp.c
        d_ = aparece(t, m(5) - 0.2, 0.6)
        if d_ > 0:
            cp.tinta(T.claro, d_)
            P.icono_reloj(c, 260, 640, 120, suave(lim((t - m(5)) / 2.0)), 6)
            DG.flecha(c, (350, 640), (470, 640), d_, 4)
            P.tarjeta(c, 500, 590, 160, 100, 40, T.panel, d_, borde=T.claro)
            cp.tinta(T.claro, d_)
            c.rectangle(540, 625, 80, 30)
            c.fill()
            cp.tinta(ROJO, aparece(t, m(5) + 1.6, 0.4))
            DG.cruz(c, 760, 800, 46, 7)
            cp.tinta(T.acento, aparece(t, m(5) + 2.4, 0.4))
            P.icono_check(c, 760, 900, 46)
        img = cp.componer(img, sombra=0.45, brillo=0.3, col_brillo=T.acento)
        rotulo(img, "1 hora bloqueado", 200, 760, 30, T.claro, d_, nombre="Inter-Regular.ttf")
        rotulo(img, "datos", 820, 815, 36, T.claro, aparece(t, m(5) + 1.6, 0.4))
        rotulo(img, "solo carga", 820, 915, 36, T.acento, aparece(t, m(5) + 2.4, 0.4))
        return img

    def _graykey(self, t):
        z, cx, cy = recorrido(t - self.m(6), self.d - self.m(6), 1.0, 1.08, (0.5, 0.5), (0.55, 0.5))
        img = self.graykey.ver(z, cx, cy) * 0.9 if self.graykey.existe else self.fondo()
        oscurecer(img, True, 380, 0.7)
        leyenda(img, "caja de desbloqueo de la policía", "GrayKey", aparece(t, self.en(6, "graykey") - 0.3, 0.6),
                detalle="entraba por el cable", a_detalle=aparece(t, self.en(6, "cable") - 0.2, 0.6))
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return self.mezclar(t, (self._dinero, self._usb, self._graykey))

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("caja", 0.3, S.caja_registradora(3901), -3)
        m.agregar("zumbido", 0.0, S.zumbido(d, 3902), -16, 1.5, 1.5)
        m.agregar("candado", self.m(4), sfx.candado(3903), -4)
        m.agregar("error", self.m(5) + 1.6, sfx.error_suave(3904), -8)
        m.agregar("conector", self.en(6, "cable"), S.conector(3905), -6)
        return m.x[:n]


# =========================================================================== 3.10


def _llaves(c, xs, y, s, a_col):
    for x in xs:
        DG.llave(c, x, y, s)


class Sub310(Sub3):
    """El teléfono estaba apagado. Qué hace el primer desbloqueo: el chip calcula las claves y las
    deja en la memoria de trabajo; así las apps leen aunque la pantalla se bloquee."""

    tema = MANZANA
    cine = CINE_AP

    def cuadro(self, t: float) -> np.ndarray:
        img = self.fondo()
        T = MANZANA
        m = self.m
        cp = Capa()
        c = cp.c
        enc = aparece(t, m(1) + 0.6, 0.6)
        codigo = lim((t - m(2) + 0.6) / 1.2)
        bloq = aparece(t, m(3) + 0.2, 0.5)
        cp.tinta(T.claro, 0.9)
        pc = 960 - 480 * suave(lim((t - m(2) + 0.6) / 1.0))             # solo, al centro; luego a la izquierda
        pantalla = mezcla(NEGRO, T.panel, 0.3 + 0.6 * enc * (1 - 0.6 * bloq))
        px, py, pw, ph = DG.telefono(c, pc, 540, 640, 5, pantalla=pantalla)
        if t < m(1) + 0.6:
            cp.tinta(T.tenue, aparece(t, 0.3, 0.6))
            P.icono_power(c, pc, 540, 120, 10)
        else:
            if codigo < 1:
                cp.tinta(T.claro, enc)
                for k in range(6):
                    c.arc(pc + (k - 2.5) * 36, 420, 9, 0, TAU)
                    c.fill() if k < int(codigo * 6.99) else c.stroke()
            else:
                cp.tinta(T.claro, 1 - bloq)
                for k in range(6):
                    D.rect_redondeado(c, pc - 100 + (k % 3) * 70, 330 + (k // 3) * 80, 56, 56, 12)
                    c.fill()
                cp.tinta(T.claro, bloq)
                DG.candado(c, pc, 330, 50)
        # el chip calcula las claves y las deja en la memoria
        a_chip = aparece(t, m(2) - 0.2, 0.6)
        if a_chip > 0:
            cp.tinta(T.claro, 0.9 * a_chip)
            DG.chip(c, 1000, 380, 190, 3, 6, a_chip)
            cp.tinta(T.claro, aparece(t, m(2) + 1.6, 0.6))
            P.icono_memoria(c, 1380, 700, 440, 150, 3)
            viaje = suave(lim((t - m(2) - 1.4) / 1.4))
            for k in range(3):
                x = 1000 + (1260 + k * 120 - 1000) * viaje
                y = 380 + (585 - 380) * viaje
                cp.tinta(T.acento, a_chip * aparece(t, m(2) + 0.6 + 0.2 * k, 0.4))
                DG.llave(c, x, y, 90)
        # las apps leen con las claves aunque la pantalla esté bloqueada
        if t > m(3):
            b = aparece(t, m(3) + 0.8, 0.6)
            for k in range(3):
                x = 1220 + k * 160
                cp.tinta(T.claro, b)
                P.tarjeta(c, x - 45, 880, 90, 90, 22, mezcla(T.panel, T.acento, 0.2 + 0.15 * k), b, borde=T.claro)
                cp.tinta(T.acento, b * (0.5 + 0.5 * math.sin(t * 4 + k)))
                DG.flecha(c, (x, 870), (x, 780), b, 3, 12)
        # el mensaje que llega con la pantalla bloqueada
        n_ = aparece(t, m(4) + 0.6, 0.5)
        if n_ > 0:
            P.tarjeta(c, px + 16, py + 150, pw - 32, 100, 18, mezcla(T.panel, T.claro, 0.18), n_, borde=T.claro)
            cp.tinta(T.acento, n_)
            P.tarjeta(c, px + 32, py + 172, 56, 56, 14, T.acento, n_)
        img = cp.componer(img, sombra=0.45, brillo=0.35, col_brillo=T.acento)
        rotulo(img, "apagado", pc, 960, 40, T.claro, aparece(t, 0.3, 0.6, m(1) + 0.3), "centro")
        rotulo(img, "la regla de los peritos", pc, 1010, 28, T.tenue, aparece(t, 1.2, 0.6, m(1) + 0.3), "centro", nombre="Inter-Regular.ttf")
        rotulo(img, "primer desbloqueo después de encender", pc, 960, 30, T.claro, aparece(t, m(1) + 1.0, 0.6, m(3) - 0.3), "centro")
        rotulo(img, "el chip calcula las claves", 1000, 250, 30, T.claro, a_chip, "centro")
        rotulo(img, "memoria de trabajo", 1625, 712, 30, T.claro, aparece(t, m(2) + 1.6, 0.6))
        rotulo(img, "las apps leen sus datos", 1380, 1030, 28, T.acento, aparece(t, m(3) + 0.8, 0.6), "centro")
        rotulo(img, "aunque la pantalla esté bloqueada", pc, 960, 30, T.claro, aparece(t, m(3) + 0.4, 0.6, m(4) + 0.2), "centro")
        if n_ > 0:
            rotulo(img, "Mensaje nuevo", px + 102, py + 207, 22, T.claro, n_)
            rotulo(img, "llega con la pantalla bloqueada", pc, 960, 30, T.acento, n_, "centro")
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", self.m(1), S.zumbido(d - self.m(1), 3101), -16, 1.5, 1.5)
        m.agregar("encendido", self.m(1) + 0.5, S.reinicio(3102), -6)
        m.agregar("teclado", self.m(2) - 0.6, sfx.teclado(1.2, 3103, 1.5), -10)
        m.agregar("desbloqueo", self.m(2) + 0.6, S.desbloqueo(3104), -2)
        m.agregar("aviso", self.m(4) + 0.6, S.notificacion(3105), -4)
        return m.x[:n]


# =========================================================================== 3.11


class Sub311(Sub3):
    """Los dos estados: BFU (antes del primer desbloqueo) y AFU (después); al apagar, AFU vuelve a
    BFU. Por eso la policía guarda el teléfono encendido, cargando, en una bolsa de Faraday (3D)."""

    tema = MANZANA
    cine = CINE_AP

    def preparar(self) -> None:
        o = self.o
        self.foto_bolsa = P.cargar("3.11_bolsa_faraday.jpg")
        self.c_3d = o[6] - 0.2
        self.seg = Segmentos([self.c_3d], CRUCE)
        self.ini_3d = self.c_3d - CRUCE / 2
        self.faraday = Plano3D("e03_bolsa_faraday", self.d - self.ini_3d + 0.2, motor=MOTOR["e03_bolsa_faraday"])
        self.planos3d = [self.faraday]
        self.t_bolsa = self.en(7, "bolsa")

    def _estados(self, t):
        img = self.fondo()
        T = MANZANA
        m = self.m
        cp = Capa()
        c = cp.c
        aB = aparece(t, m(1) - 0.2, 0.6)
        aA = aparece(t, m(3) - 0.2, 0.6)
        apaga = suave(lim((t - m(5) - 0.6) / 1.0))
        for k, (x, a, abierto) in enumerate(((560, aB, False), (1360, aA, True))):
            if a <= 0:
                continue
            luz = 0.0 if not abierto else 1 - apaga
            cp.tinta(T.claro, a)
            DG.telefono(c, x, 480, 460, 5, pantalla=mezcla(T.panel, T.acento, 0.15 * luz))
            cp.tinta(T.acento if (abierto and luz > 0.5) else T.claro, a)
            DG.candado(c, x, 420, 90, cerrado=0.0 if (abierto and luz > 0.5) else 1.0)
            # el chip debajo y, en AFU, la memoria con claves
            cp.tinta(T.claro, 0.85 * a)
            DG.chip(c, x - 110, 850, 120, 3, 5)
            P.icono_memoria(c, x + 110, 850, 200, 80, 2.5)
        # claves encerradas en el chip (BFU)
        k_b = aparece(t, m(2) - 0.1, 0.6)
        if k_b > 0:
            cp.tinta(T.acento, k_b)
            DG.llave(c, 450, 852, 56)
            DG.candado(c, 450, 768, 30)
        # claves vivas en memoria (AFU) y las herramientas forenses que entran
        k_a = aparece(t, m(4) - 0.2, 0.6) * (1 - apaga)
        if k_a > 0:
            cp.tinta(T.acento, k_a)
            for j in range(3):
                DG.llave(c, 1425 + j * 46, 785 - (j % 2) * 18, 44)
            for j in range(3):
                u = ((t * 0.7) + j / 3) % 1.0
                cp.tinta(T.acento, k_a * math.sin(math.pi * u))
                DG.flecha(c, (1700, 380 + j * 110), (1600 - 40 * u, 420 + j * 90), 1.0, 3, 14)
        img = cp.componer(img, sombra=0.45, brillo=0.35, col_brillo=T.acento)
        rotulo(img, "dos estados", W / 2, 150, 40, T.claro, aparece(t, 0.2, 0.6, m(1) + 1.0), "centro")
        rotulo(img, "BFU", 560, 160, 64, T.claro, aB, "centro")
        rotulo(img, "antes del primer desbloqueo", 560, 205, 26, T.tenue, aB, "centro", nombre="Inter-Regular.ttf")
        rotulo(img, "claves encerradas en el chip", 560, 980, 26, T.acento, k_b, "centro")
        etiqueta_afu = "AFU" if apaga < 0.5 else "BFU"
        rotulo(img, etiqueta_afu, 1360, 160, 64, T.acento if apaga < 0.5 else T.claro, aA, "centro")
        rotulo(img, "después del primer desbloqueo" if apaga < 0.5 else "apagado: vuelve a BFU", 1360, 205, 26, T.tenue, aA, "centro",
               nombre="Inter-Regular.ttf")
        rotulo(img, "claves vivas en memoria", 1360, 980, 26, T.acento, k_a, "centro")
        rotulo(img, "más por dónde entrar", 1640, 330, 24, T.acento, aparece(t, m(4) + 1.5, 0.6) * (1 - apaga), "centro",
               nombre="Inter-Regular.ttf")
        return img

    def _bolsa(self, t):
        T = MANZANA
        m = self.m
        img = self.faraday.cuadro(t - self.ini_3d)
        oscurecer(img, True, 360, 0.6)
        leyenda(img, "", "encendido y cargando", aparece(t, m(6) + 0.3, 0.6, self.t_bolsa - 0.2), tema=T)
        leyenda(img, "", "bolsa de Faraday", aparece(t, self.t_bolsa - 0.1, 0.6), tema=T, detalle="forrada de metal: bloquea la señal",
                a_detalle=aparece(t, self.en(7, "forrada"), 0.6))
        f = aparece(t, self.t_bolsa + 0.3, 0.6, m(8) - 0.2)
        if self.foto_bolsa is not None and f > 0:
            P.ventana(img, self.foto_bolsa, 1290, 120, 510, 340, a=f, zoom=1.0 + 0.04 * lim((t - self.t_bolsa) / 5), radio=10, borde=T.claro)
            rotulo(img, "una bolsa de Faraday real", 1290, 500, 24, T.tenue, f, nombre="Inter-Regular.ttf")
        # la señal que no entra: el borrado a distancia queda bloqueado
        s = aparece(t, m(8) - 0.1, 0.5)
        if s > 0:
            cp = Capa()
            c = cp.c
            for k in range(4):
                u = ((t - m(8)) * 0.8 + k / 4) % 1.0
                r = 40 + 222 * u
                cp.tinta(T.claro, s * (1 - u) * 0.8)
                c.set_line_width(4)
                c.arc(960, -40, r, math.radians(55), math.radians(125))
                c.stroke()
            cp.tinta(ROJO, s)
            c.set_line_width(6)
            c.move_to(760, 225)
            c.line_to(1160, 225)
            c.stroke()
            DG.cruz(c, 1195, 225, 36, 6)
            img = cp.componer(img, sombra=0.3, brillo=0.3, col_brillo=T.claro)
            rotulo(img, "borrado a distancia: bloqueado", W - 120, H - 140, 40, T.claro, s, "der")
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return self.mezclar(t, (self._estados, self._bolsa))

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, S.zumbido(self.c_3d + 1.0, 3111), -16, 1.5, 1.0)
        m.agregar("candado", self.m(1) + 0.2, sfx.candado(3112), -6)
        m.agregar("desbloqueo", self.m(3) + 0.2, S.desbloqueo(3113), -4)
        m.agregar("apagado", self.m(5) + 0.6, sfx.error_suave(3114), -8)
        m.agregar("bolsa", self.t_bolsa, S.cierre_bolsa(1.0, 3115), -4)
        m.agregar("cuarto", self.c_3d, sfx.zumbido_cctv(self.d - self.c_3d, 3116), -18, 1.0, 1.0)
        return m.x[:n]


# =========================================================================== 3.12


class Sub312(Sub3):
    """Detroit, 2024: iPhones de evidencia que se reinician solos y vuelven a BFU; Jiska Classen lo
    averigua en tres pasos: «inactivity_reboot» en iOS 18.1, las 72 horas, el contador del Secure Enclave."""

    tema = MANZANA
    cine = CINE_AP

    def preparar(self) -> None:
        o = self.o
        self.articulo = P.cargar("3.12_carta_detroit.png")
        self.jiska = foto_tintada("3.12_jiska_classen.jpg", MANZANA, 0.08)
        self.c_3d = o[1] + 4.2
        self.seg = Segmentos([o[1], self.c_3d, o[3], o[4]], CRUCE)
        self.ini_3d = self.c_3d - CRUCE / 2
        dur = o[3] + CRUCE / 2 - self.ini_3d + 0.2
        self.reinicios = [[2, round(1.2, 2)], [5, round(min(dur - 2.5, 4.0), 2)], [0, round(min(dur - 1.2, 7.0), 2)]]
        self.sala = Plano3D("e03_sala_evidencias", dur, motor=MOTOR["e03_sala_evidencias"], reinicios=self.reinicios)
        self.planos3d = [self.sala]

    def _sigue(self, t):
        img = self.fondo()
        T = MANZANA
        a = aparece(t, 0.2, 0.6)
        rotulo(img, "2016", 700, 560, 60, T.tenue, a, "centro", nombre="Inter-Light.ttf")
        cp = Capa()
        cp.tinta(T.tenue, a)
        DG.flecha(cp.c, (800, 540), (1080, 540), suave(lim((t - 0.3) / 0.8)), 4)
        img = cp.componer(img, sombra=0.2)
        rotulo(img, "2024", 1220, 560, 60, T.claro, aparece(t, 0.8, 0.5), "centro", nombre="Inter-Light.ttf")
        return img

    def _articulo(self, t):
        img = self.fondo()
        T = MANZANA
        a = aparece(t, self.m(1) - 0.3, 0.6)
        w = 1220
        h = int(w * self.articulo.height / self.articulo.width) if self.articulo is not None else 880
        z = 1.0 + 0.03 * suave(lim((t - self.m(1)) / 5.0))
        P.ventana(img, self.articulo, (W - w) / 2, 50, w, h, a=a, zoom=z, cx=0.5, cy=0.4, radio=8, borde=T.claro)
        rotulo(img, "Detroit · noviembre de 2024", W / 2, 1015, 40, T.claro, a, "centro")
        return img

    def _sala(self, t):
        T = MANZANA
        m = self.m
        img = self.sala.cuadro(t - self.ini_3d)
        oscurecer(img, True, 360, 0.6)
        leyenda(img, "evidencia guardada", "se reiniciaban solos", aparece(t, self.c_3d + 0.2, 0.6, m(2) - 0.2), tema=T,
                detalle="y volvían a BFU", a_detalle=aparece(t, self.c_3d + 1.0, 0.6, m(2) - 0.2))
        s = aparece(t, m(2) - 0.1, 0.5)
        if s > 0:
            cp = Capa()
            c = cp.c
            for k, x in enumerate((640, 960, 1280)):
                u = (t * 0.9 + k * 0.33) % 1.0
                cp.tinta(T.claro, s * 0.8 * (1 - u))
                c.set_line_width(3)
                for r in (30 + 90 * u,):
                    c.arc(x, 420, r, math.radians(200), math.radians(340))
                    c.stroke()
            img = cp.componer(img, sombra=0.2, brillo=0.4, col_brillo=T.claro)
            rotulo(img, "?", 960, 300, 90, T.acento, s, "centro", nombre="Inter-Light.ttf")
            leyenda(img, "sospechaban", "una señal entre teléfonos", s, tema=T)
        return img

    def _jiska(self, t):
        img = self.fondo()
        T = MANZANA
        a = aparece(t, self.m(3) - 0.3, 0.6)
        persona_en(img, self.jiska, 240, 260, 620, int(620 * 452 / 677), t, self.m(3), a, cy=0.4, tema=T)
        rotulo(img, "Jiska Classen", 960, 470, 66, T.claro, a)
        rotulo(img, "investigadora", 964, 530, 32, T.tenue, a, nombre="Inter-Regular.ttf")
        cp = Capa()
        for k in range(3):
            ak = aparece(t, self.en(3, "tres") + 0.2 * k, 0.4)
            P.tarjeta(cp.c, 964 + k * 110, 600, 84, 84, 42, T.panel, ak, borde=T.acento, a_borde=0.9, grosor=3)
        img = cp.componer(img, sombra=0.3)
        for k in range(3):
            rotulo(img, str(k + 1), 1006 + k * 110, 660, 40, T.acento, aparece(t, self.en(3, "tres") + 0.2 * k, 0.4), "centro",
                   nombre="Inter-Light.ttf")
        return img

    def _pasos_jiska(self, t):
        img = self.fondo()
        T = MANZANA
        m = self.m
        # cabecera con los tres pasos
        cp = Capa()
        c = cp.c
        activo = 0 if t < m(5) else (1 if t < m(6) else 2)
        for k in range(3):
            P.tarjeta(c, 778 + k * 150, 70, 64, 64, 32, T.acento if k == activo else T.panel, 1.0, borde=T.claro)
        img = cp.componer(img, sombra=0.3)
        for k in range(3):
            rotulo(img, str(k + 1), 810 + k * 150, 116, 32, T.oscuro if k == activo else T.claro, 1.0, "centro")
        cp = Capa()
        c = cp.c
        # 1: la palabra nueva dentro del código de iOS
        a1 = aparece(t, m(4) - 0.2, 0.5, m(5) - 0.3)
        if a1 > 0:
            P.tarjeta(c, 260, 220, 1400, 640, 22, mezcla(T.panel, NEGRO, 0.35), a1, borde=T.claro)
            P.barras_codigo(c, 320, 270, 1280, 18, 32, 1210 + int(t * 6) % 3, (T.tenue, T.claro), a1 * 0.6, sangria=False)
            hall = aparece(t, self.en(4, "encontró"), 0.5)
            P.tarjeta(c, 560, 500, 800, 90, 14, mezcla(T.panel, T.acento, 0.35), a1 * hall, borde=T.acento, a_borde=1.0, grosor=3)
        # 2: un iPhone de pruebas, sin tocar, y el reloj que llega a 72 horas
        a2 = aparece(t, m(5) - 0.2, 0.5, m(6) - 0.3)
        u72 = lim((t - m(5) - 1.0) / max(1.0, self.en(5, "exactas") - m(5) - 0.6))
        reinicia = aparece(t, self.en(5, "reinició") - 0.2, 0.3)
        if a2 > 0:
            cp.tinta(T.claro, a2)
            DG.telefono(c, 620, 560, 520, 5, pantalla=mezcla(T.panel, NEGRO if reinicia < 0.5 else T.claro, 0.3 + 0.4 * reinicia))
            P.icono_wifi(c, 620, 420, 110, 8)
            cp.tinta(T.acento, a2)
            P.icono_reloj(c, 1260, 470, 240, u72 * 3, 9)
        # 3: el Secure Enclave por dentro: el contador
        a3 = aparece(t, m(6) - 0.2, 0.6)
        if a3 > 0:
            cp.tinta(T.claro, 0.9 * a3)
            DG.chip(c, 620, 560, 420, 4, 8, a3)
            P.tarjeta(c, 470, 430, 300, 260, 20, mezcla(T.panel, T.acento, 0.15), a3, borde=T.acento, a_borde=0.9, grosor=3)
            fin_ = aparece(t, m(8) + 0.6, 0.5)
            if fin_ > 0:
                cp.tinta(T.acento, fin_)
                DG.flecha(c, (840, 560), (1150, 560), fin_, 5)
                P.tarjeta(c, 1170, 470, 360, 180, 22, T.panel, fin_, borde=T.claro)
            senal = aparece(t, m(9) - 0.1, 0.5)
            if senal > 0:
                cp.tinta(T.tenue, senal)
                for r in (40, 80, 120):
                    c.set_line_width(3)
                    c.arc(1500, 880, r, math.radians(200), math.radians(340))
                    c.stroke()
                cp.tinta(ROJO, senal)
                DG.cruz(c, 1500, 840, 110, 8)
        img = cp.componer(img, sombra=0.45, brillo=0.35, col_brillo=T.acento)
        if a1 > 0:
            hall = aparece(t, self.en(4, "encontró"), 0.5)
            rotulo(img, "inactivity_reboot", 960, 562, 52, T.claro, a1 * hall, "centro")
            rotulo(img, "palabras nuevas en el código de iOS", 960, 200, 32, T.claro, a1, "centro")
            rotulo(img, "reinicio por inactividad", 960, 640, 30, T.acento, a1 * aparece(t, self.en(4, "reinicio"), 0.5), "centro")
            rotulo(img, "aparece por primera vez en iOS 18.1", 960, 940, 32, T.claro, a1 * aparece(t, self.en(4, "aparecía"), 0.5), "centro")
        if a2 > 0:
            rotulo(img, "sin tocarlo", 1260, 760, 32, T.tenue, a2, "centro", nombre="Inter-Regular.ttf")
            rotulo(img, "72 horas", 1260, 840, 64, T.acento, a2 * aparece(t, self.en(5, "72") - 0.2, 0.4), "centro", nombre="Inter-Light.ttf")
            rotulo(img, "conectado a wifi", 620, 880, 28, T.tenue, a2, "centro", nombre="Inter-Regular.ttf")
            rotulo(img, "se reinició", 620, 960, 40, T.acento, a2 * reinicia, "centro")
        if a3 > 0:
            llena = lim((t - m(7)) / max(1.0, m(8) + 0.4 - m(7)))
            rotulo(img, "Secure Enclave", 620, 290, 34, T.claro, a3, "centro")
            rotulo(img, "contador", 620, 520, 40, T.acento, a3, "centro", nombre="Inter-Light.ttf")
            rotulo(img, "tiempo sin desbloquear", 620, 640, 24, T.tenue, a3 * aparece(t, m(7), 0.5), "centro", nombre="Inter-Regular.ttf")
            if t > m(7):                                     # una barra que se llena, sin horas que la voz no dice
                img[566:576, 510:730] = img[566:576, 510:730] * 0.5 + T.tenue * 0.15
                img[566:576, 510 : 510 + int(220 * llena)] = T.acento
            fin_ = aparece(t, m(8) + 0.6, 0.5)
            rotulo(img, "3 días:", 1350, 545, 32, T.acento, fin_, "centro")
            rotulo(img, "reiníciate", 1350, 600, 40, T.claro, fin_, "centro")
            rotulo(img, "ninguna señal entre teléfonos", 1500, 1010, 30, T.claro, aparece(t, m(9) - 0.1, 0.5), "centro")
            rotulo(img, "Apple lo agregó sin anunciarlo", 620, 960, 32, T.acento, aparece(t, m(10) + 0.1, 0.6), "centro")
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return self.mezclar(t, (self._sigue, self._articulo, self._sala, self._jiska, self._pasos_jiska))

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, S.zumbido(d, 3121), -16, 1.5, 1.5)
        m.agregar("papel", self.m(1) - 0.3, S.papel(1.0, 3122), -6)
        for k, (_, tk) in enumerate(self.reinicios):
            m.agregar("reinicio", self.ini_3d + tk, S.reinicio(3123 + k), -4)
        ticks = list(np.arange(self.m(5) + 1.0, self.en(5, "exactas") + 0.4, 0.12))
        m.agregar("reloj", 0.0, sfx.tics(ticks, d, 3127), -10, 0.2, 0.4)
        m.agregar("reinicio", self.en(5, "reinició"), S.reinicio(3128), -4)
        m.agregar("hallazgo", self.en(4, "encontró"), S.hallazgo(3129), -6)
        return m.x[:n]


# =========================================================================== 3.13


ESLABONES = ((420, "bootrom"), (960, "cargador"), (1500, "iOS"))


def cadena_arranque(img, t, tema, a, p_eslabon, firmas, grieta=0.0, col_grieta=ROJO):
    """Los tres programas del arranque como eslabones de una cadena, cada uno con la firma de Apple."""
    T = tema
    cp = Capa()
    c = cp.c
    for k, (x, _) in enumerate(ESLABONES):
        ak = a * p_eslabon[k]
        if ak <= 0:
            continue
        col = col_grieta if (k == 0 and grieta > 0) else T.claro
        P.tarjeta(c, x - 170, 460, 340, 170, 85, mezcla(T.panel, col, 0.06), ak, borde=col, a_borde=0.8, grosor=3)
        if k < 2:
            cp.tinta(T.claro, ak * p_eslabon[k + 1])
            P.eslabon(c, x + 270, 545, 160, 64, 0.0, 9, grieta if k == 0 else 0.0)
        if firmas[k] > 0:
            cp.tinta(T.acento, a * firmas[k])
            P.sello(c, x + 120, 470, 64)
            cp.tinta(T.oscuro, a * firmas[k])
            P.icono_check(c, x + 120, 470, 30, 5)
    img = cp.componer(img, sombra=0.45, brillo=0.35, col_brillo=T.acento)
    for k, (x, nombre) in enumerate(ESLABONES):
        rotulo(img, nombre, x, 560, 40, T.claro, a * p_eslabon[k], "centro")
    return img


class Sub313(Sub3):
    """La primera arma está grabada en el silicio: la bootrom revisa la firma de Apple del siguiente
    programa y le pasa el control; es el primer eslabón de la cadena de confianza."""

    tema = MANZANA
    cine = CINE_AP

    def cuadro(self, t: float) -> np.ndarray:
        img = self.fondo()
        T = MANZANA
        m = self.m
        cp = Capa()
        c = cp.c
        # el chip con la bootrom grabada (antes de que aparezca la cadena)
        a_chip = aparece(t, 0.2, 0.8, m(3) - 0.3)
        if a_chip > 0:
            cp.tinta(T.claro, 0.9 * a_chip)
            DG.chip(c, 960, 520, 460, 4, 9, a_chip)
            rom = aparece(t, m(2) - 0.1, 0.6)
            P.tarjeta(c, 820, 450, 280, 140, 16, mezcla(T.panel, T.acento, 0.25), a_chip * rom, borde=T.acento, a_borde=1.0, grosor=3)
            for k in range(7):
                cp.tinta(T.acento, a_chip * rom * 0.5)
                c.rectangle(845 + k * 34, 560, 22, 8)
                c.fill()
            if t > m(1) - 0.2:
                b = aparece(t, m(1) - 0.2, 0.5)
                cp.tinta(T.claro, b * a_chip)
                P.icono_power(c, 380, 520, 120, 10)
                DG.flecha(c, (470, 520), (700, 520), suave(lim((t - m(1)) / 0.8)) * a_chip, 4)
        img = cp.componer(img, sombra=0.45, brillo=0.35, col_brillo=T.acento)
        if a_chip > 0:
            rotulo(img, "grabada en el silicio", 960, 200, 36, T.claro, a_chip * aparece(t, self.en(0, "grabada"), 0.6), "centro")
            rotulo(img, "lo primero que corre no es iOS", 960, 880, 32, T.claro, a_chip * aparece(t, m(1) + 0.4, 0.6, m(2) - 0.2), "centro")
            rom = aparece(t, m(2) - 0.1, 0.6)
            rotulo(img, "bootrom", 960, 530, 40, T.claro, a_chip * rom, "centro")
            rotulo(img, "de fábrica · no se puede modificar", 960, 880, 32, T.acento, a_chip * aparece(t, self.en(2, "fábrica"), 0.6), "centro")
        # la cadena: bootrom revisa la firma del cargador y le pasa el control
        a = aparece(t, m(3) - 0.2, 0.7)
        if a > 0:
            p = [1.0, aparece(t, m(3) + 0.3, 0.6), aparece(t, m(5) + 0.2, 0.6)]
            firmas = [aparece(t, m(5) + 0.4, 0.5), aparece(t, m(3) + 1.4, 0.5), aparece(t, m(5) + 0.8, 0.5)]
            img = cadena_arranque(img, t, T, a, p, firmas)
            rotulo(img, "revisa la firma de Apple", 960, 360, 34, T.claro, aparece(t, m(3) + 1.2, 0.6, m(4) - 0.1), "centro")
            pasa = aparece(t, m(4), 0.5)
            if pasa > 0:
                cp = Capa()
                u = suave(lim((t - m(4)) / 1.0))
                cp.tinta(T.acento, pasa)
                DG.flecha(cp.c, (420, 680), (420 + 540 * u, 680), 1.0, 5, curva=40)
                img = cp.componer(img, sombra=0.2, brillo=0.5, col_brillo=T.acento)
                rotulo(img, "solo entonces le pasa el control", 960, 360, 34, T.claro, pasa * (1 - aparece(t, m(5), 0.4)), "centro")
            rotulo(img, "cadena de confianza", 960, 360, 44, T.acento, aparece(t, m(5) + 0.3, 0.6), "centro")
            rotulo(img, "primer eslabón", 420, 780, 28, T.acento, aparece(t, m(5) + 0.6, 0.6), "centro")
        return img

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, S.zumbido(d, 3131), -16, 1.5, 1.5)
        m.agregar("láser", self.m(2), sfx.laser(1.4, 3132), -10)
        m.agregar("encendido", self.m(1), S.reinicio(3133), -8)
        m.agregar("eslabón", self.m(3) + 0.3, S.eslabones(1, 3134), -4)
        m.agregar("cadena", self.m(5) + 0.2, S.eslabones(3, 3135), -2)
        return m.x[:n]


# =========================================================================== 3.14




class Sub314(Sub3):
    """checkm8: un error en la bootrom, en la parte del USB del modo de recuperación; nadie lo puede
    corregir; del 4S al X. El primer eslabón se agrieta; el Secure Enclave sigue protegiendo."""

    tema = MANZANA
    cine = CINE_AP

    def preparar(self) -> None:
        o = self.o
        self.tuit = P.cargar("3.14_tweet_checkm8.png")
        self.seg = Segmentos([o[1]], CRUCE)

    def _tuit(self, t):
        img = self.fondo()
        T = MANZANA
        a = aparece(t, 0.2, 0.6)
        w = 1160
        h = int(w * self.tuit.height / self.tuit.width) if self.tuit is not None else 580
        x0, y0 = (W - w) / 2, 270
        # la imagen del tuit llega al borde: va sobre una tarjeta blanca con margen
        P.ventana(img, None, x0 - 40, y0 - 36, w + 80, h + 72, a=a, radio=18, borde=T.claro, fondo_vacio=(1.0, 1.0, 1.0))
        P.ventana(img, self.tuit, x0, y0, w, h, a=a, radio=2, sombra=0)
        antetitulo(img, "2019", W / 2, 180, T.tenue, a, "centro")
        rotulo(img, "checkm8", W / 2, 960, 64, T.acento, aparece(t, self.en(0, "checkm8"), 0.6), "centro")
        rotulo(img, "un error dentro de la bootrom", W / 2, 1016, 30, T.claro, aparece(t, self.en(0, "error"), 0.6), "centro",
               nombre="Inter-Regular.ttf")
        return img

    def _cadena(self, t):
        img = self.fondo()
        T = MANZANA
        m = self.m
        a = aparece(t, m(1) - 0.4, 0.6)
        grieta = suave(lim((t - m(1) - 1.0) / 0.6))
        img = cadena_arranque(img, t, T, a, [1.0, 1.0, 1.0], [1.0, 1.0, 1.0], grieta)
        rotulo(img, "USB · modo de recuperación", 420, 720, 26, ROJO, aparece(t, m(1) + 1.2, 0.6), "centro")
        # ninguna actualización lo corrige: las flechas rebotan
        r = aparece(t, m(2) - 0.1, 0.5, m(3) - 0.2)
        if r > 0:
            cp = Capa()
            for k in range(3):
                u = ((t - m(2)) * 0.7 + k / 3) % 1.0
                x = 340 + 80 * k
                baja = min(1.0, u / 0.6)
                cp.tinta(T.claro, r * (1 - max(0.0, u - 0.6) / 0.4))
                DG.flecha(cp.c, (x, 250), (x, 250 + 180 * baja), 1.0, 4, 14)
                if u > 0.6:
                    cp.tinta(ROJO, r * (1 - (u - 0.6) / 0.4))
                    DG.cruz(cp.c, x, 445, 26, 5)
            img = cp.componer(img, sombra=0.2)
            rotulo(img, "actualizaciones", 420, 225, 26, T.tenue, r, "centro", nombre="Inter-Regular.ttf")
            rotulo(img, "ninguna actualización lo corrige", 960, 900, 34, T.claro, r, "centro")
            rotulo(img, "la bootrom no se puede reescribir", 960, 950, 28, T.tenue, r, "centro", nombre="Inter-Regular.ttf")
        # del 4S al X
        mo = aparece(t, m(3) - 0.1, 0.5, m(4) - 0.2)
        if mo > 0:
            cp = Capa()                                      # del primero al último: solo los que nombra la voz
            for k in range(7):
                ak = mo * aparece(t, m(3) + 0.1 * k, 0.3)
                cp.tinta(T.claro if k in (0, 6) else T.tenue, ak)
                DG.telefono(cp.c, 420 + k * 180, 860, 150, 4)
            img = cp.componer(img, sombra=0.35)
            rotulo(img, "4S", 420, 975, 34, T.claro, mo, "centro")
            rotulo(img, "X", 420 + 6 * 180, 975, 34, T.claro, mo * aparece(t, m(3) + 0.6, 0.3), "centro")
            rotulo(img, "del iPhone 4S al X", 960, 340, 40, T.claro, mo, "centro")
        # la herramienta forense entra por el eslabón roto y saca el sistema de archivos
        h_ = aparece(t, m(4) - 0.1, 0.6, m(5) - 0.2)
        if h_ > 0:
            cp = Capa()
            c = cp.c
            u = suave(lim((t - m(4)) / 2.0))
            cp.tinta(T.acento, h_)
            DG.computadora(c, 190, 880, 150, 5)
            DG.flecha(c, (215, 790), (290, 645), u, 5, curva=-25)
            for k in range(4):
                ak = h_ * aparece(t, m(4) + 2.2 + 0.25 * k, 0.4)
                cp.tinta(T.claro, ak)
                DG.archivo(c, 1050 + k * 120, 770, 90, 4)
            img = cp.componer(img, sombra=0.35, brillo=0.35, col_brillo=T.acento)
            rotulo(img, "arranca con su propio software", 960, 340, 34, T.claro, h_, "centro")
            rotulo(img, "y saca el sistema de archivos", 1230, 930, 30, T.acento, h_ * aparece(t, m(4) + 2.2, 0.5), "centro")
        # el Secure Enclave sigue en pie
        s = aparece(t, m(5) - 0.1, 0.6)
        if s > 0:
            cp = Capa()
            c = cp.c
            P.tarjeta(c, 760, 760, 400, 220, 30, mezcla(T.panel, T.acento, 0.2), s, borde=T.acento, a_borde=1.0, grosor=3)
            cp.tinta(T.acento, s)
            DG.candado(c, 960, 850, 80)
            img = cp.componer(img, sombra=0.4, brillo=0.5, col_brillo=T.acento)
            rotulo(img, "Secure Enclave", 960, 950, 32, T.claro, s, "centro")
            rotulo(img, "checkm8 no se lo puede saltar", 960, 340, 34, T.claro, s * (1 - aparece(t, m(6), 0.4)), "centro")
            rotulo(img, "la contraseña sigue protegiendo lo más importante", 960, 340, 34, T.acento, aparece(t, m(6) + 0.2, 0.6), "centro")
        return img

    def cuadro(self, t: float) -> np.ndarray:
        return self.mezclar(t, (self._tuit, self._cadena))

    def efectos(self) -> np.ndarray:
        d, n = self.d, int(round(self.d * SR))
        m = sfx.Mezcla(d)
        m.agregar("zumbido", 0.0, S.zumbido(d, 3141), -16, 1.5, 1.5)
        m.agregar("grieta", self.m(1) + 1.0, S.grieta(3142), -1)
        m.agregar("datos", self.m(4) + 2.2, sfx.datos(2.0, 3143, 16), -10)
        m.agregar("candado", self.m(5), sfx.candado(3144), -4)
        return m.x[:n]


# =========================================================================== registro

SUBESCENAS = {"3.0": Sub30, "3.1": Sub31, "3.2": Sub32, "3.3": Sub33, "3.4": Sub34, "3.5": Sub35, "3.6": Sub36,
              "3.7": Sub37, "3.8": Sub38, "3.9": Sub39, "3.10": Sub310, "3.11": Sub311, "3.12": Sub312,
              "3.13": Sub313, "3.14": Sub314}

# Fotogramas clave para revisar antes del render completo: (archivo, clip, tiempo en el clip)
REVISION = [
    ("1_centro_noche.png", "3.0", lambda T: T.oraciones[2] + 1.0),
    ("2_puerto_lightning.png", "3.3", lambda T: repartir_oraciones("3.3", T)[5] - 0.6),
    ("3_bfu_afu.png", "3.11", lambda T: T.oraciones[4] + 2.5),
    ("4_checkm8_cadena.png", "3.14", lambda T: T.oraciones[2] + 1.5),
]


def clips() -> list[str]:
    return ["titulo"] + [s.id for s in guion.leer()[NUMERO].subescenas]


def crear(id_: str) -> Subescena:
    if id_ == "titulo":
        return titulo()
    return SUBESCENAS[id_](id_, tiempos(id_))
