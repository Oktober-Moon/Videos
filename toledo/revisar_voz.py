"""Revisión automática de la narración generada: que diga todo el texto y que no tenga sonidos que no
son palabras («mmm», bostezos, suspiros, respiraciones fuertes).

Con los tiempos por palabra de Whisper (medium, en la GPU) se ubica cada palabra; lo que suena fuera
de ellas se clasifica:
  - sonido con tono (voz) de 0.15 s o más fuera de toda palabra: vocalización («mmm», bostezo);
  - ruido sin tono de 0.15 s o más en una pausa, entre -40 y -10 dB de la voz: respiración o suspiro;
  - cualquier sonido después de la última palabra: cola (se corta al procesar).
El texto dicho se compara con el del guion (las cifras de Whisper se pasan a palabras).

Corre en el entorno de render, con las bibliotecas CUDA de PyTorch de `.venv-voz` en el PATH:

    $env:PATH = "$(Resolve-Path .venv-voz/Lib/site-packages/torch/lib);$env:PATH"
    .venv/Scripts/python revisar_voz.py voz/elevenlabs/tomas/*.mp3

El resultado se suma a `voz/elevenlabs/revision.json` ({archivo: {...}}). El id de la subescena es
el nombre del archivo hasta el primer «_» (`3.4_b.mp3` -> 3.4).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
import guion  # noqa: E402

SALIDA = RAIZ / "voz" / "elevenlabs" / "revision.json"
SR = 16000


def _leer(ruta: Path) -> np.ndarray:
    crudo = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ruta), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                           capture_output=True, check=True).stdout
    return np.frombuffer(crudo, np.float32).copy()


def _palabras(texto: str) -> list[str]:
    try:
        from num2words import num2words
        texto = re.sub(r"\d+", lambda m: " " + num2words(int(m.group(0)), lang="es") + " ", texto)
    except ImportError:
        pass
    t = unicodedata.normalize("NFKD", texto.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.findall(r"[a-zñ]+", t)


def _parecido(dicho: str, id_: str) -> float:
    """Lo dicho contra el guion, en su forma escrita y en la hablada; vale la mejor."""
    d = _palabras(dicho)
    return max(SequenceMatcher(None, d, _palabras(" ".join(guion.subescena(id_, hablado=h).oraciones))).ratio()
               for h in (False, True))


def _tramos(m: np.ndarray, minimo: int) -> list[tuple[int, int]]:
    d = np.diff(np.concatenate([[0], m.astype(int), [0]]))
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minimo]


def revisar(modelo, ruta: Path) -> dict:
    x = _leer(ruta)
    segs, _ = modelo.transcribe(x, language="es", word_timestamps=True, vad_filter=False,
                                condition_on_previous_text=False, beam_size=5)
    palabras = [w for s in segs for w in s.words]
    dicho = "".join(w.word for w in palabras).strip()
    id_ = ruta.stem.split("_")[0]
    n = SR // 100
    nt = len(x) // n
    db = 20 * np.log10(np.sqrt(np.mean(x[: nt * n].reshape(-1, n) ** 2, axis=1)) + 1e-9)
    ref = np.percentile(db, 95)
    # Sonido con tono (voz, «mmm») contra ruido (respiración, «s»): la voz cruza el cero pocas veces
    # por trama; el ruido de aire, muchas.
    tramas = x[: nt * n].reshape(-1, n)
    cruces = np.mean(np.abs(np.diff(np.sign(tramas), axis=1)) > 0, axis=1)
    sonoro = cruces < 0.12
    cubierto = np.zeros(nt, bool)
    for w in palabras:                                          # cada palabra, con margen
        cubierto[max(0, int((w.start - 0.08) * 100)): int((w.end + 0.12) * 100)] = True
    fin = palabras[-1].end if palabras else 0.0
    fuera = ~cubierto
    vocal = _tramos(fuera & sonoro & (db > ref - 30), 30)      # 0.3 s: lo más corto es desfase de Whisper
    resp = _tramos(fuera & ~sonoro & (db > ref - 40) & (db < ref - 10), 15)
    cola = [(a, b) for a, b in _tramos(fuera & (db > ref - 35), 8) if a * 0.01 > fin + 0.1]
    return {
        "id": id_, "duracion": round(len(x) / SR, 2), "fin_ultima_palabra": round(fin, 2),
        "parecido_texto": round(_parecido(dicho, id_), 3),
        "vocalizaciones": [[round(float(a) / 100, 2), round(float(b) / 100, 2)] for a, b in vocal],
        "respiraciones": len(resp),
        "cola": [[round(float(a) / 100, 2), round(float(b) / 100, 2)] for a, b in cola],
        "dicho": dicho,
    }


def main() -> None:
    from faster_whisper import WhisperModel
    rutas = [Path(p) for a in sys.argv[1:] if not a.startswith("--") for p in sorted(Path().glob(a))]
    modelo = WhisperModel("medium", device="cuda", compute_type="float16")
    datos = json.loads(SALIDA.read_text(encoding="utf-8")) if SALIDA.exists() else {}
    for r in rutas:
        if r.name in datos and "--todo" not in sys.argv:
            continue                                            # ya revisada
        d = revisar(modelo, r)
        datos[r.name] = d
        marca = []
        if d["parecido_texto"] < 0.85:
            marca.append(f"texto {d['parecido_texto']:.2f}")
        if d["vocalizaciones"]:
            marca.append(f"vocalización en {d['vocalizaciones']}")
        if d["respiraciones"]:
            marca.append(f"{d['respiraciones']} respiraciones")
        if d["cola"]:
            marca.append("cola")
        print(f"{r.name:18} {d['duracion']:5.1f} s  texto {d['parecido_texto']:.2f}  " + ("; ".join(marca) or "bien"),
              flush=True)
        SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
