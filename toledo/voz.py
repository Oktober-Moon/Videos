"""Narración con la voz de Eduardo clonada en local (Chatterbox Multilingual, de Resemble AI, licencia
MIT), en su versión afinada para el español de México y Latinoamérica. Nada sale de la computadora:
los pesos se bajan una vez de Hugging Face (`--bajar`) y después se leen solo de la caché local.

Corre en su propio entorno, `.venv-voz` (PyTorch con CUDA y chatterbox-tts), aparte del de render:

    .venv-voz/Scripts/python voz.py --bajar           # una sola vez: los pesos del modelo (unos 3.2 GB)
    .venv-voz/Scripts/python voz.py --muestra         # elige sola 12 s de habla continua de las grabaciones
    .venv-voz/Scripts/python voz.py --muestra audios/1.0.m4a 2.5 14   # o a mano: 14 s desde el segundo 2.5
    .venv-voz/Scripts/python voz.py --prueba 2.1      # revision/voz/2.1_clonada_mexico.wav, para compararla con la grabada
    .venv-voz/Scripts/python voz.py --prueba 2.1 --modelo base   # lo mismo con el modelo general
    .venv-voz/Scripts/python voz.py 3.6 3.7 4.0       # genera esas subescenas en audios/
    .venv-voz/Scripts/python voz.py --faltantes       # todas las subescenas que no tienen audio

El texto sale del guion de Word con cada nombre escrito como se pronuncia (lo que va entre
paréntesis), con las cifras en palabras y con seseo (ver `seseo`). Se genera oración por oración, con un silencio corto entre
oraciones y uno largo donde el guion dice «(pausa)». Cada audio generado se anota en
`audios/GENERADOS.txt`, para saber qué narración es grabada y cuál es clonada.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import guion  # noqa: E402

AUDIOS = RAIZ / "audios"
MUESTRA = RAIZ / "voz" / "muestra.wav"
CRUDAS = RAIZ / "voz" / "crudas"                 # salida directa del modelo, antes de igualarla
PYTHON_RENDER = RAIZ / ".venv" / "Scripts" / "python.exe"   # el entorno de limpiar_audios.py
REVISION = RAIZ / "revision" / "voz"
REGISTRO = AUDIOS / "GENERADOS.txt"
SR = 24000
SILENCIO_ORACION = 0.35          # s entre oraciones
SILENCIO_PAUSA = 1.2             # s donde el guion dice «(pausa)»

# Pesos de cada versión del modelo: (repositorio en Hugging Face, T3 = texto a sonidos, S3Gen = sonidos
# a audio). «mexico» es la afinada por Resemble AI para el español de México y Latinoamérica; «base», la
# multilingüe general, aprendió sobre todo español de España y se le nota el acento.
BASE = "ResembleAI/chatterbox"
MODELOS = {
    "mexico": ("ResembleAI/Chatterbox-Multilingual-es-mx-latam", "t3_es_mx_latam.safetensors", "s3gen_v3.safetensors"),
    "base": (BASE, "t3_mtl23ls_v2.safetensors", "s3gen.pt"),
}
TOKENIZADOR = "grapheme_mtl_merged_expanded_v1.json"
MODELO = "mexico"

# Cómo suena la voz (Chatterbox): expresividad (0.5 = neutra; más = más enfática), apego al texto
# (más bajo = ritmo más pausado) y variación entre tomas. Prueba del 15 de noviembre de 2026
# (`revision/voz/`), midiendo con Whisper de la primera a la última palabra de cada oración: con
# apego 0.5 la clonada hablaba más rápido que Eduardo y con 0.3 (lo que Resemble AI sugiere para
# voces rápidas) un 12 % más lento; 0.4 queda en medio. Bajar la expresividad no aplanó la
# entonación (quedó dentro del ruido de la medición).
EXPRESIVIDAD, APEGO, TEMPERATURA = 0.5, 0.4, 0.8

# Siglas y palabras en inglés del guion, escritas como se dicen en México. Se corrigen aquí.
PRONUNCIA = {
    "iPhone": "áifon", "iOS": "ái o es", "iCloud": "ái claud", "Apple": "ápol", "Google": "gúgol",
    "Android": "ándroid", "Amazon": "ámazon", "Facebook": "féisbuk", "Firefox": "fáirfox",
    "wifi": "uáifai", "hardware": "járdguer", "software": "sófguer", "hackear": "jaquear", "flash": "flash",
    "FBI": "efe be i", "FBE": "efe be e", "BFU": "be efe u", "AFU": "a efe u", "USB": "u ese be",
    "IP": "i pe", "IoT": "ai o ti", "apps": "aps",
}
LETRAS = dict(A="a", B="be", C="ce", D="de", E="e", F="efe", G="ge", H="hache", I="i", J="jota", K="ka",
              L="ele", M="eme", N="ene", O="o", P="pe", Q="cu", R="erre", S="ese", T="te", U="u", V="ve",
              W="doble ve", X="equis", Y="ye", Z="zeta")
MASCULINOS = {"años", "días", "minutos", "metros", "pies", "dólares", "galones", "litros", "caracteres",
              "dígitos", "milisegundos", "pascales", "segundos", "meses", "kilómetros"}
FEMENINOS = {"personas", "horas", "páginas", "semanas", "combinaciones", "veces"}


def _numero(n: int, siguiente: str = "") -> str:
    from num2words import num2words
    t = num2words(n, lang="es")
    s = siguiente.lower().strip(",.;:")
    if t.endswith("uno") and s in MASCULINOS:
        t = t[:-3] + ("ún" if t.endswith("iuno") else "un")
    elif t.endswith("uno") and s in FEMENINOS:
        t = t[:-3] + "una"
    return t


def normalizar(texto: str, con_seseo: bool = True) -> str:
    """Cifras, horas, modelos y siglas -> palabras, como se leen en voz alta. `con_seseo` solo hace
    falta en los modelos locales, que aprendieron sobre todo español de España."""
    for k, v in PRONUNCIA.items():
        texto = re.sub(rf"(?<![\w]){re.escape(k)}(?![\w])", v, texto)
    texto = re.sub(r"\b911\b", "nueve once", texto)
    texto = re.sub(r"\bal X\b", "al diez", texto)                 # «del iPhone 4S al X»: el iPhone diez

    def hora(m):
        h, mi = int(m.group(1)), int(m.group(2))
        if mi == 0:
            return _numero(h)
        return f"{_numero(h)} {'con ' if mi < 10 else ''}{_numero(mi)}"
    texto = re.sub(r"\b(\d{1,2}):(\d{2})\b", hora, texto)
    texto = re.sub(r"\b(\d+)\.(\d+)\b", lambda m: f"{_numero(int(m.group(1)))} punto "
                   + " ".join(_numero(int(c)) for c in m.group(2)), texto)
    texto = re.sub(r"\b(\d+)([A-Z])\b", lambda m: f"{_numero(int(m.group(1)))} {LETRAS[m.group(2)]}", texto)
    texto = re.sub(r"\b\d{1,3}(?:,\d{3})+\b", lambda m: m.group(0).replace(",", ""), texto)
    texto = re.sub(r"\b(\d+)\b(\s+(\S+))?",
                   lambda m: _numero(int(m.group(1)), m.group(3) or "") + (m.group(2) or ""), texto)
    texto = re.sub(r"\b([A-Z]{2,4})\b", lambda m: " ".join(LETRAS[c] for c in m.group(1)), texto)
    if con_seseo:
        texto = seseo(texto)
    return texto[:1].upper() + texto[1:]


def seseo(texto: str) -> str:
    """La c ante e/i y la z escritas como s, como suenan en México («celdas» -> «seldas»,
    «escena» -> «esena»). El modelo aprendió el español sobre todo de España y, si ve una c o una
    z, las pronuncia con la «z» española aunque la muestra de voz sea mexicana."""
    texto = re.sub(r"(?i)(s)c(?=[eiéí])", r"\1", texto)
    texto = re.sub(r"c(?=[eiéíEIÉÍ])", "s", texto)
    texto = re.sub(r"C(?=[eiéíEIÉÍ])", "S", texto)
    return texto.replace("z", "s").replace("Z", "S")


def tomar_muestra(origen: Path, inicio: float, duracion: float) -> None:
    """Recorta la muestra de voz: mono, 24 kHz, volumen normalizado, sin ruido grave."""
    MUESTRA.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(inicio), "-t", str(duracion), "-i", str(origen),
                    "-ac", "1", "-ar", str(SR), "-af", "highpass=f=70,loudnorm=I=-20:TP=-2", str(MUESTRA)], check=True)
    print("muestra:", MUESTRA.relative_to(RAIZ), f"({duracion:.1f} s de {origen.name} desde {inicio:.1f} s)")


def elegir_muestra(segundos: float = 12.0) -> tuple[Path, float]:
    """El tramo de `segundos` con más habla continua (menos silencios y sin saturar) de todas las
    grabaciones de Eduardo. Devuelve (audio, inicio)."""
    mejor = (-1.0, None, 0.0)
    for ruta in sorted(AUDIOS.glob("*.*")):
        if ruta.suffix.lower() not in (".wav", ".mp3", ".m4a") or not _grabada(ruta.stem):
            continue
        crudo = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ruta), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                               capture_output=True, check=True).stdout
        x = np.frombuffer(crudo, np.float32)
        paso = 800                                                   # tramos de 50 ms
        rms = np.sqrt(np.mean(x[: len(x) // paso * paso].reshape(-1, paso) ** 2, axis=1))
        if rms.size == 0:
            continue
        habla = rms > 0.12 * np.percentile(rms, 95)
        satura = np.abs(x[: len(x) // paso * paso].reshape(-1, paso)).max(axis=1) > 0.98
        n = int(segundos / 0.05)
        for i in range(0, max(1, len(habla) - n), 10):              # cada medio segundo
            nota = habla[i:i + n].mean() - 5 * satura[i:i + n].mean()
            if nota > mejor[0]:
                mejor = (nota, ruta, i * 0.05)
    if mejor[1] is None:
        raise SystemExit("No hay grabaciones en audios/ para sacar la muestra de voz.")
    print(f"tramo elegido: {mejor[1].name} desde {mejor[2]:.1f} s ({mejor[0]:.0%} con voz)")
    return mejor[1], mejor[2]


def _recortar(w: np.ndarray, umbral_db: float = -32.0) -> np.ndarray:
    """Quita lo que hay antes y después de la voz de una oración. El umbral es relativo a la voz de
    esa oración (tramas de 10 ms): el modelo suele dejar al final casi un segundo de cola entre
    -35 y -50 dB (exhalación, ruido), que con un umbral fijo se quedaba y alargaba cada pausa."""
    n = SR // 100
    if len(w) < 2 * n:
        return w
    rms = np.sqrt(np.mean(w[: len(w) // n * n].reshape(-1, n) ** 2, axis=1))
    db = 20 * np.log10(rms + 1e-9)
    voz = np.flatnonzero(db > np.percentile(db, 95) + umbral_db)
    if voz.size == 0:
        return w
    a = max(0, voz[0] * n - int(0.03 * SR))
    b = min(len(w), (voz[-1] + 1) * n + int(0.10 * SR))
    w = w[a:b].copy()
    f = int(0.02 * SR)                                       # fundido corto en el corte final
    w[-f:] *= np.linspace(1, 0, f, dtype=np.float32)
    return w


def _archivos(modelo: str) -> list[tuple[str, str]]:
    repo, t3, s3 = MODELOS[modelo]
    return [(BASE, "ve.pt"), (repo, TOKENIZADOR), (repo, t3), (repo, s3)]


def bajar(modelo: str) -> None:
    """Lo único que usa la red: baja los pesos a la caché de Hugging Face (~/.cache/huggingface)."""
    from huggingface_hub import hf_hub_download
    for repo, archivo in _archivos(modelo):
        print("listo:", hf_hub_download(repo, archivo))


def cargar(modelo: str, device: str):
    """Arma Chatterbox con los pesos de `modelo`, leídos solo de la caché local."""
    import torch
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    from chatterbox.models.s3gen import S3Gen
    from chatterbox.models.t3 import T3
    from chatterbox.models.t3.modules.t3_config import T3Config
    from chatterbox.models.tokenizers import MTLTokenizer
    from chatterbox.models.voice_encoder import VoiceEncoder

    def pesos(repo: str, archivo: str) -> dict:
        try:
            ruta = hf_hub_download(repo, archivo, local_files_only=True)
        except Exception:
            raise SystemExit(f"Faltan los pesos del modelo «{modelo}»: correr una vez voz.py --bajar --modelo {modelo}")
        return load_file(ruta) if ruta.endswith(".safetensors") else torch.load(ruta, map_location="cpu", weights_only=True)

    (_, ve_nombre), (repo, tok_nombre), (_, t3_nombre), (_, s3_nombre) = _archivos(modelo)
    ve = VoiceEncoder()
    ve.load_state_dict(pesos(BASE, ve_nombre))
    t3 = T3(T3Config.multilingual())
    estado = pesos(repo, t3_nombre)
    t3.load_state_dict(estado["model"][0] if "model" in estado else estado)
    from chatterbox.models.s3tokenizer import S3Tokenizer
    s3 = S3Gen()
    faltan, sobran = s3.load_state_dict(pesos(repo, s3_nombre), strict=False)
    # Pueden faltar solo las tablas fijas que el tokenizador calcula al crearse (filtros mel y ventana);
    # cualquier otra pieza que falte o sobre detiene todo en vez de ignorarse en silencio.
    faltan = [k for k in faltan if k.rsplit(".", 1)[-1] not in S3Tokenizer.ignore_state_dict_missing]
    if faltan or sobran:
        raise SystemExit(f"S3Gen de «{modelo}» no coincide con chatterbox-tts: faltan {faltan[:3]}…, sobran {sobran[:3]}…")
    tok = MTLTokenizer(hf_hub_download(repo, tok_nombre, local_files_only=True))
    return ChatterboxMultilingualTTS(t3.to(device).eval(), s3.to(device).eval(), ve.to(device).eval(), tok, device)


HUELLA = RAIZ / "voz" / "huella.npz"


def _leer16(ruta: Path) -> np.ndarray:
    crudo = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ruta), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                           capture_output=True, check=True).stdout
    return np.frombuffer(crudo, np.float32).copy()


def huella(modelo) -> tuple[np.ndarray, np.ndarray]:
    """Huella de voz promediada sobre TODAS las grabaciones, no solo los 12 s de la muestra: la del
    codificador de Chatterbox (guía a T3: cómo habla) y la x-vector de S3Gen (el timbre), esta en
    trozos de 10 s. Con ella el timbre se acerca más (prueba del 15 de noviembre de 2026: 0.784
    contra 0.735 con la muestra sola). Se guarda en `voz/huella.npz` y se rehace si cambia una grabación."""
    import torch
    rutas = [r for r in sorted(AUDIOS.glob("*.wav")) if _grabada(r.stem)]
    fuentes = np.array([f"{r.name}:{r.stat().st_mtime:.0f}" for r in rutas])
    if HUELLA.exists():
        g = np.load(HUELLA)
        if g["fuentes"].tolist() == fuentes.tolist():
            return g["ve"], g["xv"]
    ve, xv = [], []
    for r in rutas:
        x = _leer16(r)
        ve.append(modelo.ve.embeds_from_wavs([x], sample_rate=16000)[0])
        for a in range(0, max(1, len(x) - 160000), 160000):
            with torch.inference_mode():
                t = torch.from_numpy(x[a:a + 160000])[None].to(modelo.device)
                e = modelo.s3gen.speaker_encoder.inference(t).squeeze().cpu().numpy()
            xv.append(e / np.linalg.norm(e))
    ve, xv = np.mean(ve, 0), np.mean(xv, 0)
    ve, xv = ve / np.linalg.norm(ve), xv / np.linalg.norm(xv)
    HUELLA.parent.mkdir(parents=True, exist_ok=True)
    np.savez(HUELLA, fuentes=fuentes, ve=ve, xv=xv)
    print(f"huella de voz: {len(rutas)} grabaciones -> {HUELLA.relative_to(RAIZ)}")
    return ve, xv


class Voz:
    def __init__(self, modelo: str = MODELO):
        import torch
        if not MUESTRA.exists():
            raise SystemExit("Falta la muestra de voz: correr primero con --muestra <audio> <inicio> <segundos>.")
        self.torch = torch
        self.nombre = modelo
        self.modelo = cargar(modelo, "cuda" if torch.cuda.is_available() else "cpu")
        self.modelo.prepare_conditionals(str(MUESTRA), exaggeration=EXPRESIVIDAD)
        # La muestra pone el estilo y el sonido de arranque; la huella promedio, quién habla.
        ve, xv = huella(self.modelo)
        c = self.modelo.conds
        c.t3.speaker_emb = torch.from_numpy(ve)[None].float().to(self.modelo.device)
        norma = float(c.gen["embedding"].norm())
        c.gen["embedding"] = torch.from_numpy(xv * norma)[None].float().to(self.modelo.device)

    def oracion(self, texto: str, semilla: int) -> np.ndarray:
        self.torch.manual_seed(semilla)
        w = self.modelo.generate(texto, language_id="es", exaggeration=EXPRESIVIDAD, cfg_weight=APEGO,
                                 temperature=TEMPERATURA)
        return _recortar(w.squeeze().detach().cpu().numpy().astype(np.float32))

    def subescena(self, id_: str, destino: Path) -> Path:
        s = guion.subescena(id_, hablado=True)
        partes = []
        for i, o in enumerate(s.oraciones):
            texto = normalizar(o)
            print(f"  {id_} [{i + 1}/{len(s.oraciones)}] {texto}", flush=True)
            partes.append(self.oracion(texto, semilla=1000 * int(id_.split(".")[0]) + 10 * int(id_.split(".")[1]) + i))
            partes.append(np.zeros(int((SILENCIO_PAUSA if i in s.pausas else SILENCIO_ORACION) * SR), np.float32))
        audio = np.concatenate(partes[:-1]) if partes else np.zeros(SR, np.float32)
        import soundfile as sf
        CRUDAS.mkdir(parents=True, exist_ok=True)
        cruda = CRUDAS / f"{destino.stem}.wav"
        sf.write(cruda, audio, SR, subtype="PCM_16")
        igualar(cruda, destino)
        print(f"  -> {destino.relative_to(RAIZ)} ({len(audio) / SR:.1f} s)", flush=True)
        return destino


def igualar(cruda: Path, destino: Path) -> None:
    """Mismo tono de micrófono y nivel que las grabaciones limpias (`limpiar_audios.py --clonada`):
    48 kHz estéreo, -18 LUFS. Se escribe en un temporal y solo se renombra si terminó bien."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".tmp.wav")
    subprocess.run([str(PYTHON_RENDER), "-I", str(RAIZ / "limpiar_audios.py"), "--clonada", str(cruda), str(tmp)],
                   check=True)
    tmp.replace(destino)


def _anotar(ruta: Path, modelo: str) -> None:
    linea = f"{ruta.name} | voz clonada (Chatterbox Multilingual «{modelo}», muestra voz/muestra.wav) | {dt.date.today()}\n"
    previas = REGISTRO.read_text(encoding="utf-8").splitlines(keepends=True) if REGISTRO.exists() else []
    previas = [p for p in previas if not p.startswith(ruta.name + " ")]
    REGISTRO.write_text("".join(previas) + linea, encoding="utf-8")


def _todas() -> list[str]:
    return [s.id for e in guion.leer().values() for s in e.subescenas]


def _tiene_audio(id_: str) -> bool:
    return any((AUDIOS / f"{id_}{ext}").exists() for ext in (".wav", ".mp3", ".m4a"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("subescenas", nargs="*")
    ap.add_argument("--muestra", nargs="*", metavar="AUDIO INICIO SEGUNDOS",
                    help="sin argumentos elige sola el mejor tramo de 12 s de las grabaciones")
    ap.add_argument("--prueba", metavar="ID", help="genera una subescena ya grabada en revision/voz/ para comparar")
    ap.add_argument("--faltantes", action="store_true")
    ap.add_argument("--texto", action="store_true", help="solo muestra el texto que se diría, sin generar")
    ap.add_argument("--modelo", choices=sorted(MODELOS), default=MODELO)
    ap.add_argument("--bajar", action="store_true", help="baja los pesos del modelo (lo único que usa la red)")
    a = ap.parse_args()
    if a.bajar:
        bajar(a.modelo)
    if a.muestra is not None:
        if a.muestra:
            tomar_muestra(Path(a.muestra[0]), float(a.muestra[1]), float(a.muestra[2]))
        else:
            tomar_muestra(*elegir_muestra(), 12.0)
    ids = list(a.subescenas)
    if a.faltantes:
        ids += [i for i in _todas() if not _tiene_audio(i)]
    if a.texto:
        for i in ids or ([a.prueba] if a.prueba else []):
            s = guion.subescena(i, hablado=True)
            print(i, *[normalizar(o) for o in s.oraciones], sep="\n  ")
        return
    if not ids and not a.prueba:
        return
    voz = Voz(a.modelo)
    if a.prueba:
        voz.subescena(a.prueba, REVISION / f"{a.prueba}_clonada_{a.modelo}.wav")
    for i in ids:
        if _grabada(i):
            print(f"  {i}: ya tiene audio grabado; no se toca")
            continue
        _anotar(voz.subescena(i, AUDIOS / f"{i}.wav"), a.modelo)


def _grabada(id_: str) -> bool:
    """Un audio que no está en GENERADOS.txt es una grabación de Eduardo: nunca se sobrescribe."""
    if not _tiene_audio(id_):
        return False
    generados = REGISTRO.read_text(encoding="utf-8") if REGISTRO.exists() else ""
    return not any(l.startswith(f"{id_}.wav ") for l in generados.splitlines())


if __name__ == "__main__":
    main()
