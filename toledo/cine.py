"""Realismo de cine: profundidad, parallax 2.5D, desenfoque de profundidad y acabado de película.

- `profundidad(foto)`: mapa de cercanía (1 = cerca, 0 = lejos) con Depth Anything V2 Small en ONNX
  (licencia Apache 2.0); el modelo se descarga solo la primera vez a ~/.cache.
- `Parallax`: separa la foto en capas por profundidad (y a la persona, recortada con rembg), rellena
  lo que queda detrás de cada capa y mueve cada una a su velocidad: las cercanas se desplazan más
  que las lejanas, como una cámara real que se mueve frente a la escena.
- `acabado_cine`: corrección de color hacia la paleta de la escena (sombras y luces), curva de
  contraste, halo en las luces, viñeta y grano de película fino.

Mapas y máscaras se guardan en `salida/cache/` para que los procesos en paralelo no los repitan.
"""

from __future__ import annotations

import functools
import hashlib
import math
import urllib.request
from pathlib import Path

import cv2
import numpy as np

from graficos import FPS, H, W, color

RAIZ = Path(__file__).resolve().parent
CACHE = RAIZ / "salida" / "cache"
MODELO = Path.home() / ".cache" / "depth-anything-v2-small" / "model.onnx"
URL_MODELO = "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx"


# --------------------------------------------------------------------------- caché en disco


def _clave(*partes) -> str:
    return hashlib.sha1("|".join(map(str, partes)).encode()).hexdigest()[:12]


def _en_cache(nombre: str, calcular):
    CACHE.mkdir(parents=True, exist_ok=True)
    ruta = CACHE / f"{nombre}.npy"
    if ruta.exists():
        return np.load(ruta)
    valor = calcular()
    tmp = ruta.with_suffix(".tmp.npy")
    np.save(tmp, valor)
    tmp.replace(ruta)
    return valor


# --------------------------------------------------------------------------- profundidad


@functools.lru_cache(maxsize=1)
def _sesion_profundidad():
    import onnxruntime as ort

    if not MODELO.exists():
        MODELO.parent.mkdir(parents=True, exist_ok=True)
        tmp = MODELO.with_suffix(".tmp")
        urllib.request.urlretrieve(URL_MODELO, tmp)
        tmp.replace(MODELO)
    return ort.InferenceSession(str(MODELO), providers=["CPUExecutionProvider"])


def profundidad(foto: np.ndarray, nombre: str = "") -> np.ndarray:
    """Cercanía por píxel (float32, 0 lejos .. 1 cerca) del tamaño de `foto` (RGB 0..1)."""

    def calcular():
        h, w = foto.shape[:2]
        lado = 518
        escala = lado / min(h, w)
        nh, nw = int(round(h * escala / 14)) * 14, int(round(w * escala / 14)) * 14
        x = cv2.resize(foto, (nw, nh), interpolation=cv2.INTER_AREA)
        x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
        x = x.transpose(2, 0, 1)[None].astype(np.float32)
        d = _sesion_profundidad().run(None, {"pixel_values": x})[0][0]
        d = cv2.resize(d, (w, h), interpolation=cv2.INTER_CUBIC)
        lo, hi = np.percentile(d, 1), np.percentile(d, 99)
        d = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1).astype(np.float32)
        return cv2.bilateralFilter(d, 9, 0.1, 9)

    if not nombre:
        return calcular()
    return _en_cache(f"prof_{nombre}_{_clave(foto.shape, float(foto[::50, ::50].sum()))}", calcular)


def mascara_persona(foto: np.ndarray, nombre: str) -> np.ndarray:
    """Silueta de la persona (o del objeto principal) con rembg, suavizada en el borde."""

    def calcular():
        from PIL import Image
        from rembg import new_session, remove

        im = Image.fromarray((np.clip(foto, 0, 1) * 255).astype(np.uint8))
        m = remove(im, session=new_session("u2net_human_seg"), only_mask=True, post_process_mask=True)
        m = np.asarray(m.resize((foto.shape[1], foto.shape[0]), Image.BILINEAR), np.float32) / 255
        return cv2.GaussianBlur(m, (0, 0), 1.0).astype(np.float32)

    return _en_cache(f"persona_{nombre}_{_clave(foto.shape, float(foto[::50, ::50].sum()))}", calcular)


# --------------------------------------------------------------------------- parallax 2.5D


class Parallax:
    """Foto partida en capas de profundidad que se mueven a distinta velocidad.

    Cámara: `ver(zoom, dx, dy, empuje)` — zoom general; (dx, dy) desplazamiento lateral en fracción
    del ancho (las capas cercanas se mueven más); `empuje` acerca más lo cercano que lo lejano
    (sensación de avanzar hacia la escena).
    """

    def __init__(self, foto: np.ndarray, nombre: str, capas: int = 4, persona: bool = False,
                 foco: float | None = None, desenfoque: float = 0.0, ancho: int = 2400):
        if foto.shape[1] > ancho:
            foto = cv2.resize(foto, (ancho, int(foto.shape[0] * ancho / foto.shape[1])), interpolation=cv2.INTER_AREA)
        self.foto = foto.astype(np.float32)
        self.h, self.w = foto.shape[:2]
        d = profundidad(self.foto, nombre)
        cortes = np.quantile(d, np.linspace(0, 1, capas + 1)[1:-1])
        cerca = [np.clip((d - c) / 0.04 + 0.5, 0, 1) for c in cortes]          # alfa: de este corte hacia adelante
        if persona:
            cerca.append(mascara_persona(self.foto, nombre))
        self.capas = []
        niveles = [0.0] + [float(c) for c in cortes] + ([1.0] if persona else [])
        for k in range(len(cerca) + 1):
            alfa = np.ones((self.h, self.w), np.float32) if k == 0 else cerca[k - 1]
            delante = np.zeros((self.h, self.w), np.float32)
            for m in cerca[k:]:
                delante = np.maximum(delante, m)
            img = self._rellenar(self.foto, delante) if k < len(cerca) else self.foto
            nivel = niveles[k] if k < len(niveles) else 1.0
            if desenfoque > 0 and foco is not None:
                s = desenfoque * abs(nivel - foco)
                if s > 0.4:
                    img = cv2.GaussianBlur(img, (0, 0), s)
                    alfa = cv2.GaussianBlur(alfa, (0, 0), s * 0.6)
            self.capas.append((np.dstack([img * alfa[..., None], alfa]).astype(np.float32), nivel))

    @staticmethod
    def _rellenar(foto: np.ndarray, delante: np.ndarray) -> np.ndarray:
        """Lo que estaría detrás de las capas cercanas: se rellena con lo de alrededor."""
        if delante.max() < 0.05:
            return foto
        hueco = cv2.dilate((delante > 0.2).astype(np.uint8) * 255, np.ones((21, 21), np.uint8))
        f = 0.33
        chico = cv2.resize((foto * 255).astype(np.uint8), None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        h_c = cv2.resize(hueco, (chico.shape[1], chico.shape[0]), interpolation=cv2.INTER_NEAREST)
        relleno = cv2.inpaint(chico, h_c, 15, cv2.INPAINT_TELEA)
        relleno = cv2.resize(relleno, (foto.shape[1], foto.shape[0]), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255
        a = cv2.GaussianBlur(hueco.astype(np.float32) / 255, (0, 0), 3)[..., None]
        return foto * (1 - a) + relleno * a

    def ver(self, zoom: float = 1.08, dx: float = 0.0, dy: float = 0.0, empuje: float = 0.0,
            cx: float = 0.5, cy: float = 0.5) -> np.ndarray:
        base = max(W / self.w, H / self.h) * zoom
        salida = np.zeros((H, W, 3), np.float32)
        for capa, nivel in self.capas:
            s = base * (1 + empuje * nivel)
            tx = W / 2 - cx * self.w * s + dx * W * nivel
            ty = H / 2 - cy * self.h * s + dy * H * nivel
            M = np.array([[s, 0, tx], [0, s, ty]], np.float32)
            v = cv2.warpAffine(capa, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            a = v[..., 3:]
            salida = salida * (1 - a) + v[..., :3]
        return salida


# --------------------------------------------------------------------------- acabado de cine


@functools.lru_cache(maxsize=4)
def _vineta(fuerza: float) -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)) / math.sqrt(2)
    v = 1 - fuerza * np.clip(r - 0.25, 0, 1) ** 1.8 * 1.6
    return np.clip(v, 0, 1)[..., None].astype(np.float32)


@functools.lru_cache(maxsize=2)
def _granos(n: int = 12) -> tuple:
    rng = np.random.default_rng(29)
    salida = []
    for _ in range(n):
        g = rng.standard_normal((H, W)).astype(np.float32)
        g = cv2.GaussianBlur(g, (0, 0), 0.65)                                   # grano fino, no ruido de sensor
        g /= g.std() + 1e-6
        salida.append(g)
    return tuple(salida)


def corregir_color(img: np.ndarray, sombras, luces, *, mezcla: float = 0.22, saturacion: float = 0.9,
                   contraste: float = 0.12) -> np.ndarray:
    """Tono partido: las sombras van hacia `sombras` y las luces hacia `luces` (colores de la paleta)."""
    lum = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    gris = lum[..., None]
    img = gris + (img - gris) * saturacion
    s = color(sombras)
    l_ = color(luces)
    peso_s = np.clip(1 - lum / 0.5, 0, 1)[..., None] * mezcla
    peso_l = np.clip((lum - 0.5) / 0.5, 0, 1)[..., None] * mezcla
    img = img * (1 - peso_s) + (gris * 0.6 + s * 0.4) * peso_s
    img = img * (1 - peso_l) + (gris * 0.4 + l_ * 0.6) * peso_l
    if contraste:
        x = np.clip(img, 0, 1)
        curva = x + contraste * (x - 0.5) * (1 - np.abs(2 * x - 1))          # curva en S suave
        img = np.where(img <= 1, curva, img)
    return img


def acabado_cine(img: np.ndarray, cuadro: int, *, sombras, luces, opacidad: float = 1.0, mezcla: float = 0.22,
                 saturacion: float = 0.9, contraste: float = 0.12, halo: float = 0.18, grano: float = 0.028,
                 vineta: float = 0.42) -> np.ndarray:
    img = corregir_color(img, sombras, luces, mezcla=mezcla, saturacion=saturacion, contraste=contraste)
    if halo > 0:                                                               # luces que se abren un poco
        brillo = np.clip(img.max(axis=-1) - 0.72, 0, None)[..., None] * img
        chico = cv2.resize(brillo, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        chico = cv2.GaussianBlur(chico, (0, 0), 6)
        img = img + cv2.resize(chico, (W, H), interpolation=cv2.INTER_LINEAR) * halo * np.array([1.0, 0.85, 0.75], np.float32)
    img = img * _vineta(round(vineta, 3))
    if grano > 0:
        g = _granos()[cuadro % 12]
        lum = img.mean(axis=-1)
        peso = 0.4 + 0.6 * np.clip(1 - np.abs(lum - 0.4) * 1.5, 0, 1)          # más grano en los medios tonos
        img = img + (g * peso * grano)[..., None]
    if opacidad < 1:
        img = img * opacidad
    return img


# --------------------------------------------------------------------------- sombras de los diagramas


def sombra_suave(alfa: np.ndarray, dx: int = 10, dy: int = 14, sigma: float = 14, fuerza: float = 0.55) -> np.ndarray:
    """Sombra difusa de una capa (para que los diagramas floten sobre el fondo)."""
    m = np.roll(np.roll(alfa, dy, axis=0), dx, axis=1)
    chico = cv2.resize(m, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    chico = cv2.GaussianBlur(chico, (0, 0), sigma / 2)
    return cv2.resize(chico, (W, H), interpolation=cv2.INTER_LINEAR) * fuerza


# --------------------------------------------------------------------------- clips de video reales


class Clip:
    """Clip de video leído con ffmpeg a 30 fps, encuadrado a 1920×1080 con un acercamiento lento.

    Se lee en orden (un solo proceso de ffmpeg abierto); si se pide un instante que no sigue al
    anterior, se vuelve a abrir en ese punto. `cuadro(t)` usa el tiempo del clip desde `inicio`.
    """

    def __init__(self, archivo: str, inicio: float = 0.0, margen: float = 1.12, velocidad: float = 1.0):
        self.ruta = RAIZ / "clips_reales" / archivo
        self.existe = self.ruta.exists()
        self.inicio, self.margen, self.velocidad = inicio, margen, velocidad
        self.w, self.h = int(W * margen) // 2 * 2, int(H * margen) // 2 * 2
        self._proc = None
        self._siguiente = None
        self._ultimo = None
        if self.existe:
            import subprocess
            r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1",
                                str(self.ruta)], capture_output=True, text=True)
            self.duracion = float(r.stdout.strip() or 0)

    def _abrir(self, t_clip: float) -> None:
        import subprocess
        self.cerrar()
        filtro = (f"setpts=PTS/{self.velocidad},fps={FPS},scale={self.w}:{self.h}:force_original_aspect_ratio=increase,"
                  f"crop={self.w}:{self.h}")
        self._proc = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{t_clip:.3f}", "-i", str(self.ruta), "-an",
                                       "-vf", filtro, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._siguiente = round(t_clip * FPS)

    def cerrar(self) -> None:
        if self._proc is not None:
            self._proc.kill()
            self._proc = None

    def _leer(self, t_clip: float) -> np.ndarray:
        """Cuadro del clip en `t_clip` (s, ya con la velocidad aplicada al reloj de la escena)."""
        k = round(t_clip * FPS)
        if self._ultimo is not None and self._ultimo[0] == k:
            return self._ultimo[1]
        if self._proc is None or self._siguiente is None or k < self._siguiente or k > self._siguiente + 8:
            self._abrir(t_clip * self.velocidad)                  # -ss va en tiempo del archivo
            self._siguiente = k
        tam = self.w * self.h * 3
        datos = None
        while self._siguiente <= k:
            leido = self._proc.stdout.read(tam)
            if len(leido) < tam:                                   # se acabó el clip: se queda en el último cuadro
                break
            datos = leido
            self._siguiente += 1
        if datos is None:
            return self._ultimo[1] if self._ultimo is not None else np.zeros((self.h, self.w, 3), np.float32)
        img = np.frombuffer(datos, np.uint8).reshape(self.h, self.w, 3).astype(np.float32) / 255
        self._ultimo = (k, img)
        return img

    def cuadro(self, t: float, zoom: float = 1.0, cx: float = 0.5, cy: float = 0.5) -> np.ndarray:
        """Cuadro a 1920×1080. `zoom` 1 = el margen completo; >1 acerca. Sale en negro si falta el clip."""
        if not self.existe:
            return np.zeros((H, W, 3), np.float32)
        t_clip = min(max(0.0, self.inicio + t), max(0.0, self.duracion / self.velocidad - 0.1))
        img = self._leer(t_clip)
        s = zoom * W / self.w * self.margen
        bw, bh = W / s, H / s
        x0 = min(max(cx * self.w - bw / 2, 0), self.w - bw)
        y0 = min(max(cy * self.h - bh / 2, 0), self.h - bh)
        M = np.array([[s, 0, -x0 * s], [0, s, -y0 * s]], np.float32)
        return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
