"""Prueba de estilo 2: animación 3D realista hecha en Blender (Eevee, en la GPU).

Calle del casco viejo de Friburgo a la hora azul, después de la lluvia: empedrado mojado que
refleja los faroles y las vitrinas, fachadas de revoque con ventanas, toldos y tejados, catenaria
y un tranvía azul y verde que llega y frena frente a la cámara. Todo se construye aquí con código
(cajas, materiales procedurales y luces); no hay modelos descargados.

Uso (desde la raíz del proyecto):
  blender -b --factory-startup -P pruebas_estilo/estilo2_blender.py -- pruebas_estilo prueba 200
  blender -b --factory-startup -P pruebas_estilo/estilo2_blender.py -- pruebas_estilo todo
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
AQUI = Path(ARGS[0]).resolve()
MODO = ARGS[1] if len(ARGS) > 1 else "prueba"
sys.path.insert(0, str(AQUI))
import calle_datos as C  # noqa: E402

SALIDA = AQUI.parent / "revision" / "estilos" / "blender"
SALIDA.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- utilidades

def poner(obj, attr, valor) -> bool:
    """Asigna si la versión de Blender tiene ese ajuste (los nombres cambian entre versiones)."""
    try:
        setattr(obj, attr, valor)
        return True
    except (AttributeError, TypeError, ValueError):
        return False


def entrada(nodo, *nombres):
    for n in nombres:
        if n in nodo.inputs:
            return nodo.inputs[n]
    raise KeyError(f"{nodo.name}: ninguna entrada {nombres}")


def es_socket(v) -> bool:
    return isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], bpy.types.Node)


class Arbol:
    """Atajos para armar árboles de nodos de material sin repetir links.new por todos lados."""

    def __init__(self, mat):
        poner(mat, "use_nodes", True)
        self.nt = mat.node_tree
        self.salida = next(n for n in self.nt.nodes if n.type == "OUTPUT_MATERIAL")
        for n in list(self.nt.nodes):
            if n.type == "BSDF_PRINCIPLED":
                self.nt.nodes.remove(n)

    def nodo(self, tipo, **props):
        n = self.nt.nodes.new(tipo)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def unir(self, origen, destino_nodo, destino):
        self.nt.links.new(origen[0].outputs[origen[1]], destino_nodo.inputs[destino])

    def dar(self, nodo, destino, v):
        if es_socket(v):
            self.unir(v, nodo, destino)
        elif v is not None:
            nodo.inputs[destino].default_value = v

    def m(self, op, a, b=None):
        n = self.nodo("ShaderNodeMath", operation=op)
        self.dar(n, 0, a)
        self.dar(n, 1, b)
        return (n, 0)

    def v(self, op, a, b=None, escala=None):
        n = self.nodo("ShaderNodeVectorMath", operation=op)
        self.dar(n, 0, a)
        self.dar(n, 1, b)
        if escala is not None:
            self.dar(n, "Scale", escala)
        return (n, 0)

    def mezcla(self, a, b, f):
        """a·(1−f) + b·f para colores o vectores."""
        return self.v("ADD", a, self.v("SCALE", self.v("SUBTRACT", b, a), escala=f))

    def rango(self, x, de0, de1, a0=0.0, a1=1.0):
        n = self.nodo("ShaderNodeMapRange")
        self.dar(n, 0, x)
        for i, val in enumerate((de0, de1, a0, a1), start=1):
            n.inputs[i].default_value = val
        return (n, 0)

    def separar(self, vec):
        n = self.nodo("ShaderNodeSeparateXYZ")
        self.unir(vec, n, 0)
        return (n, 0), (n, 1), (n, 2)

    def ruido(self, vec, escala, detalle=4.0, rugosidad=0.5):
        n = self.nodo("ShaderNodeTexNoise")
        if vec is not None:
            self.unir(vec, n, "Vector")
        entrada(n, "Scale").default_value = escala
        entrada(n, "Detail").default_value = detalle
        entrada(n, "Roughness").default_value = rugosidad
        return (n, "Fac"), (n, "Color")

    def bsdf(self, color, rug, metal=0.0, coat=0.0, emision=None, fuerza=0.0, normal=None, especular=None):
        b = self.nodo("ShaderNodeBsdfPrincipled")
        self.dar(b, "Base Color", color if es_socket(color) else (*color, 1.0))
        self.dar(b, "Roughness", rug)
        self.dar(b, "Metallic", metal)
        if coat:
            self.dar(b, entrada(b, "Coat Weight", "Clearcoat").name, coat)
        if emision is not None:
            sock = entrada(b, "Emission Color", "Emission").name
            self.dar(b, sock, emision if es_socket(emision) else (*emision, 1.0))
            self.dar(b, "Emission Strength", fuerza)
        if especular is not None:
            self.dar(b, entrada(b, "Specular IOR Level", "Specular").name, especular)
        if normal is not None:
            self.unir(normal, b, "Normal")
        return (b, 0)

    def mezclar_shader(self, a, b, f):
        n = self.nodo("ShaderNodeMixShader")
        self.dar(n, 0, f)
        self.unir(a, n, 1)
        self.unir(b, n, 2)
        return (n, 0)

    def bump(self, altura, fuerza, distancia):
        n = self.nodo("ShaderNodeBump")
        self.unir(altura, n, "Height")
        self.dar(n, "Strength", fuerza)
        self.dar(n, "Distance", distancia)
        return (n, "Normal")

    def final(self, shader, donde="Surface"):
        self.unir(shader, self.salida, donde)


def pos_mundo(a: Arbol):
    return (a.nodo("ShaderNodeNewGeometry"), "Position")


def coord_objeto(a: Arbol):
    return (a.nodo("ShaderNodeTexCoord"), "Object")


def material(nombre, construir):
    mat = bpy.data.materials.new(nombre)
    a = Arbol(mat)
    a.final(construir(a))
    return mat


def simple(nombre, color, rug=0.5, metal=0.0, coat=0.0, emision=None, fuerza=0.0):
    return material(nombre, lambda a: a.bsdf(color, rug, metal, coat, emision, fuerza))


# --------------------------------------------------------------------------- materiales

def mat_adoquin():
    def hacer(a):
        p = pos_mundo(a)
        # leve deformación para que las piedras no queden en cuadrícula perfecta
        _, col = a.ruido(p, 2.2, 3.0)
        p2 = a.v("ADD", p, a.v("SCALE", a.v("SUBTRACT", col, (0.5, 0.5, 0.5)), escala=0.05))
        lad = a.nodo("ShaderNodeTexBrick", offset=0.5)
        a.unir(p2, lad, "Vector")
        for k, v in {"Color1": (0.34, 0.33, 0.31, 1), "Color2": (0.16, 0.155, 0.15, 1),
                     "Mortar": (0.07, 0.068, 0.065, 1), "Scale": 1.0, "Mortar Size": 0.016,
                     "Mortar Smooth": 0.45, "Bias": 0.0, "Brick Width": 0.21, "Row Height": 0.125}.items():
            entrada(lad, k).default_value = v
        junta = (lad, "Fac")
        color = (lad, "Color")
        # charcos: manchas grandes donde el agua quedó encima de las piedras
        charco_f, _ = a.ruido(p, 0.32, 3.0, 0.55)
        charco = a.rango(charco_f, 0.50, 0.58)
        grano_f, _ = a.ruido(p, 38.0, 6.0, 0.6)
        color = a.v("SCALE", color, escala=a.rango(grano_f, 0.3, 0.7, 0.8, 1.15))
        color = a.v("SCALE", color, escala=a.rango(charco, 0, 1, 1.0, 0.55))
        rug = a.m("ADD", a.rango(charco, 0, 1, 0.34, 0.03), a.m("MULTIPLY", junta, 0.35))
        altura = a.m("ADD", a.m("SUBTRACT", 1.0, junta), a.m("MULTIPLY", grano_f, 0.25))
        normal = a.bump(altura, a.rango(charco, 0, 1, 0.55, 0.05), 0.02)
        return a.bsdf(color, rug, normal=normal)
    return material("adoquin", hacer)


def mat_acera():
    def hacer(a):
        p = pos_mundo(a)
        q = a.v("MULTIPLY", p, (1.0, 1.0, 1.0))
        lad = a.nodo("ShaderNodeTexBrick", offset=0.0)
        a.unir(q, lad, "Vector")
        for k, v in {"Color1": (0.42, 0.41, 0.40, 1), "Color2": (0.36, 0.355, 0.35, 1),
                     "Mortar": (0.2, 0.2, 0.19, 1), "Scale": 1.0, "Mortar Size": 0.008,
                     "Brick Width": 0.6, "Row Height": 0.6}.items():
            entrada(lad, k).default_value = v
        mancha, _ = a.ruido(p, 0.9, 4.0)
        color = a.v("SCALE", (lad, "Color"), escala=a.rango(mancha, 0.3, 0.7, 0.7, 1.05))
        rug = a.rango(mancha, 0.35, 0.65, 0.12, 0.5)
        normal = a.bump(a.m("SUBTRACT", 1.0, (lad, "Fac")), 0.3, 0.01)
        return a.bsdf(color, rug, normal=normal)
    return material("acera", hacer)


def mat_fachada():
    """Revoque: el color de cada casa sale del color del objeto (Object Info), con suciedad
    abajo, manchas de humedad y textura de revoque en relieve."""
    def hacer(a):
        info = a.nodo("ShaderNodeObjectInfo")
        p = pos_mundo(a)
        _, _, z = a.separar(p)
        mancha, _ = a.ruido(p, 0.6, 5.0, 0.6)
        fino, _ = a.ruido(p, 55.0, 4.0, 0.6)
        color = a.v("SCALE", (info, "Color"), escala=a.rango(mancha, 0.3, 0.75, 0.78, 1.06))
        color = a.v("SCALE", color, escala=a.rango(z, 0.0, 1.4, 0.62, 1.0))       # salpicado de la calle
        # chorreado: franjas verticales más oscuras bajo las ventanas
        q = a.v("MULTIPLY", p, (3.0, 3.0, 0.25))
        chorro, _ = a.ruido(q, 1.0, 2.0)
        color = a.v("SCALE", color, escala=a.rango(chorro, 0.55, 0.75, 1.0, 0.86))
        normal = a.bump(fino, 0.12, 0.01)
        return a.bsdf(color, 0.86, normal=normal, especular=0.3)
    return material("fachada", hacer)


def mat_tejado():
    def hacer(a):
        p = pos_mundo(a)
        x, y, z = a.separar(p)
        comb = a.nodo("ShaderNodeCombineXYZ")
        a.unir(y, comb, 0)
        a.unir(a.m("ADD", x, z), comb, 1)
        lad = a.nodo("ShaderNodeTexBrick", offset=0.5)
        a.unir((comb, 0), lad, "Vector")
        for k, v in {"Color1": (0.30, 0.10, 0.07, 1), "Color2": (0.20, 0.07, 0.05, 1),
                     "Mortar": (0.06, 0.03, 0.02, 1), "Scale": 1.0, "Mortar Size": 0.012,
                     "Brick Width": 0.24, "Row Height": 0.18}.items():
            entrada(lad, k).default_value = v
        musgo, _ = a.ruido(p, 0.8, 4.0)
        color = a.mezcla((lad, "Color"), (0.10, 0.12, 0.07), a.rango(musgo, 0.55, 0.75, 0.0, 0.6))
        normal = a.bump(a.m("SUBTRACT", 1.0, (lad, "Fac")), 0.6, 0.03)
        return a.bsdf(color, 0.45, normal=normal)                # tejas aún mojadas
    return material("tejado", hacer)


def mat_vidrio(nombre, luz=None, fuerza=0.0):
    def hacer(a):
        p = coord_objeto(a)
        if luz is None:
            return a.bsdf((0.012, 0.014, 0.018), 0.04, especular=0.6)
        # interior encendido: la luz no es pareja (lámparas, cortinas)
        f, _ = a.ruido(p, 1.6, 2.0)
        emis = a.v("SCALE", luz, escala=a.rango(f, 0.3, 0.7, 0.45, 1.25))
        return a.bsdf((0.02, 0.02, 0.02), 0.05, emision=emis, fuerza=fuerza, especular=0.6)
    return material(nombre, hacer)


def mat_toldo():
    def hacer(a):
        info = a.nodo("ShaderNodeObjectInfo")
        p = pos_mundo(a)
        _, y, _ = a.separar(p)
        raya = a.m("GREATER_THAN", a.m("FRACT", a.m("MULTIPLY", y, 2.2)), 0.5)
        color = a.mezcla((0.85, 0.83, 0.78), (info, "Color"), raya)
        return a.bsdf(color, 0.7)
    return material("toldo", hacer)


def mat_tranvia(nombre: str, largo: float, frente: bool):
    """Pintura azul con el frente verde (como los Urbos de Friburgo), banda de ventanas con
    parantes, franja plateada, faldón oscuro abajo. Todo con la posición local del tramo."""
    def hacer(a):
        p = coord_objeto(a)
        _, y, z = a.separar(p)
        mitad = largo / 2
        banda = a.m("MULTIPLY", a.m("GREATER_THAN", z, -0.18), a.m("LESS_THAN", z, 1.08))
        parante = a.m("GREATER_THAN", a.m("FRACT", a.m("MULTIPLY", a.m("ADD", y, 0.3), 1 / 1.7)), 0.12)
        vidrio = a.m("MULTIPLY", banda, parante)
        if frente:
            # parabrisas grande en el frente (y local negativa), más alto que las ventanas
            zona = a.m("LESS_THAN", y, -mitad + 0.55)
            parab = a.m("MULTIPLY", zona, a.m("MULTIPLY", a.m("GREATER_THAN", z, -0.55), a.m("LESS_THAN", z, 1.12)))
            vidrio = a.m("MAXIMUM", vidrio, parab)
        franja = a.m("MULTIPLY", a.m("GREATER_THAN", z, -0.36), a.m("LESS_THAN", z, -0.26))
        falda = a.m("LESS_THAN", z, -1.22)
        azul, verde = (0.010, 0.07, 0.32), (0.0, 0.26, 0.11)
        if frente:
            g = a.m("MULTIPLY", a.rango(y, -mitad + 0.3, -mitad + 2.6, 1.0, 0.0), a.m("LESS_THAN", z, -0.18))
            pintura_c = a.mezcla(azul, verde, g)
        else:
            pintura_c = azul
        pintura = a.bsdf(pintura_c, 0.28, coat=1.0)
        plata = a.bsdf((0.75, 0.76, 0.78), 0.25, metal=1.0)
        oscuro = a.bsdf((0.025, 0.025, 0.028), 0.55)
        # Vidrio de verdad: casi todo transparente (se ve el interior iluminado) y un reflejo
        # que crece en ángulo rasante, como en cualquier ventana (Fresnel).
        fres = a.nodo("ShaderNodeFresnel")
        fres.inputs["IOR"].default_value = 1.5
        transp = (a.nodo("ShaderNodeBsdfTransparent"), 0)
        brillo = a.bsdf((0.01, 0.01, 0.012), 0.02, especular=0.8)
        cristal = a.mezclar_shader(transp, brillo, a.m("ADD", a.m("MULTIPLY", (fres, 0), 0.85), 0.06))
        # por dentro (caras de atrás) las paredes son un panel claro, no pintura azul
        interior = a.bsdf((0.62, 0.62, 0.58), 0.6)
        reves = (a.nodo("ShaderNodeNewGeometry"), "Backfacing")
        s = a.mezclar_shader(pintura, plata, franja)
        s = a.mezclar_shader(s, oscuro, falda)
        s = a.mezclar_shader(s, interior, reves)
        return a.mezclar_shader(s, cristal, vidrio)
    mat = material(nombre, hacer)
    poner(mat, "use_transparent_shadow", True)               # la luz de adentro sale por las ventanas
    return mat


def mat_vitrina():
    """Vitrina encendida: estantes con borde iluminado, objetos a contraluz y focos arriba; el tono
    cambia de una tienda a otra (Object Info › Random)."""
    def hacer(a):
        p = pos_mundo(a)
        info = a.nodo("ShaderNodeObjectInfo")
        _, _, z = a.separar(p)
        estante = a.m("GREATER_THAN", a.m("FRACT", a.m("MULTIPLY", a.m("SUBTRACT", z, 1.0), 1 / 0.62)), 0.9)
        # productos: «ladrillos» de ancho variable sobre cada estante, cada uno de su color
        x, y, _ = a.separar(p)
        plano = a.nodo("ShaderNodeCombineXYZ")
        a.unir(a.m("ADD", x, y), plano, 0)
        a.unir(a.m("SUBTRACT", z, 1.0), plano, 1)
        prod = a.nodo("ShaderNodeTexBrick", offset=0.37, offset_frequency=1)
        a.unir((plano, 0), prod, "Vector")
        for k, v in {"Color1": (0.55, 0.12, 0.08, 1), "Color2": (0.12, 0.25, 0.45, 1), "Mortar": (1, 1, 1, 1),
                     "Scale": 1.0, "Mortar Size": 0.05, "Mortar Smooth": 0.1, "Bias": 0.0,
                     "Brick Width": 0.23, "Row Height": 0.62}.items():
            entrada(prod, k).default_value = v
        hueco = (prod, "Fac")
        en_estante = a.m("LESS_THAN", a.m("FRACT", a.m("MULTIPLY", a.m("SUBTRACT", z, 1.0), 1 / 0.62)), 0.62)
        cosas = a.m("MULTIPLY", a.m("SUBTRACT", 1.0, hueco), en_estante)
        arriba = a.rango(z, 2.3, 3.4)
        brillo = a.m("ADD", a.m("ADD", 0.16, a.m("MULTIPLY", arriba, 0.5)), a.m("MULTIPLY", estante, 0.35))
        tinte = a.mezcla((1.0, 0.60, 0.30), (0.95, 0.88, 0.78), (info, "Random"))
        fondo_c = a.v("SCALE", tinte, escala=brillo)
        prod_c = a.v("SCALE", a.v("MULTIPLY", (prod, "Color"), tinte), escala=a.m("ADD", 0.25, a.m("MULTIPLY", arriba, 0.3)))
        emis = a.mezcla(fondo_c, prod_c, cosas)
        return a.bsdf((0.01, 0.01, 0.01), 0.04, emision=emis, fuerza=1.3, especular=0.6)
    return material("vitrina", hacer)


def mat_cielo_mundo(escena):
    """Cielo de la hora azul: degradado de azul profundo a un horizonte rosado, más cálido hacia el
    fondo de la calle (donde se acaba de poner el sol), y neblina muy tenue en el aire."""
    mundo = bpy.data.worlds.new("hora_azul")
    escena.world = mundo
    poner(mundo, "use_nodes", True)
    nt = mundo.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_WORLD":
            nt.nodes.remove(n)
    salida = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(sep.outputs[2], rampa.inputs[0])
    els = rampa.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.12, 0.13, 0.27, 1)          # horizonte
    els[1].position, els[1].color = 1.0, (0.010, 0.020, 0.065, 1)       # cenit azul profundo
    e = els.new(0.12)
    e.color = (0.04, 0.07, 0.22, 1)
    e = els.new(0.35)
    e.color = (0.02, 0.04, 0.15, 1)
    # resplandor hacia +y (fondo de la calle)
    punto = nt.nodes.new("ShaderNodeVectorMath")
    punto.operation = "DOT_PRODUCT"
    nt.links.new(coord.outputs["Generated"], punto.inputs[0])
    punto.inputs[1].default_value = (0.0, 1.0, 0.0)
    brillo = nt.nodes.new("ShaderNodeMapRange")
    nt.links.new(punto.outputs["Value"], brillo.inputs[0])
    brillo.inputs[1].default_value, brillo.inputs[2].default_value = 0.6, 1.0
    brillo.inputs[3].default_value, brillo.inputs[4].default_value = 0.0, 0.22
    tibio = nt.nodes.new("ShaderNodeVectorMath")
    tibio.operation = "SCALE"
    tibio.inputs[0].default_value = (0.9, 0.45, 0.25)
    nt.links.new(brillo.outputs[0], tibio.inputs["Scale"])
    suma = nt.nodes.new("ShaderNodeVectorMath")
    suma.operation = "ADD"
    nt.links.new(rampa.outputs["Color"], suma.inputs[0])
    nt.links.new(tibio.outputs[0], suma.inputs[1])
    fondo = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(suma.outputs[0], fondo.inputs["Color"])
    fondo.inputs["Strength"].default_value = 0.30            # hora azul: el cielo ya alumbra poco
    nt.links.new(fondo.outputs[0], salida.inputs["Surface"])


def mat_neblina():
    """Neblina tenue en el aire de la calle: hace visibles los conos de luz de los faroles y
    aleja el fondo. Va en un volumen (caja) y no en el mundo, porque los volúmenes de objeto
    reciben la luz de las lámparas en Eevee."""
    def hacer(a):
        n = a.nodo("ShaderNodeVolumeScatter")
        n.inputs["Density"].default_value = 0.0035
        entrada(n, "Anisotropy").default_value = 0.5
        n.inputs["Color"].default_value = (0.70, 0.76, 0.90, 1)
        return (n, 0)
    mat = bpy.data.materials.new("neblina")
    a = Arbol(mat)
    a.final(hacer(a), "Volume")
    return mat


# --------------------------------------------------------------------------- geometría

COLECCION = None


def caja(bm, centro, tam, mat=0):
    M = Matrix.Translation(Vector(centro)) @ Matrix.Diagonal((tam[0], tam[1], tam[2], 1.0))
    r = bmesh.ops.create_cube(bm, size=1.0, matrix=M)
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mat
    return r["verts"]


def barra(bm, p1, p2, radio, mat=0, lados=8):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    M = Matrix.Translation((p1 + p2) / 2) @ rot
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=lados, radius1=radio, radius2=radio,
                              depth=d.length, matrix=M)
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mat


def objeto(nombre, bm, mats, color=None, padre=None, suave=False):
    me = bpy.data.meshes.new(nombre)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    if suave:
        for pol in me.polygons:
            pol.use_smooth = True
    ob = bpy.data.objects.new(nombre, me)
    COLECCION.objects.link(ob)
    if color is not None:
        ob.color = (*color, 1.0)
    if padre is not None:
        ob.parent = padre
    return ob


def vacio(nombre, pos=(0, 0, 0), padre=None):
    ob = bpy.data.objects.new(nombre, None)
    COLECCION.objects.link(ob)
    ob.location = pos
    if padre is not None:
        ob.parent = padre
    return ob


def luz(nombre, tipo, pos, energia, color, radio=0.1, padre=None, rot=None, cono=None):
    ld = bpy.data.lights.new(nombre, tipo)
    ld.energy = energia
    ld.color = color
    poner(ld, "shadow_soft_size", radio)
    if cono is not None:
        ld.spot_size = cono
        ld.spot_blend = 0.6
    ob = bpy.data.objects.new(nombre, ld)
    COLECCION.objects.link(ob)
    ob.location = pos
    if rot is not None:
        ob.rotation_euler = rot
    if padre is not None:
        ob.parent = padre
    return ob


# --------------------------------------------------------------------------- la calle

def construir_calle(M):
    largo = C.Y_MAX - C.Y_MIN
    yc = (C.Y_MIN + C.Y_MAX) / 2
    bm = bmesh.new()
    caja(bm, (0, yc, -0.05), (2 * C.BORDILLO, largo, 0.1))
    objeto("calzada", bm, [M["adoquin"]])
    for lado in (-1, 1):
        bm = bmesh.new()
        ancho = C.FACHADA + 0.6 - C.BORDILLO - 0.22
        caja(bm, (lado * (C.BORDILLO + 0.22 + ancho / 2), yc, C.ACERA_ALTO / 2 - 0.05), (ancho, largo, C.ACERA_ALTO + 0.1))
        objeto(f"acera_{lado}", bm, [M["acera"]])
        bm = bmesh.new()
        caja(bm, (lado * (C.BORDILLO + 0.11), yc, 0.02), (0.22, largo, 0.16))
        objeto(f"bordillo_{lado}", bm, [M["granito"]])
    # rieles: cabeza de acero brillante al ras, con la ranura oscura al lado
    bm = bmesh.new()
    for x in (-C.ANCHO_VIA / 2, C.ANCHO_VIA / 2):
        caja(bm, (x, yc, 0.004), (0.065, largo, 0.012), 0)
        caja(bm, (x - math.copysign(0.05, x), yc, 0.001), (0.035, largo, 0.006), 1)   # ranura, del lado de adentro
    objeto("rieles", bm, [M["acero"], M["ranura"]])
    # catenaria: hilo de contacto sobre la vía y tensores de fachada a fachada
    bm = bmesh.new()
    barra(bm, (0, C.Y_MIN, 6.0), (0, C.Y_MAX, 6.0), 0.009, lados=6)
    barra(bm, (0, C.Y_MIN, 6.35), (0, C.Y_MAX, 6.35), 0.006, lados=6)
    y = C.Y_MIN + 6
    while y < C.Y_MAX:
        barra(bm, (-C.FACHADA, y, 7.2), (C.FACHADA, y, 7.2), 0.007, lados=6)
        barra(bm, (0, y, 6.0), (0, y, 7.2), 0.006, lados=6)
        y += 27.0
    objeto("catenaria", bm, [M["cable"]])


def construir_edificio(i, e: C.Edificio, M):
    s = e.lado
    fx = e.x
    y0, y1 = e.y0, e.y0 + e.ancho
    ym = (y0 + y1) / 2
    hacia = -s                              # sentido hacia la calle en x
    # cuerpo
    bm = bmesh.new()
    caja(bm, (fx + s * e.fondo / 2, ym, e.alto / 2), (e.fondo, e.ancho - 0.04, e.alto))
    objeto(f"casa{i}", bm, [M["fachada"]], color=e.color)

    # molduras, marcos, postigos, zócalo
    bm = bmesh.new()
    pinta = 0  # material 0 = marco blanco, 1 = fachada (con el color de la casa), 2 = postigo, 3 = piedra
    caja(bm, (fx + hacia * 0.06, ym, 0.45), (0.14, e.ancho - 0.04, 0.9), 3)                # zócalo de piedra
    caja(bm, (fx + hacia * 0.10, ym, C.PISO_BAJO - 0.05), (0.22, e.ancho - 0.04, 0.22), 1)   # cornisa baja
    for p in range(1, e.pisos):
        caja(bm, (fx + hacia * 0.05, ym, C.PISO_BAJO + p * C.PISO + 0.2), (0.1, e.ancho - 0.04, 0.12), 1)
    caja(bm, (fx + hacia * 0.22, ym, e.alto - 0.15), (0.45, e.ancho - 0.02, 0.32), 1)          # cornisa del alero
    for yc_, z, w, h, _ in e.ventanas():
        x = fx + hacia * 0.06
        caja(bm, (x, yc_, z + h + 0.06), (0.12, w + 0.24, 0.12), pinta)      # dintel
        caja(bm, (fx + hacia * 0.1, yc_, z - 0.06), (0.2, w + 0.3, 0.1), 3)  # repisa
        caja(bm, (x, yc_ - w / 2 - 0.06, z + h / 2), (0.12, 0.12, h + 0.12), pinta)
        caja(bm, (x, yc_ + w / 2 + 0.06, z + h / 2), (0.12, 0.12, h + 0.12), pinta)
        caja(bm, (fx + hacia * 0.03, yc_, z + h * 0.62), (0.05, w, 0.05), pinta)  # travesaño
        caja(bm, (fx + hacia * 0.03, yc_, z + h / 2), (0.05, 0.05, h), pinta)    # parteluz
    objeto(f"molduras{i}", bm, [M["marco"], M["fachada"], M["postigo"], M["piedra"]], color=e.color)
    if e.postigos:                                            # objeto aparte: su color es el del postigo
        bm = bmesh.new()
        for yc_, z, w, h, _ in e.ventanas():
            for lado_p in (-1, 1):
                caja(bm, (fx + hacia * 0.08, yc_ + lado_p * (w / 2 + 0.42), z + h / 2), (0.05, 0.6, h + 0.05))
        objeto(f"postigos{i}", bm, [M["postigo"]], color=e.postigos)

    # vidrios: oscuros o con luz adentro; planta baja con vitrina encendida y puerta
    bm = bmesh.new()
    for yc_, z, w, h, encendida in e.ventanas():
        caja(bm, (fx + hacia * 0.005, yc_, z + h / 2), (0.03, w, h), 1 if encendida else 0)
    ancho_v = min(e.ancho * 0.62, 6.0)
    caja(bm, (fx + hacia * 0.01, ym - 0.6, 0.95 + 1.3), (0.03, ancho_v, 2.5), 2)
    caja(bm, (fx + hacia * 0.01, ym + ancho_v / 2 + 0.3, 1.15), (0.03, 1.1, 2.3), 0)
    objeto(f"vidrios{i}", bm, [M["vidrio"], M["ventana_luz"], M["vitrina"]])
    bm = bmesh.new()
    caja(bm, (fx + hacia * 0.05, ym - 0.6, 3.38), (0.1, ancho_v + 0.3, 0.16), 0)         # dintel de la vitrina
    for d in (-1, 1):
        caja(bm, (fx + hacia * 0.05, ym - 0.6 + d * (ancho_v / 2 + 0.07), 1.9), (0.1, 0.14, 3.0), 0)
    objeto(f"vitrina_marco{i}", bm, [M["metal_oscuro"]])

    # toldo inclinado sobre la vitrina
    if e.toldo:
        bm = bmesh.new()
        a0 = Vector((fx, ym - 0.6 - ancho_v / 2 - 0.15, 3.55))
        sale = 1.5
        vs = [bm.verts.new(v) for v in (
            a0, a0 + Vector((0, ancho_v + 0.3, 0)),
            a0 + Vector((hacia * sale, ancho_v + 0.3, -0.6)), a0 + Vector((hacia * sale, 0, -0.6)))]
        bm.faces.new(vs)
        caida = [bm.verts.new(v) for v in (vs[3].co, vs[2].co, vs[2].co + Vector((0, 0, -0.28)), vs[3].co + Vector((0, 0, -0.28)))]
        bm.faces.new(caida)
        objeto(f"toldo{i}", bm, [M["toldo"]], color=e.toldo)

    # tejado a dos aguas, con alero hacia la calle
    bm = bmesh.new()
    vuelo = 0.5
    ef = fx + hacia * vuelo
    cumbre_x = fx + s * e.fondo / 2
    atras = fx + s * (e.fondo + vuelo)
    zc = e.alto + e.tejado
    pts = [(ef, y0, e.alto - 0.12), (ef, y1, e.alto - 0.12), (cumbre_x, y0, zc), (cumbre_x, y1, zc),
           (atras, y0, e.alto - 0.12), (atras, y1, e.alto - 0.12)]
    v = [bm.verts.new(p) for p in pts]
    for cara in ((0, 1, 3, 2), (2, 3, 5, 4), (0, 2, 4), (1, 5, 3), (0, 4, 5, 1)):
        bm.faces.new([v[k] for k in cara])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if (i * 7) % 3 == 0:                                       # chimenea en algunas casas
        caja(bm, (cumbre_x + s * 1.2, ym + 1.0, zc - 0.4), (0.6, 0.8, 2.2), 1)
    objeto(f"tejado{i}", bm, [M["tejado"], M["ladrillo"]])


def construir_farol(k, lado, y, M):
    fx = lado * C.FACHADA
    hacia = -lado
    bm = bmesh.new()
    barra(bm, (fx, y, 4.9), (fx + hacia * 0.95, y, 4.9), 0.025, 0)
    barra(bm, (fx, y, 4.45), (fx + hacia * 0.6, y, 4.88), 0.018, 0)          # tornapuntas
    cx = fx + hacia * 0.95
    caja(bm, (cx, y, 4.62), (0.34, 0.34, 0.06), 0)                         # techo del farol
    caja(bm, (cx, y, 4.16), (0.26, 0.26, 0.05), 0)
    barra(bm, (cx, y, 4.9), (cx, y, 4.62), 0.02, 0)
    caja(bm, (cx, y, 4.39), (0.24, 0.24, 0.42), 1)                         # vidrio encendido
    objeto(f"farol{k}", bm, [M["metal_oscuro"], M["farol"]])
    luz(f"luz_farol{k}", "POINT", (cx, y, 4.35), 140.0, (1.0, 0.70, 0.42), radio=0.12)


RETRO_ABAJO, RETRO_ARRIBA = 0.08, 0.48     # cuánto se mete la nariz abajo y arriba (parabrisas inclinado)


def cara_y(zl: float) -> float:
    """y (desde el frente del tranvía) de la cara frontal a la altura local zl del tramo."""
    return RETRO_ABAJO + (RETRO_ARRIBA - RETRO_ABAJO) * (zl + C.ALTO_T / 2) / C.ALTO_T


def construir_interior(k, y0, largo, es_frente, es_cola, raiz, M):
    """Lo que se ve por las ventanas: piso, asientos azules, barras amarillas, tiras de luz en el
    techo y la luz que sale a la calle. Sin pasajeros."""
    piso = C.BASE_T + 0.06
    techo = C.BASE_T + C.ALTO_T
    medio = y0 + largo / 2
    bm = bmesh.new()
    caja(bm, (0, medio, piso), (2.1, largo - 0.5, 0.06), 0)
    ya, yb = y0 + (1.6 if es_frente else 0.6), y0 + largo - (1.6 if es_cola else 0.6)
    yy = ya
    while yy < yb:
        if abs(yy - medio) > 0.85:                       # el centro es la puerta: ahí no hay asientos
            for x in (-0.72, 0.72):
                caja(bm, (x, yy, piso + 0.45), (0.5, 0.45, 0.09), 1)
                caja(bm, (x, yy + 0.24, piso + 0.75), (0.5, 0.08, 0.6), 1)
        yy += 0.85
    y = ya + 0.4
    while y < yb:
        for x in (-0.38, 0.38):
            barra(bm, (x, y, piso), (x, y, techo - 0.05), 0.02, 2, lados=6)
        y += 3.0
    barra(bm, (-0.38, ya, techo - 0.35), (-0.38, yb, techo - 0.35), 0.016, 2, lados=6)
    barra(bm, (0.38, ya, techo - 0.35), (0.38, yb, techo - 0.35), 0.016, 2, lados=6)
    for x in (-0.55, 0.55):
        caja(bm, (x, medio, techo - 0.06), (0.12, largo - 1.2, 0.03), 3)
    if es_frente:                                        # pupitre del conductor
        caja(bm, (0, 0.85, piso + 0.5), (1.9, 0.55, 0.95), 0)
    objeto(f"interior{k}", bm, [M["piso_t"], M["asiento"], M["barra_t"], M["led_techo"]], padre=raiz)
    adentro = luz(f"luz_interior{k}", "AREA", (0, medio, techo - 0.12), 110.0, (1.0, 0.95, 0.88), padre=raiz)
    adentro.data.shape = "RECTANGLE"
    adentro.data.size, adentro.data.size_y = 1.6, largo - 1.0


def construir_tranvia(M):
    raiz = vacio("tranvia")
    for k, (y0, largo) in enumerate(C.tramos_y()):
        bm = bmesh.new()
        caja(bm, (0, 0, 0), (C.ANCHO_T, largo, C.ALTO_T))
        es_frente = k == 0
        es_cola = k == len(C.TRAMOS) - 1
        # La cola es igual al frente (los tranvías de Friburgo andan en los dos sentidos): se
        # modela con la punta en y negativa, como el frente, y después se gira media vuelta.
        for v in bm.verts:
            if (es_frente or es_cola) and v.co.y < 0:
                if v.co.z > 0:                           # parabrisas inclinado y techo más angosto
                    v.co.y += RETRO_ARRIBA
                    v.co.x *= 0.9
                else:
                    v.co.y += RETRO_ABAJO
        mat = mat_tranvia(f"tranvia{k}", largo, es_frente or es_cola)
        ob = objeto(f"tramo{k}", bm, [mat], padre=raiz, suave=True)
        ob.location = (0, y0 + largo / 2, C.BASE_T + C.ALTO_T / 2)
        if es_cola:
            ob.rotation_euler = (0, 0, math.pi)
        bis = ob.modifiers.new("bisel", "BEVEL")
        bis.width = 0.22
        bis.segments = 6
        bis.limit_method = "ANGLE"
        poner(bis, "harden_normals", True)
        # techo: equipo de aire acondicionado
        bm = bmesh.new()
        caja(bm, (0, 0, C.ALTO_T / 2 + 0.18), (1.5, largo * 0.45, 0.36))
        techo = objeto(f"techo{k}", bm, [M["gris_techo"]], padre=ob)
        b2 = techo.modifiers.new("bisel", "BEVEL")
        b2.width, b2.segments = 0.08, 3
        # fuelle hacia el tramo siguiente
        if not es_cola:
            bm = bmesh.new()
            caja(bm, (0, y0 + largo + C.HUECO / 2, C.BASE_T + C.ALTO_T / 2 - 0.05), (2.05, C.HUECO + 0.3, C.ALTO_T - 0.35))
            objeto(f"fuelle{k}", bm, [M["fuelle"]], padre=raiz)
        construir_interior(k, y0, largo, es_frente, es_cola, raiz, M)

    # detalles del frente, pegados a la cara inclinada
    zc = C.BASE_T + C.ALTO_T / 2
    inclina = math.atan((RETRO_ARRIBA - RETRO_ABAJO) / C.ALTO_T)
    bm = bmesh.new()
    for x in (-0.78, 0.78):
        caja(bm, (x, cara_y(-0.95) - 0.01, zc - 0.95), (0.24, 0.06, 0.13), 0)
    objeto("faros", bm, [M["faro"]], padre=raiz)
    bm = bmesh.new()
    for x in (-0.5, 0.5):
        caja(bm, (x, cara_y(-1.12) - 0.01, zc - 1.12), (0.10, 0.06, 0.07), 0)
    objeto("pilotos", bm, [M["piloto"]], padre=raiz)
    # letrero de destino arriba del parabrisas, inclinado igual que la cara
    z_txt = 1.18
    bm = bmesh.new()
    caja(bm, (0, 0, 0), (1.55, 0.04, 0.30), 0)
    panel = objeto("panel_destino", bm, [M["metal_oscuro"]], padre=raiz)
    panel.location = (0, cara_y(z_txt) - 0.012, zc + z_txt)
    panel.rotation_euler = (-inclina, 0, 0)
    cu = bpy.data.curves.new("destino", "FONT")
    cu.body = "1   Littenweiler"
    cu.size = 0.19
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    txt = bpy.data.objects.new("destino", cu)
    COLECCION.objects.link(txt)
    txt.data.materials.append(M["led"])
    txt.parent = raiz
    txt.location = (0, cara_y(z_txt) - 0.04, zc + z_txt)
    txt.rotation_euler = (math.pi / 2 - inclina, 0, 0)

    # pantógrafo sobre el tramo del medio
    y0, largo = C.tramos_y()[1]
    yp = y0 + largo / 2
    zt = C.BASE_T + C.ALTO_T + 0.1
    bm = bmesh.new()
    caja(bm, (0, yp, zt), (1.1, 1.4, 0.2))
    codo = (0, yp + 1.0, zt + 1.3)
    barra(bm, (0, yp - 0.4, zt + 0.1), codo, 0.035)
    barra(bm, codo, (0, yp - 0.1, 6.0 - 0.05), 0.028)
    barra(bm, (-0.8, yp - 0.1, 5.95), (0.8, yp - 0.1, 5.95), 0.03)
    objeto("pantografo", bm, [M["metal_oscuro"]], padre=raiz)

    # faros que alumbran la calle delante del tranvía
    for x in (-0.78, 0.78):
        luz("faro", "SPOT", (x, cara_y(-0.95) - 0.12, zc - 0.95), 260.0, (1.0, 0.93, 0.82), radio=0.05,
            padre=raiz, rot=(math.radians(84), 0, math.pi), cono=math.radians(55))
    foco = vacio("foco", (0, 0.2, zc), padre=raiz)
    return raiz, foco


# --------------------------------------------------------------------------- escena

def preparar_render(escena):
    r = escena.render
    for motor in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if poner(r, "engine", motor):
            break
    r.resolution_x, r.resolution_y = 1920, 1080
    r.fps = C.FPS
    escena.frame_start, escena.frame_end = 1, C.CUADROS
    r.image_settings.file_format = "PNG"
    r.image_settings.color_depth = "8"
    poner(r, "film_transparent", False)
    ev = escena.eevee
    poner(ev, "taa_render_samples", 32)
    poner(ev, "use_raytracing", True)
    poner(ev, "ray_tracing_method", "SCREEN")
    if hasattr(ev, "ray_tracing_options"):
        poner(ev.ray_tracing_options, "resolution_scale", "1")
        poner(ev.ray_tracing_options, "use_denoise", True)
    poner(ev, "use_fast_gi", True)
    poner(ev, "fast_gi_method", "GLOBAL_ILLUMINATION")
    poner(ev, "use_shadows", True)
    poner(ev, "shadow_ray_count", 2)
    poner(ev, "shadow_step_count", 8)
    poner(ev, "volumetric_start", 0.5)
    poner(ev, "volumetric_end", 180.0)
    poner(ev, "volumetric_tile_size", "4")
    poner(ev, "volumetric_samples", 96)
    poner(ev, "use_volumetric_shadows", True)
    poner(ev, "use_bloom", True)                                # versiones viejas
    if not poner(r, "use_motion_blur", True):
        poner(ev, "use_motion_blur", True)
    poner(r, "motion_blur_shutter", 0.5)
    vs = escena.view_settings
    poner(vs, "view_transform", "AgX")
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        if poner(vs, "look", look):
            break
    vs.exposure = 0.0


def main():
    global COLECCION
    bpy.ops.wm.read_factory_settings(use_empty=True)
    escena = bpy.context.scene
    COLECCION = escena.collection
    mat_cielo_mundo(escena)
    M = {
        "adoquin": mat_adoquin(),
        "acera": mat_acera(),
        "granito": simple("granito", (0.30, 0.30, 0.29), 0.3),
        "acero": simple("acero", (0.8, 0.8, 0.8), 0.12, metal=1.0),
        "ranura": simple("ranura", (0.02, 0.02, 0.02), 0.4),
        "cable": simple("cable", (0.05, 0.05, 0.05), 0.4, metal=0.6),
        "fachada": mat_fachada(),
        "tejado": mat_tejado(),
        "ladrillo": simple("ladrillo", (0.28, 0.12, 0.08), 0.8),
        "marco": simple("marco", (0.82, 0.81, 0.78), 0.5),
        "postigo": material("postigo", lambda a: a.bsdf((a.nodo("ShaderNodeObjectInfo"), "Color"), 0.55)),
        "piedra": simple("piedra", (0.45, 0.25, 0.20), 0.75),           # arenisca roja, como en Friburgo
        "vidrio": mat_vidrio("vidrio"),
        "ventana_luz": mat_vidrio("ventana_luz", (1.0, 0.55, 0.25), 0.45),
        "vitrina": mat_vitrina(),
        "piso_t": simple("piso_tranvia", (0.08, 0.08, 0.09), 0.6),
        "asiento": simple("asiento", (0.06, 0.16, 0.30), 0.7),
        "barra_t": simple("barra_amarilla", (0.85, 0.62, 0.05), 0.3, metal=0.3),
        "led_techo": simple("led_techo", (1, 1, 1), 0.3, emision=(1.0, 0.96, 0.9), fuerza=6.0),
        "metal_oscuro": simple("metal_oscuro", (0.03, 0.03, 0.03), 0.35, metal=0.8),
        "farol": simple("farol", (1, 0.8, 0.6), 0.2, emision=(1.0, 0.72, 0.42), fuerza=28.0),
        "toldo": mat_toldo(),
        "gris_techo": simple("gris_techo", (0.35, 0.36, 0.37), 0.4),
        "fuelle": simple("fuelle", (0.02, 0.02, 0.02), 0.8),
        "faro": simple("faro", (1, 1, 1), 0.1, emision=(1.0, 0.96, 0.9), fuerza=60.0),
        "piloto": simple("piloto", (0.5, 0, 0), 0.2, emision=(1.0, 0.05, 0.02), fuerza=12.0),
        "led": simple("led", (0.1, 0.05, 0), 0.4, emision=(1.0, 0.55, 0.08), fuerza=14.0),
    }
    construir_calle(M)
    for i, e in enumerate(C.edificios()):
        construir_edificio(i, e, M)
    # cierre de la perspectiva al fondo de la calle
    bm = bmesh.new()
    caja(bm, (0, C.Y_MAX + 8, 9), (40, 6, 18))
    objeto("fondo", bm, [M["fachada"]], color=(0.7, 0.66, 0.6))
    bm = bmesh.new()
    caja(bm, (0, (C.Y_MIN + C.Y_MAX) / 2, 7), (30, C.Y_MAX - C.Y_MIN + 20, 14))
    objeto("neblina", bm, [mat_neblina()])
    for k, (lado, y) in enumerate(C.faroles()):
        construir_farol(k, lado, y, M)
    tranvia, foco = construir_tranvia(M)

    cam_d = bpy.data.cameras.new("camara")
    cam_d.lens = C.LENTE
    cam_d.sensor_width = 36.0
    cam_d.clip_end = 400
    cam_d.dof.use_dof = True
    cam_d.dof.focus_object = foco
    cam_d.dof.aperture_fstop = 2.2
    cam = bpy.data.objects.new("camara", cam_d)
    COLECCION.objects.link(cam)
    escena.camera = cam
    cam.location = C.CAMARA
    mira = vacio("mira")
    seg = cam.constraints.new("TRACK_TO")
    seg.target = mira
    seg.track_axis = "TRACK_NEGATIVE_Z"
    seg.up_axis = "UP_Y"

    # animación: un cuadro clave por fotograma (la curva la manda calle_datos.frente)
    for f in range(1, C.CUADROS + 2):
        t = (f - 1) / C.FPS
        tranvia.location = (0.0, C.frente(t), 0.0)
        tranvia.keyframe_insert("location", frame=f)
        mira.location = C.mira(t)
        mira.keyframe_insert("location", frame=f)
        # cámara en mano muy leve: respiración del camarógrafo
        cam.location = (C.CAMARA[0] + 0.012 * math.sin(t * 1.3), C.CAMARA[1] + 0.01 * math.sin(t * 0.7 + 1),
                        C.CAMARA[2] + 0.008 * math.sin(t * 1.9 + 2))
        cam.keyframe_insert("location", frame=f)

    preparar_render(escena)
    if MODO == "info":
        for n in bpy.data.materials["tranvia1"].node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                print("BSDF", [(i.name, tuple(i.default_value) if hasattr(i.default_value, "__len__") else i.default_value)
                               for i in n.inputs if i.name in ("Base Color", "Roughness", "Metallic", "Emission Color",
                                                               "Emission Strength", "Coat Weight", "Specular IOR Level")],
                      [l.from_node.name for l in n.inputs["Base Color"].links])
        return
    if MODO == "diag":                                      # diagnóstico: cada variante en un png chico
        cuadro = 200
        escena.render.resolution_percentage = 40
        escena.frame_set(cuadro)
        variantes = {"base": lambda: None,
                     "sin_emision": lambda: [setattr(n.inputs["Emission Strength"], "default_value", 0.0)
                                             for m in bpy.data.materials if m.name.startswith("tranvia")
                                             for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"],
                     "sin_luces": lambda: [setattr(o, "hide_render", True) for o in bpy.data.objects if o.type == "LIGHT"],
                     "sin_niebla": lambda: setattr(bpy.data.objects["neblina"], "hide_render", True)}
        for nombre, hacer in variantes.items():
            hacer()
            escena.render.filepath = str(SALIDA / f"diag_{nombre}.png")
            bpy.ops.render.render(write_still=True)
        return
    if MODO == "prueba":
        cuadro = int(ARGS[2]) if len(ARGS) > 2 else 200
        escena.render.resolution_percentage = int(ARGS[3]) if len(ARGS) > 3 else 50
        escena.frame_set(cuadro)
        escena.render.filepath = str(SALIDA / f"prueba_{cuadro:04d}.png")
        bpy.ops.render.render(write_still=True)
    else:
        escena.render.resolution_percentage = 100
        escena.render.use_overwrite = False                    # si se corta, al repetir sigue donde iba
        escena.render.filepath = str(SALIDA / "f_####")
        bpy.ops.render.render(animation=True)
    if "--guardar" in ARGS:
        bpy.ops.wm.save_as_mainfile(filepath=str(SALIDA / "calle.blend"))


main()
