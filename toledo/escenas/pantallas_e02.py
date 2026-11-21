"""Pantallas de la escena 2 dibujadas en 2D y pegadas sobre el vidrio de los teléfonos y la laptop en 3D.

Cada función devuelve la imagen de una pantalla (float32, 0..1, alto × ancho × 3) a la resolución del
aparato: el iPhone 7 (750 × 1334), un Android de 2016 (720 × 1280) y la laptop (1600 × 900). `pegar`
la lleva al cuadro con la perspectiva de las cuatro esquinas que calcula `tres_d/vista_e02.py` con la
misma cámara del plano 3D. Así la letra queda nítida y los avisos se animan sin volver a renderizar.
"""

from __future__ import annotations

import functools
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from graficos import H, W, fuente, lim

AZUL = (10, 132, 255)
ROJO = (255, 69, 58)
VERDE = (61, 220, 132)


# --------------------------------------------------------------------------- pegar en perspectiva


def pegar(img: np.ndarray, contenido: np.ndarray, esquinas, brillo: float = 1.0, halo: float = 0.18,
          modo: str = "sumar") -> np.ndarray:
    """Pone `contenido` en el cuadro con la perspectiva de `esquinas` (arriba-izquierda, arriba-derecha,
    abajo-derecha, abajo-izquierda, en píxeles). `sumar`: la pantalla emite luz sobre el vidrio negro
    del render (se conservan sus reflejos); `cubrir`: reemplaza lo que había."""
    if brillo <= 0.002:
        return img
    dst = np.float32(esquinas)
    alto = max(np.linalg.norm(dst[3] - dst[0]), np.linalg.norm(dst[2] - dst[1]))
    ch, cw = contenido.shape[:2]
    escala = min(1.0, 1.6 * alto / ch)                   # se reduce antes (sin dientes) y se deforma después
    if escala < 0.98:
        contenido = cv2.resize(contenido, (max(2, int(cw * escala)), max(2, int(ch * escala))), interpolation=cv2.INTER_AREA)
        ch, cw = contenido.shape[:2]
    src = np.float32([[0, 0], [cw, 0], [cw, ch], [0, ch]])
    M = cv2.getPerspectiveTransform(src, dst)
    x0, y0 = np.floor(dst.min(0)).astype(int) - 2
    x1, y1 = np.ceil(dst.max(0)).astype(int) + 2
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x0 >= x1 or y0 >= y1:
        return img
    T = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]], np.float64) @ M
    ventana = (x1 - x0, y1 - y0)
    capa = cv2.warpPerspective(contenido.astype(np.float32), T, ventana, flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    if modo == "cubrir":
        uno = np.ones((ch, cw), np.float32)
        m = cv2.warpPerspective(uno, T, ventana, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)[..., None]
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - m * brillo) + capa * brillo
    else:
        img[y0:y1, x0:x1] += capa * brillo
    if halo > 0:                                          # la luz de la pantalla se abre un poco en el aire
        s = max(4.0, alto * 0.06)
        pad = int(3 * s)
        a0, b0, a1, b1 = max(0, y0 - pad), max(0, x0 - pad), min(H, y1 + pad), min(W, x1 + pad)
        grande = np.zeros((a1 - a0, b1 - b0, 3), np.float32)
        grande[y0 - a0 : y1 - a0, x0 - b0 : x1 - b0] = capa
        img[a0:a1, b0:b1] += cv2.GaussianBlur(grande, (0, 0), s) * halo * brillo
    return img


def a_np(im: Image.Image) -> np.ndarray:
    return np.asarray(im.convert("RGB"), np.float32) / 255.0


# --------------------------------------------------------------------------- iPhone


@functools.lru_cache(maxsize=4)
def _fondo_ios(borroso: bool) -> Image.Image:
    """Fondo de pantalla: degradado azul noche con dos manchas de luz, como los de iOS 10."""
    w, h = 750, 1334
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = np.zeros((h, w, 3), np.float32)
    a[..., 0] = 0.05 + 0.10 * (yy / h)
    a[..., 1] = 0.07 + 0.05 * (yy / h)
    a[..., 2] = 0.20 + 0.10 * (1 - yy / h)
    for cx, cy, r, col in ((180, 300, 380, (0.25, 0.20, 0.55)), (600, 1050, 420, (0.05, 0.30, 0.45))):
        d = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r))
        a += d[..., None] * np.array(col, np.float32) * 0.55
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    if borroso:
        im = im.filter(ImageFilter.GaussianBlur(30))
        im = Image.eval(im, lambda v: int(v * 0.55))
    return im


def _centrado(d: ImageDraw.ImageDraw, x, y, cadena, tam, nombre="Inter-Regular.ttf", fill=(255, 255, 255)):
    f = fuente(nombre, tam)
    w_ = f.getlength(cadena)
    d.text((x - w_ / 2, y), cadena, font=f, fill=fill)


# Ninguna pantalla lleva hora, fecha, operador ni porcentaje: el guion no los da, y en un documental de
# un caso real una cifra en pantalla se lee como dato del caso. Solo íconos.
def _barra_estado(d):
    for k in range(5):
        d.ellipse((20 + k * 17, 18, 32 + k * 17, 30), fill=(255, 255, 255) if k < 4 else None, outline=(255, 255, 255))
    d.rounded_rectangle((672, 15, 722, 35), 5, outline=(255, 255, 255), width=2)
    d.rectangle((676, 19, 676 + 38, 31), fill=(255, 255, 255))


@functools.lru_cache(maxsize=2)
def ios_bloqueo() -> np.ndarray:
    """Pantalla de bloqueo de iOS 10, sin hora ni fecha (no son datos del caso): el candado y
    «Presiona Inicio para desbloquear»."""
    im = _fondo_ios(False).copy()
    d = ImageDraw.Draw(im)
    _barra_estado(d)
    candado(d, 375, 470, 120)
    _centrado(d, 375, 1240, "Presiona Inicio para desbloquear", 32, "Inter-Regular.ttf", (235, 235, 240))
    return a_np(im)


def candado(d, cx, cy, s, fill=(255, 255, 255)):
    w, h = s * 0.8, s * 0.55
    d.rounded_rectangle((cx - w / 2, cy, cx + w / 2, cy + h), int(s * 0.08), fill=fill)
    r = w * 0.32
    d.arc((cx - r, cy - r * 1.8, cx + r, cy + r * 0.2), 180, 360, fill=fill, width=max(2, int(s * 0.11)))
    d.line((cx - r + s * 0.05, cy - r * 0.8, cx - r + s * 0.05, cy), fill=fill, width=max(2, int(s * 0.11)))
    d.line((cx + r - s * 0.05, cy - r * 0.8, cx + r - s * 0.05, cy), fill=fill, width=max(2, int(s * 0.11)))


TECLAS = (("1", ""), ("2", "ABC"), ("3", "DEF"), ("4", "GHI"), ("5", "JKL"), ("6", "MNO"), ("7", "PQRS"), ("8", "TUV"),
          ("9", "WXYZ"), ("", ""), ("0", ""), ("", ""))


@functools.lru_cache(maxsize=64)
def ios_codigo(puntos: int = 0, titulo: str = "Ingresa el código", aviso: str = "", sub: str = "",
               teclado: bool = True, emergencia: bool = True) -> np.ndarray:
    """Pantalla para escribir el código de seis dígitos; con `aviso`, la de espera tras los errores
    (iPhone no disponible / Vuelve a intentarlo en …)."""
    im = _fondo_ios(True).copy()
    d = ImageDraw.Draw(im)
    _barra_estado(d)
    if aviso:
        _centrado(d, 375, 380, aviso, 58, "Inter-SemiBold.ttf")
        if sub:
            _centrado(d, 375, 470, sub, 36, "Inter-Regular.ttf", (230, 230, 235))
    else:
        candado(d, 375, 150, 40)
        _centrado(d, 375, 230, titulo, 40, "Inter-Regular.ttf")
        for k in range(6):
            x = 375 + (k - 2.5) * 52
            if k < puntos:
                d.ellipse((x - 11, 330 - 11, x + 11, 330 + 11), fill=(255, 255, 255))
            else:
                d.ellipse((x - 11, 330 - 11, x + 11, 330 + 11), outline=(255, 255, 255), width=3)
    if teclado and not aviso:
        for k, (n, letras) in enumerate(TECLAS):
            if not n:
                continue
            cx, cy = 375 + (k % 3 - 1) * 200, 560 + (k // 3) * 170
            d.ellipse((cx - 72, cy - 72, cx + 72, cy + 72), fill=(70, 75, 95))
            _centrado(d, cx, cy - (52 if letras else 42), n, 72, "Inter-Light.ttf")
            if letras:
                _centrado(d, cx, cy + 22, letras, 20, "Inter-SemiBold.ttf", (235, 235, 240))
    if emergencia:
        d.text((60, 1250), "Emergencia", font=fuente("Inter-Regular.ttf", 32), fill=(255, 255, 255))
        if not aviso:
            d.text((560, 1250), "Cancelar", font=fuente("Inter-Regular.ttf", 32), fill=(255, 255, 255))
    return a_np(im)


def ios_borrando(avance: float) -> np.ndarray:
    im = Image.new("RGB", (750, 1334), (0, 0, 0))
    d = ImageDraw.Draw(im)
    _centrado(d, 375, 560, "Borrando datos…", 44, "Inter-Regular.ttf")
    d.rounded_rectangle((215, 680, 535, 690), 5, fill=(70, 70, 75))
    d.rounded_rectangle((215, 680, 215 + max(10, int(320 * lim(avance))), 690), 5, fill=(255, 255, 255))
    return a_np(im)


@functools.lru_cache(maxsize=4)
def ios_arranque(lineas: int) -> np.ndarray:
    """El teléfono arrancado con el programa del perito: texto blanco sobre negro, no el iOS normal."""
    im = Image.new("RGB", (750, 1334), (0, 0, 0))
    d = ImageDraw.Draw(im)
    f = fuente("Inter-Regular.ttf", 26)
    texto = ("RAMDISK DEL PERITO v2.1", "", "> sistema propio cargado", "> montar /dev/disk0 …  ok",
             "> leer memoria desde 0x00000000", "> enviar por USB …", "", "NO DESCONECTAR")
    for k, linea in enumerate(texto[:lineas]):
        d.text((48, 120 + k * 44), linea, font=f, fill=(235, 235, 235) if k else (255, 255, 255))
    return a_np(im)


# --------------------------------------------------------------------------- Android


@functools.lru_cache(maxsize=4)
def android_inicio() -> np.ndarray:
    """Android con cifrado de disco completo después de reiniciarse: no arranca hasta que alguien
    escriba el PIN («Para iniciar Android, ingresa tu PIN»)."""
    w, h = 720, 1280
    im = Image.new("RGB", (w, h), (12, 14, 18))
    d = ImageDraw.Draw(im)
    candado(d, 360, 210, 54, (230, 230, 230))
    _centrado(d, 360, 300, "Para iniciar Android,", 38, "Inter-Regular.ttf", (235, 235, 235))
    _centrado(d, 360, 348, "ingresa tu PIN", 38, "Inter-Regular.ttf", (235, 235, 235))
    d.line((180, 470, 540, 470), fill=(61, 220, 132), width=3)
    for k, (n, _) in enumerate(TECLAS):
        if not n:
            continue
        cx, cy = 360 + (k % 3 - 1) * 210, 640 + (k // 3) * 150
        _centrado(d, cx, cy - 40, n, 64, "Inter-Light.ttf", (240, 240, 240))
    return a_np(im)


# --------------------------------------------------------------------------- laptop del perito


def _hex(semilla: int, n: int = 16) -> str:
    rng = np.random.default_rng(semilla)
    return " ".join(f"{v:02X}" for v in rng.integers(0, 256, n))


def _ventana(titulo: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGB", (1600, 900), (22, 24, 28))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1600, 56), fill=(36, 39, 45))
    for k, c in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))):
        d.ellipse((22 + k * 30, 18, 42 + k * 30, 38), fill=c)
    _centrado(d, 800, 14, titulo, 26, "Inter-SemiBold.ttf", (220, 222, 228))
    return im, d


def laptop_extraccion(t: float, m) -> np.ndarray:
    """La herramienta del perito durante la 2.2. `m` son los inicios de las oraciones 0…8."""
    im, d = _ventana("Extracción física · iPhone (USB)")
    chica = fuente("Inter-Regular.ttf", 26)
    media = fuente("Inter-SemiBold.ttf", 34)
    mono = fuente("Inter-Regular.ttf", 24)
    gris = (150, 155, 165)
    # columna de la izquierda: el aparato
    d.rectangle((0, 56, 400, 900), fill=(28, 30, 35))
    d.text((40, 100), "Aparato", font=chica, fill=gris)
    d.text((40, 140), "iPhone", font=media, fill=(240, 240, 245))
    d.text((40, 200), "Conexión: USB", font=chica, fill=(220, 222, 228))
    estado = "arrancando…" if t < m[2] else ("leyendo" if t < m[3] else "copia lista")
    d.text((40, 240), f"Estado: {estado}", font=chica, fill=(220, 222, 228))
    if t < m[4]:
        # copia bit por bit: barra y volcado hexadecimal que corre
        avance = lim((t - m[2]) / max(0.5, m[3] - m[2] - 0.2))
        d.text((460, 100), "Copiando la memoria completa, bit por bit", font=media, fill=(240, 240, 245))
        d.rounded_rectangle((460, 170, 1540, 196), 13, fill=(50, 54, 62))
        if avance > 0:
            d.rounded_rectangle((460, 170, 460 + max(26, int(1080 * avance)), 196), 13, fill=AZUL)
        d.text((460, 214), f"{int(avance * 100)} %", font=chica, fill=(220, 222, 228))
        fila0 = int(max(0.0, t - m[2]) * 60)
        for k in range(16):
            n = fila0 + k
            addr = f"{(n * 16) * 4096:010X}"
            color = (120, 200, 255) if k == 15 and t < m[3] else (165, 170, 180)
            d.text((460, 290 + k * 34), f"{addr}   {_hex(n)}", font=mono, fill=color)
        if t >= m[3] - 0.2:
            a = int(255 * lim((t - m[3] + 0.2) / 0.5))
            d.rounded_rectangle((460, 830, 1100, 872), 10, fill=(18, 60, 36))
            d.text((480, 836), "✓  Copia exacta  ·  SHA-256 3f9a…c41e", font=chica, fill=(VERDE[0], VERDE[1], VERDE[2]) if a > 128 else gris)
    elif t < m[7]:
        # explorador de archivos: lo borrado sigue ahí
        d.text((460, 100), "Archivos en la copia", font=media, fill=(240, 240, 245))
        d.text((460, 170), "Nombre", font=chica, fill=gris)
        d.text((1080, 170), "Estado", font=chica, fill=gris)
        d.line((460, 206, 1540, 206), fill=(60, 64, 72), width=2)
        filas = (("IMG_0412.JPG", "normal"), ("sms.db", "normal"), ("nota_borrada.txt", "borrado"), ("IMG_0388.JPG", "normal"),
                 ("voz_0031.m4a", "normal"), ("chat_respaldo.db", "borrado"), ("Calendar.sqlitedb", "normal"))
        resalta = lim((t - m[5]) / 0.6)
        for k, (nom, est) in enumerate(filas):
            y = 226 + k * 70
            if est == "borrado":
                c = (int(22 + 28 * resalta), int(24 + 20 * resalta), int(28 + 46 * resalta))
                d.rectangle((452, y - 10, 1548, y + 50), fill=c)
            d.text((470, y), nom, font=media if est == "borrado" else chica, fill=(240, 240, 245))
            d.text((1080, y + 4), "borrado · recuperable" if est == "borrado" else "—", font=chica,
                   fill=(255, 159, 10) if est == "borrado" else gris)
        if t >= m[5]:
            d.text((470, 740), "El espacio quedó marcado como libre: los datos siguen ahí.", font=chica, fill=(220, 222, 228))
        if t >= m[6]:
            d.rounded_rectangle((460, 790, 1540, 880), 12, fill=(70, 30, 20))
            d.text((540, 796), "Memoria sin cifrar", font=media, fill=(255, 200, 160))
            d.text((540, 840), "o cifrada con una clave que se podía sacar del propio teléfono", font=chica, fill=(240, 190, 160))
            candado(d, 500, 806, 30, (255, 200, 160))
    else:
        # fuerza bruta con tarjetas gráficas
        # sin contador ni velocidad exacta: el guion dice «millones por segundo», no cuántos
        d.text((460, 100), "Probando contraseñas", font=media, fill=(240, 240, 245))
        d.text((460, 160), "millones por segundo, con tarjetas gráficas", font=chica, fill=(220, 222, 228))
        for k in range(4):
            y = 240 + k * 64
            d.text((460, y), "Tarjeta gráfica", font=chica, fill=gris)
            carga = 0.96 + 0.04 * math.sin(t * 7 + k)
            d.rounded_rectangle((760, y + 6, 1500, y + 30), 12, fill=(50, 54, 62))
            d.rounded_rectangle((760, y + 6, 760 + int(740 * carga), y + 30), 12, fill=(48, 209, 88))
        rng = np.random.default_rng(int(t * 20))
        for k in range(8):
            prueba = "".join(rng.choice(list("0123456789abcdefghijklmnopqrstuvwxyz"), 6))
            d.text((460 + (k % 2) * 420, 540 + (k // 2) * 44), f"{prueba}   ✗", font=mono, fill=(120, 125, 135))
    return a_np(im)


def laptop_cifrado(t: float) -> np.ndarray:
    """2.7: la copia del laboratorio abierta: solo bytes al azar, nada legible."""
    im, d = _ventana("Copia del laboratorio · iPhone")
    media = fuente("Inter-SemiBold.ttf", 34)
    mono = fuente("Inter-Regular.ttf", 24)
    d.text((60, 90), "Datos cifrados", font=media, fill=(240, 240, 245))
    d.text((360, 96), "sin la clave del chip no se pueden leer", font=fuente("Inter-Regular.ttf", 26), fill=(150, 155, 165))
    fila0 = int(t * 4)
    for k in range(20):
        n = fila0 + k
        d.text((60, 170 + k * 34), f"{(n * 16):08X}   {_hex(n + 991, 22)}", font=mono, fill=(165, 170, 180))
    return a_np(im)
