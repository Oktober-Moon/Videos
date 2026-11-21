"""Congela y reanuda los renders en curso sin perder nada.

Congelar deja cada proceso quieto donde va (como pausar un video): la laptop se enfría y se libera
el procesador y la GPU, pero la memoria sigue ocupada. Al reanudar, cada render sigue en el mismo
cuadro. Se congela todo lo que cuelga de cada `render.py` (procesos de trabajo, ffmpeg y Blender).

    .venv/Scripts/python pausa_render.py --congelar
    .venv/Scripts/python pausa_render.py --reanudar
    .venv/Scripts/python pausa_render.py              # solo muestra qué procesos hay
    .venv/Scripts/python pausa_render.py --despierta  # no deja que Windows se suspenda mientras haya renders

`--despierta` hace lo que un reproductor de video: pide a Windows que no se suspenda por inactividad
(SetThreadExecutionState) mientras exista algún render, y lo suelta al terminar. No cambia la
configuración de energía; cerrar la tapa o elegir «Suspender» sí suspende.

Detener los renders (cerrarlos) también es seguro: los cuadros 3D y los clips terminados quedan
guardados, y el candado de Blender se libera solo cuando su dueño ya no existe.
"""

from __future__ import annotations

import ctypes
import json
import subprocess
import sys

ACCESO = 0x0800 | 0x1000                     # PROCESS_SUSPEND_RESUME | PROCESS_QUERY_LIMITED_INFORMATION


def procesos() -> list[dict]:
    salida = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True).stdout
    return json.loads(salida)


def de_render() -> list[dict]:
    """Cada `render.py` y todos sus descendientes. «render.py» va como palabra suelta: este mismo
    archivo se llama pausa_render.py y no debe congelarse a sí mismo."""
    import os
    import re

    todos = procesos()
    hijos: dict[int, list[dict]] = {}
    for p in todos:
        hijos.setdefault(p["ParentProcessId"], []).append(p)
    padres = {p["ProcessId"]: p["ParentProcessId"] for p in todos}
    propios, pid = set(), os.getpid()
    while pid and pid not in propios:                       # este proceso y sus ancestros
        propios.add(pid)
        pid = padres.get(pid)
    raices = [p for p in todos if p["Name"] == "python.exe" and p["ProcessId"] not in propios
              and re.search(r"(?<![\w.])render\.py\b", p["CommandLine"] or "")]
    vistos, pila = {}, list(raices)
    while pila:
        p = pila.pop()
        if p["ProcessId"] in vistos or p["ProcessId"] in propios:
            continue
        vistos[p["ProcessId"]] = p
        pila += hijos.get(p["ProcessId"], [])
    return list(vistos.values())


def _aplicar(pid: int, funcion: str) -> bool:
    k, nt = ctypes.windll.kernel32, ctypes.windll.ntdll
    h = k.OpenProcess(ACCESO, False, pid)
    if not h:
        return False
    try:
        return getattr(nt, funcion)(h) == 0
    finally:
        k.CloseHandle(h)


def despierta() -> int:
    import time

    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    k = ctypes.windll.kernel32
    k.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    print("Despierta mientras haya renders.", flush=True)
    try:
        # Entre una escena y la siguiente de una cola hay un instante sin render: se suelta solo tras
        # 3 revisiones seguidas (3 min) sin ninguno.
        vacias = 0
        while vacias < 3:
            vacias = 0 if de_render() else vacias + 1
            time.sleep(60)
    finally:
        k.SetThreadExecutionState(ES_CONTINUOUS)
    print("Ya no hay renders: Windows puede suspenderse otra vez.", flush=True)
    return 0


def main() -> int:
    if "--despierta" in sys.argv:
        return despierta()
    lista = de_render()
    if not lista:
        print("No hay renders en curso.")
        return 0
    accion = {"--congelar": "NtSuspendProcess", "--reanudar": "NtResumeProcess"}.get(sys.argv[1] if len(sys.argv) > 1 else "")
    for p in sorted(lista, key=lambda p: p["ProcessId"]):
        cmd = (p["CommandLine"] or "")[-60:]
        estado = ""
        if accion:
            estado = "ok" if _aplicar(p["ProcessId"], accion) else "SIN ACCESO"
        print(f"{p['ProcessId']:>7} {p['Name']:<14} {estado:<10} {cmd}")
    if accion:
        print(("Congelados" if "Suspend" in accion else "Reanudados") + f": {len(lista)} procesos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
