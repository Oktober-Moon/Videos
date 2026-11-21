"""Une las tres pruebas de estilo: codifica el video de Blender (desde sus PNG), arma la hoja
comparativa con el mismo instante de cada una y un video con las tres en fila, una tras otra.

Uso: python pruebas_estilo/comparar.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
E = RAIZ / "revision" / "estilos"
FUENTE = RAIZ / "fuentes" / "Inter-SemiBold.ttf"
ESTILOS = [
    ("estilo1_pintado.mp4", "1 · Foto real pintada y animada"),
    ("estilo2_3d.mp4", "2 · Animación 3D (Blender)"),
    ("estilo3_dibujo.mp4", "3 · Ilustración dibujada con código"),
]


def correr(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def video_blender() -> None:
    tmp = E / "estilo2_3d.tmp.mp4"
    correr(["-framerate", "30", "-i", str(E / "blender" / "f_%04d.png"), "-c:v", "libx264", "-preset", "medium",
            "-crf", "20", "-pix_fmt", "yuv420p", str(tmp)])
    tmp.replace(E / "estilo2_3d.mp4")


def cuadro(video: str, t: float) -> np.ndarray:
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(E / video), "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(out, np.uint8).reshape(1080, 1920, 3)


def hoja() -> None:
    fuente = ImageFont.truetype(str(FUENTE), 34)
    filas = []
    for t in (1.5, 6.0):
        celdas = []
        for video, nombre in ESTILOS:
            im = Image.fromarray(cuadro(video, t)).resize((960, 540), Image.LANCZOS)
            d = ImageDraw.Draw(im)
            d.rectangle((0, 0, 960, 56), fill=(0, 0, 0))
            d.text((18, 9), f"{nombre}   ({t:.1f} s)", font=fuente, fill=(240, 240, 240))
            celdas.append(np.asarray(im))
        filas.append(np.hstack(celdas))
    Image.fromarray(np.vstack(filas)).save(E / "comparacion_estilos.png")
    chica = Image.open(E / "comparacion_estilos.png")
    chica.thumbnail((1920, 1920))
    chica.save(E / "comparacion_estilos_chica.jpg", quality=88)


def seguidos() -> None:
    """Los tres videos uno tras otro, con un rótulo arriba, para verlos de corrido."""
    entradas, filtros = [], []
    for i, (video, nombre) in enumerate(ESTILOS):
        entradas += ["-i", str(E / video)]
        texto = nombre.replace(":", r"\:").replace("·", "-")
        filtros.append(f"[{i}:v]drawbox=x=0:y=0:w=iw:h=70:color=black@0.75:t=fill,"
                       f"drawtext=fontfile='{FUENTE.as_posix().replace(':', chr(92) + ':')}':text='{texto}':"
                       f"x=28:y=16:fontsize=38:fontcolor=white,setsar=1[v{i}]")
    filtros.append("".join(f"[v{i}]" for i in range(len(ESTILOS))) + f"concat=n={len(ESTILOS)}:v=1:a=0[out]")
    tmp = E / "tres_estilos.tmp.mp4"
    correr([*entradas, "-filter_complex", ";".join(filtros), "-map", "[out]", "-c:v", "libx264", "-preset",
            "medium", "-crf", "23", "-pix_fmt", "yuv420p", str(tmp)])
    tmp.replace(E / "tres_estilos.mp4")


if __name__ == "__main__":
    video_blender()
    hoja()
    seguidos()
    for f in ("estilo1_pintado.mp4", "estilo2_3d.mp4", "estilo3_dibujo.mp4", "tres_estilos.mp4"):
        print(f, f"{(E / f).stat().st_size / 1e6:.1f} MB")
