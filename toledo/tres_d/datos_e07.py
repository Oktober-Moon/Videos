"""Datos de los planos 3D de las escenas 7 y 8 que no necesitan Blender: dónde está cada pieza de la
placa, de la mesa del laboratorio y de la casa de Bates, y el recorrido de cada cámara.

Los usan los planos (`tres_d/planos_e07.py`, `planos_e08.py`) y también los rótulos 2D de
`escenas/escena07.py`: con `proyectar` se calcula dónde cae en pantalla un punto del mundo 3D (un
punto de prueba, un aparato de la mesa) con la misma cámara que usa Blender, así un rótulo sigue a
su objeto aunque la cámara se mueva.

Unidades: metros, z hacia arriba. La placa se describe en milímetros (`MM`) con el origen en su
centro; su cara de arriba queda en z = GROSOR.
"""

import math

MM = 0.001

# --------------------------------------------------------------------------- la placa (mm)

LARGO, ANCHO, GROSOR = 100.0, 70.0, 1.6

# nombre -> (x, y, ancho, largo, alto, marca en dos renglones)
CHIPS = {
    "U1": (-14.0, 6.0, 14.0, 14.0, 1.1, ("SX7701A", "1931 KA2")),        # procesador (BGA)
    "U2": (21.0, 9.0, 11.5, 13.0, 1.0, ("FM08G4B", "2215 TW")),           # memoria flash eMMC (BGA)
    "U3": (-14.0, -18.0, 9.0, 11.0, 0.95, ("D3L4G", "16B 2208")),          # memoria RAM
    "U4": (5.0, -17.0, 6.0, 6.0, 0.85, ("P3501", "")),                      # regulador (QFN)
}
BLINDAJE = (33.0, -16.0, 13.0, 13.0, 2.0)          # módulo wifi bajo su tapa metálica
CRISTAL = (3.0, 15.0, 3.2, 2.5, 0.8)
BOBINA = (16.0, -15.0, 4.0, 4.0, 2.0)
USB = (-47.0, -6.0, 7.5, 6.0, 2.8)                  # micro-USB en el borde izquierdo

# Puntos de prueba JTAG: cinco pastillas redondas sin rótulo en la esquina de arriba a la izquierda
JTAG = [(-41.0 + k * 2.54, 25.0) for k in range(5)]
SENALES = ("TCK", "TMS", "TDI", "TDO", "GND")
# otras pastillas de prueba sueltas, igual de anónimas
OTROS_TP = [(-3.0, 27.5), (1.0, 27.5), (40.0, 4.0), (43.0, 24.0), (-30.0, -29.0), (8.0, -28.5), (-24.0, 16.0)]
AGUJEROS = [(-45.0, -30.0), (45.0, -30.0), (-45.0, 30.0), (45.0, 30.0)]


def en_placa(x_mm: float, y_mm: float, z_mm: float = GROSOR, centro=(0.0, 0.0, 0.0)) -> tuple:
    """Un punto de la placa (mm) en metros del mundo, con la placa centrada en `centro`."""
    return (centro[0] + x_mm * MM, centro[1] + y_mm * MM, centro[2] + z_mm * MM)


# --------------------------------------------------------------------------- la mesa de aparatos (7.0), en metros

# nombre -> (x, y, giro en grados)
APARATOS = {
    "iphone": (-0.36, 0.02, 8.0),
    "android": (-0.27, -0.03, -6.0),
    "camara": (-0.12, 0.06, 18.0),
    "reloj": (-0.01, -0.05, -12.0),
    "bocina": (0.10, 0.07, 0.0),
    "termostato": (0.21, -0.04, 0.0),
    "sensor": (0.33, 0.05, -10.0),
}
# altura del punto que se rotula (centro visible del aparato)
ALTO_APARATO = {"iphone": 0.008, "android": 0.008, "camara": 0.06, "reloj": 0.01, "bocina": 0.03,
                "termostato": 0.028, "sensor": 0.035}


# --------------------------------------------------------------------------- casa de Bates (metros)

ECHO = (0.0, 0.0, 0.0)            # la bocina sobre la barra de la cocina (base)
ECHO_ALTO, ECHO_RADIO = 0.235, 0.042
JACUZZI = (0.0, 0.0)              # centro de la tina en el patio
JACUZZI_LADO, JACUZZI_ALTO = 2.1, 0.9


# --------------------------------------------------------------------------- utilidades de cámara

def suave(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def mezclar(a, b, u: float):
    return tuple(p + (q - p) * u for p, q in zip(a, b))


def tramo(t: float, a: float, b: float) -> float:
    return suave((t - a) / (b - a)) if b > a else float(t >= b)


def proyectar(p, cam, mira, lente: float, w: int = 1920, h: int = 1080):
    """Punto del mundo -> píxel (x, y) con una cámara que mira a `mira` con z hacia arriba (lo mismo
    que la restricción «Track To» de `base.camara`), lente en mm y sensor de 36 mm a lo ancho.
    Devuelve None si el punto queda detrás de la cámara."""
    f = [m - c for m, c in zip(mira, cam)]
    nf = math.sqrt(sum(v * v for v in f))
    f = [v / nf for v in f]
    r = [f[1] * 1.0 - f[2] * 0.0, f[2] * 0.0 - f[0] * 1.0, 0.0]        # f × z
    nr = math.sqrt(sum(v * v for v in r)) or 1e-9
    r = [v / nr for v in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    d = [a - b for a, b in zip(p, cam)]
    z = sum(a * b for a, b in zip(d, f))
    if z <= 1e-6:
        return None
    x = sum(a * b for a, b in zip(d, r)) / z
    y = sum(a * b for a, b in zip(d, u)) / z
    k = lente / 36.0 * w
    return (w / 2 + x * k, h / 2 - y * k)


# --------------------------------------------------------------------------- recorridos de cámara
# Cada uno devuelve (posición, mira, lente en mm) para el tiempo t (s) del plano. Los que dependen de
# la narración reciben `marcas`: instantes del plano (s) donde empieza cada oración que importa.

def _encadenar(t: float, inicio, pasos):
    """Cámara que va de una toma a la siguiente: `pasos` = [(toma, desde, hasta)], cada toma
    (pos, mira, lente) se alcanza con una curva suave entre `desde` y `hasta`."""
    pos, mira, lente = inicio
    for (p, m, l), a, b in pasos:
        u = tramo(t, a, b)
        pos, mira, lente = mezclar(pos, p, u), mezclar(mira, m, u), lente + (l - lente) * u
    return pos, mira, lente


def cam_mesa(t: float, marcas: dict):
    """7.0 — Mesa de aparatos: abre amplia, va a los dos teléfonos («iOS o Android»), se abre a los
    aparatos IoT («cualquier cosa») y luego se detiene en la cámara barata, el reloj y el sensor de
    fábrica cuando se nombran."""
    amplia = ((0.02, -0.80, 0.46), (0.0, 0.02, 0.0), 38.0)
    amplia2 = ((0.0, -0.74, 0.42), (0.0, 0.02, 0.0), 39.0)
    telefonos = ((-0.28, -0.40, 0.25), (-0.315, 0.0, 0.0), 50.0)
    iot = ((0.04, -0.66, 0.34), (0.05, 0.02, 0.0), 40.0)
    camara = ((-0.08, -0.36, 0.17), (-0.11, 0.05, 0.035), 50.0)
    reloj = ((0.02, -0.37, 0.19), (-0.005, -0.04, 0.008), 50.0)
    sensor = ((0.30, -0.37, 0.19), (0.325, 0.045, 0.025), 50.0)
    m = marcas
    pos, mira, lente = _encadenar(t, amplia, [
        (amplia2, 0.0, max(1.0, m["telefonos"] - 1.2)),
        (telefonos, m["telefonos"] - 1.2, m["telefonos"] + 1.6),
        (iot, m["iot"] - 1.0, m["iot"] + 1.8),
        (camara, m["camara"] - 1.3, m["camara"] + 0.5),
        (reloj, m["reloj"] - 1.1, m["reloj"] + 0.5),
        (sensor, m["sensor"] - 1.4, m["sensor"] + 0.5),
    ])
    deriva = 0.006 * math.sin(t * 0.21) + 0.004 * t / max(m["fin"], 1.0)        # nunca del todo quieta
    return (pos[0] + deriva, pos[1], pos[2] + 0.3 * deriva), mira, lente


def cam_placa(t: float, dur: float, marcas: dict):
    """7.2 — Vista de fábrica sobre la placa: pasa sobre los chips y llega a la esquina de los puntos de
    prueba JTAG, que se encienden («unos puntos de contacto llamados puertos de prueba»)."""
    jtag = en_placa(-36.0, 25.0)
    p0 = ((0.055, -0.135, 0.105), (0.008, 0.006, 0.0), 50.0)
    p1 = ((-0.010, -0.090, 0.085), (-0.012, 0.010, 0.0), 55.0)
    p2 = ((-0.062, -0.045, 0.080), (jtag[0] + 0.004, jtag[1] - 0.002, jtag[2]), 50.0)
    u = tramo(t, 0.0, marcas["puertos"] - 1.5)
    pos, mira, lente = mezclar(p0[0], p1[0], u), mezclar(p0[1], p1[1], u), p0[2] + (p1[2] - p0[2]) * u
    v = tramo(t, marcas["puertos"] - 2.2, marcas["puertos"] + 1.2)
    pos, mira, lente = mezclar(pos, p2[0], v), mezclar(mira, p2[1], v), lente + (p2[2] - lente) * v
    deriva = max(0.0, t - marcas["puertos"] - 1.2) * 0.0012
    return (pos[0] + deriva, pos[1] + deriva * 0.5, pos[2] - deriva * 0.4), mira, lente


def cam_soldar(t: float, dur: float):
    """7.3 — Primer plano de los puntos de prueba mientras se sueldan los cables (macro, poca
    profundidad de campo), con un acercamiento muy lento."""
    jtag = en_placa(-36.0, 25.0)
    u = suave(t / max(dur, 1.0))
    pos = (jtag[0] - 0.028 + 0.010 * u, jtag[1] - 0.062 + 0.012 * u, jtag[2] + 0.050 - 0.008 * u)
    mira = (jtag[0] + 0.0015 * u, jtag[1] + 0.001, jtag[2])
    return pos, mira, 85.0


def cam_aire(t: float, dur: float):
    """7.4 — La boquilla de aire caliente sobre la memoria; las pinzas la levantan al final."""
    u2 = en_placa(21.0, 9.0)
    u = suave(t / max(dur, 1.0))
    pos = (u2[0] + 0.060 - 0.010 * u, u2[1] - 0.085 + 0.012 * u, u2[2] + 0.060 - 0.006 * u)
    mira = (u2[0] - 0.002, u2[1] + 0.002, u2[2] + 0.004 + 0.003 * u)
    return pos, mira, 60.0


def cam_lector(t: float, dur: float):
    """7.4 — El chip en el adaptador del programador: acercamiento lento desde un lado."""
    u = suave(t / max(dur, 1.0))
    pos = (0.135 - 0.025 * u, -0.150 + 0.030 * u, 0.115 - 0.015 * u)
    mira = (0.0, 0.004, 0.030)
    return pos, mira, 55.0


def cam_echo(t: float, dur: float, toma: str):
    """7.6 y 7.7 — La bocina Echo sobre la barra de la cocina, de noche. «repisa»: un empuje lento
    desde lejos; «anillo»: el anillo de luz de cerca."""
    u = suave(t / max(dur, 1.0))
    e = ECHO
    if toma == "anillo":
        pos = (e[0] + 0.36 - 0.05 * u, e[1] - 0.55 + 0.07 * u, e[2] + 0.36 - 0.02 * u)
        mira = (e[0], e[1], e[2] + 0.19)
        return pos, mira, 70.0
    pos = (e[0] + 0.85 - 0.18 * u, e[1] - 1.45 + 0.30 * u, e[2] + 0.42 - 0.04 * u)
    mira = (e[0] - 0.05, e[1] + 0.05, e[2] + 0.12)
    return pos, mira, 50.0


def cam_patio(t: float, dur: float, toma: str):
    """El patio de los Bates de noche, vacío. «llegada»: desde el pasto hacia la casa; «tina»: la tina
    con su vapor; «piso»: a ras del piso del patio, hacia la tina y la llave de la manguera."""
    u = suave(t / max(dur, 1.0))
    cx, cy = JACUZZI
    if toma == "tina":
        pos = (cx + 2.6 - 0.35 * u, cy - 3.4 + 0.45 * u, 1.75 - 0.10 * u)
        mira = (cx, cy + 0.2, 0.75)
        return pos, mira, 45.0
    if toma == "piso":                     # desde la derecha: la tina a un lado, al fondo la llave y la manguera
        pos = (cx + 3.4 - 0.5 * u, cy - 3.2 + 0.4 * u, 0.62 + 0.02 * u)
        mira = (cx + 0.4, cy + 3.0, 0.5)
        return pos, mira, 35.0
    pos = (cx + 4.2 - 0.9 * u, cy - 8.6 + 1.4 * u, 1.55 - 0.05 * u)
    mira = (cx + 0.4, cy + 1.8, 1.0)
    return pos, mira, 35.0
