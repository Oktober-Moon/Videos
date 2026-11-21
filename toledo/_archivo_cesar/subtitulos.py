"""Subtítulos: reparto del texto narrado en bloques, archivo .srt y rótulo quemado en el cuadro.

Reglas de forma (como el video de referencia): versalitas pequeñas, abajo al centro, blanco
hueso con sombra suave y como máximo dos líneas por bloque.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

from escenas.base import TiemposEscena, TiempoPlano

ANCHO, ALTO = 1920, 1080
FUENTE = Path(__file__).resolve().parent / "fuentes" / "EBGaramond-Versalitas.ttf"
TAMANO = 40
INTERLINEA = 1.18
ANCHO_MAXIMO = 1380          # px por línea
MARGEN_INFERIOR = 64         # px del borde inferior a la base de la última línea
COLOR = (237, 230, 214)      # blanco hueso
ADELANTO = 0.35              # s desde el inicio del plano hasta la primera palabra
COLA = 0.45                  # s que el bloque sigue en pantalla tras su última palabra
FUNDIDO = 0.12               # s de aparición y desaparición


@dataclass
class Bloque:
    inicio: float            # segundos absolutos en la escena
    fin: float
    lineas: list[str]

    @property
    def texto(self) -> str:
        return "\n".join(self.lineas)


def _fuente() -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FUENTE), TAMANO)


def _ancho(texto: str, fuente: ImageFont.FreeTypeFont) -> float:
    return fuente.getlength(texto)


def _frases(texto: str) -> list[str]:
    """Corta en frases conservando la puntuación final."""
    partes = re.split(r"(?<=[.!?…:])\s+", texto.strip())
    return [p.strip() for p in partes if p.strip()]


# Palabras tras las que no se corta una línea (quedarían colgando del sentido de la siguiente).
_NO_CORTAR_TRAS = {
    "a", "al", "con", "de", "del", "el", "en", "la", "las", "lo", "los", "para", "por", "que",
    "se", "si", "su", "sus", "un", "una", "y", "o", "no", "muy", "más", "hoy",
}


def _costo_corte(palabras: list[str], i: int, wa: float, wb: float) -> float:
    """Costo de cortar la línea antes de palabras[i]: equilibrio y respeto por la sintaxis."""
    previa = palabras[i - 1]
    costo = abs(wa - wb)
    if previa[-1] in ".!?…":
        costo *= 0.15
    elif previa[-1] in ",;:":
        costo *= 0.45
    if previa.lower().strip(",.;:") in _NO_CORTAR_TRAS:
        costo += 900
    return costo


def _partir_lineas(palabras: list[str], fuente) -> list[str]:
    """Reparte palabras en una o dos líneas de ancho máximo, cortando donde mejor se lee."""
    texto = " ".join(palabras)
    sola = _ancho(texto, fuente) <= ANCHO_MAXIMO
    mejor, mejor_costo = None, float("inf")
    for i in range(1, len(palabras)):
        a, b = " ".join(palabras[:i]), " ".join(palabras[i:])
        wa, wb = _ancho(a, fuente), _ancho(b, fuente)
        if wa > ANCHO_MAXIMO or wb > ANCHO_MAXIMO:
            continue
        costo = _costo_corte(palabras, i, wa, wb)
        if costo < mejor_costo:
            mejor, mejor_costo = [a, b], costo
    if sola:
        # Una línea basta; solo se parte si contiene dos frases y el corte cae entre ellas.
        if mejor and " ".join(mejor[0].split()[-1:])[-1:] in ".!?" and len(texto) > 45:
            return mejor
        return [texto]
    return mejor or [texto]


def _cabe(palabras: list[str], fuente) -> bool:
    lineas = _partir_lineas(palabras, fuente)
    return len(lineas) <= 2 and all(_ancho(l, fuente) <= ANCHO_MAXIMO for l in lineas)


def _bloques_de_texto(texto: str, fuente) -> list[list[str]]:
    """Agrupa frases en bloques de hasta dos líneas; parte frases largas en comas o a la mitad."""
    unidades: list[list[str]] = []
    for frase in _frases(texto):
        palabras = frase.split()
        if _cabe(palabras, fuente):
            unidades.append(palabras)
            continue
        # Partir en comas o dos puntos; si no alcanza, partir por palabras.
        trozos, actual = [], []
        for p in palabras:
            actual.append(p)
            if p[-1] in ",;:" and len(actual) >= 3:
                trozos.append(actual)
                actual = []
        if actual:
            trozos.append(actual)
        for trozo in trozos:
            while not _cabe(trozo, fuente):
                corte = len(trozo) // 2
                for k in range(len(trozo) - 1, 0, -1):
                    if _cabe(trozo[:k], fuente):
                        corte = k
                        break
                unidades.append(trozo[:corte])
                trozo = trozo[corte:]
            unidades.append(trozo)
    # Unir frases cortas consecutivas ("Pasa un día. Pasan dos.") o un arranque breve que
    # termina en dos puntos con lo que sigue; nunca mezclar el final de una frase larga con
    # el inicio de otra.
    bloques: list[list[str]] = []
    for u in unidades:
        if bloques:
            previo = bloques[-1]
            cortas = len(previo) <= 8 and len(u) <= 8
            arranque = len(previo) <= 5 and previo[-1][-1] == ":"
            if (cortas or arranque) and _cabe(previo + u, fuente) and len(previo) + len(u) <= 20:
                bloques[-1] = previo + u
                continue
        bloques.append(list(u))
    return bloques


def bloques_de_plano(plano: TiempoPlano, ppm: float, fuente=None) -> list[Bloque]:
    fuente = fuente or _fuente()
    base = plano.inicio
    if plano.subtitulos:
        salida = []
        for s in plano.subtitulos:
            palabras = s["texto"].split()
            salida.append(
                Bloque(base + float(s["desde"]), base + float(s["hasta"]), _partir_lineas(palabras, fuente))
            )
        return salida
    if not plano.texto:
        return []
    grupos = _bloques_de_texto(plano.texto, fuente)
    duraciones = [len(g) * 60.0 / ppm for g in grupos]
    disponible = plano.duracion - ADELANTO - plano.pausa_final - 0.15
    escala = min(1.0, disponible / sum(duraciones))
    t = base + ADELANTO
    salida = []
    for g, d in zip(grupos, duraciones):
        d *= escala
        salida.append(Bloque(t, t + d, _partir_lineas(g, fuente)))
        t += d
    # Cola: cada bloque se queda un poco más si no choca con el siguiente ni con la pausa final.
    limite_plano = plano.inicio + plano.duracion - plano.pausa_final - 0.05
    for i, b in enumerate(salida):
        siguiente = salida[i + 1].inicio if i + 1 < len(salida) else limite_plano
        b.fin = min(b.fin + COLA, siguiente, limite_plano)
    return salida


def bloques_de_escena(tiempos: TiemposEscena) -> list[Bloque]:
    fuente = _fuente()
    salida: list[Bloque] = []
    for p in tiempos.planos:
        salida.extend(bloques_de_plano(p, tiempos.palabras_por_minuto, fuente))
    return salida


def _marca_srt(s: float) -> str:
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    seg, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{seg:02d},{ms:03d}"


def escribir_srt(bloques: list[Bloque], ruta: Path) -> None:
    lineas = []
    for i, b in enumerate(bloques, 1):
        lineas += [str(i), f"{_marca_srt(b.inicio)} --> {_marca_srt(b.fin)}", *b.lineas, ""]
    ruta = Path(ruta)
    temporal = ruta.with_suffix(".tmp.srt")
    temporal.write_text("\n".join(lineas), encoding="utf-8")
    temporal.replace(ruta)


class Rotulador:
    """Dibuja los bloques sobre el cuadro ya terminado (después de fundidos y grano)."""

    def __init__(self, bloques: list[Bloque]):
        self.bloques = bloques
        self.fuente = _fuente()
        self._cache: dict[int, tuple[np.ndarray, np.ndarray, int, int]] = {}

    def _imagen(self, i: int):
        if i in self._cache:
            return self._cache[i]
        b = self.bloques[i]
        asc, desc = self.fuente.getmetrics()
        paso = int(TAMANO * INTERLINEA)
        anchos = [int(np.ceil(_ancho(l, self.fuente))) for l in b.lineas]
        margen = 24
        w = max(anchos) + 2 * margen
        h = paso * (len(b.lineas) - 1) + asc + desc + 2 * margen
        mascara = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(mascara)
        for k, (linea, aw) in enumerate(zip(b.lineas, anchos)):
            d.text(((w - aw) / 2, margen + k * paso), linea, font=self.fuente, fill=255)
        alfa = np.asarray(mascara, np.float32) / 255.0
        sombra = ndimage.gaussian_filter(alfa, 3.0)
        sombra = np.roll(sombra, 2, axis=0)
        sombra = np.clip(sombra * 1.6, 0, 1) * 0.78
        # posición: base de la última línea a MARGEN_INFERIOR del borde
        y = ALTO - MARGEN_INFERIOR - (margen + (len(b.lineas) - 1) * paso + asc)
        x = (ANCHO - w) // 2
        self._cache[i] = (alfa, sombra, x, int(y))
        return self._cache[i]

    def aplicar(self, cuadro: np.ndarray, t: float) -> np.ndarray:
        """`cuadro` float32 0..1; `t` en segundos absolutos de la escena."""
        color = np.array(COLOR, np.float32) / 255.0
        for i, b in enumerate(self.bloques):
            if not (b.inicio <= t <= b.fin):
                continue
            # aparece y se va dentro de su intervalo: dos bloques seguidos nunca se enciman
            op = max(0.0, min(1.0, (t - b.inicio) / FUNDIDO, (b.fin - t) / FUNDIDO))
            if op <= 0:
                continue
            alfa, sombra, x, y = self._imagen(i)
            h, w = alfa.shape
            zona = cuadro[y : y + h, x : x + w]
            zona *= (1 - sombra * op)[..., None]
            zona *= (1 - alfa * op)[..., None]
            zona += (alfa * op)[..., None] * color
        return cuadro
