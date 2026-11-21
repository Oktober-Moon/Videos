"""Materiales hechos con texturas escaneadas (ambientCG, CC0) y cielos fotográficos (HDRI).

Las texturas están en `recursos_3d/<paquete>/` (fuentes en `recursos_3d/LEEME.txt`). Como los
modelos de `tres_d/` no tienen coordenadas UV, cada textura se proyecta desde la posición en el
mundo: plana desde arriba para pisos, en caja (las tres direcciones, con fundido) para paredes y
tejados. El relieve sale del mapa de desplazamiento con un nodo Bump: funciona sin UV, a
diferencia de los mapas de normales.
"""

from pathlib import Path

import bpy

from tres_d.base import Arbol, entrada, material, mundo_nuevo, nodos_cielo, pos_mundo

RECURSOS = Path(__file__).resolve().parent.parent / "recursos_3d"


def _imagen(a: Arbol, ruta: Path, vector, dato: bool, proyeccion: str):
    n = a.nodo("ShaderNodeTexImage")
    n.image = bpy.data.images.load(str(ruta), check_existing=True)
    if dato:
        n.image.colorspace_settings.name = "Non-Color"
    n.projection = proyeccion
    if proyeccion == "BOX":
        n.projection_blend = 0.3
    a.unir(vector, n, "Vector")
    return n


def material_pbr(nombre: str, paquete: str, tam_m: float, proyeccion: str = "FLAT", tinte_objeto: bool = False,
                 brillo: float = 1.0, relieve: float = 0.8, charcos: bool = False, sucio_abajo: bool = False,
                 extra=None):
    """Material escaneado de `paquete` (p. ej. «PavingStones119_2K-JPG»), con un mosaico de `tam_m`
    metros. `tinte_objeto` multiplica el color por el color del objeto (revoque de cada casa).
    `extra(a, p, color, rugosidad) -> (color, rugosidad)` agrega capas propias del lugar (hojas
    caídas, piedra mojada junto al agua) encima de la textura."""
    carpeta = RECURSOS / paquete

    def archivo(mapa):
        return carpeta / f"{paquete}_{mapa}.jpg"

    def hacer(a: Arbol):
        p = pos_mundo(a)
        v = a.v("SCALE", p, escala=1.0 / tam_m)
        col = (_imagen(a, archivo("Color"), v, False, proyeccion), "Color")
        if archivo("AmbientOcclusion").exists():
            ao = (_imagen(a, archivo("AmbientOcclusion"), v, True, proyeccion), "Color")
            col = a.v("MULTIPLY", col, ao)
        col = a.v("SCALE", col, escala=brillo)
        if tinte_objeto:
            info = a.nodo("ShaderNodeObjectInfo")
            col = a.v("SCALE", a.v("MULTIPLY", col, (info, "Color")), escala=1.3)
        rug = (_imagen(a, archivo("Roughness"), v, True, proyeccion), "Color")
        rug = a.separar(rug)[0]
        alto = (_imagen(a, archivo("Displacement"), v, True, proyeccion), "Color")
        alto = a.separar(alto)[0]
        fuerza = relieve
        if sucio_abajo:                                  # salpicado de la calle y humedad que sube
            _, _, z = a.separar(p)
            col = a.v("SCALE", col, escala=a.rango(z, 0.0, 1.3, 0.6, 1.0))
            q = a.v("MULTIPLY", p, (3.0, 3.0, 0.25))
            chorro, _ = a.ruido(q, 1.0, 2.0)
            col = a.v("SCALE", col, escala=a.rango(chorro, 0.55, 0.75, 1.0, 0.85))
        if charcos:                                      # agua encima de las piedras: oscurece y refleja
            charco_f, _ = a.ruido(p, 0.32, 3.0, 0.55)
            charco = a.rango(charco_f, 0.50, 0.58)
            col = a.v("SCALE", col, escala=a.rango(charco, 0, 1, 0.85, 0.5))
            juntas = a.rango(alto, 0.0, 0.45, 1.0, 0.0)            # el agua se queda en las juntas
            mojado = a.m("MAXIMUM", charco, a.m("MULTIPLY", juntas, 0.8))
            rug = a.m("ADD", a.m("MULTIPLY", rug, a.m("SUBTRACT", 1.0, mojado)), a.m("MULTIPLY", mojado, 0.03))
            rug = a.m("MULTIPLY", rug, 0.7)                        # toda la calle está húmeda
            fuerza = a.rango(charco, 0, 1, relieve, 0.05)
        if extra is not None:
            col, rug = extra(a, p, col, rug)
        normal = a.bump(alto, fuerza, tam_m * 0.02)
        return a.bsdf(col, rug, normal=normal)
    return material(nombre, hacer)


def hdri(escena, paquete: str, fuerza: float = 1.0, giro_grados: float = 0.0, fondo_camara: str | None = None):
    """Cielo fotográfico de 360°: es el fondo y, a la vez, la luz ambiente de toda la escena.

    Con `fondo_camara` (un cielo de `base.CIELOS`), la cámara ve ese degradado y la foto solo
    ilumina y se refleja: sirve donde el cielo queda a la vista y la foto (una plaza con casas) no
    corresponde al lugar."""
    import math
    exr = next((RECURSOS / paquete).glob("*_HDR.exr"))
    mundo, nt, salida = mundo_nuevo(escena, paquete)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapeo = nt.nodes.new("ShaderNodeMapping")
    mapeo.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(giro_grados))
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(str(exr), check_existing=True)
    fondo = nt.nodes.new("ShaderNodeBackground")
    entrada(fondo, "Strength").default_value = fuerza
    nt.links.new(coord.outputs["Generated"], mapeo.inputs["Vector"])
    nt.links.new(mapeo.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], fondo.inputs["Color"])
    if fondo_camara is None:
        nt.links.new(fondo.outputs["Background"], salida.inputs["Surface"])
        return mundo
    camino = nt.nodes.new("ShaderNodeLightPath")
    mezcla = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(camino.outputs["Is Camera Ray"], mezcla.inputs[0])
    nt.links.new(fondo.outputs["Background"], mezcla.inputs[1])
    nt.links.new(nodos_cielo(nt, fondo_camara).outputs[0], mezcla.inputs[2])
    nt.links.new(mezcla.outputs[0], salida.inputs["Surface"])
    return mundo
