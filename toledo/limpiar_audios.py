"""Limpieza de las voces narradas por Eduardo.

Desde el 16 de noviembre de 2026 la narración del video es la voz de Eduardo clonada en ElevenLabs
(`voz_elevenlabs.py`, en `audios/`); sus grabaciones limpias se conservan aparte, en
`audios_grabados/`, que es la salida de este programa (así una corrida nunca pisa la narración).

Qué hace, en orden, con cada audio:
  1. Decodifica el original (`audios_originales/`) a mono de 48 kHz: las dos pistas del
     estéreo se promedian, porque la voz es una sola y el estéreo solo aporta fase y ruido.
  2. Conserva solo los intervalos indicados en `audios_cortes.json` (quita tomas fallidas,
     frases repetidas, respiraciones largas) y los une con fundidos cortos.
  3. Acorta las pausas internas largas y recorta el silencio del inicio y del final.
  4. Filtro pasa-altas (80 Hz) contra el ruido grave y compuerta suave en las pausas.
  5. Nivela la voz de forma lenta (control automático de ganancia con detección de voz):
     las frases dichas más fuerte o más bajo se acercan al nivel de la mediana del audio.
  6. Iguala el tono entre audios (ecualización limitada a ±4 dB hacia el espectro mediano).
  7. Normaliza la sonoridad integrada de todos al mismo objetivo y limita los picos.
  8. Escribe `audios_grabados/<subescena>.wav` (PCM de 16 bits, 48 kHz, estéreo con la voz
     centrada): el formato que busca `escenas/base.py` en `audios/`, y su duración es exacta (en
     un `.aac` crudo `ffprobe` solo la estima y se equivoca por segundos).

Nombre de la salida: el render toma el audio por número de subescena del guion (`2.6.wav` es la
voz de la subescena 2.6), no por el nombre con que se grabó el archivo. Por eso la salida lleva
el número de la subescena cuyo texto contiene la grabación:
  - un original sin punto es la parte inicial de la escena: `1` -> `1.0.wav`;
  - cualquier otro conserva su nombre, salvo que su entrada de `audios_cortes.json` traiga
    `"guion": "<subescena>"` (archivo nombrado con otro número: `2.7` -> `2.6.wav`);
  - dos grabaciones no pueden caer en la misma subescena (una sobrescribiría a la otra): el
    programa se detiene antes de escribir nada, y también si el número no existe en el guion.
Los argumentos de la línea de comandos son números de subescena del guion (los de la salida).

Los originales nunca se tocan: la primera vez se copian a `audios_originales/` y de ahí se
lee siempre, así que volver a ejecutar da el mismo resultado. Una grabación nueva o regrabada
se deja en `audios_originales/` (no en `audios_grabados/`, que es solo la salida).

Uso:
    python limpiar_audios.py                 # todos
    python limpiar_audios.py 1.0 2.1 3.2     # solo esas subescenas
    python limpiar_audios.py --informe       # solo mide, no escribe nada
    python limpiar_audios.py --clonada ENTRADA SALIDA   # voz clonada -> mismo tono y nivel que las grabaciones

`audios_cortes.json`: {"<original>": {"conservar": [[ini, fin], ...], "pausa_final": 0.35, "guion": "2.6",
"incompleto": "motivo", "omitir": true}} con tiempos en segundos del audio original, de la primera
palabra a la última de cada toma buena. Un audio sin entrada se conserva entero (solo se acortan
pausas y se nivela).
`omitir`: el original no se procesa ni produce salida (toma abortada, o sin voz utilizable).
`incompleto`: la grabación se conserva, pero corta a media subescena; el motivo se anota en
`audios_grabados/INCOMPLETOS.txt` (que este programa reescribe en cada corrida) y se avisa al ejecutar.
"""
import glob
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pyloudnorm as pn
from scipy import signal

RAIZ = os.path.dirname(os.path.abspath(__file__))
ORIGINALES = os.path.join(RAIZ, "audios_originales")
SALIDA = os.path.join(RAIZ, "audios_grabados")
CORTES = os.path.join(RAIZ, "audios_cortes.json")

SR = 48000
HOP = int(SR * 0.010)           # paso de análisis: 10 ms
VENT = int(SR * 0.020)          # ventana de análisis: 20 ms
LUFS_OBJETIVO = -18.0           # sonoridad integrada de cada audio
PICO_MAX = 10 ** (-1.5 / 20)    # techo del limitador: -1,5 dBFS
PAUSA_MAX = 0.60                # pausa interna más larga que se conserva (s)
PAUSA_MIN_UNION = 0.0           # las uniones ya traen su margen de silencio
CABEZA = 0.20                   # silencio antes de la primera palabra (s)
COLA = 0.35                     # silencio tras la última palabra (s)
MARGEN_INI = 0.15               # silencio previo que se rescata en cada corte (s)
MARGEN_FIN = 0.20               # silencio posterior que se rescata en cada corte (s)
FUNDIDO = 0.020                 # fundido cruzado en cada unión (s)
GANANCIA_MAX = 8.0              # tope de la nivelación (dB)
ATENUACION_PAUSAS = 12.0        # cuánto baja la compuerta el ruido entre palabras (dB)
EQ_MAX = 4.0                    # corrección de tono máxima (dB)


def clave(i):
    p = i.split(".")
    return [int(p[0]), int(p[1]) if len(p) > 1 else 0]


EXTENSIONES = (".wav", ".aac", ".mp3", ".m4a")


def respaldar_originales():
    """Primera vez: copia las grabaciones de `audios/` a `audios_originales/`."""
    if os.path.isdir(ORIGINALES):
        return
    os.makedirs(ORIGINALES)
    for ruta in glob.glob(os.path.join(RAIZ, "audios", "*")):
        if ruta.lower().endswith(EXTENSIONES):
            shutil.copy2(ruta, os.path.join(ORIGINALES, os.path.basename(ruta)))


def originales():
    """{id: ruta} de las grabaciones originales."""
    return {os.path.splitext(os.path.basename(p))[0]: p
            for p in glob.glob(os.path.join(ORIGINALES, "*")) if p.lower().endswith(EXTENSIONES)}


def decodificar(ruta):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", ruta, "-f", "f32le", "-ac", "1",
                        "-ar", str(SR), "pipe:1"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32).astype(np.float64)


# ---------------------------------------------------------------- análisis de voz
_SOS_ANALISIS = signal.butter(2, 130, "highpass", fs=SR, output="sos")


def energia_db(x):
    """Energía en dB por trama de 20 ms (cada 10 ms), sin contar lo que está por debajo de 130 Hz."""
    x = signal.sosfilt(_SOS_ANALISIS, x)
    n = (len(x) - VENT) // HOP + 1
    if n <= 0:
        return np.full(1, -120.0)
    idx = np.arange(VENT)[None, :] + HOP * np.arange(n)[:, None]
    return 10 * np.log10((x[idx] ** 2).mean(axis=1) + 1e-12)


def mascara_voz(db):
    """Verdadero donde hay voz: histéresis sobre la energía + 120 ms de arrastre."""
    piso, pico = np.percentile(db, 5), np.percentile(db, 95)
    alto = max(piso + 14, pico - 30)
    bajo = max(piso + 8, pico - 36)
    m = np.zeros(len(db), bool)
    on = False
    for i, v in enumerate(db):
        on = v > bajo if on else v > alto
        m[i] = on
    k = np.ones(25, bool)                       # dilatación ±120 ms
    return np.convolve(m, k, mode="same") > 0


def tramos(m):
    """[(ini, fin)) de cada racha de Verdadero."""
    d = np.diff(np.concatenate([[0], m.astype(int), [0]]))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


# ---------------------------------------------------------------- cortes y pausas
def punto_silencioso(db, t, radio=0.12):
    """Frame de menor energía a menos de `radio` s de `t` (para no cortar sobre una palabra)."""
    c = int(t / 0.010)
    a, b = max(0, c - int(radio / 0.010)), min(len(db), c + int(radio / 0.010) + 1)
    return a + int(np.argmin(db[a:b]))


def extender_silencio(m, f, sentido, maximo):
    """Desde el frame `f` avanza (sentido=+1) o retrocede (-1) por silencio hasta `maximo` s."""
    n = 0
    while n < int(maximo / 0.010) and 0 <= f + sentido < len(m) and not m[f + sentido]:
        f += sentido
        n += 1
    return f


def conservar(x, intervalos, margen_final):
    """Recorta los intervalos [ini, fin] (palabra inicial a palabra final) con su silencio
    de borde y los une con fundido cruzado."""
    db = energia_db(x)
    m = mascara_voz(db)
    trozos = []
    for ini, fin in intervalos:
        # el tiempo dado puede caer sobre una palabra: se busca el punto más callado a ±80 ms
        fi = punto_silencioso(db, ini, 0.08)
        ff = punto_silencioso(db, fin, 0.08)
        fi = extender_silencio(m, fi, -1, MARGEN_INI)
        ultimo = ini == intervalos[-1][0]
        ff = extender_silencio(m, ff, +1, margen_final if ultimo else MARGEN_FIN)
        trozos.append(x[fi * HOP: min(len(x), ff * HOP + VENT)])
    return unir(trozos)


def unir(trozos):
    n = int(SR * FUNDIDO)
    salida = trozos[0].copy()
    sube = np.sin(np.linspace(0, np.pi / 2, n)) ** 1
    baja = np.cos(np.linspace(0, np.pi / 2, n))
    for t in trozos[1:]:
        salida[-n:] = salida[-n:] * baja + t[:n] * sube
        salida = np.concatenate([salida, t[n:]])
    return salida


def acortar_pausas(x, pausa_final):
    """Pausas internas > PAUSA_MAX se reducen a PAUSA_MAX; el inicio y el final se dejan en
    CABEZA y `pausa_final`."""
    db = energia_db(x)
    m = mascara_voz(db)
    habla = tramos(m)
    if not habla:
        return x
    trozos = []
    ant_fin = None
    f = lambda i: i * HOP
    for k, (a, b) in enumerate(habla):
        if k == 0:
            ini = max(0, a - int(CABEZA / .01))
            trozos.append(np.zeros(int(round((CABEZA / .01 - (a - ini)) * HOP))))
            trozos.append(x[f(ini): f(a)])
        else:
            gap = a - ant_fin
            if gap * 0.010 > PAUSA_MAX:
                mitad = int(PAUSA_MAX / 0.010 / 2)
                trozos.append(x[f(ant_fin): f(ant_fin + mitad)])
                trozos.append(x[f(a - mitad): f(a)])
            else:
                trozos.append(x[f(ant_fin): f(a)])
        trozos.append(x[f(a): f(b)])
        ant_fin = b
    cola = int(pausa_final / 0.010)
    resto = x[f(ant_fin): f(min(len(db), ant_fin + cola))]
    trozos.append(resto)
    trozos.append(np.zeros(max(0, int(pausa_final * SR) - len(resto))))
    y = np.concatenate(trozos)
    return y


# ---------------------------------------------------------------- tono, nivel
def pasa_altas(x):
    return signal.sosfiltfilt(signal.butter(4, 80, "highpass", fs=SR, output="sos"), x)


def compuerta(x):
    db = energia_db(x)
    m = mascara_voz(db)
    g = np.where(m, 1.0, 10 ** (-ATENUACION_PAUSAS / 20))
    g = np.repeat(g, HOP)
    g = np.concatenate([g, np.full(max(0, len(x) - len(g)), g[-1])])[: len(x)]
    ventana = np.hanning(int(SR * 0.06))
    ventana /= ventana.sum()
    return x * np.convolve(g, ventana, mode="same")


def nivelar(x):
    """Control de ganancia lento: nivel de voz en ventana de ±1,2 s -> mediana del audio."""
    db = energia_db(x)
    m = mascara_voz(db)
    p = 10 ** (db / 10) * m
    caja = np.ones(241)
    num = np.convolve(p, caja, mode="same")
    den = np.convolve(m.astype(float), caja, mode="same")
    nivel = np.where(den > 20, 10 * np.log10(num / np.maximum(den, 1) + 1e-12), np.nan)
    validos = ~np.isnan(nivel)
    if validos.sum() < 10:
        return x
    objetivo = np.median(nivel[validos & m])
    nivel = np.interp(np.arange(len(nivel)), np.where(validos)[0], nivel[validos])
    gan = np.clip(objetivo - nivel, -GANANCIA_MAX, GANANCIA_MAX)
    k = np.hanning(51)
    gan = np.convolve(np.pad(gan, 25, mode="edge"), k / k.sum(), mode="valid")
    gan = np.repeat(10 ** (gan / 20), HOP)
    gan = np.concatenate([gan, np.full(max(0, len(x) - len(gan)), gan[-1])])[: len(x)]
    return x * np.convolve(gan, np.hanning(int(SR * 0.05)) / np.hanning(int(SR * 0.05)).sum(), mode="same")


BANDAS = np.array([100 * 2 ** (i / 3) for i in range(0, 21)])    # 1/3 de octava, 100 Hz - 10 kHz


def espectro_voz(x):
    """Nivel medio (dB) por tercio de octava medido solo sobre las tramas con voz."""
    m = mascara_voz(energia_db(x))
    mm = np.repeat(m, HOP)[: len(x)]
    v = x[: len(mm)][mm]
    f, P = signal.welch(v, SR, nperseg=4096)
    niveles = np.array([10 * np.log10(P[(f >= b / 2 ** (1 / 6)) & (f < b * 2 ** (1 / 6))].mean() + 1e-20)
                        for b in BANDAS])
    return niveles - niveles.mean()


def ecualizar(x, correccion):
    """FIR de fase lineal con la corrección (dB por banda) interpolada en frecuencia."""
    corr = np.clip(correccion, -EQ_MAX, EQ_MAX)
    frec = np.concatenate([[0], BANDAS, [SR / 2]])
    gan = np.concatenate([[corr[0]], corr, [corr[-1]]])
    h = signal.firwin2(2047, frec / (SR / 2), 10 ** (gan / 20))
    return signal.fftconvolve(x, h, mode="same")


def sonoridad(x):
    return pn.Meter(SR).integrated_loudness(np.stack([x, x], axis=1))


def fundidos(x, ms=15):
    n = int(SR * ms / 1000)
    x = x.copy()
    x[:n] *= np.linspace(0, 1, n)
    x[-n:] *= np.linspace(1, 0, n)
    return x


def normalizar(x):
    return x * 10 ** ((LUFS_OBJETIVO - sonoridad(x)) / 20)


def escribir(x, ruta):
    x = np.clip(x, -1, 1).astype(np.float32)
    est = np.stack([x, x], axis=1)
    filtro = f"alimiter=limit={PICO_MAX:.4f}:attack=3:release=60:level=disabled"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "pipe:0",
                    "-af", filtro, "-c:a", "pcm_s16le", "-ar", str(SR), ruta],
                   input=est.tobytes(), check=True)


# ---------------------------------------------------------------- voz clonada
ESPECTRO = os.path.join(RAIZ, "voz", "espectro_grabaciones.json")


def grabaciones_limpias():
    """Las grabaciones limpias de Eduardo: todo `audios_grabados/*.wav`, que es salida de este
    programa y nunca tiene audio clonado. (No se filtra por `audios/GENERADOS.txt`: las clonadas
    llevan los mismos nombres de subescena y vaciaban la lista.)"""
    return sorted(glob.glob(os.path.join(SALIDA, "*.wav")))


def espectro_grabaciones():
    """Espectro mediano de la voz en las grabaciones limpias; se guarda en `voz/` y se recalcula
    solo si cambia alguna grabación. Sin grabaciones se usa el espectro ya guardado: así la narración
    clonada no depende de que las grabaciones sigan en disco."""
    rutas = grabaciones_limpias()
    if not rutas:
        if os.path.exists(ESPECTRO):
            return np.array(json.load(open(ESPECTRO, encoding="utf-8"))["espectro"])
        raise SystemExit(f"No hay grabaciones limpias en {SALIDA} ni espectro guardado en {ESPECTRO}.")
    fuentes = {os.path.basename(p): os.path.getmtime(p) for p in rutas}
    if os.path.exists(ESPECTRO):
        guardado = json.load(open(ESPECTRO, encoding="utf-8"))
        if guardado.get("fuentes") == fuentes:
            return np.array(guardado["espectro"])
    e = np.median(np.stack([espectro_voz(decodificar(p)) for p in rutas]), axis=0)
    os.makedirs(os.path.dirname(ESPECTRO), exist_ok=True)
    json.dump({"fuentes": fuentes, "espectro": e.tolist()}, open(ESPECTRO, "w", encoding="utf-8"), indent=1)
    return e


def igualar_clonada(entrada, salida):
    """La voz clonada pasa por la misma cadena que las grabaciones (pasa-altas, compuerta en las
    pausas, nivelación, tono hacia su espectro mediano, sonoridad y picos), para que una subescena
    grabada y una clonada seguidas suenen al mismo micrófono; la compuerta también baja las
    respiraciones con que el modelo suele empezar cada frase, como en las grabaciones. Las pausas no
    se acortan: las de «(pausa)» las pone voz.py a propósito. Devuelve la corrección de tono (dB por banda)."""
    x = nivelar(compuerta(pasa_altas(decodificar(entrada))))
    corr = np.clip(espectro_grabaciones() - espectro_voz(x), -EQ_MAX, EQ_MAX)
    escribir(fundidos(normalizar(ecualizar(x, corr))), salida)
    return corr


# ---------------------------------------------------------------- programa
def cortes_de(i, cortes):
    return cortes.get(i, {})


INCOMPLETOS = os.path.join(SALIDA, "INCOMPLETOS.txt")   # lo escribe este programa desde audios_cortes.json


def destino(i, cortes):
    """Número de subescena del guion que contiene la grabación `i` (nombre del archivo original)."""
    g = cortes_de(i, cortes).get("guion")
    return g if g else (i if "." in i else i + ".0")


def ids_del_guion():
    """Números de subescena del guion de Word, o None si no se pudo leer."""
    try:
        if RAIZ not in sys.path:
            sys.path.insert(0, RAIZ)
        import guion
        return {s.id for e in guion.leer().values() for s in e.subescenas}
    except Exception as e:                                   # sin guion no se puede comprobar, no es fatal
        print(f"AVISO: no se pudo leer el guion para comprobar los números de subescena ({e}).")
        return None


def asignar(todos, cortes):
    """{original: subescena}. Se detiene si dos grabaciones caen en la misma subescena o si el
    número no existe en el guion: un error de nombre pondría la voz de una subescena en otra."""
    dest = {i: destino(i, cortes) for i in todos}
    por_dest = {}
    for i, d in dest.items():
        por_dest.setdefault(d, []).append(i)
    choques = {d: v for d, v in por_dest.items() if len(v) > 1}
    if choques:
        raise SystemExit("Dos grabaciones caen en la misma subescena; una sobrescribiría a la otra: " +
                         "; ".join(f"{d} <- {', '.join(v)}" for d, v in choques.items()))
    guion_ids = ids_del_guion()
    if guion_ids is not None:
        raros = {i: d for i, d in dest.items() if d not in guion_ids}
        if raros:
            raise SystemExit("Subescenas que no existen en el guion: " +
                             ", ".join(f"{i} -> {d}" for i, d in raros.items()))
    return dest


def anotar_incompletos(dest, cortes):
    """Reescribe `audios/INCOMPLETOS.txt` (`<subescena>.wav <motivo>`) con las grabaciones marcadas
    «incompleto»; sin ninguna, lo quita. Devuelve [(subescena, motivo)]."""
    lista = [(dest[i], cortes_de(i, cortes)["incompleto"]) for i in sorted(dest, key=lambda k: clave(dest[k]))
             if cortes_de(i, cortes).get("incompleto")]
    if lista:
        with open(INCOMPLETOS, "w", encoding="utf-8") as f:
            f.writelines(f"{d}.wav {motivo}\n" for d, motivo in lista)
    elif os.path.exists(INCOMPLETOS):
        os.remove(INCOMPLETOS)
    return lista


def procesar(args, solo_informe=False):
    respaldar_originales()
    cortes = json.load(open(CORTES, encoding="utf-8")) if os.path.exists(CORTES) else {}
    rutas = originales()
    todos = sorted(rutas, key=clave)
    omitidos = [i for i in todos if cortes_de(i, cortes).get("omitir")]
    todos = [i for i in todos if i not in omitidos]
    if omitidos:
        print("Originales sin salida (toma abortada o sin voz utilizable):", ", ".join(omitidos))
    dest = asignar(todos, cortes)
    por_subescena = {d: i for i, d in dest.items()}
    desconocidas = [a for a in args if a not in por_subescena]
    if desconocidas:
        raise SystemExit("Ninguna grabación contiene la subescena " + ", ".join(desconocidas) +
                         ". Con grabación: " + ", ".join(sorted(por_subescena, key=clave)))
    elegidos = [por_subescena[a] for a in args] if args else sorted(todos, key=lambda i: clave(dest[i]))
    # El espectro objetivo sale de TODOS los audios, aunque solo se reescriban algunos.
    etapa1, espectros = {}, {}
    for i in todos:
        x = decodificar(rutas[i])
        cfg = cortes_de(i, cortes)
        x = pasa_altas(x)
        if cfg.get("conservar"):
            x = conservar(x, cfg["conservar"], cfg.get("pausa_final", COLA))
        x = acortar_pausas(x, cfg.get("pausa_final", COLA))
        x = nivelar(compuerta(x))
        etapa1[i] = x
        espectros[i] = espectro_voz(x)
    objetivo = np.median(np.stack(list(espectros.values())), axis=0)
    print(f"{'original':>8} {'subescena':>9} {'dur orig':>9} {'dur nueva':>10} {'LUFS antes':>11} {'LUFS final':>11}")
    for i in elegidos:
        orig = decodificar(rutas[i])
        y = ecualizar(etapa1[i], objetivo - espectros[i])
        y = fundidos(normalizar(y))
        print(f"{i:>8} {dest[i]:>9} {len(orig) / SR:9.1f} {len(y) / SR:10.1f} {sonoridad(orig):11.1f} {sonoridad(y):11.1f}")
        if not solo_informe:
            escribir(y, os.path.join(SALIDA, dest[i] + ".wav"))
    incompletos = anotar_incompletos(dest, cortes) if not solo_informe else \
        [(dest[i], cortes_de(i, cortes)["incompleto"]) for i in dest if cortes_de(i, cortes).get("incompleto")]
    for d, motivo in incompletos:
        print(f"INCOMPLETA {d}: {motivo}")
    viejas = [os.path.basename(p) for p in grabaciones_limpias()
              if os.path.splitext(os.path.basename(p))[0] not in dest.values()]
    if viejas:
        print("AVISO: salidas sin grabación que las genere (nombre viejo; se pueden borrar):", ", ".join(viejas))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--clonada"]:
        c = igualar_clonada(sys.argv[2], sys.argv[3])
        print("tono corregido (dB, 100 Hz a 10 kHz):", " ".join(f"{v:+.1f}" for v in c))
        sys.exit()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    procesar(args, solo_informe="--informe" in sys.argv)
