"""Cámaras, teléfonos y pantallas de los planos 3D de las escenas 2 y 4, en Python puro.

Lo usan los dos lados: el plano en Blender (para poner la cámara y los objetos) y la escena (para
proyectar el contenido de cada pantalla sobre el cuadro ya renderizado). Así lo que se dibuja en 2D
—la pantalla de bloqueo, la barra de copia, los avisos de espera— cae exactamente sobre el vidrio
del teléfono o de la laptop en 3D, con letra nítida, y se puede animar sin volver a renderizar.

La cámara de Blender apunta a un punto «mira» con la restricción Track To (eje −Z hacia la mira, Y
hacia arriba) y sensor de 36 mm de ancho; `proyectar` hace la misma cuenta.

Ejes de cada objeto: x a lo ancho, y a lo largo (arriba del teléfono hacia +y), z hacia afuera de la
pantalla. Medidas en metros.
"""

from __future__ import annotations

import math

ANCHO, ALTO = 1920, 1080
SENSOR = 36.0

# --------------------------------------------------------------------------- vectores


def _sum(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _res(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _esc(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def _pto(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cruz(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _uni(a):
    n = math.sqrt(_pto(a, a)) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


def mezclar(a, b, u):
    return tuple(x + (y - x) * u for x, y in zip(a, b))


def suave(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def coseno(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return 0.5 - 0.5 * math.cos(math.pi * x)


# --------------------------------------------------------------------------- cámara


def base_camara(pos, mira):
    """Ejes adelante, derecha y arriba de una cámara en `pos` que mira a `mira` (sin alabeo)."""
    f = _uni(_res(mira, pos))
    r = _cruz(f, (0.0, 0.0, 1.0))
    if _pto(r, r) < 1e-12:                                   # mirando justo hacia abajo
        r = (1.0, 0.0, 0.0)
    r = _uni(r)
    u = _cruz(r, f)
    return f, r, u


def proyectar(p, pos, mira, lente: float):
    """Punto del mundo -> píxel (x, y) del cuadro de 1920×1080."""
    f, r, u = base_camara(pos, mira)
    d = _res(p, pos)
    z = max(1e-6, _pto(d, f))
    k = lente / SENSOR * ANCHO
    return (ANCHO / 2 + _pto(d, r) / z * k, ALTO / 2 - _pto(d, u) / z * k)


def recorrido(t: float, claves):
    """Cámara que pasa por `claves` [(t, pos, mira, lente), …]: entre una clave y la siguiente se
    mueve con arranque y frenado suaves; antes de la primera y después de la última, quieta."""
    if t <= claves[0][0]:
        return claves[0][1:]
    for (t0, p0, m0, l0), (t1, p1, m1, l1) in zip(claves, claves[1:]):
        if t <= t1:
            u = coseno((t - t0) / max(1e-6, t1 - t0))
            return mezclar(p0, p1, u), mezclar(m0, m1, u), l0 + (l1 - l0) * u
    return claves[-1][1:]


# --------------------------------------------------------------------------- teléfonos


# iPhone 7 (2016): 138.3 × 67.1 × 7.1 mm; pantalla de 4.7 pulgadas (104.0 × 58.5 mm).
IPHONE = dict(largo=0.1383, ancho=0.0671, grueso=0.0071, radio=0.0095, pant_largo=0.1040, pant_ancho=0.0585,
              pant_y=0.0, px=(750, 1334))
# Android de 2016 (del tamaño de un Pixel): 143.8 × 69.5 × 8.5 mm; pantalla de 5 pulgadas.
ANDROID = dict(largo=0.1438, ancho=0.0695, grueso=0.0085, radio=0.0080, pant_largo=0.1107, pant_ancho=0.0623,
               pant_y=0.0005, px=(720, 1280))
# Laptop de 14 pulgadas: pantalla 0.310 × 0.174 m, abierta 105°.
LAPTOP = dict(ancho=0.326, fondo=0.226, grueso=0.016, tapa=0.006, pant_ancho=0.310, pant_alto=0.174,
              abierta=105.0, px=(1600, 900))


def girar_z(p, grados: float):
    a = math.radians(grados)
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2])


def esquinas_telefono(modelo: dict, centro, giro: float = 0.0, desplazamiento=(0.0, 0.0, 0.0)):
    """Esquinas de la pantalla de un teléfono acostado boca arriba con su centro de abajo en
    `centro` y girado `giro` grados sobre z: arriba-izquierda, arriba-derecha, abajo-derecha,
    abajo-izquierda (el orden en que se lee la imagen de la pantalla)."""
    w, h, y0 = modelo["pant_ancho"] / 2, modelo["pant_largo"] / 2, modelo["pant_y"]
    z = modelo["grueso"] + 0.0003
    locales = [(-w, y0 + h, z), (w, y0 + h, z), (w, y0 - h, z), (-w, y0 - h, z)]
    return [_sum(_sum(girar_z(q, giro), centro), desplazamiento) for q in locales]


def ejes_tapa():
    """Dirección a lo largo de la tapa abierta (desde la bisagra) y normal de la cara de la pantalla.
    Cerrada, la tapa se apoya sobre el cuerpo con la pantalla hacia abajo; abrirla es girarla
    `abierta` grados sobre el eje de la bisagra (x)."""
    a = math.radians(LAPTOP["abierta"])
    return (0.0, -math.cos(a), math.sin(a)), (0.0, -math.sin(a), -math.cos(a))


def punto_tapa(x: float, s: float, despegue: float = 0.0):
    """Punto de la cara interior de la tapa: `x` a lo ancho, `s` desde la bisagra, `despegue` hacia
    afuera de la cara (en ejes de la laptop)."""
    d, n = ejes_tapa()
    b = (x, LAPTOP["fondo"] / 2, LAPTOP["grueso"])
    return _sum(_sum(b, _esc(d, s)), _esc(n, despegue))


LARGO_TAPA = LAPTOP["fondo"]
MARGEN_PANTALLA = 0.036                                    # de la bisagra al borde de abajo de la pantalla


def esquinas_laptop(centro, giro: float = 0.0):
    """Esquinas de la pantalla de la laptop (cuerpo centrado en `centro`, apoyado en z), en el mismo
    orden que `esquinas_telefono`."""
    w = LAPTOP["pant_ancho"] / 2
    s0, s1 = MARGEN_PANTALLA, MARGEN_PANTALLA + LAPTOP["pant_alto"]
    locales = [punto_tapa(-w, s1, 0.0004), punto_tapa(w, s1, 0.0004), punto_tapa(w, s0, 0.0004),
               punto_tapa(-w, s0, 0.0004)]
    return [_sum(girar_z(q, giro), centro) for q in locales]


def proyectar_esquinas(esquinas, pos, mira, lente):
    return [proyectar(p, pos, mira, lente) for p in esquinas]


# --------------------------------------------------------------------------- vibración del teléfono


def vibracion(t: float, golpes) -> tuple[float, float, float]:
    """Desplazamiento (m) del teléfono que vibra sobre la mesa tras cada error: dos zumbidos de
    0.22 s, como `sfx.vibracion`, que lo sacuden de lado unos milímetros."""
    dx = dy = 0.0
    for tg in golpes:
        x = t - tg
        for ini in (0.0, 0.36):
            u = x - ini
            if 0.0 <= u < 0.22:
                env = math.sin(math.pi * u / 0.22)
                dx += 0.0011 * env * math.sin(u * 2 * math.pi * 31)
                dy += 0.0006 * env * math.sin(u * 2 * math.pi * 23 + 1.0)
    return (dx, dy, 0.0)


# --------------------------------------------------------------------------- planos de la escena 2

# Mesa de evidencias (2.0): el teléfono dentro de la bolsa, sobre acero.
MESA_TELEFONO = ((0.0, 0.0, 0.0012), -14.0)            # centro (sobre la bolsa) y giro


def camara_mesa(t: float, dur: float):
    """Se acerca despacio y en diagonal al teléfono, desde arriba y un poco de lado."""
    u = coseno(t / max(dur, 1e-6))
    pos = mezclar((0.20, -0.34, 0.36), (0.12, -0.215, 0.235), u)
    mira = mezclar((0.005, 0.004, 0.0), (0.0, 0.006, 0.004), u)
    return pos, mira, 50.0


# Laboratorio (2.2, 2.7 y 2.8): el teléfono sobre el escritorio, un cable a la laptop.
LAB_TELEFONO = ((-0.27, -0.03, 0.0), 10.0)
LAB_LAPTOP = ((0.11, 0.12, 0.0), -12.0)


def centro_pantalla_laptop():
    e = esquinas_laptop(*LAB_LAPTOP)
    return tuple(sum(q[i] for q in e) / 4 for i in range(3))


def frente_pantalla_laptop(dist: float, lado: float = 0.0, alto: float = 0.0):
    """Punto a `dist` m delante del centro de la pantalla (sobre su normal), corrido `lado` m a la
    derecha y `alto` m hacia arriba."""
    _, n = ejes_tapa()
    n = girar_z(n, LAB_LAPTOP[1])
    c = centro_pantalla_laptop()
    derecha = girar_z((1.0, 0.0, 0.0), LAB_LAPTOP[1])
    return _sum(_sum(_sum(c, _esc(n, dist)), _esc(derecha, lado)), (0.0, 0.0, alto))


def centro_telefono_lab():
    c, giro = LAB_TELEFONO
    return _sum(c, (0.0, 0.0, IPHONE["grueso"]))


def claves_laboratorio(m):
    """`m`: inicios (s) de las oraciones 1, 3, 4, 7 y 8 de la 2.2. Primero el teléfono y su cable;
    la cámara sigue el cable hasta la laptop, se queda en la pantalla mientras copia y busca, y al
    final se aleja: el teléfono, a un lado, ni se entera."""
    m1, m3, m4, m7, m8 = m
    tel = centro_telefono_lab()
    pant = centro_pantalla_laptop()
    return [
        (0.0, _sum(tel, (-0.10, -0.25, 0.17)), tel, 50.0),
        (m1 + 0.8, _sum(tel, (-0.06, -0.21, 0.14)), _sum(tel, (0.03, 0.02, 0.0)), 50.0),
        (m3 - 0.3, frente_pantalla_laptop(0.80, -0.12, 0.05), pant, 45.0),
        (m4 + 0.3, frente_pantalla_laptop(0.66, -0.06, 0.03), pant, 45.0),
        (m7 - 0.4, frente_pantalla_laptop(0.62, -0.05, 0.03), pant, 45.0),
        (m8 - 0.5, frente_pantalla_laptop(0.58, -0.04, 0.03), pant, 45.0),
        (m8 + 1.8, frente_pantalla_laptop(0.92, -0.30, 0.20), mezclar(tel, pant, 0.45), 36.0),
    ]


def camara_cifrado(t: float, dur: float):
    """2.7: la laptop y el teléfono en el mismo cuadro; un acercamiento muy lento."""
    u = coseno(t / max(dur, 1e-6))
    tel, pant = centro_telefono_lab(), centro_pantalla_laptop()
    medio = mezclar(tel, pant, 0.5)
    pos = mezclar(frente_pantalla_laptop(1.25, -0.30, 0.25), frente_pantalla_laptop(1.15, -0.30, 0.23), u)
    return pos, _sum(medio, (0.0, 0.0, -0.03)), 32.0


def camara_errores(t: float, dur: float):
    """2.8: el teléfono casi desde arriba, llenando el cuadro; se acerca muy despacio."""
    c = centro_telefono_lab()
    u = coseno(t / max(dur, 1e-6))
    pos = mezclar(_sum(c, (0.03, -0.13, 0.25)), _sum(c, (0.025, -0.11, 0.215)), u)
    return pos, _sum(c, (0.0, 0.004, 0.0)), 50.0


# Mesa de noche (2.9): un Android boca arriba.
NOCHE_TELEFONO = ((0.0, 0.0, 0.0), 22.0)


def camara_noche(t: float, dur: float):
    u = coseno(t / max(dur, 1e-6))
    pos = mezclar((-0.30, -0.44, 0.34), (-0.22, -0.33, 0.26), u)
    mira = mezclar((0.0, 0.02, 0.0), (0.0, 0.01, 0.004), u)
    return pos, mira, 42.0


# El teléfono abierto (2.1): la pantalla gira sobre su borde de arriba.
ABIERTO_TELEFONO = ((0.0, 0.0, 0.0), 0.0)


def camara_abierto(t: float, t_acerca: float, dur: float):
    """De tres cuartos sobre el teléfono; desde `t_acerca`, se mete hasta el chip de memoria."""
    u = coseno(t / max(t_acerca + 1.5, 1e-6)) * 0.35
    lejos_p = mezclar((0.16, -0.24, 0.24), (0.12, -0.20, 0.21), u)
    lejos_m = (0.0, -0.005, 0.0)
    a = coseno((t - t_acerca) / 2.4)
    cerca_p = (CHIP_FLASH[0] + 0.012, CHIP_FLASH[1] - 0.030, 0.050)
    cerca_m = (CHIP_FLASH[0], CHIP_FLASH[1] + 0.002, 0.004)
    return mezclar(lejos_p, cerca_p, a), mezclar(lejos_m, cerca_m, a), 50.0 + 10.0 * a


# Posición (en el teléfono acostado, sin pantalla) del chip de memoria flash y del procesador.
CHIP_FLASH = (0.012, -0.004, 0.0)
CHIP_CPU = (0.010, 0.030, 0.0)
