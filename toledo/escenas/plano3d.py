"""Planos 3D (Blender) vistos desde las subescenas como si fueran clips de video.

Cada plano se renderiza una vez a PNG en `salida/3d/<plano>_<huella>/` y luego se lee cuadro por
cuadro. La huella sale del código de `tres_d/` que usa ese plano y de sus parámetros (incluida su duración):
si nada de eso cambia, no se vuelve a renderizar; si cambia, se renderiza en una carpeta nueva.
Pedir un cuadro que falta lo renderiza solo a él (para los fotogramas de revisión); `asegurar()`
renderiza todos los que falten de una vez (para el video).

Blender corre de a uno: dos procesos a la vez se quedarían sin memoria en la GPU de 4 GB. Se abre sin
--factory-startup porque los planos con personas necesitan la extensión MPFB, que se carga al iniciar.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
SALIDA3D = RAIZ / "salida" / "3d"
FPS = 30
BLENDER = Path(os.environ.get("BLENDER") or Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Blender-5.3" /
               "ProgramFiles64Folder" / "Blender Foundation" / "Blender 5.3" / "blender.exe")
CANDADO = SALIDA3D / ".blender.lock"


TRES_D = RAIZ / "tres_d"


def modulo_del_plano(plano: str) -> str:
    """En qué archivo de planos está la función del plano: `tres_d/planos.py` (escena 1) o el de su
    escena (`tres_d/planos_e03.py`…). Un archivo por escena deja escribir varias escenas a la vez
    sin que se pisen; los nombres de plano no se repiten entre archivos."""
    import re

    hallados = [p.stem for p in sorted(TRES_D.glob("planos*.py"))
                if re.search(rf"^def {re.escape(plano)}\(", p.read_text(encoding="utf-8"), re.M)]
    if len(hallados) != 1:
        raise RuntimeError(f"El plano {plano} está en {len(hallados)} archivos de planos: {hallados}")
    return hallados[0]


def _importados(fuente: str) -> dict[str, str]:
    """{alias: módulo} de los `from tres_d import x as y` de un archivo."""
    import ast

    return {(a.asname or a.name): a.name for n in ast.parse(fuente).body
            if isinstance(n, ast.ImportFrom) and n.module == "tres_d" for a in n.names}


def _codigo_del_plano(plano: str) -> list[str]:
    """El código del que depende un plano: su función, las funciones auxiliares de su archivo de
    planos que llama (también sus dependencias) y los módulos de tres_d/ que usan, con los que esos
    importan a su vez. Así, agregar o cambiar otro plano no obliga a volver a renderizar este."""
    import ast
    import re

    fuente = (TRES_D / f"{modulo_del_plano(plano)}.py").read_text(encoding="utf-8")
    funciones = {n.name: ast.get_source_segment(fuente, n) for n in ast.parse(fuente).body if isinstance(n, ast.FunctionDef)}
    vistas, pendientes = [], [plano]
    while pendientes:
        f = pendientes.pop()
        if f in vistas:
            continue
        vistas.append(f)
        pendientes += [g for g in funciones if g not in vistas and re.search(rf"\b{g}\(", funciones[f])]
    codigo = [funciones[f] for f in sorted(vistas)]
    alias = _importados(fuente)
    modulos, pendientes = set(), [m for a, m in alias.items() if any(f"{a}." in funciones[f] for f in vistas)]
    while pendientes:
        m = pendientes.pop()
        if m in modulos or not (TRES_D / f"{m}.py").exists():
            continue
        modulos.add(m)
        pendientes += list(_importados((TRES_D / f"{m}.py").read_text(encoding="utf-8")).values())
    codigo += [(TRES_D / f"{m}.py").read_text(encoding="utf-8") for m in sorted(modulos)]
    codigo.append((TRES_D / "plano.py").read_text(encoding="utf-8"))
    return codigo


def _huella(plano: str, duracion: float, params: dict) -> str:
    h = hashlib.sha1()
    for texto in _codigo_del_plano(plano):
        h.update(texto.encode("utf-8"))
    h.update(json.dumps({"plano": plano, "duracion": duracion, "params": params}, sort_keys=True).encode())
    return h.hexdigest()[:10]


def _inicio(pid: int) -> int | None:
    """Cuándo arrancó un proceso (FILETIME), o None si ya no existe. Con el número de proceso solo no
    basta: tras reiniciar la computadora, Windows reparte los números otra vez y uno nuevo puede
    tener el del dueño viejo del candado. (Sin señales: en Windows os.kill(pid, 0) lo terminaría.)"""
    import ctypes

    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)                       # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return None
    try:
        codigo = ctypes.c_ulong()
        if not k.GetExitCodeProcess(h, ctypes.byref(codigo)) or codigo.value != 259:     # STILL_ACTIVE
            return None
        t = [ctypes.c_ulonglong() for _ in range(4)]
        if not k.GetProcessTimes(h, *[ctypes.byref(x) for x in t]):
            return None
        return t[0].value
    finally:
        k.CloseHandle(h)


def _vivo(pid: int, inicio: int | None = None) -> bool:
    actual = _inicio(pid)
    return actual is not None and (inicio is None or actual == inicio)


class _Candado:
    """Un solo Blender a la vez. El candado guarda el número de proceso de quien lo tiene y cuándo
    arrancó; se considera abandonado solo si ese proceso ya no existe (un plano largo en Cycles
    puede pasar de diez horas, y un render congelado sigue vivo)."""

    def __enter__(self):
        SALIDA3D.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                self.fd = os.open(CANDADO, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self.fd, f"{os.getpid()} {_inicio(os.getpid()) or 0}".encode())
                return self
            except FileExistsError:
                try:                                                    # pudo soltarse entre tanto
                    partes = (CANDADO.read_text() or "0").split()
                    dueno, inicio = int(partes[0]), (int(partes[1]) or None) if len(partes) > 1 else None
                    viejo = time.time() - CANDADO.stat().st_mtime > 60
                except (OSError, ValueError):
                    dueno, inicio, viejo = 0, None, False
                if viejo and (not dueno or not _vivo(dueno, inicio)):    # quedó de un proceso muerto
                    CANDADO.unlink(missing_ok=True)
                time.sleep(2.0)

    def __exit__(self, *exc):
        os.close(self.fd)
        CANDADO.unlink(missing_ok=True)


class Plano3D:
    def __init__(self, plano: str, duracion: float, motor: str = "eevee", **params):
        self.plano = plano
        self.duracion = math.ceil(duracion * 2) / 2                         # de medio en medio segundo
        self.params = params
        self.motor = motor                                                  # «eevee» o «cycles»
        self.n = max(1, math.ceil(self.duracion * FPS))
        clave = dict(params, _motor=motor) if motor != "eevee" else params
        self.dir = SALIDA3D / f"{plano}_{_huella(plano, self.duracion, clave)}"
        self._ultimo: tuple[int, np.ndarray] | None = None

    def ruta(self, f: int) -> Path:
        return self.dir / f"f_{f:04d}.png"

    def faltan(self) -> list[int]:
        return [f for f in range(1, self.n + 1) if not self.ruta(f).exists()]

    def renderizar(self, cuadros: list[int] | None = None) -> None:
        if not BLENDER.exists():
            raise RuntimeError(f"No está Blender en {BLENDER} (o en la variable de entorno BLENDER).")
        with _Candado():
            if cuadros is not None:
                cuadros = [f for f in cuadros if not self.ruta(f).exists()]
                if not cuadros:
                    return
            self.dir.mkdir(parents=True, exist_ok=True)
            pedido = self.dir / "pedido.json"
            pedido.write_text(json.dumps({"plano": self.plano, "modulo": modulo_del_plano(self.plano),
                                          "duracion": self.duracion, "params": self.params,
                                          "salida": str(self.dir), "cuadros": cuadros, "motor": self.motor},
                                         indent=1), encoding="utf-8")
            r = subprocess.run([str(BLENDER), "-b", "-P", str(RAIZ / "tres_d" / "plano.py"),
                                "--", str(pedido)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            faltan = [f for f in (cuadros or range(1, self.n + 1)) if not self.ruta(f).exists()]
            if r.returncode != 0 or faltan:
                cola = "\n".join((r.stdout + r.stderr).splitlines()[-25:])
                raise RuntimeError(f"Blender no terminó el plano {self.plano} (faltan {len(faltan)} cuadros):\n{cola}")

    def asegurar(self) -> None:
        """Renderiza todo lo que falte y borra las versiones viejas de este mismo plano. Va por tandas
        de unos 10 a 15 minutos (300 cuadros en Eevee, 12 en Cycles) y suelta el candado entre una y
        otra, para que un fotograma de revisión pedido mientras tanto no espere horas."""
        faltan = self.faltan()
        tanda = 300 if self.motor == "eevee" else 12
        for i in range(0, len(faltan), tanda):
            self.renderizar(faltan[i:i + tanda])
            time.sleep(3.0)                                                 # deja pasar a quien espera
        for viejo in SALIDA3D.glob(f"{self.plano}_*"):
            if viejo.is_dir() and viejo != self.dir and len(viejo.name) == len(self.dir.name) and self._misma_toma(viejo):
                shutil.rmtree(viejo, ignore_errors=True)

    def _misma_toma(self, viejo: Path) -> bool:
        """Si una carpeta vieja es una versión anterior de esta misma toma (mismos parámetros, con
        otro código o duración). Un mismo plano usado con otros parámetros en otra subescena es otra
        toma y se conserva; sin pedido.json no se sabe y también se conserva."""
        try:
            pedido = json.loads((viejo / "pedido.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        return pedido.get("params") == json.loads(json.dumps(self.params))

    def cuadro(self, t: float) -> np.ndarray:
        f = min(self.n, max(1, int(round(t * FPS)) + 1))
        if self._ultimo is not None and self._ultimo[0] == f:
            return self._ultimo[1].copy()
        if not self.ruta(f).exists():
            self.renderizar([f])
        img = self._leer(f)
        self._ultimo = (f, img)
        return img.copy()

    def _leer(self, f: int) -> np.ndarray:
        """Que el archivo del cuadro exista no quiere decir que esté completo: otro clip que comparte
        el plano puede tener a Blender escribiéndolo en ese instante («image file is truncated»). Se
        reintenta un minuto; si sigue roto, quedó de un Blender cortado y se rehace."""
        ruta = self.ruta(f)
        for intento in range(31):
            try:
                with Image.open(ruta) as im:
                    return np.asarray(im.convert("RGB"), np.float32) / 255
            except (OSError, SyntaxError, ValueError):
                if intento < 30:
                    time.sleep(2.0)
        ruta.unlink(missing_ok=True)
        self.renderizar([f])
        with Image.open(ruta) as im:
            return np.asarray(im.convert("RGB"), np.float32) / 255
