"""Prueba de realismo: el mismo plano de 8 s (el tranvía que llega de madrugada) en tres versiones.

1. actual  — todo hecho con código (cajas y patrones calculados), Eevee.
2. libre   — texturas escaneadas, cielo fotográfico y detalles (Bächle, bajantes, faroles), Eevee.
3. cycles  — lo mismo que 2, renderizado con Cycles (la luz calculada rebote por rebote).

Uso: python pruebas_estilo/prueba_realismo.py  -> revision/realismo/
Se puede cortar y volver a correr: sigue con los cuadros que falten.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from escenas.plano3d import Plano3D  # noqa: E402

E = RAIZ / "revision" / "realismo"
FUENTE = RAIZ / "fuentes" / "Inter-SemiBold.ttf"
VERSIONES = [
    ("1_actual", "1 - Como está ahora (todo con código, Eevee)", Plano3D("prueba_realismo", 8.0, libre=False)),
    ("2_libre", "2 - Texturas escaneadas, cielo real y detalles (Eevee)", Plano3D("prueba_realismo", 8.0, libre=True)),
    ("3_cycles", "3 - Lo mismo, con Cycles", Plano3D("prueba_realismo", 8.0, motor="cycles", libre=True)),
]


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def main() -> None:
    E.mkdir(parents=True, exist_ok=True)
    for nombre, _, plano in VERSIONES:
        t0 = time.time()
        faltan = plano.faltan()
        print(f"{nombre}: {len(faltan)} de {plano.n} cuadros por hacer", flush=True)
        if faltan:
            plano.renderizar(None)          # no asegurar(): borraría las otras versiones del mismo plano
        print(f"{nombre}: listo en {(time.time() - t0) / 60:.1f} min", flush=True)
        tmp = E / f"{nombre}.tmp.mp4"
        ffmpeg("-framerate", "30", "-i", str(plano.dir / "f_%04d.png"), "-c:v", "libx264", "-preset", "medium",
               "-crf", "20", "-pix_fmt", "yuv420p", str(tmp))
        tmp.replace(E / f"{nombre}.mp4")
    # los tres seguidos, con su rótulo
    entradas, filtros = [], []
    fuente = FUENTE.as_posix().replace(":", "\\:")
    for i, (nombre, rotulo, _) in enumerate(VERSIONES):
        entradas += ["-i", str(E / f"{nombre}.mp4")]
        filtros.append(f"[{i}:v]drawbox=x=0:y=0:w=iw:h=70:color=black@0.75:t=fill,"
                       f"drawtext=fontfile='{fuente}':text='{rotulo}':x=28:y=16:fontsize=38:fontcolor=white,setsar=1[v{i}]")
    filtros.append("".join(f"[v{i}]" for i in range(len(VERSIONES))) + f"concat=n={len(VERSIONES)}:v=1:a=0[out]")
    tmp = E / "tres_niveles.tmp.mp4"
    ffmpeg(*entradas, "-filter_complex", ";".join(filtros), "-map", "[out]", "-c:v", "libx264", "-preset", "medium",
           "-crf", "23", "-pix_fmt", "yuv420p", str(tmp))
    tmp.replace(E / "tres_niveles.mp4")
    # hoja: el mismo instante de las tres, apiladas
    ffmpeg(*[x for nombre, _, _ in VERSIONES for x in ("-ss", "6", "-i", str(E / f"{nombre}.mp4"))],
           "-filter_complex", "[0:v][1:v][2:v]vstack=inputs=3,scale=1280:-2", "-frames:v", "1", str(E / "hoja_6s.jpg"))
    print("listo:", *(f.name for f in sorted(E.glob("*.mp4"))))


if __name__ == "__main__":
    main()
