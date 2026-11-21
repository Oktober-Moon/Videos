"""Piezas comunes de las escenas: tiempos que manda el audio, la clase base de una subescena,
fotos con movimiento de cámara lento, textos en pantalla y la tarjeta de título.

Tiempos
-------
La duración de cada subescena es la de su audio (`audios/N.N.wav` o `.mp3`) más medio segundo
de respiro. Sin audio, se estima con el guion a `PALABRAS_POR_MINUTO`, con 1.6 s por cada
"(pausa)". Dentro de la subescena, cada imagen se ancla al inicio de una oración: con audio, se
busca el silencio entre oraciones más cercano a donde caería por número de palabras; sin audio,
se reparte por palabras. Así, al grabar o volver a grabar la voz, todo se reacomoda solo.
"""

from __future__ import annotations

import functools
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import guion
from graficos import FPS, H, W, caja_dentro, color, fuente, lim, suave, texto_alfa

RAIZ = Path(__file__).resolve().parent.parent
AUDIOS = RAIZ / "audios"
IMAGENES = RAIZ / "imagenes"
SR = 48_000
RESPIRO = 0.5
PALABRAS_POR_MINUTO = 165
SEG_PAUSA = 1.6
TITULO_SEG = 3.0


# --------------------------------------------------------------------------- audio de la voz


def ruta_audio(id_: str) -> Path | None:
    for ext in (".wav", ".mp3", ".m4a"):
        r = AUDIOS / f"{id_}{ext}"
        if r.exists():
            return r
    return None


def leer_audio(ruta: Path) -> np.ndarray:
    """Cualquier audio -> float32 estéreo a 48 kHz (vía ffmpeg)."""
    datos = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ruta), "-ac", "2", "-ar", str(SR),
                            "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(datos, np.float32).reshape(-1, 2).copy()


def duracion_ffprobe(ruta: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                        "default=nw=1:nk=1", str(ruta)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


@dataclass
class Tiempos:
    duracion: float              # segundos del clip (múltiplo exacto de un cuadro)
    oraciones: list[float]       # inicio de cada oración
    fin_voz: float               # dónde termina de hablar
    pausas: list[tuple[float, float]]  # tramos de "(pausa)": (inicio, fin)
    con_audio: bool

    @property
    def cuadros(self) -> int:
        return int(round(self.duracion * FPS))


def _a_cuadros(seg: float) -> float:
    return math.ceil(seg * FPS - 1e-6) / FPS


def _silencios(voz: np.ndarray, minimo: float = 0.22) -> list[tuple[float, float]]:
    nivel = ndimage.uniform_filter1d(np.abs(voz).mean(axis=1), int(SR * 0.03))
    pico = np.percentile(nivel, 99) + 1e-9
    callado = nivel < pico * 0.06
    tramos, i, n = [], 0, len(callado)
    while i < n:
        if callado[i]:
            j = i
            while j < n and callado[j]:
                j += 1
            if (j - i) / SR >= minimo:
                tramos.append((i / SR, j / SR))
            i = j
        else:
            i += 1
    return tramos


@functools.lru_cache(maxsize=None)
def tiempos(id_: str) -> Tiempos:
    sub = guion.subescena(id_)
    palabras = sub.palabras
    total = sum(palabras) or 1
    ruta = ruta_audio(id_)
    if ruta is None:
        hablar = total / PALABRAS_POR_MINUTO * 60
        dur = _a_cuadros(hablar + SEG_PAUSA * len(sub.pausas) + RESPIRO)

        def antes(k):  # segundos de pausa que ya pasaron antes de la oración k
            return SEG_PAUSA * sum(1 for q in sub.pausas if q < k)

        inicios = [sum(palabras[:k]) / total * hablar + antes(k) for k in range(len(palabras))]
        pausas = [(sum(palabras[: q + 1]) / total * hablar + antes(q),
                   sum(palabras[: q + 1]) / total * hablar + antes(q) + SEG_PAUSA) for q in sub.pausas]
        fin_voz = hablar + SEG_PAUSA * sum(1 for q in sub.pausas if q < len(palabras) - 1)
        return Tiempos(dur, inicios, fin_voz, pausas, False)
    voz = leer_audio(ruta)
    largo = duracion_ffprobe(ruta)
    dur = _a_cuadros(largo + RESPIRO)
    silencios = _silencios(voz)
    habla = [(a, b) for a, b in zip([0.0] + [s[1] for s in silencios], [s[0] for s in silencios] + [largo]) if b - a > 0.05]
    ini_voz = habla[0][0] if habla else 0.0
    fin_voz = habla[-1][1] if habla else largo
    inicios, acum = [], 0
    for p in palabras:
        estimado = ini_voz + acum / total * (fin_voz - ini_voz)
        cerca = [b for a, b in silencios if ini_voz < b < fin_voz and abs(b - estimado) < 1.5]
        inicios.append(min(cerca, key=lambda b: abs(b - estimado)) if (cerca and acum) else estimado)
        acum += p
    inicios = list(np.maximum.accumulate(inicios))
    pausas = []
    for q in sub.pausas:
        fin_q = inicios[q + 1] if q + 1 < len(inicios) else dur
        largos = [(a, b) for a, b in silencios if inicios[q] < a < fin_q]
        if largos:
            a, b = max(largos, key=lambda s: s[1] - s[0])
            pausas.append((a, b))
        else:
            pausas.append((fin_voz, dur))
    return Tiempos(dur, inicios, fin_voz, pausas, True)


# --------------------------------------------------------------------------- subescena base


class Subescena:
    """Una subescena: `preparar()` una vez, `cuadro(t)` por cuadro y `efectos()` para el sonido."""

    fundido_entrada = 0.5
    fundido_salida = 0.6

    def __init__(self, id_: str, t: Tiempos):
        self.id = id_
        self.T = t
        self.d = t.duracion

    def m(self, k: int) -> float:
        """Inicio de la oración k (negativos cuentan desde el final)."""
        return self.T.oraciones[k]

    def preparar(self) -> None:
        pass

    def cuadro(self, t: float) -> np.ndarray:
        raise NotImplementedError

    def efectos(self) -> np.ndarray:
        return np.zeros((int(round(self.d * SR)), 2), np.float32)

    def opacidad(self, t: float) -> float:
        a = lim(t / self.fundido_entrada) if self.fundido_entrada > 0 else 1.0
        b = lim((self.d - t) / self.fundido_salida) if self.fundido_salida > 0 else 1.0
        return suave(a) * suave(b)

    def quieto(self, t: float) -> float:
        """Tiempo de cámara: se congela durante las pausas, para que la imagen se quede quieta."""
        for a, b in self.T.pausas:
            if t > a:
                t = a + max(0.0, t - b) if t > b else a
        return t


# --------------------------------------------------------------------------- fotos


class Foto:
    """Foto real con acercamiento o paneo lento, a pantalla completa.

    `tinte`: color de la paleta del lugar que se mezcla suave sobre la foto (0 = sin tocar).
    `noche`: baja la exposición y enfría (fotos nocturnas). Las fotos de víctimas van con
    tinte 0 y movimiento muy lento: sin filtros ni efectos.
    """

    def __init__(self, archivo: str, tinte=None, fuerza: float = 0.16, noche: float = 0.0,
                 contraste: float = 1.0):
        self.ruta = IMAGENES / archivo
        self.existe = self.ruta.exists()
        if not self.existe:
            return
        im = Image.open(self.ruta).convert("RGB")
        escala = min(1.0, 2.2 * W / im.width, 2.2 * H / im.height)
        if escala < 1.0:
            im = im.resize((int(im.width * escala), int(im.height * escala)), Image.LANCZOS)
        a = np.asarray(im, np.float32) / 255.0
        a = a ** 2.2                                    # lineal: mezclas de luz correctas
        if contraste != 1.0:
            media = a.mean()
            a = np.clip(media + (a - media) * contraste, 0, 1)
        if noche > 0:
            a = a * (1 - 0.55 * noche) * np.array([0.82, 0.92, 1.12], np.float32) ** noche
        if tinte is not None and fuerza > 0:
            lum = (a * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
            a = a * (1 - fuerza) + lum * color(tinte) ** 2.2 * 1.6 * fuerza
        self.im = Image.fromarray((np.clip(a, 0, 1) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8))
        self.w, self.h = self.im.size

    def ver(self, zoom: float = 1.0, cx: float = 0.5, cy: float = 0.5) -> np.ndarray:
        """Encuadre de 1920×1080 que cubre la pantalla, con zoom y centro relativos (0..1)."""
        cubre = max(W / self.w, H / self.h) * zoom
        bw, bh = W / cubre, H / cubre
        # max(0, …) al final: con zoom 1, self.w - bw puede dar -1e-13 por redondeo y PIL rechaza la caja.
        x0 = max(0.0, min(max(cx * self.w - bw / 2, 0), self.w - bw))
        y0 = max(0.0, min(max(cy * self.h - bh / 2, 0), self.h - bh))
        im = self.im.resize((W, H), Image.BICUBIC, box=caja_dentro((x0, y0, x0 + bw, y0 + bh), self.w, self.h))
        return np.asarray(im, np.float32) / 255.0


def recorrido(t: float, d: float, z0: float, z1: float, c0=(0.5, 0.5), c1=(0.5, 0.5)):
    """Zoom y centro de un movimiento de cámara lento y continuo (sin frenar en medio)."""
    u = lim(t / max(d, 1e-6))
    u = 0.5 - 0.5 * math.cos(math.pi * u) if u < 1 else 1.0
    return (z0 + (z1 - z0) * u, c0[0] + (c1[0] - c0[0]) * u, c0[1] + (c1[1] - c0[1]) * u)


# --------------------------------------------------------------------------- tramos de imagen


def fundir(a: np.ndarray, b: np.ndarray, x: float) -> np.ndarray:
    if x <= 0:
        return a
    if x >= 1:
        return b
    return a * (1 - x) + b * x


class Segmentos:
    """Tramos de imagen que se encadenan con fundidos de `cruce` segundos en cada frontera."""

    def __init__(self, cortes: list[float], cruce: float = 0.9):
        self.cortes, self.cruce = cortes, cruce

    def pesos(self, t: float) -> list[tuple[int, float]]:
        k = sum(1 for c in self.cortes if t >= c - self.cruce / 2)
        if k > 0:
            c = self.cortes[k - 1]
            x = lim((t - (c - self.cruce / 2)) / self.cruce)
            if x < 1:
                return [(k - 1, 1 - x), (k, x)]
        return [(k, 1.0)]


# --------------------------------------------------------------------------- texto


def texto(img: np.ndarray, cadena: str, x: float, y: float, tam: int, col, *, nombre="Inter-SemiBold.ttf",
          alinear: str = "izq", opacidad: float = 1.0, interletra: float = 0.0, sombra: float = 0.55) -> tuple[int, int]:
    """Escribe una línea de texto con sombra suave. (x, y) es la línea base a la izquierda,
    al centro o a la derecha según `alinear`. Devuelve el ancho y alto del texto."""
    if opacidad <= 0.002 or not cadena:
        return 0, 0
    a, borroso, asc = _alfa_texto(cadena, nombre, tam, interletra)
    h, w = a.shape
    margen = int(tam * 0.4)
    x0 = {"izq": x, "centro": x - w / 2, "der": x - w}[alinear]
    x0, y0 = int(round(x0)), int(round(y - asc - margen))
    if sombra > 0:
        _componer(img, borroso * (sombra * opacidad), np.zeros(3), x0 + 2, y0 + 3)
    _componer(img, a * opacidad, color(col), x0, y0)
    return w - 2 * margen, h


@functools.lru_cache(maxsize=512)
def _alfa_texto(cadena: str, nombre: str, tam: int, interletra: float):
    """Máscara del texto y su sombra difusa, guardadas: el mismo rótulo se dibuja en cientos de cuadros."""
    a = texto_alfa(cadena, nombre, tam, interletra)
    a.setflags(write=False)
    borroso = ndimage.gaussian_filter(a, tam * 0.08)
    borroso.setflags(write=False)
    return a, borroso, fuente(nombre, tam).getmetrics()[0]


def _componer(img: np.ndarray, alfa: np.ndarray, col, x0: int, y0: int) -> None:
    h, w = alfa.shape
    a0, b0 = max(0, y0), max(0, x0)
    a1, b1 = min(H, y0 + h), min(W, x0 + w)
    if a0 >= a1 or b0 >= b1:
        return
    k = alfa[a0 - y0 : a1 - y0, b0 - x0 : b1 - x0, None]
    img[a0:a1, b0:b1] = img[a0:a1, b0:b1] * (1 - k) + np.asarray(col, np.float32) * k


def aparece(t: float, inicio: float, dur: float = 0.6, fin: float | None = None, salida: float = 0.6) -> float:
    """Opacidad de un elemento que entra en `inicio` y (opcional) sale en `fin`."""
    a = suave(lim((t - inicio) / dur))
    if fin is not None:
        a *= 1 - suave(lim((t - fin) / salida))
    return a


# --------------------------------------------------------------------------- tarjeta de título


class TarjetaTitulo(Subescena):
    """Tres segundos sobre negro: «Escena N» pequeño, el nombre de la escena y una línea de color
    que crece debajo; un golpe grave al aparecer."""

    fundido_entrada = 0.6
    fundido_salida = 0.6
    debajo_db = 6.0          # sin voz encima: el golpe grave se oye más que los efectos de fondo

    def __init__(self, numero: int, titulo: str, acento, claro):
        super().__init__("titulo", Tiempos(TITULO_SEG, [0.0], 0.0, [], False))
        self.numero, self.titulo, self.acento, self.claro = numero, titulo, acento, claro

    def preparar(self) -> None:
        import atmosfera as A
        self.polvo = A.Polvo(70, 300 + self.numero, vel=(4.0, -2.0), tam=(0.6, 1.8))

    def cuadro(self, t: float) -> np.ndarray:
        img = np.zeros((H, W, 3), np.float32)
        self.polvo.dibujar(img, t, self.claro, 0.18)
        sube = suave(lim(t / 1.2))
        texto(img, f"ESCENA {self.numero}", W / 2, H / 2 - 70 - 10 * (1 - sube), 30, self.acento,
              nombre="Inter-SemiBold.ttf", alinear="centro", opacidad=sube, interletra=0.35)
        ancho, _ = texto(img, self.titulo, W / 2, H / 2 + 30 + 8 * (1 - sube), 92, self.claro,
                         nombre="Inter-SemiBold.ttf", alinear="centro", opacidad=suave(lim((t - 0.15) / 1.0)),
                         interletra=-0.01)
        largo = ancho * 0.5 * suave(lim((t - 0.3) / 1.4))
        img[H // 2 + 72 : H // 2 + 75, int(W / 2 - largo / 2) : int(W / 2 + largo / 2)] = color(self.acento)
        return img

    def efectos(self) -> np.ndarray:
        import sfx
        n = int(round(self.d * SR))
        salida = np.zeros((n, 2), np.float32)
        g = sfx.golpe_sordo(10 + self.numero)[: n - int(0.12 * SR)]
        salida[int(0.12 * SR) : int(0.12 * SR) + len(g)] += g
        return salida
