"""La casa de los Dabate en Ellington, Connecticut (escenas 5 y 6), hecha con código.

No hay foto libre de la casa real, así que se arma una casa colonial de dos pisos típica de los
suburbios de Connecticut: tablas de madera pintadas (clapboard), molduras blancas, contraventanas
negras, tejado de tejas asfálticas, cochera adosada, pasto de diciembre y árboles sin hojas. El
23 de diciembre de 2015 fue un día templado y gris en Nueva Inglaterra: sin nieve, cielo nublado.

Además de la fachada, los interiores vacíos que se ven en las escenas: la cocina, la escalera al
sótano, el pasillo de arriba, y los objetos de cerca (sensor de puerta, teclado de la alarma, Fitbit,
documento del seguro). La violencia nunca se muestra: solo el lugar vacío.

Ejes: x hacia el este, y hacia el norte (la fachada mira a −y, a la calle), z hacia arriba, metros.
"""

import math
import random
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from tres_d import base as B
from tres_d import pbr as PB
from tres_d import rio as RI

FUENTES = Path(__file__).resolve().parent.parent / "fuentes"

# cielo de invierno nublado, de mañana: gris parejo, un poco más claro en el horizonte
B.CIELOS.setdefault("invierno_nublado", ((0.66, 0.68, 0.71), (0.58, 0.61, 0.66), (0.49, 0.53, 0.60),
                                         (0.38, 0.43, 0.52), 0.06, 0.95))

PISO1 = 0.55            # el primer piso está sobre el cimiento
ALTO_PISO = 2.8
ALERO = PISO1 + 2 * ALTO_PISO            # 6.15
CASA_X = (-6.2, 6.2)
CASA_Y = (0.0, 8.4)
COCHERA_X = (6.2, 13.0)
COCHERA_Y = (1.2, 8.4)


# =========================================================================== geometría básica


def cubo(bm, x0, x1, y0, y1, z0, z1, mat=0):
    return B.caja(bm, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), mat)


def tubo(bm, p0, p1, r0, r1=None, mat=0, lados=6):
    """Cilindro (o cono truncado) de p0 a p1."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    if d.length < 1e-6:
        return
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=lados, radius1=r0, radius2=r0 if r1 is None else r1,
                              depth=d.length, matrix=Matrix.Translation((p0 + p1) / 2) @ rot)
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mat


def transformar(bm, verts, M):
    bmesh.ops.transform(bm, matrix=M, verts=list(verts))


def mover_nuevos(bm, antes: set, M):
    """Aplica M a los vértices creados después de tomar `antes = set(bm.verts)`. (No sirve contar
    vértices y tomar bm.verts[n:]: bmesh reutiliza los huecos de los vértices que borran sus propias
    operaciones, y el orden no es el de creación.)"""
    transformar(bm, [v for v in bm.verts if v not in antes], M)


def texto3d(nombre, cadena, tam, mat, fuente="Inter-SemiBold.ttf", alinear="LEFT", padre=None, pos=(0, 0, 0),
            rot=(0, 0, 0), extruir=0.0):
    """Texto de Blender con la fuente Inter del proyecto (letras de un documento o una pantalla)."""
    cu = bpy.data.curves.new(nombre, "FONT")
    cu.body = cadena
    cu.size = tam
    cu.align_x = alinear
    cu.extrude = extruir
    try:
        cu.font = bpy.data.fonts.load(str(FUENTES / fuente), check_existing=True)
    except RuntimeError:
        pass
    ob = bpy.data.objects.new(nombre, cu)
    ob.data.materials.append(mat)
    B.enlazar(ob)
    if padre is not None:
        ob.parent = padre
    ob.location = pos
    ob.rotation_euler = rot
    return ob


# =========================================================================== materiales


def mat_tablas(nombre, color, paso=0.178):
    """Revestimiento de tablas horizontales (clapboard): cada tabla monta sobre la de abajo, con una
    línea de sombra en su borde inferior, pintura algo gastada y vetas finas."""
    def hacer(a):
        p = B.pos_mundo(a)
        _, _, z = a.separar(p)
        u = a.m("FRACT", a.m("DIVIDE", z, paso))
        mancha, _ = a.ruido(p, 0.5, 4.0, 0.6)
        veta, _ = a.ruido(a.v("MULTIPLY", p, (0.6, 0.6, 40.0)), 3.0, 3.0, 0.6)
        col = a.v("SCALE", color, escala=a.rango(mancha, 0.3, 0.7, 0.86, 1.04))
        col = a.v("SCALE", col, escala=a.rango(u, 0.0, 0.1, 0.55, 1.0))              # sombra bajo cada tabla
        col = a.v("SCALE", col, escala=a.rango(z, 0.0, 1.2, 0.8, 1.0))               # salpicado junto al piso
        alto = a.m("ADD", u, a.m("MULTIPLY", veta, 0.04))
        normal = a.bump(alto, 0.5, 0.012)
        return a.bsdf(col, 0.62, normal=normal, especular=0.35)
    return B.material(nombre, hacer)


def mat_pintura(nombre, color, rug=0.45, relieve=0.05):
    """Pintura de molduras, puertas y muebles: color parejo con algo de textura de brocha."""
    def hacer(a):
        p = B.pos_mundo(a)
        fino, _ = a.ruido(p, 70.0, 3.0, 0.6)
        mancha, _ = a.ruido(p, 2.0, 3.0, 0.6)
        col = a.v("SCALE", color, escala=a.rango(mancha, 0.3, 0.7, 0.93, 1.03))
        return a.bsdf(col, a.rango(mancha, 0.3, 0.7, rug - 0.08, rug + 0.08), normal=a.bump(fino, relieve, 0.002))
    return B.material(nombre, hacer)


def mat_tejas_asfalticas():
    """Tejas asfálticas gris oscuro en hileras desfasadas, con granulado y algo de musgo y manchas."""
    def hacer(a):
        p = B.pos_mundo(a)
        x, y, z = a.separar(p)
        comb = a.nodo("ShaderNodeCombineXYZ")
        a.unir(x, comb, 0)
        a.unir(a.m("ADD", a.m("MULTIPLY", y, 0.77), a.m("MULTIPLY", z, 0.64)), comb, 1)
        lad = a.nodo("ShaderNodeTexBrick", offset=0.5)
        a.unir((comb, 0), lad, "Vector")
        for k, v in {"Color1": (0.075, 0.075, 0.08, 1), "Color2": (0.045, 0.046, 0.05, 1),
                     "Mortar": (0.02, 0.02, 0.022, 1), "Scale": 1.0, "Mortar Size": 0.006,
                     "Brick Width": 0.92, "Row Height": 0.143}.items():
            B.entrada(lad, k).default_value = v
        grano, _ = a.ruido(p, 140.0, 2.0, 0.7)
        mancha, _ = a.ruido(p, 0.4, 4.0, 0.6)
        col = a.v("SCALE", (lad, "Color"), escala=a.rango(grano, 0.3, 0.7, 0.7, 1.3))
        col = a.mezcla(col, (0.05, 0.06, 0.035), a.rango(mancha, 0.6, 0.8, 0.0, 0.5))
        normal = a.bump(a.m("ADD", a.m("SUBTRACT", 1.0, (lad, "Fac")), a.m("MULTIPLY", grano, 0.3)), 0.6, 0.02)
        return a.bsdf(col, 0.8, normal=normal)
    return B.material("tejas_asfalticas", hacer)


def mat_ladrillo(nombre="ladrillo"):
    def hacer(a):
        p = B.pos_mundo(a)
        x, y, z = a.separar(p)
        comb = a.nodo("ShaderNodeCombineXYZ")
        a.unir(a.m("ADD", x, y), comb, 0)
        a.unir(z, comb, 1)
        lad = a.nodo("ShaderNodeTexBrick", offset=0.5)
        a.unir((comb, 0), lad, "Vector")
        for k, v in {"Color1": (0.30, 0.09, 0.05, 1), "Color2": (0.20, 0.06, 0.04, 1),
                     "Mortar": (0.35, 0.33, 0.30, 1), "Scale": 1.0, "Mortar Size": 0.012,
                     "Brick Width": 0.21, "Row Height": 0.075}.items():
            B.entrada(lad, k).default_value = v
        grano, _ = a.ruido(p, 40.0, 3.0, 0.6)
        col = a.v("SCALE", (lad, "Color"), escala=a.rango(grano, 0.3, 0.7, 0.75, 1.15))
        return a.bsdf(col, 0.85, normal=a.bump(a.m("SUBTRACT", 1.0, (lad, "Fac")), 0.6, 0.01))
    return B.material(nombre, hacer)


def mat_vidrio_casa(nombre="vidrio_casa", cortina=0.0):
    """Ventana vista de afuera: vidrio oscuro que refleja el cielo; adentro, una cortina clara tenue."""
    def hacer(a):
        p = B.coord_objeto(a)
        f, _ = a.ruido(p, 3.0, 2.0)
        col = a.v("SCALE", (0.02, 0.022, 0.025), escala=a.rango(f, 0.3, 0.7, 0.7, 1.3))
        if cortina:
            col = a.mezcla(col, (0.32, 0.30, 0.27), cortina)
        return a.bsdf(col, 0.03, especular=0.75)
    return B.material(nombre, hacer)


def _diciembre(a, p, col, rug):
    """Pasto de diciembre en Nueva Inglaterra: amarillento y apagado, con manchas verdes y hojas secas."""
    lum = a.v("DOT_PRODUCT", col, (0.33, 0.34, 0.33))
    paja = a.v("SCALE", (1.0, 0.86, 0.52), escala=a.m("MULTIPLY", lum, 0.95))
    m, _ = a.ruido(p, 0.18, 3.0, 0.6)
    col = a.mezcla(col, paja, a.rango(m, 0.3, 0.7, 0.2, 0.5))
    col = a.v("SCALE", col, escala=a.rango(m, 0.3, 0.7, 0.62, 0.85))
    rug = a.m("MAXIMUM", rug, 0.92)                      # el pasto seco no brilla: sin reflejo del cielo
    vor = a.nodo("ShaderNodeTexVoronoi")
    a.unir(p, vor, "Vector")
    B.entrada(vor, "Scale").default_value = 7.0
    zona, _ = a.ruido(p, 0.3, 2.0)
    hay = a.m("MULTIPLY", a.m("LESS_THAN", (vor, "Distance"), 0.12), a.rango(zona, 0.5, 0.65))
    hoja = a.mezcla((0.16, 0.08, 0.03), (0.24, 0.15, 0.06), (vor, "Color"))
    return a.mezcla(col, hoja, hay), rug


def mat_madera_piso(nombre="piso_madera", tono=(0.30, 0.17, 0.08)):
    """Duela de roble barnizada: tablas largas desfasadas, vetas y un brillo de barniz."""
    def hacer(a):
        p = B.pos_mundo(a)
        x, y, z = a.separar(p)
        comb = a.nodo("ShaderNodeCombineXYZ")
        a.unir(y, comb, 0)
        a.unir(x, comb, 1)
        lad = a.nodo("ShaderNodeTexBrick", offset=0.37, offset_frequency=1)
        a.unir((comb, 0), lad, "Vector")
        for k, v in {"Color1": (1, 1, 1, 1), "Color2": (0.0, 0.0, 0.0, 1), "Mortar": (0.0, 0.0, 0.0, 1),
                     "Scale": 1.0, "Mortar Size": 0.0025, "Mortar Smooth": 0.2, "Bias": 0.0,
                     "Brick Width": 1.25, "Row Height": 0.125}.items():
            B.entrada(lad, k).default_value = v
        tabla = a.separar((lad, "Color"))[0]
        veta_v = a.v("MULTIPLY", p, (1.0, 0.06, 1.0))
        veta, _ = a.ruido(a.v("ADD", veta_v, a.v("SCALE", (3.1, 7.7, 1.3), escala=tabla)), 9.0, 5.0, 0.65)
        anillos = a.nodo("ShaderNodeTexWave", wave_type="BANDS")
        a.unir(a.v("ADD", veta_v, a.v("SCALE", (2.0, 5.0, 0.0), escala=tabla)), anillos, "Vector")
        B.entrada(anillos, "Scale").default_value = 6.0
        B.entrada(anillos, "Distortion").default_value = 6.0
        col = a.v("SCALE", tono, escala=a.rango(tabla, 0.0, 1.0, 0.78, 1.15))
        col = a.v("SCALE", col, escala=a.rango((anillos, "Fac"), 0.0, 1.0, 0.82, 1.08))
        col = a.v("SCALE", col, escala=a.rango(veta, 0.3, 0.7, 0.85, 1.1))
        junta = (lad, "Fac")
        col = a.v("SCALE", col, escala=a.rango(junta, 0.0, 1.0, 1.0, 0.35))
        rug = a.rango(veta, 0.3, 0.7, 0.42, 0.58)
        normal = a.bump(a.m("SUBTRACT", 1.0, junta), 0.4, 0.002)
        return a.bsdf(col, rug, normal=normal, especular=0.35)
    return B.material(nombre, hacer)


def mat_granito(nombre="granito"):
    def hacer(a):
        p = B.pos_mundo(a)
        f1, _ = a.ruido(p, 120.0, 2.0, 0.8)
        f2, _ = a.ruido(p, 30.0, 4.0, 0.6)
        col = a.mezcla((0.03, 0.028, 0.026), (0.22, 0.20, 0.18), a.rango(f1, 0.62, 0.7))
        col = a.mezcla(col, (0.10, 0.06, 0.04), a.rango(f2, 0.6, 0.75, 0.0, 0.5))
        return a.bsdf(col, 0.12, especular=0.6)
    return B.material(nombre, hacer)


def mat_azulejo(nombre="azulejo"):
    """Azulejo de metro blanco del salpicadero de la cocina."""
    def hacer(a):
        p = B.pos_mundo(a)
        x, y, z = a.separar(p)
        comb = a.nodo("ShaderNodeCombineXYZ")
        a.unir(a.m("ADD", x, y), comb, 0)
        a.unir(z, comb, 1)
        lad = a.nodo("ShaderNodeTexBrick", offset=0.5)
        a.unir((comb, 0), lad, "Vector")
        for k, v in {"Color1": (0.80, 0.80, 0.78, 1), "Color2": (0.76, 0.76, 0.74, 1),
                     "Mortar": (0.55, 0.54, 0.52, 1), "Scale": 1.0, "Mortar Size": 0.003,
                     "Mortar Smooth": 0.3, "Brick Width": 0.15, "Row Height": 0.075}.items():
            B.entrada(lad, k).default_value = v
        return a.bsdf((lad, "Color"), 0.08, normal=a.bump(a.m("SUBTRACT", 1.0, (lad, "Fac")), 0.4, 0.003), especular=0.6)
    return B.material(nombre, hacer)


def mat_alfombra(nombre="alfombra", color=(0.30, 0.26, 0.21)):
    def hacer(a):
        p = B.pos_mundo(a)
        fino, _ = a.ruido(p, 400.0, 2.0, 0.8)
        m, _ = a.ruido(p, 1.5, 3.0, 0.6)
        col = a.v("SCALE", color, escala=a.rango(fino, 0.3, 0.7, 0.8, 1.15))
        col = a.v("SCALE", col, escala=a.rango(m, 0.3, 0.7, 0.9, 1.05))
        return a.bsdf(col, 0.95, normal=a.bump(fino, 0.5, 0.003), especular=0.15)
    return B.material(nombre, hacer)


def mat_pared(nombre="pared", color=(0.62, 0.56, 0.46)):
    """Pared de tablaroca pintada: color del objeto (Object Info), textura fina de rodillo y alguna
    mancha suave; casi mate."""
    def hacer(a):
        p = B.pos_mundo(a)
        info = a.nodo("ShaderNodeObjectInfo")
        fino, _ = a.ruido(p, 160.0, 3.0, 0.7)
        mancha, _ = a.ruido(p, 0.8, 4.0, 0.6)
        col = a.v("SCALE", (info, "Color"), escala=a.rango(mancha, 0.3, 0.7, 0.9, 1.03))
        return a.bsdf(col, 0.82, normal=a.bump(fino, 0.06, 0.002), especular=0.3)
    return B.material(nombre, hacer)


def mat_acero(nombre="acero", color=(0.55, 0.55, 0.56), rug=0.32):
    def hacer(a):
        p = B.pos_mundo(a)
        rayas, _ = a.ruido(a.v("MULTIPLY", p, (1.0, 1.0, 60.0)), 20.0, 2.0, 0.5)
        return a.bsdf(color, a.rango(rayas, 0.3, 0.7, rug - 0.08, rug + 0.08), metal=1.0)
    return B.material(nombre, hacer)


def mat_emision(nombre, color, fuerza):
    """Material que brilla; su fuerza queda en un nodo «fuerza» que se puede animar."""
    mat = bpy.data.materials.new(nombre)
    a = B.Arbol(mat)
    em = a.nodo("ShaderNodeEmission")
    em.name = "fuerza"
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = fuerza
    a.final((em, 0))
    return mat


def animar_fuerza(mat, valores, fps=30):
    """Pone una clave por cuadro a la fuerza de un material de emisión (`valores`: lista por cuadro)."""
    s = mat.node_tree.nodes["fuerza"].inputs["Strength"]
    for f, v in enumerate(valores, start=1):
        s.default_value = v
        s.keyframe_insert("default_value", frame=f)


def materiales_exterior() -> dict:
    return {
        "tablas": mat_tablas("tablas", (0.50, 0.45, 0.36)),
        "tablas_vecino": mat_tablas("tablas_vecino", (0.42, 0.45, 0.47)),
        "tablas_vecino2": mat_tablas("tablas_vecino2", (0.55, 0.50, 0.42)),
        "moldura": mat_pintura("moldura", (0.78, 0.77, 0.74), 0.4),
        "contraventana": mat_pintura("contraventana", (0.018, 0.02, 0.022), 0.5),
        "puerta": mat_pintura("puerta_entrada", (0.16, 0.025, 0.02), 0.35),
        "tejado": mat_tejas_asfalticas(),
        "vidrio": mat_vidrio_casa(cortina=0.0),
        "vidrio_cortina": mat_vidrio_casa("vidrio_cortina", 0.35),
        "cimiento": PB.material_pbr("cimiento", "Concrete031_2K-JPG", 2.0, "BOX", brillo=0.75, relieve=0.4, sucio_abajo=True),
        "pasto": PB.material_pbr("pasto_diciembre", "Grass004_2K-JPG", 2.2, "FLAT", brillo=0.62, relieve=0.8, extra=_diciembre),
        "asfalto": PB.material_pbr("asfalto_entrada", "Asphalt010_2K-JPG", 2.5, "FLAT", brillo=1.15, relieve=0.4),
        "calle": PB.material_pbr("asfalto_calle", "Asphalt010_2K-JPG", 3.0, "FLAT", brillo=0.6, relieve=0.4),
        "banqueta": PB.material_pbr("losas_entrada", "PavingStones109_2K-JPG", 1.2, "FLAT", brillo=0.85, relieve=0.5),
        "concreto": PB.material_pbr("concreto_casa", "Concrete031_2K-JPG", 3.0, "BOX", brillo=0.8, relieve=0.4),
        "ladrillo": mat_ladrillo(),
        "corteza": PB.material_pbr("corteza_ct", "Bark001_2K-JPG", 1.0, "BOX", brillo=0.5, relieve=1.0),
        "pino": mat_agujas("pino", (0.018, 0.035, 0.022)),
        "arbusto": mat_agujas("arbusto", (0.022, 0.040, 0.020)),
        "buzon": mat_pintura("buzon", (0.02, 0.02, 0.022), 0.35),
        "poste": mat_pintura("poste_buzon", (0.62, 0.60, 0.56), 0.6),
        "cochera": mat_pintura("puerta_cochera", (0.74, 0.73, 0.70), 0.42),
        "metal_oscuro": B.simple("metal_oscuro", (0.03, 0.03, 0.032), 0.4, metal=0.8),
    }


def mat_agujas(nombre, color):
    """Follaje de coníferas y arbustos de hoja perenne: verde muy oscuro, algo translúcido, cada planta
    con su tono (Object Info › Random)."""
    def hacer(a):
        info = a.nodo("ShaderNodeObjectInfo")
        f, _ = a.ruido(B.pos_mundo(a), 3.0, 3.0, 0.6)
        col = a.v("SCALE", color, escala=a.rango((info, "Random"), 0, 1, 0.75, 1.2))
        col = a.v("SCALE", col, escala=a.rango(f, 0.3, 0.7, 0.7, 1.2))
        tras = a.nodo("ShaderNodeBsdfTranslucent")
        a.dar(tras, "Color", a.v("SCALE", col, escala=0.8))
        return a.mezclar_shader(a.bsdf(col, 0.6), (tras, 0), 0.2)
    return B.material(nombre, hacer)


# =========================================================================== fachada


def ventana(bm, M, w, h, mats, contraventanas=True, cuadros=(3, 2)):
    """Ventana de guillotina con su marco blanco, cuadrícula y contraventanas negras. Se arma de cara
    a −y con el centro del borde inferior en el origen, y se lleva a su lugar con la matriz M.
    mats: (vidrio, moldura, contraventana)."""
    antes = set(bm.verts)
    iv, im, ic = mats
    cubo(bm, -w / 2, w / 2, -0.03, 0.0, 0.0, h, iv)
    m = 0.11
    cubo(bm, -w / 2 - m, w / 2 + m, -0.07, 0.0, h, h + 0.16, im)                 # cabezal
    cubo(bm, -w / 2 - m, -w / 2, -0.07, 0.0, -0.02, h, im)
    cubo(bm, w / 2, w / 2 + m, -0.07, 0.0, -0.02, h, im)
    cubo(bm, -w / 2 - 0.13, w / 2 + 0.13, -0.11, 0.0, -0.07, -0.01, im)          # alféizar
    cubo(bm, -w / 2, w / 2, -0.06, -0.03, h / 2 - 0.025, h / 2 + 0.025, im)      # riel donde se cruzan las hojas
    for k in range(1, cuadros[0]):                                              # cuadrícula
        x = -w / 2 + w * k / cuadros[0]
        cubo(bm, x - 0.012, x + 0.012, -0.05, -0.03, 0.0, h, im)
    for k in range(1, cuadros[1]):
        for mitad in (0, 1):
            z = mitad * h / 2 + (h / 2) * k / cuadros[1]
            cubo(bm, -w / 2, w / 2, -0.05, -0.03, z - 0.012, z + 0.012, im)
    if contraventanas:
        for s in (-1, 1):
            x0 = s * (w / 2 + m + 0.03)
            x1 = x0 + s * w * 0.48
            cubo(bm, min(x0, x1), max(x0, x1), -0.06, -0.01, -0.01, h + 0.02, ic)
            for k in range(14):                                                 # tablillas
                z = (k + 0.5) * h / 14
                cubo(bm, min(x0, x1) + 0.04, max(x0, x1) - 0.04, -0.075, -0.05, z - 0.015, z + 0.015, ic)
    mover_nuevos(bm, antes, M)


def en_fachada(x, y, z, giro=0.0):
    """Matriz para poner algo armado de cara a −y en (x, y, z), girado `giro` grados sobre z."""
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(giro), 4, "Z")


def tejado_dos_aguas(bm, x0, x1, y0, y1, z_alero, pendiente, vuelo, mat_t, mat_frontis, cumbrera_y=True):
    """Tejado de dos aguas con la cumbrera a lo largo de x (si `cumbrera_y` es False, a lo largo de y)
    y los frontones triangulares de tablas en los extremos."""
    if cumbrera_y:
        mitad = (y1 - y0) / 2
        zc = z_alero + mitad * math.tan(math.radians(pendiente))
        ym = (y0 + y1) / 2
        g = 0.12
        caida = vuelo * math.tan(math.radians(pendiente))
        for s in (-1, 1):
            ya = ym + s * (mitad + vuelo)
            vs = [bm.verts.new(v) for v in ((x0 - vuelo, ya, z_alero - caida), (x1 + vuelo, ya, z_alero - caida),
                                            (x1 + vuelo, ym, zc), (x0 - vuelo, ym, zc))]
            arriba = [bm.verts.new(v.co + Vector((0, 0, g))) for v in vs]
            caras = [bm.faces.new(vs[::-1]), bm.faces.new(arriba)]
            for i in range(4):
                j = (i + 1) % 4
                caras.append(bm.faces.new((vs[i], vs[j], arriba[j], arriba[i])))
            for f in caras:
                f.material_index = mat_t
        for x in (x0, x1):
            vs = [bm.verts.new(v) for v in ((x, y0, z_alero), (x, y1, z_alero), (x, ym, zc))]
            f = bm.faces.new(vs if x == x1 else vs[::-1])
            f.material_index = mat_frontis
        return zc
    mitad = (x1 - x0) / 2
    zc = z_alero + mitad * math.tan(math.radians(pendiente))
    xm = (x0 + x1) / 2
    g = 0.12
    caida = vuelo * math.tan(math.radians(pendiente))
    for s in (-1, 1):
        xa = xm + s * (mitad + vuelo)
        vs = [bm.verts.new(v) for v in ((xa, y0 - vuelo, z_alero - caida), (xa, y1 + vuelo, z_alero - caida),
                                        (xm, y1 + vuelo, zc), (xm, y0 - vuelo, zc))]
        arriba = [bm.verts.new(v.co + Vector((0, 0, g))) for v in vs]
        caras = [bm.faces.new(vs), bm.faces.new(arriba[::-1])]
        for i in range(4):
            j = (i + 1) % 4
            caras.append(bm.faces.new((arriba[i], arriba[j], vs[j], vs[i])))
        for f in caras:
            f.material_index = mat_t
    for y in (y0, y1):
        vs = [bm.verts.new(v) for v in ((x0, y, z_alero), (x1, y, z_alero), (xm, y, zc))]
        f = bm.faces.new(vs if y == y0 else vs[::-1])
        f.material_index = mat_frontis
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return zc


def casa_colonial(nombre, M, ox=0.0, oy=0.0, giro=0.0, tablas="tablas", con_cochera=True, detalle=True):
    """La casa: cuerpo de dos pisos, cochera adosada al este, portal de entrada, chimenea."""
    mats = [M[k] for k in (tablas, "moldura", "contraventana", "vidrio", "tejado", "cimiento", "puerta",
                           "ladrillo", "cochera", "vidrio_cortina", "metal_oscuro")]
    T, MO, CV, VI, TE, CI, PU, LA, CO, VC, MET = range(11)
    bm = bmesh.new()
    x0, x1 = CASA_X
    y0, y1 = CASA_Y
    cubo(bm, x0 - 0.05, x1 + 0.05, y0 - 0.05, y1 + 0.05, 0.0, PISO1, CI)                   # cimiento
    cubo(bm, x0, x1, y0, y1, PISO1, ALERO, T)
    # molduras: esquineros y cornisa
    for x in (x0, x1):
        for y in (y0, y1):
            cubo(bm, x - 0.09, x + 0.09, y - 0.09, y + 0.09, PISO1, ALERO, MO)
    cubo(bm, x0 - 0.12, x1 + 0.12, y0 - 0.14, y0, ALERO - 0.28, ALERO, MO)
    cubo(bm, x0 - 0.12, x1 + 0.12, y1, y1 + 0.14, ALERO - 0.28, ALERO, MO)
    tejado_dos_aguas(bm, x0, x1, y0, y1, ALERO, 38.0, 0.35, TE, T)
    # ventanas del frente: cuatro abajo (dos a cada lado de la puerta) y cinco arriba
    vm = (VI, MO, CV)
    for x in (-4.6, -2.3, 2.3, 4.6):
        ventana(bm, en_fachada(x, y0, PISO1 + 0.85), 0.92, 1.55, (VC if x < 0 else VI, MO, CV))
    for x in (-4.6, -2.3, 0.0, 2.3, 4.6):
        ventana(bm, en_fachada(x, y0, PISO1 + ALTO_PISO + 0.75), 0.88, 1.42, (VC if x in (-2.3, 4.6) else VI, MO, CV))
    # costado oeste y atrás: menos ventanas
    for y in (2.4, 6.0):
        ventana(bm, en_fachada(x0, y, PISO1 + 0.85, -90), 0.9, 1.5, vm)
        ventana(bm, en_fachada(x0, y, PISO1 + ALTO_PISO + 0.75, -90), 0.86, 1.4, vm)
    for x in (-3.5, 0.0, 3.5):
        ventana(bm, en_fachada(x, y1, PISO1 + ALTO_PISO + 0.75, 180), 0.86, 1.4, vm, contraventanas=False)
    # puerta de entrada con sus luces laterales y el portal
    cubo(bm, -0.5, 0.5, y0 - 0.04, y0, PISO1, PISO1 + 2.2, PU)
    for k in range(3):                                                                   # tableros
        z = PISO1 + 0.25 + k * 0.65
        cubo(bm, -0.38, -0.06, y0 - 0.06, y0 - 0.04, z, z + 0.5, PU)
        cubo(bm, 0.06, 0.38, y0 - 0.06, y0 - 0.04, z, z + 0.5, PU)
    cubo(bm, 0.3, 0.36, y0 - 0.09, y0 - 0.04, PISO1 + 1.0, PISO1 + 1.08, MET)               # manija
    for s in (-1, 1):
        cubo(bm, s * 0.56, s * 0.86, y0 - 0.03, y0, PISO1 + 0.6, PISO1 + 2.1, VC)          # luces laterales
        cubo(bm, s * 0.52 - 0.04, s * 0.52 + 0.04, y0 - 0.08, y0, PISO1, PISO1 + 2.25, MO)
        cubo(bm, s * 0.90 - 0.06, s * 0.90 + 0.06, y0 - 0.08, y0, PISO1, PISO1 + 2.25, MO)
    cubo(bm, -1.0, 1.0, y0 - 0.08, y0, PISO1 + 2.2, PISO1 + 2.42, MO)
    # portal: losa, dos columnas y un tejadito a dos aguas
    cubo(bm, -1.3, 1.3, y0 - 1.6, y0, PISO1 - 0.18, PISO1, CI)
    cubo(bm, -1.1, 1.1, y0 - 2.0, y0 - 1.6, PISO1 - 0.36, PISO1 - 0.18, CI)
    for s in (-1, 1):
        tubo(bm, (s * 1.1, y0 - 1.45, PISO1), (s * 1.1, y0 - 1.45, PISO1 + 2.6), 0.1, 0.085, MO, 16)
        cubo(bm, s * 1.1 - 0.14, s * 1.1 + 0.14, y0 - 1.59, y0 - 1.31, PISO1, PISO1 + 0.12, MO)
    cubo(bm, -1.35, 1.35, y0 - 1.65, y0, PISO1 + 2.6, PISO1 + 2.85, MO)
    tejado_dos_aguas(bm, -1.4, 1.4, y0 - 1.7, y0, PISO1 + 2.85, 42.0, 0.15, TE, MO, cumbrera_y=False)
    # chimenea de ladrillo en el costado oeste
    cubo(bm, x0 - 0.9, x0 - 0.05, 3.4, 5.0, 0.0, ALERO + 4.2, LA)
    cubo(bm, x0 - 0.98, x0 + 0.03, 3.32, 5.08, ALERO + 4.0, ALERO + 4.15, LA)
    if con_cochera:
        cx0, cx1 = COCHERA_X
        cy0, cy1 = COCHERA_Y
        za = PISO1 + 2.7
        cubo(bm, cx0, cx1, cy0, cy1, 0.0, 0.25, CI)
        cubo(bm, cx0, cx1, cy0, cy1, 0.25, za, T)
        for x in (cx1,):
            for y in (cy0, cy1):
                cubo(bm, x - 0.09, x + 0.09, y - 0.09, y + 0.09, 0.25, za, MO)
        cubo(bm, cx0, cx1 + 0.12, cy0 - 0.14, cy0, za - 0.25, za, MO)
        tejado_dos_aguas(bm, cx0 - 0.3, cx1, cy0, cy1, za, 32.0, 0.3, TE, T)
        # dos puertas de cochera de tableros
        for xc in (cx0 + 1.75, cx0 + 5.05):
            cubo(bm, xc - 1.35, xc + 1.35, cy0 - 0.03, cy0, 0.02, 2.3, CO)
            for fila in range(4):
                for col in range(4):
                    z = 0.12 + fila * 0.55
                    xx = xc - 1.25 + col * 0.64
                    cubo(bm, xx + 0.04, xx + 0.58, cy0 - 0.05, cy0 - 0.03, z, z + 0.45, CO)
            cubo(bm, xc - 1.47, xc + 1.47, cy0 - 0.08, cy0, 2.3, 2.45, MO)
            for s in (-1, 1):
                cubo(bm, xc + s * 1.41 - 0.06, xc + s * 1.41 + 0.06, cy0 - 0.08, cy0, 0.0, 2.45, MO)
        ventana(bm, en_fachada(cx1, 4.8, 1.3, 90), 0.8, 1.2, vm)
        # luz de la cochera: un farol junto a cada puerta
        for xc in (cx0 + 0.2, cx1 - 0.2):
            cubo(bm, xc - 0.09, xc + 0.09, cy0 - 0.16, cy0, 2.55, 2.85, MET)
    ob = B.objeto(nombre, bm, mats)
    ob.matrix_world = Matrix.Translation((ox, oy, 0)) @ Matrix.Rotation(math.radians(giro), 4, "Z")
    return ob


# =========================================================================== jardín, calle y árboles


def arbol_pelado(nombre, x, y, alto, rng: random.Random, mat, niveles=4, z0=0.0):
    """Árbol de hoja caduca en invierno: tronco, ramas que se abren y ramitas finas, sin hojas."""
    bm = bmesh.new()

    def rama(p0, d, largo, r, nivel):
        p1 = p0 + d * largo
        tubo(bm, p0, p1, r, r * 0.68, 0, 7 if nivel == 0 else (5 if nivel < 3 else 3))
        if nivel >= niveles:
            return
        hijos = 3 if nivel == 0 else rng.randint(2, 4)
        for k in range(hijos):
            s = rng.uniform(0.75, 1.0) if nivel == 0 else rng.uniform(0.35, 1.0)
            q = p0 + d * largo * s
            eje = d.orthogonal().normalized()
            eje.rotate(Matrix.Rotation(rng.uniform(0, math.tau), 3, d))
            ang = math.radians(rng.uniform(22, 48) if nivel else rng.uniform(25, 38))
            nd = (Matrix.Rotation(ang, 3, eje) @ d).normalized()
            nd = (nd + Vector((0, 0, 0.25 if nivel < 2 else 0.1))).normalized()          # hacia arriba, como los arces
            rama(q, nd, largo * rng.uniform(0.58, 0.78), r * rng.uniform(0.5, 0.62) * (0.68 + 0.32 * (1 - s)), nivel + 1)

    inclina = Vector((rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), 1.0)).normalized()
    rama(Vector((x, y, z0 - 0.2)), inclina, alto * 0.42, 0.06 * alto ** 0.9 * 0.5, 0)
    return B.objeto(nombre, bm, [mat])


def pino(nombre, x, y, alto, g: np.random.Generator, mat, radio=None, densidad=550.0):
    """Conífera: tronco y pisos de agujas cada vez más angostos hacia la punta."""
    radio = radio or alto * 0.22
    masas = []
    n = max(5, int(alto / 0.7))
    for k in range(n):
        u = k / n
        r = radio * (1 - u) ** 0.9 + 0.15
        masas.append(((x + g.normal(0, 0.08), y + g.normal(0, 0.08), 0.6 + u * (alto - 0.8)), (r, r, 0.55)))
    verts = RI.hojas_de_copa(masas, g, densidad=densidad)
    ob = RI.malla_triangulos(nombre, verts, mat)
    return ob


def arbusto(nombre, x, y, r, g: np.random.Generator, mat):
    masas = [((x + g.normal(0, r * 0.2), y + g.normal(0, r * 0.2), r * 0.7), (r, r, r * 0.8)) for _ in range(2)]
    return RI.malla_triangulos(nombre, RI.hojas_de_copa(masas, g, densidad=2400.0), mat)


def terreno_y_calle(M):
    """Pasto, entrada de autos, andador, la calle con su guarnición y el buzón."""
    bm = bmesh.new()
    cubo(bm, -120, 120, -24.0, 140, -0.05, 0.0)
    B.objeto("pasto", bm, [M["pasto"]])
    bm = bmesh.new()
    cubo(bm, COCHERA_X[0] + 0.1, COCHERA_X[1] - 0.1, -24.0, COCHERA_Y[0], 0.0, 0.025)      # entrada de autos
    B.objeto("entrada_autos", bm, [M["asfalto"]])
    bm = bmesh.new()
    cubo(bm, -0.7, 0.7, -16.0, -2.0, 0.0, 0.03)                                            # andador a la puerta
    cubo(bm, 0.7, COCHERA_X[0] + 0.1, -16.0, -14.8, 0.0, 0.03)
    B.objeto("andador", bm, [M["banqueta"]])
    bm = bmesh.new()
    cubo(bm, -200, 200, -33.0, -25.0, -0.12, -0.06)
    B.objeto("calle", bm, [M["calle"]])
    bm = bmesh.new()
    cubo(bm, -200, 200, -25.0, -24.0, -0.12, 0.02)
    cubo(bm, -200, 200, -34.0, -33.0, -0.12, 0.02)
    B.objeto("guarnicion", bm, [M["concreto"]])
    bm = bmesh.new()
    xb = COCHERA_X[0] - 0.6
    tubo(bm, (xb, -23.3, 0.0), (xb, -23.3, 1.05), 0.05, 0.05, 1, 8)
    cubo(bm, xb - 0.12, xb + 0.12, -23.62, -23.0, 1.05, 1.28, 0)
    tubo(bm, (xb, -23.62, 1.28), (xb, -23.0, 1.28), 0.12, 0.12, 0, 16)
    # farol del andador
    tubo(bm, (-1.25, -15.4, 0.0), (-1.25, -15.4, 1.75), 0.04, 0.035, 0, 10)
    cubo(bm, -1.41, -1.09, -15.56, -15.24, 1.75, 2.05, 0)
    B.objeto("buzon", bm, [M["buzon"], M["poste"]])


def jardin(M, semilla=7):
    """Árboles del jardín, arbustos junto al cimiento, coníferas atrás y la arboleda del fondo."""
    rng = random.Random(semilla)
    g = np.random.default_rng(semilla)
    k = 0
    for x, y, alto in ((-12.0, -10.0, 14.0), (16.5, -14.0, 12.5), (-19.0, 6.0, 15.0), (21.0, 4.0, 13.0),
                       (-9.0, -19.0, 11.0)):
        arbol_pelado(f"arbol{k}", x, y, alto, rng, M["corteza"])
        k += 1
    for x in np.arange(-5.4, 5.6, 1.1):
        if abs(x) > 1.6:
            arbusto(f"arbusto{k}", float(x), -0.55, 0.5 + 0.08 * rng.random(), g, M["arbusto"])
            k += 1
    for x, y, alto in ((-14.0, 14.0, 13.0), (-9.0, 18.0, 15.0), (3.0, 20.0, 16.0), (10.0, 17.0, 14.0),
                       (17.0, 15.0, 12.0), (24.0, 20.0, 15.0)):
        pino(f"pino{k}", x, y, alto, g, M["pino"])
        k += 1
    # arboleda del fondo y de los costados: árboles más simples
    for _ in range(84):
        ang = rng.uniform(-2.3, 2.3)
        r = rng.uniform(28, 66)
        x, y = r * math.sin(ang), 8 + r * math.cos(ang) * 0.8
        if y < -5 or math.hypot(x + 30, y - 8) < 13 or math.hypot(x - 46, y - 12) < 13:
            continue
        if rng.random() < 0.28:
            pino(f"pino{k}", x, y, rng.uniform(12, 20), g, M["pino"], densidad=260.0)
        else:
            arbol_pelado(f"arbol{k}", x, y, rng.uniform(12, 19), rng, M["corteza"], niveles=3)
        k += 1


def armar_exterior(escena, sol=True, neblina=True):
    """Toda la vista de afuera: la casa, la del vecino, el jardín y la calle, de mañana y nublado."""
    B.cielo(escena, "invierno_nublado")
    M = materiales_exterior()
    casa = casa_colonial("casa", M)
    casa_colonial("vecino", M, ox=-34.0, oy=4.0, giro=8.0, tablas="tablas_vecino", con_cochera=True)
    casa_colonial("vecino2", M, ox=40.0, oy=8.0, giro=-6.0, tablas="tablas_vecino2", con_cochera=True)
    terreno_y_calle(M)
    jardin(M)
    if sol:                                     # sol bajo de diciembre detrás de las nubes: sombras blandas
        s = B.luz("sol", "SUN", (0, 0, 30), 1.6, (1.0, 0.93, 0.84), rot=(math.radians(68), 0, math.radians(-35)))
        B.poner(s.data, "angle", math.radians(9.0))
    if neblina:
        B.neblina((0, 30, 12), (260, 160, 26), 0.0016, (0.78, 0.80, 0.84), anisotropia=0.1, nombre="bruma")
    return M, casa


def patrulla(cuadros, fps, inicio, posiciones=((-10.5, -26.5, 1.55), (-9.0, -27.2, 1.55)), energia=9000.0,
             barra_cerca=None):
    """Luces de una patrulla fuera de cuadro: destellos rojos y azules alternados que bañan la casa
    desde la calle. `barra_cerca`: (posición, giro) de la barra de luces en primer plano, desenfocada."""
    def destello(t, fase):
        if t < inicio:
            return 0.0
        u = ((t - inicio) * 1.25 + fase) % 1.0
        v = 0.0
        for c in (0.0, 0.16):
            x = u - c
            if 0 <= x < 0.11:
                v = max(v, math.sin(math.pi * x / 0.11) ** 0.6)
        return v * min(1.0, (t - inicio) / 0.25)
    rojo = B.luz("patrulla_roja", "POINT", posiciones[0], 0.0, (1.0, 0.06, 0.08), radio=0.3)
    azul = B.luz("patrulla_azul", "POINT", posiciones[1], 0.0, (0.10, 0.25, 1.0), radio=0.3)
    em_r = mat_emision("barra_roja", (1.0, 0.05, 0.06), 0.0)
    em_a = mat_emision("barra_azul", (0.15, 0.3, 1.0), 0.0)
    vr, va = [], []
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        r, a = destello(t, 0.0), destello(t, 0.5)
        B.clave(rojo.data, "energy", energia * 1.7 * r, f)
        B.clave(azul.data, "energy", energia * 1.6 * a, f)
        vr.append(60.0 * r)
        va.append(80.0 * a)
    animar_fuerza(em_r, vr, fps)
    animar_fuerza(em_a, va, fps)
    if barra_cerca is not None:
        pos, giro = barra_cerca
        bm = bmesh.new()
        cubo(bm, -0.7, -0.05, -0.12, 0.12, 0.0, 0.11, 0)
        cubo(bm, 0.05, 0.7, -0.12, 0.12, 0.0, 0.11, 1)
        cubo(bm, -0.8, 0.8, -0.16, 0.16, -0.04, 0.0, 2)
        ob = B.objeto("barra_luces", bm, [em_r, em_a, B.simple("techo_patrulla", (0.01, 0.01, 0.012), 0.2)])
        ob.location = pos
        ob.rotation_euler = (0, 0, math.radians(giro))
    return rojo, azul


# =========================================================================== interiores


def sin_rayas(escena):
    """Interiores: el trazado de rayos en pantalla de Eevee supone que todo tiene 20 cm de grosor, y
    los objetos delgados del piso (cinchos, marcadores) dejaban rayas oscuras largas hacia la cámara
    y reflejos falsos de los gabinetes. Se traza solo lo muy brillante, con grosor fino."""
    ev = escena.eevee
    if hasattr(ev, "ray_tracing_options"):
        B.poner(ev.ray_tracing_options, "trace_max_roughness", 0.18)
        B.poner(ev.ray_tracing_options, "screen_trace_thickness", 0.02)
    B.poner(ev, "fast_gi_thickness_near", 0.05)
    B.poner(ev, "fast_gi_thickness_far", 0.3)


def mats_interior() -> dict:
    return {
        "pared": mat_pared("pared_interior"),
        "techo": mat_pintura("techo", (0.72, 0.71, 0.68), 0.9, 0.02),
        "piso": mat_madera_piso(),
        "gabinete": mat_pintura("gabinete", (0.58, 0.56, 0.51), 0.38, 0.02),
        "granito": mat_granito(),
        "azulejo": mat_azulejo(),
        "acero": mat_acero(),
        "moldura": mat_pintura("moldura_int", (0.76, 0.75, 0.72), 0.35, 0.02),
        "puerta": mat_pintura("puerta_int", (0.74, 0.73, 0.70), 0.38, 0.02),
        "negro": B.simple("negro_mate", (0.01, 0.01, 0.011), 0.6),
        "afuera": mat_emision("afuera", (0.80, 0.84, 0.90), 2.2),
        "vidrio": B.material("vidrio_int", lambda a: a.mezclar_shader(
            (a.nodo("ShaderNodeBsdfTransparent"), 0), a.bsdf((0.02, 0.02, 0.02), 0.02, especular=0.8), 0.12)),
        "alfombra": mat_alfombra(),
        "concreto": PB.material_pbr("concreto_sotano", "Concrete031_2K-JPG", 2.0, "BOX", brillo=0.7, relieve=0.5),
        "madera_escalon": mat_madera_piso("escalon", (0.24, 0.14, 0.07)),
        "silla": mat_pintura("silla_plegable", (0.42, 0.40, 0.36), 0.38, 0.03),
        "cincho": B.simple("cincho", (0.012, 0.012, 0.013), 0.35),
        "marcador": RI.mat_marcador(),
        "numero": B.simple("numero_marcador", (0.01, 0.01, 0.01), 0.6),
    }


def cuarto(bm, x0, x1, y0, y1, z0, z1, mats, huecos=(), grosor=0.12, sin=()):
    """Cuarto de cajas: piso, techo y cuatro paredes con huecos rectangulares.
    mats = (pared, piso, techo); huecos: [(pared, a0, a1, b0, b1)] con pared en «n», «s», «e», «o», a a lo
    largo de la pared y b en altura; `sin`: paredes que no se construyen."""
    ip, ipi, it = mats
    cubo(bm, x0 - grosor, x1 + grosor, y0 - grosor, y1 + grosor, z0 - 0.1, z0, ipi)
    cubo(bm, x0 - grosor, x1 + grosor, y0 - grosor, y1 + grosor, z1, z1 + 0.1, it)
    paredes = {"s": (x0, x1, y0 - grosor, y0, "x"), "n": (x0, x1, y1, y1 + grosor, "x"),
               "o": (y0, y1, x0 - grosor, x0, "y"), "e": (y0, y1, x1, x1 + grosor, "y")}
    for nombre, (a0, a1, c0, c1, eje) in paredes.items():
        if nombre in sin:
            continue
        hs = sorted([(h[1], h[2], h[3], h[4]) for h in huecos if h[0] == nombre])
        tramos = []
        cur = a0
        for (h0, h1, b0, b1) in hs:
            tramos.append((cur, h0, z0, z1))
            tramos.append((h0, h1, z0, z0 + b0))
            tramos.append((h0, h1, z0 + b1, z1))
            cur = h1
        tramos.append((cur, a1, z0, z1))
        for (u0, u1, w0, w1) in tramos:
            if u1 - u0 < 1e-4 or w1 - w0 < 1e-4:
                continue
            if eje == "x":
                cubo(bm, u0, u1, c0, c1, w0, w1, ip)
            else:
                cubo(bm, c0, c1, u0, u1, w0, w1, ip)


def gabinetes(bm, x0, x1, y_pared, prof, M_idx, arriba=True, hueco=None, lado=1):
    """Gabinetes de cocina estilo shaker contra una pared que corre a lo largo de x.
    `lado` 1: la pared está en +y y los gabinetes salen hacia −y. M_idx: (gabinete, granito, acero)."""
    ig, igr, iac = M_idx
    yf = y_pared - lado * prof
    ya, yb = min(y_pared, yf), max(y_pared, yf)
    cubo(bm, x0, x1, ya, yb, 0.0, 0.1, ig)                                                     # zócalo
    cubo(bm, x0, x1, ya + (0.06 if lado > 0 else 0), yb - (0.0 if lado > 0 else 0.06), 0.1, 0.88, ig)
    cubo(bm, x0 - 0.02, x1 + 0.02, ya - (0.03 if lado > 0 else 0), yb + (0.0 if lado > 0 else 0.03), 0.88, 0.92, igr)
    n = max(1, round((x1 - x0) / 0.6))
    w = (x1 - x0) / n
    cara = yf - lado * 0.005
    for k in range(n):
        xa = x0 + k * w
        for (z0, z1) in ((0.12, 0.66), (0.70, 0.86)):
            cubo(bm, xa + 0.015, xa + w - 0.015, min(cara, cara - lado * 0.02), max(cara, cara - lado * 0.02), z0, z1, ig)
            cubo(bm, xa + 0.07, xa + w - 0.07, min(cara, cara - lado * 0.03), max(cara, cara - lado * 0.03), z0 + 0.06, z1 - 0.06, ig)
        xm = xa + w / 2
        cubo(bm, xm - 0.07, xm + 0.07, min(cara, cara - lado * 0.05), max(cara, cara - lado * 0.05), 0.775, 0.787, iac)
    if arriba:
        pa = 0.33
        yfa = y_pared - lado * pa
        for k in range(n):
            xa = x0 + k * w
            if hueco and xa + w > hueco[0] and xa < hueco[1]:
                continue
            cubo(bm, xa, xa + w, min(y_pared, yfa), max(y_pared, yfa), 1.45, 2.3, ig)
            c = yfa - lado * 0.005
            cubo(bm, xa + 0.07, xa + w - 0.07, min(c, c - lado * 0.025), max(c, c - lado * 0.025), 1.53, 2.22, ig)
            cubo(bm, xa + w / 2 - 0.006, xa + w / 2 + 0.006, min(c, c - lado * 0.05), max(c, c - lado * 0.05), 1.52, 1.66, iac)


def silla_plegable(nombre, mat_silla, tumbada=True):
    """Silla plegable de metal, como las de cualquier casa; tumbada de lado en el piso."""
    bm = bmesh.new()
    for s in (-1, 1):
        x = s * 0.205
        tubo(bm, (x, 0.24, 0.0), (x, 0.12, 0.84), 0.011, None, 0, 8)              # pata trasera y respaldo
        tubo(bm, (x * 0.97, -0.25, 0.0), (x * 0.97, 0.10, 0.47), 0.011, None, 0, 8)  # pata delantera
        for p in ((x, 0.24, 0.0), (x * 0.97, -0.25, 0.0)):                        # regatones
            tubo(bm, p, Vector(p) + Vector((0, 0, 0.025)), 0.015, None, 0, 8)
    tubo(bm, (-0.2, -0.20, 0.10), (0.2, -0.20, 0.10), 0.008, None, 0, 6)
    tubo(bm, (-0.205, 0.225, 0.12), (0.205, 0.225, 0.12), 0.008, None, 0, 6)
    cubo(bm, -0.2, 0.2, -0.22, 0.17, 0.44, 0.47, 0)                                # asiento
    cubo(bm, -0.19, 0.19, -0.2, 0.15, 0.425, 0.44, 0)
    antes = set(bm.verts)
    cubo(bm, -0.2, 0.2, -0.012, 0.012, -0.08, 0.08, 0)                             # respaldo
    mover_nuevos(bm, antes, Matrix.Translation((0, 0.145, 0.72)) @ Matrix.Rotation(math.radians(-8), 4, "X"))
    ob = B.objeto(nombre, bm, [mat_silla], suave=False)
    if tumbada:
        ob.rotation_euler = (0, math.radians(90), math.radians(10))
        ob.location = (0, 0, 0.215)
    return ob


def cincho(bm, centro, eje, radio=0.022, abierto=0.0, giro=0.0, mat=0):
    """Cincho de plástico: un aro fino con su cabeza cuadrada; `abierto` (0..1) lo deja cortado."""
    eje = Vector(eje).normalized()
    u = eje.orthogonal().normalized()
    u.rotate(Matrix.Rotation(giro, 3, eje))
    v = eje.cross(u)
    c = Vector(centro)
    n = 18
    arco = math.tau * (1 - 0.32 * abierto)
    pts = [c + (u * math.cos(arco * i / n) + v * math.sin(arco * i / n)) * radio * (1 + 0.15 * abierto * i / n)
           for i in range(n + 1)]
    for p0, p1 in zip(pts[:-1], pts[1:]):
        tubo(bm, p0, p1, 0.0022, None, mat, 4)
    antes = set(bm.verts)
    cubo(bm, -0.004, 0.004, -0.004, 0.004, -0.003, 0.003, mat)
    mover_nuevos(bm, antes, Matrix.Translation(pts[0]))
    if abierto > 0.5:                                                             # la cola suelta
        tubo(bm, pts[-1], pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.05, 0.0022, None, mat, 4)


def cocina(escena, M=None):
    """La cocina de la casa, vacía: gabinetes blancos, granito oscuro, piso de duela, la ventana sobre
    el fregadero con la luz gris de la mañana. En el piso, la silla plegable tumbada con los cinchos
    cortados y los marcadores amarillos de evidencia."""
    M = M or mats_interior()
    mats = [M[k] for k in ("pared", "piso", "techo", "gabinete", "granito", "acero", "azulejo", "afuera", "vidrio",
                           "moldura", "puerta", "negro")]
    PA, PI, TE, GA, GR, AC, AZ, AF, VI, MO, PU, NE = range(12)
    bm = bmesh.new()
    x0, x1, y0, y1, h = 0.0, 5.6, 0.0, 4.6, 2.6
    vent = (2.1, 3.5, 1.05, 2.15)
    cuarto(bm, x0, x1, y0, y1, 0.0, h, (PA, PI, TE),
           huecos=[("n", *vent), ("o", 1.2, 2.1, 0.0, 2.1), ("s", 3.2, 4.6, 0.0, 2.2)])
    ob = B.objeto("cocina", bm, mats)
    ob.color = (0.70, 0.64, 0.54, 1.0)                            # pared beige cálido
    bm = bmesh.new()
    gabinetes(bm, 0.95, x1, y1, 0.62, (GA, GR, AC), arriba=True, hueco=(vent[0] - 0.1, vent[1] + 0.1))
    cubo(bm, 0.95, x1, y1 - 0.02, y1, 0.92, 1.45, AZ)                                           # salpicadero
    cubo(bm, vent[0] + 0.25, vent[1] - 0.25, y1 - 0.58, y1 - 0.12, 0.70, 0.905, AC)                 # tarja
    tubo(bm, (2.8, y1 - 0.08, 0.92), (2.8, y1 - 0.08, 1.25), 0.014, None, AC, 10)                   # llave
    tubo(bm, (2.8, y1 - 0.08, 1.25), (2.8, y1 - 0.3, 1.22), 0.012, None, AC, 10)
    # gabinetes de la pared este (forman una L)
    antes = set(bm.verts)
    gabinetes(bm, 0.0, 3.0, 0.0, 0.62, (GA, GR, AC), arriba=True, lado=1)
    mover_nuevos(bm, antes, Matrix.Translation((x1, y1 - 0.62, 0)) @ Matrix.Rotation(math.radians(-90), 4, "Z"))
    # refrigerador de acero
    cubo(bm, 0.05, 0.92, y1 - 0.72, y1, 0.0, 1.78, AC)
    cubo(bm, 0.05, 0.92, y1 - 0.735, y1 - 0.72, 1.02, 1.03, NE)
    for z0, z1 in ((0.6, 0.98), (1.1, 1.5)):
        tubo(bm, (0.82, y1 - 0.76, z0), (0.82, y1 - 0.76, z1), 0.012, None, AC, 8)
    # ventana: marco, vidrio y lo de afuera (luz gris pareja)
    vx0, vx1, vz0, vz1 = vent
    for (a0, a1, b0, b1) in ((vx0 - 0.08, vx0, vz0 - 0.08, vz1 + 0.08), (vx1, vx1 + 0.08, vz0 - 0.08, vz1 + 0.08),
                             (vx0, vx1, vz1, vz1 + 0.08), (vx0 - 0.1, vx1 + 0.1, vz0 - 0.08, vz0)):
        cubo(bm, a0, a1, y1 - 0.03, y1 + 0.13, b0, b1, MO)
    xm = (vx0 + vx1) / 2
    cubo(bm, xm - 0.02, xm + 0.02, y1 + 0.03, y1 + 0.07, vz0, vz1, MO)
    cubo(bm, vx0, vx1, y1 + 0.04, y1 + 0.05, vz0, vz1, VI)
    cubo(bm, -4, 10, y1 + 3.0, y1 + 3.1, -2, 6, AF)
    # puerta al pasillo (oeste) y al comedor (sur): marcos
    for (a0, a1) in ((1.12, 1.2), (2.1, 2.18)):
        cubo(bm, x0 - 0.13, x0 + 0.02, a0, a1, 0.0, 2.18, MO)
    cubo(bm, x0 - 0.13, x0 + 0.02, 1.12, 2.18, 2.1, 2.18, MO)
    for (a0, a1) in ((3.12, 3.2), (4.6, 4.68)):
        cubo(bm, a0, a1, y0 - 0.13, y0 + 0.02, 0.0, 2.28, MO)
    # zócalo de madera blanca
    cubo(bm, x0, x0 + 0.015, 0.0, 1.2, 0.0, 0.11, MO)
    cubo(bm, x0, x0 + 0.015, 2.1, y1, 0.0, 0.11, MO)
    cubo(bm, x0, 3.2, y0, y0 + 0.015, 0.0, 0.11, MO)
    # lámpara del techo (apagada)
    tubo(bm, (2.8, 2.0, h - 0.02), (2.8, 2.0, h - 0.14), 0.22, 0.18, MO, 24)
    # estufa en la pared este, con su campana
    cubo(bm, x1 - 0.64, x1, 2.2, 2.96, 0.0, 0.93, AC)
    cubo(bm, x1 - 0.655, x1 - 0.64, 2.25, 2.91, 0.12, 0.72, NE)
    cubo(bm, x1 - 0.66, x1 - 0.645, 2.3, 2.86, 0.78, 0.81, AC)
    cubo(bm, x1 - 0.64, x1, 2.2, 2.96, 0.93, 0.945, NE)
    for (dy, dx) in ((2.38, 0.18), (2.78, 0.18), (2.38, 0.45), (2.78, 0.45)):
        tubo(bm, (x1 - dx, dy, 0.945), (x1 - dx, dy, 0.955), 0.09, 0.09, AC, 20)
    cubo(bm, x1 - 0.5, x1, 2.2, 2.96, 1.5, 1.62, AC)
    cubo(bm, x1 - 0.3, x1, 2.4, 2.76, 1.62, 2.3, AC)
    B.objeto("cocina_muebles", bm, mats)
    props = bmesh.new()
    cubo(props, 1.18, 1.42, y1 - 0.38, y1 - 0.12, 0.92, 1.28, 0)                       # cafetera
    tubo(props, (1.3, y1 - 0.44, 0.93), (1.3, y1 - 0.44, 1.08), 0.07, 0.065, 1, 20)
    cubo(props, 4.0, 4.28, y1 - 0.34, y1 - 0.16, 0.92, 1.12, 2)                        # tostador
    tubo(props, (x1 - 0.32, 1.45, 0.92), (x1 - 0.32, 1.45, 1.0), 0.13, 0.16, 3, 24)     # frutero
    for k, (dx, dy) in enumerate(((0.0, 0.0), (0.07, 0.05), (-0.06, 0.06), (0.02, -0.07))):
        r = bmesh.ops.create_uvsphere(props, u_segments=12, v_segments=8, radius=0.04,
                                      matrix=Matrix.Translation((x1 - 0.32 + dx, 1.45 + dy, 1.02 + 0.01 * (k % 2))))
        for f in {f for v in r["verts"] for f in v.link_faces}:
            f.material_index = 4
    tubo(props, (x1 - 0.18, 3.55, 0.92), (x1 - 0.18, 3.55, 1.2), 0.06, 0.06, 5, 20)    # toallas de papel
    tubo(props, (3.6, y1 - 0.25, 0.92), (3.6, y1 - 0.25, 1.06), 0.07, 0.09, 6, 20)      # maceta
    ob = B.objeto("utensilios", props, [B.simple("plastico_negro", (0.015, 0.015, 0.017), 0.35),
                                         B.material("vidrio_jarra", lambda a: a.bsdf((0.05, 0.03, 0.02), 0.05, especular=0.8)),
                                         mat_acero("acero_tostador", (0.6, 0.6, 0.6), 0.25),
                                         mat_pintura("frutero", (0.42, 0.40, 0.36), 0.3, 0.01),
                                         B.simple("naranjas", (0.62, 0.22, 0.03), 0.45),
                                         B.simple("papel_cocina", (0.75, 0.74, 0.70), 0.9),
                                         mat_pintura("maceta", (0.35, 0.05, 0.04), 0.4, 0.01)], suave=True)
    nochebuena((3.6, y1 - 0.25, 1.06))
    # luz: lo de afuera entra por la ventana
    ventana_luz = B.luz("luz_ventana", "AREA", (xm, y1 + 0.3, (vz0 + vz1) / 2), 160.0, (0.86, 0.9, 1.0))
    ventana_luz.data.shape = "RECTANGLE"
    ventana_luz.data.size, ventana_luz.data.size_y = vx1 - vx0, vz1 - vz0
    ventana_luz.rotation_euler = (math.radians(-90), 0, 0)
    # luz que entra por la puerta del comedor (otra ventana, fuera de cuadro)
    rebote = B.luz("luz_comedor", "AREA", (3.9, -1.2, 1.6), 90.0, (0.9, 0.92, 1.0))
    rebote.data.size = 1.4
    rebote.rotation_euler = (math.radians(90), 0, 0)
    return M


def nochebuena(base, semilla=23):
    """Nochebuena en maceta (es 23 de diciembre): brácteas rojas alargadas en roseta, en dos pisos,
    sobre hojas verdes más grandes y oscuras."""
    rng = random.Random(semilla)
    bm = bmesh.new()
    b = Vector(base)
    for piso, (n, largo, alza, mat) in enumerate(((9, 0.13, 0.35, 1), (11, 0.11, 0.18, 0), (8, 0.08, 0.55, 0))):
        for k in range(n):
            ang = math.tau * (k + rng.uniform(-0.2, 0.2) + 0.5 * piso) / n
            d = Vector((math.cos(ang), math.sin(ang), math.tan(alza + rng.uniform(-0.1, 0.1)))).normalized()
            lado = d.cross(Vector((0, 0, 1))).normalized()
            l = largo * rng.uniform(0.85, 1.15)
            w = l * 0.32
            c = b + Vector((0, 0, 0.05 + 0.015 * piso))
            p1 = c + d * l * 0.45 + lado * w * 0.5 + Vector((0, 0, 0.01))
            p2 = c + d * l
            p3 = c + d * l * 0.45 - lado * w * 0.5 + Vector((0, 0, 0.01))
            f = bm.faces.new([bm.verts.new(v) for v in (c, p1, p2, p3)])
            f.material_index = mat
    hojas = B.material("bracteas", lambda a: a.mezclar_shader(
        a.bsdf(a.v("SCALE", (0.42, 0.015, 0.025), escala=a.rango(a.ruido(B.pos_mundo(a), 60.0)[0], 0.3, 0.7, 0.75, 1.15)), 0.5),
        (lambda n: (n, 0))(_trasluz(a, (0.5, 0.02, 0.03))), 0.25))
    verdes = B.simple("hojas_verdes", (0.02, 0.06, 0.02), 0.5)
    return B.objeto("nochebuena", bm, [hojas, verdes], suave=False)


def _trasluz(a, color):
    n = a.nodo("ShaderNodeBsdfTranslucent")
    n.inputs["Color"].default_value = (*color, 1)
    return n


def escena_silla(M, centro=(3.0, 1.9)):
    """La silla plegable tumbada, los cinchos cortados y los marcadores amarillos numerados."""
    cx, cy = centro
    s = silla_plegable("silla", M["silla"])
    s.location = (cx, cy, 0.215)
    bm = bmesh.new()                                    # cinchos cortados que quedaron en las patas
    cincho(bm, (0.199, -0.18, 0.094), (0, 0.35, 0.47), 0.017, 0.7, 1.0)
    cincho(bm, (0.205, 0.222, 0.126), (0, -0.12, 0.84), 0.017, 0.6, 2.0)
    B.objeto("cinchos_silla", bm, [M["cincho"]]).parent = s
    bm = bmesh.new()
    rng = random.Random(3)
    for k, (dx, dy, ab) in enumerate(((-0.62, -0.32, 1.0), (-0.48, -0.55, 1.0), (0.55, -0.42, 1.0), (0.25, 0.62, 1.0))):
        cincho(bm, (cx + dx, cy + dy, 0.004), (0, 0, 1), 0.024, ab, rng.uniform(0, 6))
    B.objeto("cinchos", bm, [M["cincho"]])
    for k, (dx, dy, n) in enumerate(((-0.75, -0.15, 1), (-0.45, -0.8, 2), (0.8, -0.35, 3), (0.5, 0.85, 4))):
        RI.marcador_evidencia(k, (cx + dx, cy + dy, 0.0), n, M["marcador"], M["numero"], giro=math.radians(-50 + 12 * k))         # el número mira a la cámara


def escalera_sotano(M=None):
    """La escalera al sótano vista desde arriba: escalones de madera entre paredes pintadas, el
    pasamanos, y abajo el sótano de concreto que da vuelta hacia la izquierda, en penumbra."""
    M = M or mats_interior()
    mats = [M[k] for k in ("pared", "madera_escalon", "techo", "concreto", "moldura", "acero", "negro", "piso")]
    PA, ES, TE, CO, MO, AC, NE, PI = range(8)
    bm = bmesh.new()
    ancho, n, sube, huella = 0.95, 13, 0.19, 0.255
    largo = n * huella
    # rellano de arriba (pasillo) y el marco de la puerta
    cubo(bm, -1.2, 1.2, -2.0, 0.0, -0.1, 0.0, PI)
    cubo(bm, -ancho / 2 - 0.12, -ancho / 2, -0.06, 0.06, 0.0, 2.1, MO)
    cubo(bm, ancho / 2, ancho / 2 + 0.12, -0.06, 0.06, 0.0, 2.1, MO)
    cubo(bm, -ancho / 2 - 0.12, ancho / 2 + 0.12, -0.06, 0.06, 2.03, 2.15, MO)
    cubo(bm, -1.2, -ancho / 2 - 0.12, -0.08, 0.0, 0.0, 2.6, PA)
    cubo(bm, ancho / 2 + 0.12, 1.2, -0.08, 0.0, 0.0, 2.6, PA)
    cubo(bm, -1.2, 1.2, -0.08, 0.0, 2.15, 2.6, PA)
    # escalones
    for k in range(n):
        z = -(k + 1) * sube
        y = k * huella
        cubo(bm, -ancho / 2, ancho / 2, y, y + huella + 0.02, z, z + 0.03, ES)                 # huella
        cubo(bm, -ancho / 2, ancho / 2, y + huella - 0.005, y + huella + 0.015, z - sube, z, MO)  # contrahuella (baja al siguiente)
        cubo(bm, -ancho / 2, ancho / 2, y + 0.02, y + huella, z - 0.25, z, NE)
    zf = -n * sube
    # paredes del cubo de la escalera y el techo inclinado
    for s in (-1, 1):
        x = s * (ancho / 2 + 0.06)
        cubo(bm, x - 0.06, x + 0.06, 0.0, largo + 0.2, zf, 2.6, PA)
    vs = [bm.verts.new(v) for v in ((-ancho / 2 - 0.12, 0.0, 2.6), (ancho / 2 + 0.12, 0.0, 2.6),
                                    (ancho / 2 + 0.12, largo + 0.2, zf + 2.25), (-ancho / 2 - 0.12, largo + 0.2, zf + 2.25))]
    bm.faces.new(vs).material_index = TE
    # zócalos
    for s in (-1, 1):
        for k in range(n):
            y, z = k * huella, -(k + 1) * sube
            cubo(bm, s * ancho / 2 - 0.012 * s, s * ancho / 2, y, y + huella + 0.02, z, z + 0.12 + 0.19, MO)
    # pasamanos a la derecha
    p0 = Vector((ancho / 2 - 0.07, 0.15, 0.9))
    p1 = Vector((ancho / 2 - 0.07, largo - 0.2, zf + 0.95))
    tubo(bm, p0, p1, 0.025, None, ES, 12)
    for u in (0.08, 0.5, 0.92):
        q = p0.lerp(p1, u)
        tubo(bm, q, q + Vector((0.07, 0, 0)), 0.008, None, AC, 6)
    # el sótano: piso, paredes de concreto; la escalera llega a una pared y el sótano sigue a la izquierda
    cubo(bm, -5.0, 2.0, largo - 0.2, largo + 4.0, zf - 0.1, zf, CO)
    cubo(bm, -5.0, 2.0, largo + 1.4, largo + 1.6, zf, zf + 2.3, CO)                         # pared de enfrente
    cubo(bm, ancho / 2 + 0.06, ancho / 2 + 0.2, largo + 0.2, largo + 1.4, zf, zf + 2.3, CO)  # pared derecha
    cubo(bm, -5.0, 2.0, largo - 0.2, largo + 1.6, zf + 2.25, zf + 2.4, CO)                  # techo del sótano
    tubo(bm, (-3.0, largo + 0.5, zf + 2.1), (0.3, largo + 0.5, zf + 2.1), 0.05, None, AC, 10)  # tubo de agua
    cubo(bm, -4.6, -4.0, largo + 0.3, largo + 1.3, zf, zf + 1.6, AC)                         # calentador
    # foco desnudo apagado arriba de la escalera
    tubo(bm, (0, 1.2, 2.32), (0, 1.2, 2.2), 0.05, 0.03, MO, 10)
    B.objeto("escalera_sotano", bm, mats).color = (0.62, 0.58, 0.50, 1.0)
    return M


def pasillo_arriba(M=None):
    """El pasillo del segundo piso: alfombra, puertas blancas a los lados y al fondo una ventana con la
    luz gris de la mañana, que deja a contraluz lo que pase delante de ella."""
    M = M or mats_interior()
    mats = [M[k] for k in ("pared", "alfombra", "techo", "puerta", "moldura", "afuera", "acero", "vidrio")]
    PA, AL, TE, PU, MO, AF, AC, VI = range(8)
    bm = bmesh.new()
    ancho, largo, h = 1.25, 7.0, 2.45
    x0, x1 = -ancho / 2, ancho / 2
    # pasillo y, al fondo, un rellano más ancho con la ventana
    cuarto(bm, x0, x1, -4.0, largo, 0.0, h, (PA, AL, TE),
           huecos=[("o", 1.2, 2.05, 0.0, 2.05), ("e", 3.3, 4.15, 0.0, 2.05), ("o", 4.6, 5.45, 0.0, 2.05)], sin=("n",))
    cuarto(bm, -2.6, 2.6, largo, largo + 3.2, 0.0, h, (PA, AL, TE), huecos=[("n", -0.75, 0.75, 0.7, 2.1)], sin=("s",))
    cubo(bm, -2.6, x0, largo - 0.12, largo, 0.0, h, PA)
    cubo(bm, x1, 2.6, largo - 0.12, largo, 0.0, h, PA)
    # marcos de puertas y las puertas entreabiertas (oscuro adentro)
    for (lado, a0, a1) in ((-1, 1.2, 2.05), (1, 3.3, 4.15), (-1, 4.6, 5.45)):
        x = x0 if lado < 0 else x1
        for y in (a0, a1):
            cubo(bm, x - 0.02, x + 0.02, y - 0.07, y + 0.07, 0.0, 2.12, MO)
        cubo(bm, x - 0.02, x + 0.02, a0 - 0.07, a1 + 0.07, 2.05, 2.14, MO)
        antes = set(bm.verts)
        cubo(bm, 0.0, 0.035, 0.0, a1 - a0 - 0.02, 0.0, 2.03, PU)
        bisagra = Vector((x + lado * 0.04, a0 + 0.01, 0.0))
        mover_nuevos(bm, antes, Matrix.Translation(bisagra) @ Matrix.Rotation(math.radians(-lado * 115), 4, "Z"))
    # cuartos en penumbra detrás de las puertas
    for (lado, a0, a1) in ((-1, 1.2, 2.05), (1, 3.3, 4.15), (-1, 4.6, 5.45)):
        if lado < 0:
            cuarto(bm, x0 - 3.0, x0 - 0.12, a0 - 0.8, a1 + 0.8, 0.0, h, (PA, AL, TE), sin=("e",))
        else:
            cuarto(bm, x1 + 0.12, x1 + 3.0, a0 - 0.8, a1 + 0.8, 0.0, h, (PA, AL, TE), sin=("o",))
    # zócalos
    for x in (x0, x1 - 0.015):
        cubo(bm, x, x + 0.015, 0.0, largo, 0.0, 0.1, MO)
    # ventana del fondo: marco, vidrio y la luz de afuera
    yv = largo + 3.2
    for (a0, a1, b0, b1) in ((-0.83, -0.75, 0.62, 2.18), (0.75, 0.83, 0.62, 2.18), (-0.75, 0.75, 2.1, 2.18),
                             (-0.86, 0.86, 0.62, 0.7)):
        cubo(bm, a0, a1, yv - 0.05, yv + 0.13, b0, b1, MO)
    cubo(bm, -0.75, 0.75, yv + 0.02, yv + 0.06, 1.38, 1.42, MO)
    cubo(bm, -0.02, 0.02, yv + 0.02, yv + 0.06, 0.7, 2.1, MO)
    cubo(bm, -8, 8, yv + 4.0, yv + 4.1, -4, 8, AF)
    B.objeto("pasillo", bm, mats).color = (0.66, 0.62, 0.55, 1.0)
    luz = B.luz("luz_ventana_pasillo", "AREA", (0, yv + 0.4, 1.4), 520.0, (0.88, 0.92, 1.0))
    luz.data.shape = "RECTANGLE"
    luz.data.size, luz.data.size_y = 1.5, 1.4
    luz.rotation_euler = (math.radians(-90), 0, 0)
    return M


# =========================================================================== objetos de cerca


def mat_plastico(nombre, color, rug=0.35):
    def hacer(a):
        p = B.pos_mundo(a)
        fino, _ = a.ruido(p, 900.0, 2.0, 0.7)
        sucio, _ = a.ruido(p, 40.0, 3.0, 0.6)
        col = a.v("SCALE", color, escala=a.rango(sucio, 0.35, 0.7, 0.9, 1.03))
        return a.bsdf(col, a.rango(sucio, 0.3, 0.7, rug - 0.06, rug + 0.1), normal=a.bump(fino, 0.08, 0.0005), especular=0.5)
    return B.material(nombre, hacer)


def caja_redonda(bm, cx, cy, cz, w, d, h, r, mat=0, segs=6):
    """Caja con las esquinas verticales redondeadas (plástico moldeado)."""
    r = min(r, w / 2 - 1e-4, d / 2 - 1e-4)
    pts = []
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccy = cx + sx * (w / 2 - r), cy + sy * (d / 2 - r)
        for i in range(segs + 1):
            a = math.radians(a0 + 90 * i / segs)
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    abajo = [bm.verts.new((x, y, cz)) for x, y in pts]
    arriba = [bm.verts.new((x, y, cz + h)) for x, y in pts]
    caras = [bm.faces.new(abajo[::-1]), bm.faces.new(arriba)]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        caras.append(bm.faces.new((abajo[i], abajo[j], arriba[j], arriba[i])))
    for f in caras:
        f.material_index = mat
    return caras


def sensor_puerta(M_sensor, M_ranura):
    """Contacto magnético de alarma: el interruptor (pieza larga, con su tapa redonda) va en el marco y
    el imán (pieza corta) en la puerta. Medidas de un contacto común: 6.5 × 3.2 × 1.6 cm."""
    bm = bmesh.new()
    caja_redonda(bm, 0.0, 0.0, 0.0, 0.016, 0.065, 0.016, 0.006, 0)                 # interruptor (marco)
    tubo(bm, (0.0, 0.012, 0.016), (0.0, 0.012, 0.0175), 0.0065, 0.0062, 0, 24)
    tubo(bm, (0.0, 0.012, 0.0155), (0.0, 0.012, 0.0162), 0.0072, 0.0072, 1, 24)
    interruptor = B.objeto("interruptor", bm, [M_sensor, M_ranura], suave=False)
    bm = bmesh.new()
    caja_redonda(bm, 0.0, 0.0, 0.0, 0.013, 0.04, 0.013, 0.005, 0)                   # imán (puerta)
    for k in range(2):
        cubo(bm, -0.0025 + k * 0.0035, -0.0012 + k * 0.0035, -0.008, 0.008, 0.013, 0.0136, 0)
    iman = B.objeto("iman", bm, [M_sensor])
    return interruptor, iman


def fitbit_one(M_cuerpo, M_pantalla, M_clip):
    """Fitbit One: una pastilla negra brillante de 4.8 × 1.9 × 0.9 cm con su pantalla, y el clip de
    goma gris donde se mete para engancharlo a la ropa."""
    bm = bmesh.new()
    n = 24
    L, Wd, Hh = 0.048, 0.019, 0.0095
    perfil = []
    for i in range(n):                                                              # contorno de cápsula
        a = math.tau * i / n
        x = (L / 2 - Wd / 2) * (1 if math.cos(a) >= 0 else -1) + Wd / 2 * math.cos(a)
        perfil.append((x, Wd / 2 * math.sin(a)))
    capas = []
    for k in range(7):                                                              # de canto redondeado
        u = k / 6
        z = Hh * u
        enc = 1 - 0.18 * (1 - math.sin(math.pi * u)) ** 2
        capas.append([bm.verts.new((x * (1 - 0.06 * (1 - math.sin(math.pi * u))), y * enc, z)) for x, y in perfil])
    for c0, c1 in zip(capas[:-1], capas[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((c0[i], c0[j], c1[j], c1[i]))
    bm.faces.new(capas[0][::-1])
    bm.faces.new(capas[-1])
    cuerpo = B.objeto("fitbit", bm, [M_cuerpo], suave=True)
    bm = bmesh.new()
    cubo(bm, -0.014, 0.012, -0.0045, 0.0045, Hh + 0.0001, Hh + 0.0003, 0)
    pantalla = B.objeto("fitbit_pantalla", bm, [M_pantalla])
    pantalla.parent = cuerpo
    bm = bmesh.new()
    tubo(bm, (-0.0195, 0.0, Hh - 0.0002), (-0.0195, 0.0, Hh + 0.0002), 0.0025, 0.0025, 0, 16)
    boton = B.objeto("fitbit_boton", bm, [M_clip])
    boton.parent = cuerpo
    # clip: funda de goma con su lengüeta
    bm = bmesh.new()
    for s in (-1, 1):
        cubo(bm, -0.029, 0.029, s * 0.0115 - 0.0018, s * 0.0115 + 0.0018, 0.0, 0.012, 0)
    cubo(bm, -0.029, 0.029, -0.0133, 0.0133, 0.0, 0.0018, 0)
    cubo(bm, -0.029, -0.0255, -0.0133, 0.0133, 0.0, 0.012, 0)
    cubo(bm, 0.0255, 0.029, -0.0133, 0.0133, 0.0, 0.012, 0)
    cubo(bm, -0.029, 0.026, -0.0105, 0.0105, 0.0135, 0.0158, 0)                     # lengüeta del clip
    clip = B.objeto("fitbit_clip", bm, [M_clip])
    return cuerpo, clip


def llavero(M_negro, M_metal):
    """Llave de auto con control y su argolla, para dar la escala del Fitbit («del tamaño de un llavero»)."""
    bm = bmesh.new()
    caja_redonda(bm, 0.0, 0.0, 0.0, 0.032, 0.058, 0.012, 0.012, 0)
    for k in range(3):
        tubo(bm, (0.0, 0.012 - k * 0.012, 0.012), (0.0, 0.012 - k * 0.012, 0.0128), 0.0045, 0.0045, 0, 12)
    ctrl = B.objeto("control", bm, [M_negro], suave=False)
    bm = bmesh.new()
    n = 32
    c = Vector((0.0, 0.043, 0.004))
    pts = [c + Vector((0.013 * math.cos(math.tau * i / n), 0.013 * math.sin(math.tau * i / n), 0)) for i in range(n + 1)]
    for p0, p1 in zip(pts[:-1], pts[1:]):
        tubo(bm, p0, p1, 0.0011, None, 0, 6)
    cubo(bm, -0.003, 0.003, 0.026, 0.033, 0.0, 0.006, 0)
    argolla = B.objeto("argolla", bm, [M_metal])
    return ctrl, argolla
