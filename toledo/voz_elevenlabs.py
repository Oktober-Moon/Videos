"""Narración completa con la voz de Eduardo clonada en ElevenLabs (decisión del 16 de noviembre de 2026).

La generación se hace en ElevenLabs con su conector oficial (OAuth, sin claves en la computadora):
una petición por subescena con el texto de `voz/elevenlabs/textos.json`, voz «Eduardo» (clon instantáneo
de `voz/elevenlabs/muestra_eduardo.mp3`) y los ajustes de `AJUSTES`. Este programa hace la parte local:

    .venv-voz/Scripts/python voz_elevenlabs.py --textos           # voz/elevenlabs/textos.json
    .venv-voz/Scripts/python voz_elevenlabs.py --procesar [ids]   # crudas -> audios/<id>.wav

Cada audio descargado se guarda en `voz/elevenlabs/crudas/<id>.mp3`; al procesarlo se le recorta lo que
hay antes de la primera palabra y después de la última y pasa por la misma cadena que las grabaciones
(`limpiar_audios.py --clonada`: compuerta, nivelación, tono de micrófono de las grabaciones, −18 LUFS).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import guion  # noqa: E402
import voz  # noqa: E402

CARPETA = RAIZ / "voz" / "elevenlabs"
TEXTOS = CARPETA / "textos.json"
CRUDAS = CARPETA / "crudas"
AUDIOS = RAIZ / "audios"
REGISTRO = AUDIOS / "GENERADOS.txt"
SR = 44100

# Probado el 16 de noviembre de 2026 con la 2.1 (`revision/voz/`): multilingual_v2 es el más parecido a la
# lectura de Eduardo (su tono sube y baja 23-25 Hz contra 16 de él; v4 llega a 77-89 Hz, suena
# entusiasta y mete suspiros entre frases, 5 a 7 en 20 s; multilingual_v2, ninguno).
MODELO = "eleven_multilingual_v2"
VOZ = "OLXuaxP3r64yBhfRgaLa"          # «Eduardo», clon instantáneo
# Primera pasada con estabilidad 0.8 y estilo 0: tono parejo, «sin énfasis». Segunda (16 de noviembre de
# 2026, prueba 1.0 A/B en `revision/voz/`): estabilidad 0.5 y estilo 0.15, más viva y sin respiraciones;
# con 0.65/0.05 la toma metió un «mmm» de 0.66 s. Se generan dos tomas y `revisar_voz.py` elige.
AJUSTES = dict(stability=0.5, similarity_boost=0.9, style=0.15, use_speaker_boost=True, speed=0.9)
NODOS = CARPETA / "nodos.json"        # flujo de ElevenLabs y nodo de cada subescena
PAUSA = '<break time="1.2s" />'       # donde el guion dice «(pausa)»


def texto(id_: str) -> str:
    """El texto de la subescena como se dice: nombres según su pronunciación del guion, cifras en
    palabras, siglas letra por letra y una pausa larga en cada «(pausa)»."""
    s = guion.subescena(id_, hablado=True)
    partes = []
    for i, o in enumerate(s.oraciones):
        partes.append(voz.normalizar(o, con_seseo=False))
        if i in s.pausas and i < len(s.oraciones) - 1:
            partes.append(PAUSA)
    return " ".join(partes)


def todas() -> list[str]:
    return [s.id for e in guion.leer().values() for s in e.subescenas]


def _leer(ruta: Path) -> np.ndarray:
    crudo = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ruta), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                           capture_output=True, check=True).stdout
    return np.frombuffer(crudo, np.float32).copy()


def recortar(x: np.ndarray, umbral_db: float = -40.0) -> np.ndarray:
    """Quita el silencio de antes de la primera palabra y de después de la última (tramas de 10 ms,
    umbral relativo a la voz), dejando 50 ms y 150 ms de margen."""
    n = SR // 100
    db = 20 * np.log10(np.sqrt(np.mean(x[: len(x) // n * n].reshape(-1, n) ** 2, axis=1)) + 1e-9)
    voz_ = np.flatnonzero(db > np.percentile(db, 95) + umbral_db)
    if voz_.size == 0:
        return x
    return x[max(0, voz_[0] * n - SR // 20): min(len(x), (voz_[-1] + 1) * n + int(0.15 * SR))]


# ElevenLabs casi no respira: en la 1.0 sus silencios entre oraciones miden 0.09-0.17 s y los de
# Eduardo, 0.35-0.58 s («no hay pausas pequeñas»). Se alargan a su medida, con algo de variación.
PAUSA_ORACION = (0.38, 0.55)
PAUSA_COMA = (0.16, 0.24)


def espaciar(x: np.ndarray, id_: str) -> np.ndarray:
    """Alarga los silencios de fin de oración y de coma. Cuántos hay de cada uno sale del texto: los
    k-1 silencios más largos (sin contar las pausas de 1.2 s) son fines de oración y los c siguientes,
    comas; los demás (cierres de consonantes dentro de las palabras) no se tocan."""
    s = guion.subescena(id_, hablado=True)
    k = len(s.oraciones) - 1 - sum(1 for p in s.pausas if p < len(s.oraciones) - 1)
    c = sum(len(re.findall(r"[,;:—–]", o)) for o in s.oraciones)
    n = SR // 100
    db = 20 * np.log10(np.sqrt(np.mean(x[: len(x) // n * n].reshape(-1, n) ** 2, axis=1)) + 1e-9)
    voz_ = np.flatnonzero(db > np.percentile(db, 95) - 35)
    huecos = [(a, b) for a, b in zip(voz_[:-1], voz_[1:]) if b - a - 1 >= 4]       # >= 40 ms
    huecos.sort(key=lambda h: h[1] - h[0], reverse=True)
    huecos = [h for h in huecos if (h[1] - h[0]) * 0.01 < 0.9]                    # las «(pausa)» ya son largas
    azar = np.random.default_rng([int(p) for p in id_.split(".")])     # misma variación en cada corrida
    extra = {}
    for j, (a, b) in enumerate(huecos[: k + c]):
        lo, hi = PAUSA_ORACION if j < k else PAUSA_COMA
        falta = azar.uniform(lo, hi) - (b - a - 1) * 0.01
        if falta > 0:
            extra[(a + b) // 2 * n] = int(falta * SR)
    partes, ini = [], 0
    for pos in sorted(extra):
        partes += [x[ini:pos], np.zeros(extra[pos], np.float32)]
        ini = pos
    return np.concatenate(partes + [x[ini:]])


def procesar(id_: str) -> Path:
    import soundfile as sf
    origen = CRUDAS / f"{id_}.mp3"
    recortada = CRUDAS / f"{id_}.recortada.wav"
    x = _leer(origen)
    fin = json.loads(ELECCION.read_text(encoding="utf-8")).get(id_, {}).get("fin") if ELECCION.exists() else None
    if fin:                                     # nada después de la última palabra (colas, «mmm»)
        x = x[: int((fin + 0.25) * SR)]
    sf.write(recortada, espaciar(recortar(x), id_), SR, subtype="PCM_16")
    destino = AUDIOS / f"{id_}.wav"
    voz.igualar(recortada, destino)
    recortada.unlink()
    linea = f"{destino.name} | ElevenLabs {MODELO}, voz «Eduardo» (clon instantáneo) | {dt.date.today()}\n"
    previas = REGISTRO.read_text(encoding="utf-8").splitlines(keepends=True) if REGISTRO.exists() else []
    REGISTRO.write_text("".join(p for p in previas if not p.startswith(destino.name + " ")) + linea, encoding="utf-8")
    return destino


TOMAS = CARPETA / "tomas"                       # <id>_a.mp3, <id>_b.mp3: dos tomas por subescena
REVISION = CARPETA / "revision.json"           # lo que midió revisar_voz.py de cada toma
ELECCION = CARPETA / "eleccion.json"           # toma elegida por subescena y fin de su última palabra
ESCENAS = RAIZ / "audios_escenas"              # un audio por escena, para entregar
PAUSA_SUBESCENA = 1.0                          # s entre subescenas al unir una escena


def nota(d: dict) -> float:
    """Menos es mejor: una voz que no es palabra («mmm», bostezo) descarta la toma; luego cuenta que
    diga todo el texto y, al final, las respiraciones."""
    return 100 * len(d["vocalizaciones"]) + 20 * max(0.0, 0.97 - d["parecido_texto"]) * 10 + d["respiraciones"]


def elegir() -> None:
    """Toma la mejor de las dos tomas de cada subescena y la deja en `crudas/<id>.mp3`."""
    import shutil
    rev = json.loads(REVISION.read_text(encoding="utf-8"))
    eleccion, dudosas = {}, []
    for i in todas():
        tomas = [(nota(rev[f"{i}_{t}.mp3"]), f"{i}_{t}.mp3") for t in "ab" if f"{i}_{t}.mp3" in rev]
        if not tomas:
            dudosas.append(f"{i} (sin tomas revisadas)")
            continue
        n, archivo = min(tomas)
        d = rev[archivo]
        shutil.copy2(TOMAS / archivo, CRUDAS / f"{i}.mp3")
        eleccion[i] = {"toma": archivo, "fin": d["fin_ultima_palabra"], "nota": round(n, 2)}
        if d["vocalizaciones"] or d["parecido_texto"] < 0.9:
            dudosas.append(f"{i} ({archivo}: texto {d['parecido_texto']:.2f}, vocalizaciones {d['vocalizaciones']})")
    ELECCION.write_text(json.dumps(eleccion, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(eleccion)} subescenas elegidas -> {ELECCION.relative_to(RAIZ)}")
    for d in dudosas:
        print("  revisar:", d)


def unir_escenas(numeros: list[int] | None = None) -> None:
    """`audios_escenas/escenaNN.wav`: las subescenas de cada escena en orden, con una pausa entre ellas."""
    ESCENAS.mkdir(exist_ok=True)
    for e in guion.leer().values():
        if numeros and e.numero not in numeros:
            continue
        ids = [s.id for s in e.subescenas]
        faltan = [i for i in ids if not (AUDIOS / f"{i}.wav").exists()]
        if faltan:
            print(f"  escena {e.numero}: faltan {faltan}")
            continue
        entradas = sum([["-i", str(AUDIOS / f"{i}.wav")] for i in ids], [])
        f = "".join(f"anullsrc=r=48000:cl=stereo,atrim=0:{PAUSA_SUBESCENA}[s{k}];" for k in range(len(ids) - 1))
        f += "".join(f"[{k}:a]" + (f"[s{k}]" if k < len(ids) - 1 else "") for k in range(len(ids)))
        f += f"concat=n={2 * len(ids) - 1}:v=0:a=1[o]"
        destino = ESCENAS / f"escena{e.numero:02d}.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", *entradas, "-filter_complex", f, "-map", "[o]",
                        "-c:a", "pcm_s16le", "-ar", "48000", str(destino)], check=True)
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    str(destino)], capture_output=True, text=True).stdout)
        print(f"  escena {e.numero}: {len(ids)} subescenas, {dur / 60:.1f} min -> {destino.relative_to(RAIZ)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--textos", action="store_true")
    ap.add_argument("--elegir", action="store_true", help="la mejor toma de cada subescena -> crudas/")
    ap.add_argument("--procesar", nargs="*", metavar="ID")
    ap.add_argument("--escenas", nargs="*", type=int, metavar="N", help="un audio por escena en audios_escenas/")
    a = ap.parse_args()
    if a.elegir:
        elegir()
    if a.textos:
        CARPETA.mkdir(parents=True, exist_ok=True)
        t = {i: texto(i) for i in todas()}
        TEXTOS.write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(t)} subescenas, {sum(len(v) for v in t.values()):,} caracteres -> {TEXTOS.relative_to(RAIZ)}")
    if a.procesar is not None:
        ids = a.procesar or sorted((p.stem for p in CRUDAS.glob("*.mp3")), key=lambda i: [int(c) for c in i.split(".")])
        for i in ids:
            d = procesar(i)
            print(f"  {i} -> {d.relative_to(RAIZ)}", flush=True)
    if a.escenas is not None:
        unir_escenas(a.escenas)


if __name__ == "__main__":
    main()
