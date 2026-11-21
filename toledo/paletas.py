"""Paletas de color de cada lugar del video (tomadas de visuales.md).

Se usan en ilustraciones, diagramas, títulos y en el tinte ligero sobre las fotos. Cada paleta
es un diccionario nombre -> color hex; `rgb(paleta)` la convierte a arreglos float (0..1).
"""

from __future__ import annotations

import numpy as np

from graficos import color

FRIBURGO = {            # escenas 1, 2.0 y 4
    "verde": "#2F4A3A",      # Selva Negra
    "rojo": "#C8102E",       # escudo de Friburgo
    "blanco": "#F4F1EA",     # escudo de Friburgo
    "piedra": "#8C8C88",
    "rio": "#3E6E8E",        # el Dreisam
}
SAN_BERNARDINO = {      # 3.0 a 3.9
    "azul_fbi": "#0B2D5B",
    "dorado": "#FDB515",     # California
    "arena": "#D9C6A5",
}
APPLE = {               # 2.3 a 2.8 y 3.8 a 3.14
    "gris": "#2E2E30",
    "blanco": "#F5F5F7",
    "azul": "#0071E3",
}
ANDROID = {             # 2.9 y 2.10
    "verde": "#3DDC84",
    "gris": "#202124",
    "blanco": "#FFFFFF",
}
CONNECTICUT = {         # escenas 5 y 6 (caso Dabate)
    "azul": "#1F3A93",
    "beige": "#D8CBB3",
    "rojo_patrulla": "#D7263D",
    "azul_patrulla": "#1B4AD6",
}
LABORATORIO = {         # 7.0 a 7.5
    "placa": "#1E5B32",
    "cobre": "#B87333",
    "negro": "#111111",
    "terminal": "#33FF66",
}
ARKANSAS = {            # 7.5 a 7.8 (caso Bates)
    "rojo": "#C8102E",
    "azul": "#00205B",
    "blanco": "#FFFFFF",
}

PALETAS = {
    "friburgo": FRIBURGO, "san_bernardino": SAN_BERNARDINO, "apple": APPLE, "android": ANDROID,
    "connecticut": CONNECTICUT, "laboratorio": LABORATORIO, "arkansas": ARKANSAS,
}


def rgb(paleta: dict) -> dict[str, np.ndarray]:
    return {k: color(v) for k, v in paleta.items()}


def mezcla(a, b, x: float) -> np.ndarray:
    return (np.asarray(a, np.float32) * (1 - x) + np.asarray(b, np.float32) * x).astype(np.float32)


def cierre(x: float) -> dict[str, np.ndarray]:
    """Escena 8: de la paleta de Friburgo a la de Connecticut (x de 0 a 1), terminando en negro."""
    f, c = rgb(FRIBURGO), rgb(CONNECTICUT)
    oscuro = max(0.0, (x - 0.7) / 0.3)
    return {
        "fondo": mezcla(mezcla(f["verde"], c["azul"], x), np.zeros(3), oscuro),
        "claro": mezcla(mezcla(f["blanco"], c["beige"], x), np.zeros(3), oscuro),
        "acento": mezcla(mezcla(f["rio"], c["azul_patrulla"], x), np.zeros(3), oscuro),
    }
