"""Paletas de color por época y lugar.

Regla del video: cada mundo (época + lugar) se reconoce por sus colores, y la paleta cambia
cuando cambia el lugar. Los valores son aproximados al origen histórico de cada color; se
ajustaron solo cuando hacía falta contraste.

Uso:
    from paletas import ROMA, GALIA, rgb, mezcla
    ROMA["purpura"]           -> "#66023C"
    rgb(ROMA["purpura"])      -> (0.4, 0.0078, 0.235)   en flotante 0..1
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Color:
    hex: str
    origen: str


def _paleta(**colores: tuple[str, str]) -> dict[str, str]:
    """Construye la paleta y guarda el origen de cada color en ORIGENES."""
    salida = {}
    for nombre, (valor, origen) in colores.items():
        salida[nombre] = valor
        ORIGENES[valor] = origen
    return salida


ORIGENES: dict[str, str] = {}

# Escenas 1-3 · Roma (lado romano): la carta, César, el campamento por dentro.
ROMA = _paleta(
    purpura=("#66023C", "púrpura de Tiro, color imperial"),
    rojo_legion=("#8E1B1B", "rojo de las túnicas y estandartes de las legiones"),
    oro_aguila=("#C9A227", "oro del águila legionaria"),
    terracota=("#B5562F", "barro cocido de tejas y lámparas"),
    marmol=("#E9E4D8", "mármol y pergamino claro"),
    tinta=("#15110E", "tinta de hollín"),
)

# Escena 1 · Galia belga, los nervios, de noche: exterior, noche y guerreros.
GALIA = _paleta(
    glasto=("#2E4A7A", "azul glasto, tinte con que se pintaban los celtas"),
    bosque=("#23402B", "verde de los bosques de las Ardenas"),
    niebla=("#6E7B78", "gris de la niebla del norte"),
    antorcha=("#E08A2E", "ámbar de antorcha"),
    noche=("#0B0F14", "negro de la noche sin luna"),
)

# Escena 4 · Bagdad abasí, siglo IX.
BAGDAD = _paleta(
    negro_abasi=("#111111", "negro, color de la dinastía abasí"),
    lapislazuli=("#26619C", "lapislázuli"),
    turquesa=("#30A6A0", "turquesa de azulejos"),
    oro=("#D4AF37", "oro de manuscritos iluminados"),
    arena=("#E3D2A6", "arena del desierto"),
)

# Escena 5 · Inglaterra y Escocia, 1586.
TUDOR = _paleta(
    verde_tudor=("#1F5E3B", "verde de la librea Tudor"),
    blanco_tudor=("#F2EFE6", "blanco de la librea Tudor"),
    carmesi=("#7A0F1A", "carmesí de terciopelo"),
    azul_sotuer=("#005EB8", "azul del sotuer escocés"),
    pergamino=("#D9C7A0", "pergamino de las cartas cifradas"),
    roble=("#4A3220", "roble de los paneles"),
)

# Escena 6 · Londres victoriano.
VICTORIANO = _paleta(
    periodico=("#CDBF9C", "papel de periódico envejecido"),
    tinta_imprenta=("#1C1A17", "tinta de imprenta"),
    niebla=("#8A8D8F", "niebla de Londres"),
    verde_victoriano=("#2F4F3A", "verde victoriano"),
    burdeos=("#5E1A24", "burdeos de tapicería"),
    farol=("#F2C14E", "luz de farol de gas"),
)

# Escena 7a · Rusia, 1915.
RUSIA = _paleta(
    negro=("#000000", "negro de la bandera imperial"),
    amarillo=("#FFD200", "amarillo de la bandera imperial"),
    blanco=("#FFFFFF", "blanco de la bandera imperial"),
    caqui=("#6B6A45", "caqui de campaña"),
    nieve=("#DDE3E8", "nieve"),
)

# Escena 7b · Sicilia, 2006.
SICILIA = _paleta(
    rojo=("#C8102E", "rojo de la Trinacria"),
    amarillo=("#FCD116", "amarillo de la Trinacria"),
    caliza=("#D8CBB0", "piedra caliza"),
    olivo=("#5B6B2F", "verde olivo"),
    ocre=("#C08A3E", "ocre seco"),
)

# Escena 8 · Hoy, mundo digital.
DIGITAL = _paleta(
    terminal=("#33FF66", "verde de terminal"),
    fondo=("#0A0A0A", "fondo de terminal"),
    azul_windows=("#0078D4", "azul Windows"),
    rojo_hal=("#FF2A1A", "rojo del ojo de HAL"),
    interfaz=("#F5F7FA", "blanco de interfaz"),
)

PALETAS: dict[str, dict[str, str]] = {
    "roma": ROMA,
    "galia": GALIA,
    "bagdad": BAGDAD,
    "tudor": TUDOR,
    "victoriano": VICTORIANO,
    "rusia": RUSIA,
    "sicilia": SICILIA,
    "digital": DIGITAL,
}

# Qué paletas usa cada escena del video completo.
PALETAS_POR_ESCENA: dict[str, tuple[str, ...]] = {
    "1": ("roma", "galia"),
    "2": ("roma",),
    "3": ("roma",),
    "4": ("bagdad",),
    "5": ("tudor",),
    "6": ("victoriano",),
    "7a": ("rusia",),
    "7b": ("sicilia",),
    "8": ("digital",),
}


def rgb(valor: str) -> np.ndarray:
    """'#RRGGBB' -> arreglo float32 (r, g, b) en 0..1."""
    valor = valor.lstrip("#")
    return np.array([int(valor[i : i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=np.float32)


def rgb255(valor: str) -> tuple[int, int, int]:
    valor = valor.lstrip("#")
    return tuple(int(valor[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def mezcla(a: str | np.ndarray, b: str | np.ndarray, t: float) -> np.ndarray:
    """Interpola linealmente entre dos colores (hex o rgb flotante)."""
    ca = rgb(a) if isinstance(a, str) else a
    cb = rgb(b) if isinstance(b, str) else b
    return (ca * (1.0 - t) + cb * t).astype(np.float32)


def aclarar(c: str | np.ndarray, t: float) -> np.ndarray:
    return mezcla(c, np.ones(3, np.float32), t)


def oscurecer(c: str | np.ndarray, t: float) -> np.ndarray:
    return mezcla(c, np.zeros(3, np.float32), t)
