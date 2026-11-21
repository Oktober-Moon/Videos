"""Prueba de estilo 1: ilustración pintada a partir de la foto real, animada.

La foto del tranvía de Friburgo se convierte en pintura: manchas de color (mean-shift), pinceladas
que siguen la forma de cada cosa (convolución de ruido a lo largo de las líneas de la imagen, LIC),
contornos a tinta y color hacia la paleta de Friburgo. El tranvía se recorta con rembg y avanza por
la calle hacia la cámara; el hueco que deja en el fondo se rellena con inpainting.

Uso: python pruebas_estilo/estilo1_pintado.py  -> revision/estilos/estilo1_pintado.mp4 y .png
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import cine  # noqa: E402
from paletas import FRIBURGO, rgb  # noqa: E402

W, H, FPS, SEG = 1920, 1080, 30, 8.0
P = rgb(FRIBURGO)
SALIDA = RAIZ / "revision" / "estilos"


def pinceladas(img: np.ndarray, largo: int = 9, semilla: int = 3) -> np.ndarray:
    """Textura de pincel: ruido arrastrado a lo largo del borde de las formas (LIC)."""
    h, w = img.shape[:2]
    gris = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    gx = cv2.Sobel(gris, cv2.CV_32F, 1, 0, ksize=5)
    gy = cv2.Sobel(gris, cv2.CV_32F, 0, 1, ksize=5)
    # tensor de estructura suavizado: dirección dominante de cada zona
    jxx = cv2.GaussianBlur(gx * gx, (0, 0), 6)
    jyy = cv2.GaussianBlur(gy * gy, (0, 0), 6)
    jxy = cv2.GaussianBlur(gx * gy, (0, 0), 6)
    ang = 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2           # a lo largo del borde, no a través
    vx, vy = np.cos(ang).astype(np.float32), np.sin(ang).astype(np.float32)
    rng = np.random.default_rng(semilla)
    ruido = cv2.resize(rng.random((h // 2, w // 2)).astype(np.float32), (w, h), interpolation=cv2.INTER_NEAREST)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    acum = ruido.copy()
    for signo in (1, -1):
        px, py = xx.copy(), yy.copy()
        for _ in range(largo):
            dx = cv2.remap(vx, px, py, cv2.INTER_LINEAR)
            dy = cv2.remap(vy, px, py, cv2.INTER_LINEAR)
            px += signo * dx * 1.5
            py += signo * dy * 1.5
            acum += cv2.remap(ruido, px, py, cv2.INTER_LINEAR)
    acum /= 2 * largo + 1
    acum = (acum - acum.mean()) / (acum.std() + 1e-6)
    # Donde la imagen no tiene una dirección clara (vidrio liso, cielo) el trazo daría remolinos:
    # ahí se apaga, y se deja entero donde hay bordes con orientación definida.
    l1 = 0.5 * (jxx + jyy + np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2))
    l2 = 0.5 * (jxx + jyy - np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2))
    coherencia = ((l1 - l2) / (l1 + l2 + 1e-4)) ** 2
    return acum * (0.25 + 0.75 * coherencia)


def pintar(foto: np.ndarray) -> np.ndarray:
    h, w = foto.shape[:2]
    u8 = (foto * 255).astype(np.uint8)
    chico = cv2.resize(u8, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    manchas = cv2.pyrMeanShiftFiltering(chico, 9, 18)
    manchas = cv2.resize(manchas, (w, h), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255
    detalle = cv2.detailEnhance(u8, sigma_s=6, sigma_r=0.1).astype(np.float32) / 255
    base = manchas * 0.72 + detalle * 0.28
    trazo = pinceladas(base)
    base = base * (1 + 0.085 * trazo[..., None])
    # contornos a tinta, finos, solo los que importan
    gris = cv2.cvtColor((manchas * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    bordes = cv2.Canny(cv2.GaussianBlur(gris, (0, 0), 1.2), 40, 110)
    bordes = cv2.GaussianBlur(bordes.astype(np.float32) / 255, (0, 0), 0.8)
    base = base * (1 - 0.55 * bordes[..., None]) + np.array([0.08, 0.07, 0.08], np.float32) * 0.55 * bordes[..., None]
    # color de pintura: algo más saturado, sombras hacia el verde de la Selva Negra
    lum = (base @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    base = lum + (base - lum) * 1.18
    return np.clip(base, 0, 1).astype(np.float32)


def refinar(foto_u8: np.ndarray, burda: np.ndarray) -> np.ndarray:
    """La máscara de rembg sale como una mancha redondeada; GrabCut la ajusta a los bordes reales
    del tranvía usando la mancha como punto de partida (seguro adentro / seguro afuera)."""
    h, w = burda.shape
    k = 1200 / w
    chica = cv2.resize(foto_u8, (1200, int(h * k)), interpolation=cv2.INTER_AREA)
    b = cv2.resize(burda, (1200, int(h * k)), interpolation=cv2.INTER_AREA) > 127
    m = np.full(b.shape, cv2.GC_BGD, np.uint8)
    m[cv2.dilate(b.astype(np.uint8), np.ones((41, 41), np.uint8)) > 0] = cv2.GC_PR_BGD
    m[b] = cv2.GC_PR_FGD
    m[cv2.erode(b.astype(np.uint8), np.ones((61, 61), np.uint8)) > 0] = cv2.GC_FGD
    bg, fg = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(cv2.cvtColor(chica, cv2.COLOR_RGB2BGR), m, None, bg, fg, 6, cv2.GC_INIT_WITH_MASK)
    fina = np.isin(m, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.uint8)
    # se queda solo la pieza más grande (el tranvía) y se tapan agujeros pequeños
    n, etiquetas, stats, _ = cv2.connectedComponentsWithStats(fina)
    if n > 1:
        fina = (etiquetas == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    fina = cv2.morphologyEx(fina, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    return cv2.resize(fina.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    im = Image.open(RAIZ / "imagenes" / "1.1_tranvia_friburgo.jpg").convert("RGB")
    im = im.resize((2400, int(2400 * im.height / im.width)), Image.LANCZOS)
    foto = np.asarray(im, np.float32) / 255
    h, w = foto.shape[:2]
    print("pintando…")
    pintura = pintar(foto)
    from rembg import new_session, remove
    m = remove(im, session=new_session("u2net"), only_mask=True, post_process_mask=True)
    mascara = refinar(np.asarray(im), np.asarray(m))
    mascara = cv2.GaussianBlur(mascara, (0, 0), 1.2)
    hueco = cv2.dilate((mascara > 0.1).astype(np.uint8) * 255, np.ones((31, 31), np.uint8))
    chico = cv2.resize((pintura * 255).astype(np.uint8), (w // 3, h // 3), interpolation=cv2.INTER_AREA)
    relleno = cv2.inpaint(chico, cv2.resize(hueco, (w // 3, h // 3), interpolation=cv2.INTER_NEAREST), 21, cv2.INPAINT_TELEA)
    relleno = cv2.resize(relleno, (w, h), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255
    relleno = relleno * (1 + 0.06 * pinceladas(relleno, 7, 9)[..., None])        # que el relleno también parezca pintado
    a = cv2.GaussianBlur(hueco.astype(np.float32) / 255, (0, 0), 6)[..., None]
    fondo = pintura * (1 - a) + relleno * a
    Image.fromarray((mascara * 255).astype(np.uint8)).resize((800, 600)).save(SALIDA / "estilo1_mascara.png")
    tranvia = np.dstack([pintura * mascara[..., None], mascara])
    ys, xs = np.nonzero(mascara > 0.5)
    # El tranvía ocupa casi media foto: si se encogiera para «llegar desde el fondo», el hueco sería
    # enorme. En cambio se acerca a la cámara creciendo desde su frente: la silueta crecida tapa la
    # original y casi no hay hueco que inventar.
    ancla = np.array([w * 0.455, ys.max()], np.float32)                           # frente del tranvía, a ras de vía
    deriva = np.array([w * 0.012, h * 0.035], np.float32)                         # baja un poco siguiendo la vía

    cuadros = int(SEG * FPS)
    tmp = SALIDA / "estilo1_pintado.tmp.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                          "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    for i in range(cuadros):
        t = i / FPS
        u = t / SEG
        llega = 1 - (1 - min(1.0, u / 0.9)) ** 2.2                               # frena al llegar
        s = 0.97 + 0.10 * llega
        pos = ancla + deriva * llega
        M = np.array([[s, 0, pos[0] - ancla[0] * s], [0, s, pos[1] - ancla[1] * s]], np.float32)
        movido = cv2.warpAffine(tranvia, M, (w, h), flags=cv2.INTER_LINEAR)
        cuadro = fondo * (1 - movido[..., 3:]) + movido[..., :3]
        # cámara: acercamiento lento
        z = 1.04 + 0.05 * u
        cubre = max(W / w, H / h) * z
        bw, bh = W / cubre, H / cubre
        x0, y0 = (w - bw) * 0.45, (h - bh) * 0.30
        Mc = np.array([[cubre, 0, -x0 * cubre], [0, cubre, -y0 * cubre]], np.float32)
        img = cv2.warpAffine(cuadro, Mc, (W, H), flags=cv2.INTER_LINEAR)
        img = cine.acabado_cine(img, i, sombras=P["verde"] * 0.6, luces=P["blanco"], grano=0.012, mezcla=0.15,
                                saturacion=1.0)
        if i == int(cuadros * 0.75):
            Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(SALIDA / "estilo1_pintado.png")
        p.stdin.write((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
        if i % 30 == 0:
            print(f"  cuadro {i}/{cuadros}")
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg falló")
    tmp.replace(SALIDA / "estilo1_pintado.mp4")
    print("listo")


if __name__ == "__main__":
    main()
