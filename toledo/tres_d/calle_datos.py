"""Datos de la calle del casco viejo de Friburgo (casas, faroles, tranvía, cámara de la prueba).

Los dos estilos dibujan exactamente la misma calle, el mismo tranvía y el mismo movimiento de
cámara, para que la comparación sea justa: solo cambia la forma de pintar. Python puro (sin numpy)
para que también lo pueda importar el Python que trae Blender.

Ejes: x cruza la calle (positivo a la derecha de la cámara), y va calle adentro, z hacia arriba;
metros. La vía va por el centro (x = 0) y el tranvía avanza hacia la cámara (y decreciente).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

SEG, FPS = 8.0, 30
CUADROS = int(SEG * FPS)

BORDILLO = 3.2            # mitad de la calzada empedrada
FACHADA = 6.0             # distancia de la vía a las fachadas
ACERA_ALTO = 0.12
PISO_BAJO = 3.8
PISO = 3.1
Y_MIN, Y_MAX = -20.0, 235.0
ANCHO_VIA = 1.435         # ancho de vía estándar, como el de Friburgo

# Revoques de las casas del casco viejo (crema, amarillo, verde pálido, rosa, gris, ocre)
COLORES_FACHADA = [
    (0.84, 0.80, 0.70), (0.88, 0.80, 0.55), (0.66, 0.74, 0.64), (0.85, 0.70, 0.66),
    (0.78, 0.78, 0.76), (0.80, 0.64, 0.44), (0.92, 0.89, 0.82), (0.74, 0.66, 0.58),
]
COLORES_TOLDO = [(0.62, 0.10, 0.10), (0.15, 0.28, 0.22), (0.12, 0.18, 0.35), (0.55, 0.42, 0.18)]
COLORES_POSTIGO = [(0.16, 0.30, 0.22), (0.30, 0.20, 0.14), (0.55, 0.55, 0.52)]


@dataclass
class Edificio:
    lado: int             # -1 izquierda, +1 derecha
    y0: float
    ancho: float
    alto: float           # hasta el alero
    fondo: float
    color: tuple
    pisos: int
    columnas: int
    retranqueo: float     # cuánto se mete la fachada respecto de la línea de la calle
    toldo: tuple | None   # color del toldo de la tienda, si tiene
    postigos: tuple | None
    tejado: float         # altura de la cumbrera sobre el alero
    luces: list           # por ventana: True si está encendida (hora azul)

    @property
    def x(self) -> float:
        """x de la fachada (la cara que da a la calle)."""
        return self.lado * (FACHADA + self.retranqueo)

    def ventanas(self):
        """(y centro, z inferior, ancho, alto, encendida) de cada ventana de los pisos altos."""
        paso = self.ancho / self.columnas
        k = 0
        for p in range(self.pisos):
            z = PISO_BAJO + p * PISO + 0.85
            for c in range(self.columnas):
                yield self.y0 + (c + 0.5) * paso, z, 1.05, 1.55, self.luces[k]
                k += 1


def edificios(semilla: int = 11, fraccion_luces: float = 0.3) -> list[Edificio]:
    rng = random.Random(semilla)
    out = []
    for lado in (-1, 1):
        y = Y_MIN + rng.uniform(0, 4)
        while y < Y_MAX:
            ancho = rng.uniform(7.0, 12.5)
            pisos = rng.choice([3, 3, 4, 4, 4, 5])
            columnas = max(2, int(ancho / 2.5))
            out.append(Edificio(
                lado=lado, y0=y, ancho=ancho,
                alto=PISO_BAJO + pisos * PISO + rng.uniform(0.3, 0.9),
                fondo=12.0, color=rng.choice(COLORES_FACHADA), pisos=pisos, columnas=columnas,
                retranqueo=rng.choice([0.0, 0.0, 0.0, 0.18, -0.12]),
                toldo=rng.choice(COLORES_TOLDO) if rng.random() < 0.45 else None,
                postigos=rng.choice(COLORES_POSTIGO) if rng.random() < 0.35 else None,
                tejado=rng.uniform(3.2, 5.0),
                luces=[rng.random() < fraccion_luces for _ in range(pisos * columnas)],
            ))
            y += ancho
    return out


def faroles() -> list[tuple[int, float]]:
    """Faroles de pared, alternando lados: (lado, y)."""
    return [((-1) ** i, 5.0 + i * 15.5) for i in range(15)]


# Tranvía: tres módulos con fuelles entre ellos (los Urbos de Friburgo tienen más, pero de frente
# no se distinguen). Medidas en metros.
TRAMOS = [10.0, 8.5, 10.0]
HUECO = 0.45
ANCHO_T, ALTO_T, BASE_T = 2.30, 3.05, 0.30

Y_INICIO, Y_FIN = 58.0, 12.5
CAMARA = (3.9, 0.0, 1.6)        # en la acera derecha, a la altura de los ojos
LENTE = 30.0                   # mm, sensor de 36 mm


def frente(t: float) -> float:
    """y del frente del tranvía en el segundo t: entra a unos 49 km/h y frena hasta parar."""
    u = min(1.0, t / (SEG * 0.92))
    return Y_FIN + (Y_INICIO - Y_FIN) * (1 - u) ** 2.2


def mira(t: float) -> tuple[float, float, float]:
    """Punto al que apunta la cámara: sigue al tranvía como un camarógrafo que lo acompaña."""
    return (0.0, frente(t) + 3.0, 2.0)


def tramos_y() -> list[tuple[float, float]]:
    """(inicio, largo) de cada tramo, medido desde el frente hacia atrás."""
    out, y = [], 0.0
    for largo in TRAMOS:
        out.append((y, largo))
        y += largo + HUECO
    return out


def camara_base(t: float):
    """Posición, eje adelante, derecha y arriba de la cámara en el segundo t."""
    c = CAMARA
    m = mira(t)
    f = [m[i] - c[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in f))
    f = [v / n for v in f]
    r = [f[1], -f[0], 0.0]                       # adelante × arriba(z)
    n = math.sqrt(r[0] ** 2 + r[1] ** 2)
    r = [v / n for v in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    return c, f, r, u
