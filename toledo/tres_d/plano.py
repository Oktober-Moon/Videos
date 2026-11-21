"""Renderiza un plano 3D dentro de Blender. Lo llama `escenas/plano3d.py`; no hace falta correrlo a mano.

    blender -b -P tres_d/plano.py -- pedido.json      (sin --factory-startup: MPFB se carga al iniciar)

El pedido (JSON) trae: plano (nombre de la función), modulo (su archivo de planos: `planos` para la
escena 1, `planos_e03`… para las demás), duracion (s), params (los del plano), salida (carpeta de los
PNG) y cuadros (lista de cuadros sueltos, o null para todos los que falten).
"""

import importlib
import json
import math
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import bpy  # noqa: E402

from tres_d import base  # noqa: E402

FPS = 30


def main():
    pedido = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))
    salida = Path(pedido["salida"])
    salida.mkdir(parents=True, exist_ok=True)
    cuadros = max(1, math.ceil(pedido["duracion"] * FPS))
    escena = base.escena_nueva()
    planos = importlib.import_module(f"tres_d.{pedido.get('modulo', 'planos')}")
    ajustes = getattr(planos, pedido["plano"])(escena, cuadros, FPS, **pedido.get("params", {})) or {}
    base.preparar_render(escena, cuadros, FPS, motor=pedido.get("motor", "eevee"), **ajustes)
    escena.render.resolution_percentage = int(pedido.get("porcentaje", 100))   # pruebas rápidas
    if pedido.get("cuadros"):
        for f in pedido["cuadros"]:
            escena.frame_set(int(f))
            escena.render.filepath = str(salida / f"f_{int(f):04d}.png")
            bpy.ops.render.render(write_still=True)
    else:
        escena.render.use_overwrite = False                       # sigue donde iba si se cortó
        escena.render.filepath = str(salida / "f_####")
        bpy.ops.render.render(animation=True)


main()
