"""Render del video «Forense digital en dispositivos móviles e IoT».

Cada subescena es un clip: un .mp4 sin sonido y un .wav con la voz y los efectos, ambos de la
misma duración exacta (su audio + medio segundo). Los clips de una escena se unen con el demuxer
concat y `-c copy`; el sonido se une en PCM y se codifica a AAC una sola vez (así no quedan
huecos entre clips). Al final se unen las escenas.

Uso:
    python render.py 1                        # escena 1 completa -> salida/escena01.mp4
    python render.py 1 --clips 1.1            # rehace esa subescena (imagen y sonido) y vuelve a unir
    python render.py 1 --audio                # rehace solo el sonido (voz nueva o efectos) y une
    python render.py 1 --seguir               # sigue un render cortado (apagón, pausa): solo lo que falta
    python render.py 1 --revision             # fotogramas clave en revision/
    python render.py 1 --3d                   # solo los planos 3D de Blender (horas; se puede cortar y seguir)
    python render.py 1 --fotograma 1.1:3.2 --salida prueba.png
    python render.py --final                  # une las escenas hechas en salida/video_completo.mp4
"""

from __future__ import annotations

import argparse
import importlib
import os
import subprocess
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SALIDA = RAIZ / "salida"
REVISION = RAIZ / "revision"
LUFS_VOZ = -16.0
PICO_REAL_MAX = -1.0

X264 = [
    "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
    "-profile:v", "high", "-g", "60", "-bf", "2",
    "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
    "-video_track_timescale", "15360", "-movflags", "+faststart",
]
AAC = ["-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2"]


def modulo(n: int):
    return importlib.import_module(f"escenas.escena{n:02d}")


def dir_clips(n: int) -> Path:
    return SALIDA / "clips" / f"escena{n:02d}"


def ruta_clip(n: int, orden: int, id_: str, ext: str) -> Path:
    return dir_clips(n) / f"{orden:02d}_{id_}.{ext}"


def ffmpeg(*args: str) -> None:
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg falló:\n" + r.stderr)


def temporal(ruta: Path) -> Path:
    return ruta.with_name(ruta.stem + ".tmp" + ruta.suffix)


def confirmar(tmp: Path, final: Path) -> None:
    if not tmp.exists() or tmp.stat().st_size == 0:
        raise RuntimeError(f"No se generó {tmp}")
    tmp.replace(final)


def clip_vigente(n: int, orden: int, id_: str) -> bool:
    """Si la imagen de un clip ya está hecha y es más nueva que todo lo que la define: el código de
    su escena (y sus módulos `_eNN`), el motor de imagen compartido y su voz. Sirve para seguir un
    render cortado (`--seguir`) sin rehacer lo terminado. Los planos 3D tienen su propia caché."""
    final = ruta_clip(n, orden, id_, "mp4")
    if not final.exists():
        return False
    rutas = [RAIZ / "escenas" / f"escena{n:02d}.py", *(RAIZ / "escenas").glob(f"*_e{n:02d}.py"),
             *(RAIZ / "tres_d").glob(f"*_e{n:02d}.py"), RAIZ / "escenas" / "base.py", RAIZ / "escenas" / "diagramas.py",
             RAIZ / "graficos.py", RAIZ / "cine.py", RAIZ / "dibujo.py", RAIZ / "atmosfera.py", RAIZ / "paletas.py",
             RAIZ / "audios" / f"{id_}.wav"]
    return final.stat().st_mtime > max(p.stat().st_mtime for p in rutas if p.exists())


# --------------------------------------------------------------------------- imagen


def cuadro_final(sub, t: float, i: int):
    from graficos import acabado

    img = sub.cuadro(t)
    if getattr(sub, "cine", None):                                   # acabado de cine (enfoque realista)
        import cine

        return cine.acabado_cine(img, i + zlib.crc32(sub.id.encode()) % 997, opacidad=sub.opacidad(t), **sub.cine)
    ajustes = dict(vineta=0.38, grano=0.011, bloom=0.22, umbral_bloom=0.72)
    ajustes.update(getattr(sub, "acabado", {}))
    return acabado(img, i + zlib.crc32(sub.id.encode()) % 997, opacidad=sub.opacidad(t), **ajustes)


def _reclamar(ruta: Path) -> bool:
    """Reserva un clip para este proceso con un archivo `.en_curso` que solo uno puede crear. Si ya
    existe y su dueño sigue vivo, el clip lo está haciendo otro render (False). Evita que dos renders
    escriban el mismo temporal: pasó con dos renders de la escena 6, cuyos procesos tomaban clips
    de su fila después de arrancar."""
    from escenas.plano3d import _inicio, _vivo

    for _ in range(2):
        try:
            fd = os.open(ruta, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {_inicio(os.getpid()) or 0}".encode())
            os.close(fd)
            return True
        except FileExistsError:
            try:
                partes = ruta.read_text().split()
                dueno, inicio = int(partes[0]), (int(partes[1]) or None) if len(partes) > 1 else None
            except (OSError, ValueError, IndexError):
                dueno, inicio = 0, None
            if dueno and _vivo(dueno, inicio):
                return False
            ruta.unlink(missing_ok=True)                            # quedó de un render muerto
    return False


def video_clip(n: int, orden: int, id_: str) -> tuple[str, float]:
    dir_clips(n).mkdir(parents=True, exist_ok=True)
    reclamo = ruta_clip(n, orden, id_, "en_curso")
    if not _reclamar(reclamo):
        return id_, -1.0                                            # lo está haciendo otro render
    try:
        return _video_clip(n, orden, id_)
    finally:
        reclamo.unlink(missing_ok=True)


def _video_clip(n: int, orden: int, id_: str) -> tuple[str, float]:
    import graficos

    inicio = time.time()
    sub = modulo(n).crear(id_)
    sub.preparar()
    for plano in getattr(sub, "planos3d", []):                      # planos de Blender: todos sus cuadros
        plano.asegurar()
    dir_clips(n).mkdir(parents=True, exist_ok=True)
    final = ruta_clip(n, orden, id_, "mp4")
    tmp = temporal(final)
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{graficos.W}x{graficos.H}", "-r", str(graficos.FPS), "-i", "-",
                          *X264, "-threads", "3", "-an", str(tmp)],
                         stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for i in range(sub.T.cuadros):
            p.stdin.write(graficos.a_bytes(cuadro_final(sub, i / graficos.FPS, i)))
        p.stdin.close()
        error = p.stderr.read().decode("utf-8", "replace")
        codigo = p.wait()
    except BaseException:
        p.kill()
        p.wait()                                    # que ffmpeg suelte el archivo antes de borrarlo
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass                                    # que no tape el error original
        raise
    if codigo != 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg falló en el clip {id_}:\n{error}")
    confirmar(tmp, final)
    return id_, time.time() - inicio


# --------------------------------------------------------------------------- sonido


def audio_clip(n: int, orden: int, id_: str) -> dict:
    """Voz normalizada a -16 LUFS + efectos 15 dB debajo, que bajan más mientras se habla."""
    import numpy as np
    import pyloudnorm as pyln

    import sfx
    from escenas.base import SR, leer_audio, ruta_audio

    sub = modulo(n).crear(id_)
    sub.preparar()
    muestras = sub.T.cuadros * (SR // 30)
    ef = np.zeros((muestras, 2), np.float32)
    e = sub.efectos()[:muestras]
    ef[: len(e)] = e
    voz = None
    ruta = None if id_ == "titulo" else ruta_audio(id_)
    if ruta is not None:
        v = leer_audio(ruta)[:muestras]
        voz = np.zeros((muestras, 2), np.float32)
        voz[: len(v)] = v
        lufs = pyln.Meter(SR).integrated_loudness(voz.astype(np.float64))
        if np.isfinite(lufs):
            voz *= 10 ** ((LUFS_VOZ - lufs) / 20)
    ef = sfx.bajo_la_voz(ef, voz, debajo_db=getattr(sub, "debajo_db", 15.0))
    m = sfx.Mezcla(muestras / SR)
    m.x = (ef + (voz if voz is not None else 0)).astype(np.float32)
    if m.pico_real_db() > PICO_REAL_MAX:
        m._limitar(10 ** (PICO_REAL_MAX / 20))
    dir_clips(n).mkdir(parents=True, exist_ok=True)
    m.escribir_wav(ruta_clip(n, orden, id_, "wav"))
    return {"id": id_, "voz": ruta.name if ruta else None, "segundos": muestras / SR}


# --------------------------------------------------------------------------- unir


def unir_escena(n: int) -> Path:
    mod = modulo(n)
    ids = mod.clips()
    videos = [ruta_clip(n, k, i, "mp4") for k, i in enumerate(ids)]
    sonidos = [ruta_clip(n, k, i, "wav") for k, i in enumerate(ids)]
    faltan = [p.name for p in videos + sonidos if not p.exists()]
    if faltan:
        raise RuntimeError("Faltan clips: " + ", ".join(faltan))
    d = dir_clips(n)
    for nombre, lista in (("video", videos), ("sonido", sonidos)):
        (d / f"lista_{nombre}.txt").write_text("".join(f"file '{p.name}'\n" for p in lista), encoding="utf-8")
    SALIDA.mkdir(exist_ok=True)
    wav = SALIDA / f"escena{n:02d}.wav"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(d / "lista_sonido.txt"), "-c:a", "pcm_s24le", str(temporal(wav)))
    confirmar(temporal(wav), wav)
    solo_video = d / "escena.tmp.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(d / "lista_video.txt"), "-c", "copy", str(solo_video))
    final = SALIDA / f"escena{n:02d}.mp4"
    ffmpeg("-i", str(solo_video), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy", *AAC,
           str(temporal(final)))
    solo_video.unlink()
    confirmar(temporal(final), final)
    return final


def unir_final() -> Path:
    escenas = sorted(SALIDA.glob("escena[0-9][0-9].mp4"))
    if not escenas:
        raise RuntimeError("No hay escenas en salida/")
    lista_v = SALIDA / "lista_escenas.txt"
    lista_a = SALIDA / "lista_escenas_wav.txt"
    lista_v.write_text("".join(f"file '{p.name}'\n" for p in escenas), encoding="utf-8")
    lista_a.write_text("".join(f"file '{p.with_suffix('.wav').name}'\n" for p in escenas), encoding="utf-8")
    video = SALIDA / "video_completo.v.tmp.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lista_v), "-map", "0:v", "-c", "copy", str(video))
    wav = SALIDA / "video_completo.tmp.wav"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lista_a), "-c:a", "pcm_s24le", str(wav))
    final = SALIDA / "video_completo.mp4"
    ffmpeg("-i", str(video), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy", *AAC, str(temporal(final)))
    video.unlink()
    wav.unlink()
    confirmar(temporal(final), final)
    return final


# --------------------------------------------------------------------------- revisión y cuadros sueltos


def fotograma(n: int, id_: str, t: float, ruta: Path, sub=None) -> Path:
    import graficos

    if sub is None:
        sub = modulo(n).crear(id_)
        sub.preparar()
    img = cuadro_final(sub, t, int(t * 30))
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(ruta.stem + ".tmp.png")
    graficos.a_imagen(img).save(tmp)
    tmp.replace(ruta)
    return ruta


def _revision_clip(n: int, id_: str, pedidos: list[tuple[str, float]]) -> list[str]:
    sub = modulo(n).crear(id_)
    sub.preparar()
    return [str(fotograma(n, id_, t, REVISION / archivo, sub)) for archivo, t in pedidos]


def revision(n: int) -> None:
    mod = modulo(n)
    por_clip: dict[str, list] = {}
    for archivo, id_, cuando in mod.REVISION:
        t = cuando(mod.crear(id_).T)
        por_clip.setdefault(id_, []).append((f"escena{n:02d}_{archivo}", t))
    with ProcessPoolExecutor(max_workers=len(por_clip)) as ex:
        for f in as_completed([ex.submit(_revision_clip, n, i, p) for i, p in por_clip.items()]):
            for r in f.result():
                print("  ", Path(r).relative_to(RAIZ))


def hoja(n: int, fraccion: float = 0.72) -> Path:
    """Un cuadro de cada clip (al `fraccion` de su duración) en una hoja de revisión."""
    from PIL import Image, ImageDraw

    import graficos

    ids = modulo(n).clips()
    with ProcessPoolExecutor(max_workers=min(len(ids), max(1, (os.cpu_count() or 4) - 2))) as ex:
        rutas = list(ex.map(_cuadro_hoja, [n] * len(ids), ids, [fraccion] * len(ids)))
    cols = 4
    tw, th = 480, 270
    lamina = Image.new("RGB", (cols * tw, -(-len(ids) // cols) * (th + 30)), (12, 12, 12))
    d = ImageDraw.Draw(lamina)
    letra = graficos.fuente("Inter-SemiBold.ttf", 20)
    for k, (id_, ruta) in enumerate(zip(ids, rutas)):
        im = Image.open(ruta).resize((tw, th), Image.LANCZOS)
        x, y = (k % cols) * tw, (k // cols) * (th + 30)
        lamina.paste(im, (x, y))
        d.text((x + 8, y + th + 4), id_, font=letra, fill=(235, 235, 235))
        Path(ruta).unlink()
    destino = REVISION / f"escena{n:02d}_hoja.png"
    lamina.save(destino)
    return destino


def _cuadro_hoja(n: int, id_: str, fraccion: float) -> str:
    sub = modulo(n).crear(id_)
    sub.preparar()
    # Con el número de escena: el clip «titulo» existe en todas y dos hojas a la vez se pisaban.
    return str(fotograma(n, id_, sub.d * fraccion, REVISION / f"_hoja_e{n:02d}_{id_}.png", sub))


# --------------------------------------------------------------------------- principal


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("escena", nargs="?", type=int)
    ap.add_argument("--clips", help="ids separados por coma, p. ej. 1.1,1.2 (o «titulo»)")
    ap.add_argument("--audio", action="store_true", help="solo el sonido de los clips, y unir")
    ap.add_argument("--revision", action="store_true")
    ap.add_argument("--hoja", action="store_true", help="un cuadro por subescena en revision/escenaNN_hoja.png")
    ap.add_argument("--fotograma", help="ID:T, p. ej. 1.1:3.2")
    ap.add_argument("--salida")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--procesos", type=int, default=0)
    ap.add_argument("--seguir", action="store_true", help="sigue un render cortado: rehace solo los clips que faltan")
    ap.add_argument("--3d", dest="tres_d", action="store_true", help="renderiza solo los planos 3D de la escena")
    a = ap.parse_args()

    if a.final:
        print(unir_final().relative_to(RAIZ))
        return 0
    if a.escena is None:
        ap.error("falta el número de escena")
    n = a.escena
    if a.fotograma:
        id_, t = a.fotograma.rsplit(":", 1)
        print(fotograma(n, id_, float(t), Path(a.salida or SALIDA / f"cuadro_{id_}_{t}.png")))
        return 0
    if a.revision:
        print("Fotogramas de revisión:")
        revision(n)
        return 0
    if a.hoja:
        print(hoja(n).relative_to(RAIZ))
        return 0
    if a.tres_d:
        for id_ in modulo(n).clips():
            sub = modulo(n).crear(id_)
            sub.preparar()
            for plano in getattr(sub, "planos3d", []):
                t0 = time.time()
                print(f"  {id_} {plano.plano}: {len(plano.faltan())} de {plano.n} cuadros por hacer", flush=True)
                plano.asegurar()
                print(f"  {id_} {plano.plano}: listo en {(time.time() - t0) / 60:.1f} min", flush=True)
        return 0

    todos = modulo(n).clips()
    elegidos = a.clips.split(",") if a.clips else todos
    orden = {i: k for k, i in enumerate(todos)}
    imagen = [] if a.audio else elegidos
    if a.seguir:                                                    # solo la imagen que falta (el sonido es rápido)
        imagen = [i for i in imagen if not clip_vigente(n, orden[i], i)]
        # Un clip cuyo temporal se escribió hace menos de 10 min lo está haciendo otro render: se salta.
        en_curso = [i for i in imagen if (tmp := temporal(ruta_clip(n, orden[i], i, "mp4"))).exists()
                    and time.time() - tmp.stat().st_mtime < 600]
        if en_curso:
            print(f"Escena {n}: {en_curso} los está haciendo otro render", flush=True)
            imagen = [i for i in imagen if i not in en_curso]
        print(f"Escena {n}: {len(elegidos) - len(imagen)} clips ya hechos; faltan {imagen or 'ninguno'}", flush=True)
    procesos = a.procesos or min(len(elegidos), max(1, (os.cpu_count() or 4) - 2))
    inicio = time.time()
    with ProcessPoolExecutor(max_workers=procesos) as ex:
        trabajos = [ex.submit(audio_clip, n, orden[i], i) for i in elegidos]
        trabajos += [ex.submit(video_clip, n, orden[i], i) for i in imagen]
        for f in as_completed(trabajos):
            r = f.result()
            if isinstance(r, dict):
                print(f"  sonido {r['id']:>6}: {r['segundos']:6.2f} s, voz: {r['voz'] or 'sin grabar'}")
            elif r[1] < 0:
                print(f"  imagen {r[0]:>6}: la está haciendo otro render; se salta", flush=True)
            else:
                print(f"  imagen {r[0]:>6}: {r[1]:6.1f} s de render")
    print(f"Escena {n}: {unir_escena(n).relative_to(RAIZ)} ({time.time() - inicio:.0f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
