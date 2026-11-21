"""Render de una escena: planos en paralelo, efectos de sonido, subtítulos y ensamblado.

Uso:
    python render.py                      # escena01 completa
    python render.py --revision           # solo los fotogramas clave de revision/
    python render.py --planos 2,6         # vuelve a renderizar esos planos y re-ensambla
    python render.py --audio              # solo efectos, .srt y mezcla final (reusa los planos)
    python render.py --fotograma 6:4.17 --salida prueba.png   # un cuadro suelto (t local)

Salidas en salida/: <escena>_prueba.mp4, <escena>_sfx.wav, <escena>.srt y planos/ (un .mp4
por plano, todos con la misma configuración para poder unirlos con `-c copy`).
"""

from __future__ import annotations

import argparse
import importlib
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SALIDA = RAIZ / "salida"
DIR_PLANOS = SALIDA / "planos"
REVISION = RAIZ / "revision"

# Sonoridad de la pista de efectos. Una voz de YouTube suele mezclarse a unos -16 LUFS;
# los efectos quedan 12 dB debajo. Si la voz se masteriza a -14 LUFS, subir esto a -26.
LUFS_EFECTOS = -28.0
PICO_REAL_MAX = -6.0

X264 = [
    "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
    "-profile:v", "high", "-g", "60", "-bf", "2",
    "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
    "-video_track_timescale", "15360", "-movflags", "+faststart",
]


def cargar(nombre: str):
    modulo = importlib.import_module(f"escenas.{nombre}")
    return modulo, modulo.cargar_tiempos(modulo.RUTA_TIEMPOS)


def ffmpeg(*args: str) -> None:
    resultado = subprocess.run(["ffmpeg", "-y", "-v", "error", *args], capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError("ffmpeg falló:\n" + resultado.stderr)


def renombrar_si_existe(temporal: Path, final: Path) -> None:
    if not temporal.exists() or temporal.stat().st_size == 0:
        raise RuntimeError(f"No se generó {temporal}")
    temporal.replace(final)


# --------------------------------------------------------------------------- video por plano


def renderizar_plano(nombre: str, numero: int) -> tuple[int, float, Path]:
    """Corre en un proceso aparte: prepara el plano y manda los cuadros crudos a ffmpeg."""
    import graficos
    import subtitulos

    modulo, tiempos = cargar(nombre)
    tp = tiempos.plano(numero)
    plano = modulo.PLANOS[numero](tp)
    inicio = time.time()
    plano.preparar()
    rotulador = subtitulos.Rotulador(subtitulos.bloques_de_escena(tiempos))
    DIR_PLANOS.mkdir(parents=True, exist_ok=True)
    final = DIR_PLANOS / f"{nombre}_p{numero:02d}.mp4"
    temporal = final.with_suffix(".tmp.mp4")
    proceso = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{graficos.W}x{graficos.H}", "-r", str(graficos.FPS), "-i", "-",
         *X264, "-threads", "3", "-an", str(temporal)],
        stdin=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        for i in range(tp.cuadros):
            t = i / graficos.FPS
            img = plano.cuadro(t)
            rotulador.aplicar(img, tp.inicio + t)
            proceso.stdin.write(graficos.a_bytes(img))
        proceso.stdin.close()
        error = proceso.stderr.read().decode("utf-8", "replace")
        codigo = proceso.wait()
    except BaseException:
        proceso.kill()
        temporal.unlink(missing_ok=True)
        raise
    if codigo != 0:
        temporal.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg falló en el plano {numero}:\n{error}")
    renombrar_si_existe(temporal, final)
    return numero, time.time() - inicio, final


# --------------------------------------------------------------------------- cuadros sueltos


def cuadro_suelto(nombre: str, numero: int, t: float, ruta: Path, plano=None) -> Path:
    import graficos
    import subtitulos

    modulo, tiempos = cargar(nombre)
    tp = tiempos.plano(numero)
    if plano is None:
        plano = modulo.PLANOS[numero](tp)
        plano.preparar()
    img = plano.cuadro(t)
    subtitulos.Rotulador(subtitulos.bloques_de_escena(tiempos)).aplicar(img, tp.inicio + t)
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.stem + ".tmp.png")
    graficos.a_imagen(img).save(temporal)
    temporal.replace(ruta)
    return ruta


def _revision_un_plano(nombre: str, numero: int, pedidos: list[tuple[float, str]]) -> list[str]:
    modulo, tiempos = cargar(nombre)
    plano = modulo.PLANOS[numero](tiempos.plano(numero))
    plano.preparar()
    hechos = []
    for t, archivo in pedidos:
        cuadro_suelto(nombre, numero, t, REVISION / archivo, plano)
        hechos.append(archivo)
    return hechos


def fotogramas_revision(nombre: str) -> None:
    _, tiempos = cargar(nombre)
    por_plano: dict[int, list[tuple[float, str]]] = {}
    for r in tiempos.revision:
        tp = tiempos.plano(int(r["plano"]))
        t = float(r.get("t", 0.0)) + (tp.marcas[r["marca"]] if "marca" in r else 0.0)
        por_plano.setdefault(tp.numero, []).append((t, r["archivo"]))
    with ProcessPoolExecutor(max_workers=min(len(por_plano), os.cpu_count() or 4)) as ex:
        futuros = [ex.submit(_revision_un_plano, nombre, n, p) for n, p in por_plano.items()]
        for f in as_completed(futuros):
            for archivo in f.result():
                print("  revision/" + archivo)


# --------------------------------------------------------------------------- audio, srt, ensamblado


def audio_y_srt(nombre: str) -> dict:
    import subtitulos

    modulo, tiempos = cargar(nombre)
    SALIDA.mkdir(exist_ok=True)
    subtitulos.escribir_srt(subtitulos.bloques_de_escena(tiempos), SALIDA / f"{nombre}.srt")
    mezcla = modulo.pista_sonido(tiempos)
    medidas = mezcla.normalizar(LUFS_EFECTOS, PICO_REAL_MAX)
    mezcla.escribir_wav(SALIDA / f"{nombre}_sfx.wav")
    return medidas


def ensamblar(nombre: str) -> Path:
    _, tiempos = cargar(nombre)
    lista = DIR_PLANOS / f"{nombre}_lista.txt"
    lineas = []
    for tp in tiempos.planos:
        archivo = DIR_PLANOS / f"{nombre}_p{tp.numero:02d}.mp4"
        if not archivo.exists():
            raise FileNotFoundError(f"Falta {archivo}; renderiza ese plano primero.")
        lineas.append(f"file '{archivo.name}'")
    lista.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    video = SALIDA / f"{nombre}_video.mp4"
    temporal = video.with_suffix(".tmp.mp4")
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(temporal))
    renombrar_si_existe(temporal, video)
    final = SALIDA / f"{nombre}_prueba.mp4"
    temporal = final.with_suffix(".tmp.mp4")
    ffmpeg("-i", str(video), "-i", str(SALIDA / f"{nombre}_sfx.wav"), "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
           "-shortest", "-movflags", "+faststart", str(temporal))
    renombrar_si_existe(temporal, final)
    video.unlink(missing_ok=True)
    return final


# --------------------------------------------------------------------------- principal


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--escena", default="escena01")
    ap.add_argument("--revision", action="store_true", help="solo fotogramas clave en revision/")
    ap.add_argument("--planos", help="lista de planos a renderizar, p. ej. 2,6")
    ap.add_argument("--audio", action="store_true", help="solo efectos, srt y mezcla final")
    ap.add_argument("--fotograma", help="PLANO:T  (t en segundos desde el inicio del plano)")
    ap.add_argument("--salida", default=None, help="ruta del PNG para --fotograma")
    ap.add_argument("--procesos", type=int, default=0)
    a = ap.parse_args()
    nombre = a.escena

    if a.fotograma:
        p, t = a.fotograma.split(":")
        ruta = Path(a.salida or SALIDA / f"{nombre}_p{int(p):02d}_{float(t):.2f}.png")
        print(cuadro_suelto(nombre, int(p), float(t), ruta))
        return 0
    if a.revision:
        print("Fotogramas de revisión:")
        fotogramas_revision(nombre)
        return 0

    _, tiempos = cargar(nombre)
    if not a.audio:
        numeros = [int(x) for x in a.planos.split(",")] if a.planos else [p.numero for p in tiempos.planos]
        procesos = a.procesos or min(len(numeros), max(1, (os.cpu_count() or 4) - 2))
        print(f"Renderizando {len(numeros)} planos con {procesos} procesos…")
        inicio = time.time()
        # los planos más largos primero, para repartir mejor la carga
        numeros.sort(key=lambda n: -tiempos.plano(n).cuadros)
        with ProcessPoolExecutor(max_workers=procesos) as ex:
            futuros = {ex.submit(renderizar_plano, nombre, n): n for n in numeros}
            for f in as_completed(futuros):
                n, seg, ruta = f.result()
                print(f"  plano {n}: {seg:6.1f} s -> {ruta.relative_to(RAIZ)}")
        print(f"Video listo en {time.time() - inicio:.0f} s")
    medidas = audio_y_srt(nombre)
    print(f"Efectos: {medidas['lufs']:.1f} LUFS integrados, pico real {medidas['pico_real_db']:.1f} dBTP")
    final = ensamblar(nombre)
    print(f"Listo: {final.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
