"""El Dreisam en Friburgo: río angosto y canalizado entre taludes de pasto con escollera de piedra
abajo, ciclovía de asfalto arriba en cada orilla, hileras de árboles (octubre: hojas verdes,
amarillas y naranjas, y hojas caídas en el camino), farolas con tramos oscuros entre ellas, un
puente, las calles y edificios de los dos lados y, al fondo, las lomas de la Selva Negra.

Ejes: el río corre a lo largo de y (x = 0 al centro), z hacia arriba, metros. El agua está a
z = -2.6; los caminos, a z = 0.
"""

import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from tres_d.base import barra, caja, enlazar, entrada, luz, material, objeto, pos_mundo, simple, vacio

AGUA_Z = -2.6
Y0, Y1 = -80.0, 340.0
CAMINO = (15.0, 18.5)                  # x del camino de la orilla derecha (la izquierda es el espejo)
PUENTE_Y = 52.0

# Perfil de la orilla derecha (x, z) desde el agua hacia afuera; cada tramo con su material.
PERFIL = [
    ((8.4, AGUA_Z - 0.35), (10.6, -1.75), "escollera"),
    ((10.6, -1.75), (15.0, 0.0), "cesped"),
    ((15.0, 0.0), (18.5, 0.0), "asfalto"),
    ((18.5, 0.0), (21.5, 0.06), "cesped"),
    ((21.5, 0.12), (23.5, 0.12), "acera"),
    ((23.5, 0.0), (30.5, 0.0), "asfalto"),
    ((30.5, 0.12), (33.0, 0.12), "acera"),
]


# --------------------------------------------------------------------------- materiales

def mat_agua(nombre="agua"):
    """Agua oscura casi espejo; ondas finas que se mueven río abajo (se animan los nodos «flujo»)."""
    def hacer(a):
        p = pos_mundo(a)
        mapeo = a.nodo("ShaderNodeMapping")
        mapeo.name = "flujo"
        a.unir(p, mapeo, "Vector")
        n1 = a.nodo("ShaderNodeTexNoise", noise_dimensions="4D")
        n1.name = "ondas"
        a.unir((mapeo, 0), n1, "Vector")
        for k, v in {"Scale": 0.9, "Detail": 6.0, "Roughness": 0.55}.items():
            entrada(n1, k).default_value = v
        estirado = a.v("MULTIPLY", (mapeo, 0), (2.2, 0.6, 1.0))         # ondas alargadas a lo ancho
        n2 = a.nodo("ShaderNodeTexNoise", noise_dimensions="4D")
        n2.name = "ondas_finas"
        a.unir(estirado, n2, "Vector")
        for k, v in {"Scale": 6.0, "Detail": 3.0, "Roughness": 0.5}.items():
            entrada(n2, k).default_value = v
        altura = a.m("ADD", (n1, "Fac"), a.m("MULTIPLY", (n2, "Fac"), 0.4))
        normal = a.bump(altura, 0.09, 0.05)
        return a.bsdf((0.006, 0.009, 0.010), 0.02, normal=normal, especular=0.7)
    return material(nombre, hacer)


def animar_agua(mat, cuadros: int, fps: int = 30, velocidad: float = 0.45):
    """La corriente: las ondas se desplazan río abajo (−y) y cambian despacio."""
    nt = mat.node_tree
    mapeo, n1, n2 = nt.nodes["flujo"], nt.nodes["ondas"], nt.nodes["ondas_finas"]
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        mapeo.inputs["Location"].default_value = (0.0, velocidad * t, 0.0)
        mapeo.inputs["Location"].keyframe_insert("default_value", frame=f)
        for n, k in ((n1, 0.05), (n2, 0.25)):
            n.inputs["W"].default_value = t * k
            n.inputs["W"].keyframe_insert("default_value", frame=f)


def mat_cesped(seco=0.0):
    def hacer(a):
        p = pos_mundo(a)
        mancha, _ = a.ruido(p, 0.7, 4.0)
        fino, _ = a.ruido(p, 60.0, 3.0, 0.7)
        verde, paja = (0.035, 0.07, 0.025), (0.12, 0.10, 0.05)
        color = a.mezcla(verde, paja, a.m("ADD", a.rango(mancha, 0.35, 0.7, 0.0, 0.5), seco))
        color = a.v("SCALE", color, escala=a.rango(fino, 0.3, 0.7, 0.6, 1.2))
        normal = a.bump(fino, 0.6, 0.03)
        return a.bsdf(color, a.rango(mancha, 0.3, 0.7, 0.45, 0.85), normal=normal)     # rocío: algo de brillo
    return material("cesped", hacer)


def mat_escollera():
    def hacer(a):
        p = pos_mundo(a)
        vor = a.nodo("ShaderNodeTexVoronoi", feature="DISTANCE_TO_EDGE")
        a.unir(p, vor, "Vector")
        entrada(vor, "Scale").default_value = 2.4
        vor2 = a.nodo("ShaderNodeTexVoronoi")
        a.unir(p, vor2, "Vector")
        entrada(vor2, "Scale").default_value = 2.4
        borde = a.rango((vor, "Distance"), 0.0, 0.08)
        _, _, z = a.separar(p)
        mojado = a.rango(z, AGUA_Z + 0.2, AGUA_Z + 0.9, 1.0, 0.0)
        gris = a.v("SCALE", (0.16, 0.155, 0.15), escala=a.rango((vor2, "Distance"), 0.0, 0.5, 0.6, 1.25))
        color = a.v("SCALE", gris, escala=a.rango(mojado, 0, 1, 1.0, 0.45))
        musgo = a.rango(z, AGUA_Z + 0.3, AGUA_Z + 1.0, 0.5, 0.0)
        color = a.mezcla(color, (0.03, 0.05, 0.02), musgo)
        normal = a.bump(borde, 1.0, 0.12)
        return a.bsdf(color, a.rango(mojado, 0, 1, 0.6, 0.15), normal=normal)
    return material("escollera", hacer)


def mat_asfalto(hojas=True):
    """Asfalto mojado, con charcos y (en octubre) hojas caídas pegadas al piso."""
    def hacer(a):
        p = pos_mundo(a)
        grano, _ = a.ruido(p, 90.0, 3.0, 0.7)
        charco_f, _ = a.ruido(p, 0.45, 3.0, 0.5)
        charco = a.rango(charco_f, 0.55, 0.62)
        color = a.v("SCALE", (0.045, 0.045, 0.048), escala=a.rango(grano, 0.3, 0.7, 0.75, 1.25))
        rug = a.rango(charco, 0, 1, 0.42, 0.04)
        if hojas:
            vor = a.nodo("ShaderNodeTexVoronoi")
            a.unir(p, vor, "Vector")
            entrada(vor, "Scale").default_value = 9.0
            zona, _ = a.ruido(p, 0.25, 2.0)
            hay = a.m("MULTIPLY", a.m("LESS_THAN", (vor, "Distance"), 0.16), a.rango(zona, 0.45, 0.6))
            hoja_c = a.mezcla((0.30, 0.12, 0.03), (0.42, 0.30, 0.05), (vor, "Color"))
            color = a.mezcla(color, hoja_c, hay)
            rug = a.m("ADD", rug, a.m("MULTIPLY", a.m("SUBTRACT", 0.55, rug), hay))
        normal = a.bump(grano, a.rango(charco, 0, 1, 0.25, 0.0), 0.01)
        return a.bsdf(color, rug, normal=normal)
    return material("asfalto" + ("_hojas" if hojas else ""), hacer)


def mat_edificio_lejano():
    """Fachadas lejanas: la cuadrícula de ventanas es un patrón (no geometría) y unas pocas tienen luz,
    elegidas al azar por ventana (ruido blanco sobre el número de columna y de piso)."""
    def hacer(a):
        info = a.nodo("ShaderNodeObjectInfo")
        p = pos_mundo(a)
        x, y, z = a.separar(p)
        s_ = a.m("MULTIPLY", a.m("ADD", x, y), 1 / 2.6)                     # columnas de 2.6 m
        v_ = a.m("MULTIPLY", z, 1 / 3.1)                                    # pisos de 3.1 m
        u, w = a.m("FRACT", s_), a.m("FRACT", v_)
        dentro = a.m("MULTIPLY", a.m("MULTIPLY", a.m("GREATER_THAN", u, 0.28), a.m("LESS_THAN", u, 0.72)),
                     a.m("MULTIPLY", a.m("GREATER_THAN", w, 0.28), a.m("LESS_THAN", w, 0.76)))
        celda = a.nodo("ShaderNodeCombineXYZ")
        a.unir(a.m("FLOOR", s_), celda, 0)
        a.unir(a.m("FLOOR", v_), celda, 1)
        a.unir((info, "Random"), celda, 2)
        azar = a.nodo("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
        a.unir((celda, 0), azar, "Vector")
        luz_ = a.m("MULTIPLY", dentro, a.m("GREATER_THAN", (azar, "Value"), 0.9))
        luz_ = a.m("MULTIPLY", luz_, a.m("GREATER_THAN", z, 3.0))
        tono = a.mezcla((1.0, 0.58, 0.26), (0.85, 0.85, 0.95), a.m("GREATER_THAN", (azar, "Value"), 0.97))
        fachada = a.v("SCALE", (info, "Color"), escala=0.09)
        color = a.mezcla(fachada, (0.008, 0.009, 0.012), dentro)
        emis = a.v("SCALE", tono, escala=a.m("MULTIPLY", luz_, 0.7))
        return a.bsdf(color, a.rango(dentro, 0, 1, 0.85, 0.08), emision=emis, fuerza=1.0)
    return material("edificio_lejano", hacer)


def mat_lomas():
    def hacer(a):
        p = pos_mundo(a)
        f, _ = a.ruido(p, 0.02, 6.0, 0.6)
        return a.bsdf(a.v("SCALE", (0.012, 0.018, 0.012), escala=a.rango(f, 0.3, 0.7, 0.6, 1.3)), 0.9)
    return material("lomas", hacer)


def _hojas_caidas(a, p, color, rug):
    """Hojas de octubre pegadas al piso mojado, en manchones (capa encima de la textura escaneada)."""
    vor = a.nodo("ShaderNodeTexVoronoi")
    a.unir(p, vor, "Vector")
    entrada(vor, "Scale").default_value = 9.0
    zona, _ = a.ruido(p, 0.25, 2.0)
    hay = a.m("MULTIPLY", a.m("LESS_THAN", (vor, "Distance"), 0.16), a.rango(zona, 0.45, 0.6))
    hoja_c = a.mezcla((0.30, 0.12, 0.03), (0.42, 0.30, 0.05), (vor, "Color"))
    return a.mezcla(color, hoja_c, hay), a.m("ADD", rug, a.m("MULTIPLY", a.m("SUBTRACT", 0.55, rug), hay))


def _mojado_junto_al_agua(a, p, color, rug):
    """Piedra oscura y brillante donde la salpica el río, con una franja de musgo encima."""
    _, _, z = a.separar(p)
    mojado = a.rango(z, AGUA_Z + 0.2, AGUA_Z + 0.9, 1.0, 0.0)
    color = a.v("SCALE", color, escala=a.rango(mojado, 0, 1, 1.0, 0.45))
    color = a.mezcla(color, (0.03, 0.05, 0.02), a.rango(z, AGUA_Z + 0.3, AGUA_Z + 1.0, 0.5, 0.0))
    rug = a.m("ADD", a.m("MULTIPLY", rug, a.m("SUBTRACT", 1.0, mojado)), a.m("MULTIPLY", mojado, 0.15))
    return color, rug


def materiales_libres(M: dict, hojas=True) -> dict:
    """Cambia los materiales calculados por texturas escaneadas (ambientCG, en recursos_3d/)."""
    from tres_d.pbr import material_pbr
    M["cesped"] = material_pbr("pasto_escaneado", "Grass004_2K-JPG", 2.0, "FLAT", brillo=0.75, relieve=0.8)
    M["escollera"] = material_pbr("escollera_escaneada", "Rocks008_2K-JPG", 1.6, "BOX", brillo=0.8, relieve=1.0,
                                  extra=_mojado_junto_al_agua)
    M["asfalto"] = material_pbr("asfalto_escaneado", "Asphalt010_2K-JPG", 2.5, "FLAT", charcos=True, brillo=0.7,
                                relieve=0.4, extra=_hojas_caidas if hojas else None)
    M["acera"] = material_pbr("losas_rio", "PavingStones109_2K-JPG", 1.4, "FLAT", charcos=True, brillo=0.8, relieve=0.5)
    M["concreto"] = material_pbr("concreto_escaneado", "Concrete031_2K-JPG", 3.0, "BOX", brillo=0.85, relieve=0.5,
                                 sucio_abajo=True)
    M["corteza"] = material_pbr("corteza_escaneada", "Bark001_2K-JPG", 1.2, "BOX", brillo=0.45, relieve=1.0)
    return M


def materiales_rio(hojas=True, libre=False) -> dict:
    M = _materiales_calculados(hojas)
    return materiales_libres(M, hojas) if libre else M


def _materiales_calculados(hojas=True) -> dict:
    return {
        "agua": mat_agua(),
        "cesped": mat_cesped(),
        "escollera": mat_escollera(),
        "asfalto": mat_asfalto(hojas),
        "acera": simple("acera_rio", (0.12, 0.12, 0.125), 0.5),
        "lecho": simple("lecho", (0.01, 0.012, 0.01), 0.9),
        "corteza": material("corteza", lambda a: a.bsdf(
            a.v("SCALE", (0.05, 0.04, 0.035), escala=a.rango(a.ruido(pos_mundo(a), 8.0, 4.0)[0], 0.3, 0.7, 0.6, 1.3)), 0.85,
            normal=a.bump(a.ruido(a.v("MULTIPLY", pos_mundo(a), (6.0, 6.0, 0.8)), 3.0, 4.0)[0], 0.8, 0.03))),
        "hojas": mat_hojas(),
        "concreto": material("concreto", lambda a: a.bsdf(
            a.v("SCALE", (0.30, 0.29, 0.27), escala=a.rango(a.ruido(pos_mundo(a), 1.5, 5.0)[0], 0.3, 0.7, 0.55, 1.1)), 0.8)),
        "metal": simple("metal_farola", (0.06, 0.065, 0.07), 0.4, metal=0.8),
        "lampara": simple("lampara", (1, 0.8, 0.6), 0.2, emision=(1.0, 0.70, 0.40), fuerza=30.0),
        "edificio": mat_edificio_lejano(),
        "lomas": mat_lomas(),
        "barandal": simple("barandal", (0.05, 0.06, 0.055), 0.45, metal=0.7),
    }


# --------------------------------------------------------------------------- terreno

def terreno(M):
    """Las dos orillas, extruyendo el perfil a lo largo del río; el agua y el lecho."""
    por_mat: dict[str, bmesh.types.BMesh] = {}
    for lado in (-1, 1):
        for (x0, z0), (x1, z1), nombre in PERFIL:
            bm = por_mat.setdefault(nombre, bmesh.new())
            vs = [bm.verts.new(v) for v in ((lado * x0, Y0, z0), (lado * x1, Y0, z1), (lado * x1, Y1, z1), (lado * x0, Y1, z0))]
            cara = bm.faces.new(vs if lado > 0 else vs[::-1])
            cara.normal_update()
            if cara.normal.z < 0:
                cara.normal_flip()
            if nombre == "acera" or (nombre == "asfalto" and abs(x0) > 20):  # bordillos
                for xb in (x0, x1):
                    caja(bm, (lado * xb, (Y0 + Y1) / 2, 0.06), (0.15, Y1 - Y0, 0.12))
    for nombre, bm in por_mat.items():
        objeto(f"orilla_{nombre}", bm, [M[nombre]])
    bm = bmesh.new()
    caja(bm, (0, (Y0 + Y1) / 2, AGUA_Z - 0.01), (17.4, Y1 - Y0, 0.02))
    objeto("agua", bm, [M["agua"]])
    bm = bmesh.new()
    caja(bm, (0, (Y0 + Y1) / 2, AGUA_Z - 0.8), (20, Y1 - Y0, 0.2))
    objeto("lecho", bm, [M["lecho"]])
    # vertedero: escalón de concreto bajo el agua con una franja de espuma
    bm = bmesh.new()
    caja(bm, (0, PUENTE_Y + 34, AGUA_Z - 0.02), (17.0, 1.2, 0.05))
    objeto("espuma", bm, [simple("espuma", (0.55, 0.57, 0.58), 0.7)])


def mat_hojas():
    """Hojas sueltas de octubre: cada árbol con su mezcla de verde, amarillo y naranja (Object Info ›
    Random) y cada hoja con su tono (Random Per Island, solo en Cycles); la luz de las farolas las
    atraviesa un poco (translúcidas)."""
    def hacer(a):
        info = a.nodo("ShaderNodeObjectInfo")
        geo = a.nodo("ShaderNodeNewGeometry")
        azar = (geo, "Random Per Island")
        f, _ = a.ruido(pos_mundo(a), 0.9, 4.0, 0.6)
        verde, amarillo, naranja = (0.05, 0.09, 0.02), (0.36, 0.26, 0.03), (0.40, 0.12, 0.02)
        otono = a.m("ADD", a.m("MULTIPLY", (info, "Random"), 0.8), a.rango(f, 0.3, 0.7, -0.3, 0.3))
        otono = a.m("ADD", otono, a.m("MULTIPLY", a.m("SUBTRACT", azar, 0.5), 0.35))
        c = a.mezcla(verde, amarillo, a.rango(otono, 0.2, 0.6))
        c = a.mezcla(c, naranja, a.rango(otono, 0.6, 1.0))
        c = a.v("SCALE", c, escala=a.rango(azar, 0.0, 1.0, 0.55, 1.15))
        trasluz = a.nodo("ShaderNodeBsdfTranslucent")
        a.dar(trasluz, "Color", a.v("SCALE", c, escala=0.8))
        return a.mezclar_shader(a.bsdf(c, 0.55), (trasluz, 0), 0.3)
    return material("hojas", hacer)


def malla_triangulos(nombre: str, verts: np.ndarray, mat):
    """Malla de triángulos sueltos desde un arreglo (3·n, 3); rápida aun con cientos de miles."""
    n = len(verts)
    me = bpy.data.meshes.new(nombre)
    me.vertices.add(n)
    me.vertices.foreach_set("co", verts.astype(np.float32).ravel())
    me.loops.add(n)
    me.loops.foreach_set("vertex_index", np.arange(n, dtype=np.int32))
    me.polygons.add(n // 3)
    me.polygons.foreach_set("loop_start", np.arange(0, n, 3, dtype=np.int32))
    me.update(calc_edges=True)
    me.materials.append(mat)
    ob = bpy.data.objects.new(nombre, me)
    enlazar(ob)
    return ob


def hojas_de_copa(masas, g: np.random.Generator, densidad: float = 450.0) -> np.ndarray:
    """Hojas (triángulos de 9 a 20 cm) repartidas cerca de la superficie de cada masa de la copa,
    con bultos y huecos: de lejos se ve follaje con cielo entre las ramas, no una esfera."""
    puntos = []
    for (cx, cy, cz), (rx, ry, rz) in masas:
        n = int(densidad * rx * ry)
        d = g.normal(size=(n, 3))
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        fase = g.uniform(0, math.tau, 3)
        bulto = 1 + 0.14 * np.sin(3.0 * d[:, 0] + fase[0]) * np.sin(2.6 * d[:, 1] + fase[1]) \
            + 0.10 * np.sin(5.0 * d[:, 2] + fase[2])
        prof = 1 - 0.45 * g.random(n) ** 2.5                       # casi todas cerca de la superficie
        r = (bulto * prof)[:, None] * np.array((rx, ry, rz))
        puntos.append(np.array((cx, cy, cz)) + d * r)
    p = np.concatenate(puntos)
    n = len(p)
    tam = g.uniform(0.09, 0.20, n)[:, None]
    nrm = g.normal(size=(n, 3))
    eje = np.cross(nrm, g.normal(size=(n, 3)))
    eje /= np.linalg.norm(eje, axis=1, keepdims=True)
    otro = np.cross(nrm / np.linalg.norm(nrm, axis=1, keepdims=True), eje)
    v0 = p + eje * tam
    v1 = p + (-0.5 * eje + 0.866 * otro) * tam
    v2 = p + (-0.5 * eje - 0.866 * otro) * tam
    return np.stack((v0, v1, v2), axis=1).reshape(-1, 3)


def arbol(i, x, y, M, rng):
    alto = rng.uniform(4.0, 6.0)
    bm = bmesh.new()
    barra(bm, (x, y, 0), (x + rng.uniform(-0.2, 0.2), y + rng.uniform(-0.2, 0.2), alto), rng.uniform(0.16, 0.26), lados=10)
    for _ in range(3):                                        # ramas principales
        a = rng.uniform(0, math.tau)
        barra(bm, (x, y, alto * 0.7), (x + 1.6 * math.cos(a), y + 1.6 * math.sin(a), alto + 1.4), 0.07, lados=6)
    objeto(f"tronco{i}", bm, [M["corteza"]])
    masas = []
    for _ in range(rng.randint(4, 6)):                        # copa: varias masas de hojas
        r = rng.uniform(1.6, 2.6)
        masas.append(((x + rng.uniform(-1.8, 1.8), y + rng.uniform(-1.8, 1.8), alto + rng.uniform(0.6, 3.2)),
                      (r, r, r * rng.uniform(0.75, 0.95))))
    g = np.random.default_rng(1000 + i)                     # aparte: no mueve los demás árboles
    malla_triangulos(f"copa{i}", hojas_de_copa(masas, g), M["hojas"])


def farola(k, x, y, M, alto=4.6, energia=260.0, color=(1.0, 0.70, 0.40), lado=1, base=0.0):
    bm = bmesh.new()
    tope = base + alto
    barra(bm, (x, y, base), (x, y, tope), 0.06, 0, lados=10)
    barra(bm, (x, y, tope), (x - lado * 0.45, y, tope + 0.05), 0.04, 0, lados=8)
    caja(bm, (x - lado * 0.55, y, tope), (0.42, 0.26, 0.12), 0)
    caja(bm, (x - lado * 0.55, y, tope - 0.075), (0.36, 0.2, 0.03), 1)
    objeto(f"farola{k}", bm, [M["metal"], M["lampara"]])
    return luz(f"luz_farola{k}", "SPOT", (x - lado * 0.55, y, tope - 0.12), energia, color, radio=0.15,
               rot=(0, 0, 0), cono=math.radians(130))


def puente(M):
    """Puente de concreto que cruza el río y las dos orillas; barandal y dos farolas."""
    y = PUENTE_Y
    bm = bmesh.new()
    caja(bm, (0, y, 3.6), (70, 9.0, 1.1))
    for x in (-9.0, 9.0):                                      # pilas en las orillas del agua
        caja(bm, (x, y, (AGUA_Z + 3.0) / 2), (1.4, 7.0, 3.0 - AGUA_Z))
    for x in (-22.0, 22.0):                                    # estribos
        caja(bm, (x, y, 1.5), (2.0, 9.0, 3.0))
    objeto("puente", bm, [M["concreto"]])
    bm = bmesh.new()
    for lado in (-1, 1):
        yb = y + lado * 4.4
        barra(bm, (-35, yb, 5.25), (35, yb, 5.25), 0.04, lados=6)
        x = -35.0
        while x <= 35:
            barra(bm, (x, yb, 4.15), (x, yb, 5.25), 0.03, lados=6)
            x += 1.4
    objeto("barandal", bm, [M["barandal"]])
    farola(900, -6.0, y - 4.6, M, alto=4.2, lado=1, base=4.15)
    farola(901, 7.0, y + 4.6, M, alto=4.2, lado=-1, base=4.15)


def ciudad(M, rng):
    for lado in (-1, 1):
        y = Y0
        k = 0
        while y < Y1:
            largo = rng.uniform(18, 34)
            alto = rng.uniform(11, 21)
            bm = bmesh.new()
            caja(bm, (lado * 44, y + largo / 2, alto / 2), (16, largo - 1.5, alto))
            objeto(f"edificio{lado}_{k}", bm, [M["edificio"]],
                   color=rng.choice([(0.8, 0.76, 0.66), (0.72, 0.72, 0.7), (0.85, 0.8, 0.6), (0.7, 0.62, 0.55)]))
            y += largo + rng.uniform(0, 6)
            k += 1
    # lomas de la Selva Negra al fondo
    bm = bmesh.new()
    n = 60
    pts = []
    for i in range(n + 1):
        x = -900 + 1800 * i / n
        z = 70 + 60 * math.sin(i * 0.37) + 35 * math.sin(i * 1.13 + 1) + rng.uniform(0, 12)
        pts.append((bm.verts.new((x, 820, -5)), bm.verts.new((x, 860, z))))
    for (a0, b0), (a1, b1) in zip(pts[:-1], pts[1:]):
        bm.faces.new((a0, a1, b1, b0))
    objeto("lomas", bm, [M["lomas"]])


def armar_rio(M, semilla=4, farolas_derecha=(-46.0, -20.0, 4.0, 28.0, 118.0, 146.0, 174.0),
              farolas_izquierda=(-34.0, -8.0, 18.0, 44.0, 70.0, 96.0, 122.0), energia_farola=380.0, color_farola=(1.0, 0.70, 0.40)):
    """Todo el set. Las farolas se dejan con huecos oscuros, como en la orilla real."""
    rng = random.Random(semilla)
    terreno(M)
    puente(M)
    ciudad(M, rng)
    i = 0
    for lado in (-1, 1):
        y = Y0 + rng.uniform(0, 4)
        while y < Y1:
            if abs(y - PUENTE_Y) > 7:
                arbol(i, lado * rng.uniform(19.3, 20.6), y, M, rng)
                i += 1
            y += rng.uniform(6.0, 9.0)
    luces = []
    for k, y in enumerate(farolas_derecha):
        luces.append(farola(k, 19.0, y, M, energia=energia_farola, color=color_farola, lado=1))
    for k, y in enumerate(farolas_izquierda):
        luces.append(farola(100 + k, -19.0, y, M, energia=energia_farola, color=color_farola, lado=-1))
    for k, y in enumerate(range(int(Y0) + 10, int(Y1), 34)):   # alumbrado de las calles, más alto
        for lado in (-1, 1):
            luces.append(farola(200 + 2 * k + (lado > 0), lado * 23.2, float(y), M, alto=7.5, energia=420.0,
                                color=color_farola, lado=lado))
    return luces


# --------------------------------------------------------------------------- bicicleta (solo sus luces y su sombra)

def bicicleta(M_oscuro):
    """Una bicicleta con su ciclista vistos de lejos y de noche: casi solo una silueta oscura, el faro
    blanco que alumbra el camino de adelante y la luz roja de atrás. Avanza hacia +y."""
    raiz = vacio("bici")
    bm = bmesh.new()
    for yr in (-0.55, 0.55):                                   # ruedas: aros de tubo fino
        aro = [(0.0, yr + 0.34 * math.cos(a), 0.34 + 0.34 * math.sin(a)) for a in [i * math.tau / 18 for i in range(19)]]
        for p0, p1 in zip(aro[:-1], aro[1:]):
            barra(bm, p0, p1, 0.018, lados=5)
    barra(bm, (0, -0.55, 0.34), (0, 0.0, 0.62), 0.02)
    barra(bm, (0, 0.0, 0.62), (0, 0.55, 0.34), 0.02)
    barra(bm, (0, 0.0, 0.62), (0, 0.45, 0.95), 0.02)
    barra(bm, (0, -0.1, 0.3), (0, -0.2, 0.95), 0.02)
    # ciclista: torso inclinado, cabeza, brazos al manubrio, piernas
    barra(bm, (0, -0.2, 1.0), (0, 0.15, 1.55), 0.17, lados=10)
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.12, matrix=Matrix.Translation((0, 0.25, 1.72)))
    barra(bm, (0.15, 0.1, 1.45), (0.2, 0.45, 1.0), 0.05)
    barra(bm, (-0.15, 0.1, 1.45), (-0.2, 0.45, 1.0), 0.05)
    barra(bm, (0.1, -0.2, 1.0), (0.12, 0.05, 0.5), 0.07)
    barra(bm, (-0.1, -0.2, 1.0), (-0.12, -0.15, 0.45), 0.07)
    objeto("silueta_bici", bm, [M_oscuro], padre=raiz)
    bm = bmesh.new()
    caja(bm, (0, 0.62, 0.95), (0.07, 0.05, 0.05))
    objeto("faro_bici", bm, [simple("faro_bici", (1, 1, 1), 0.2, emision=(1.0, 0.97, 0.9), fuerza=40.0)], padre=raiz)
    bm = bmesh.new()
    caja(bm, (0, -0.62, 0.75), (0.05, 0.03, 0.04))
    objeto("piloto_bici", bm, [simple("piloto_bici", (0.5, 0, 0), 0.3, emision=(1.0, 0.02, 0.01), fuerza=30.0)], padre=raiz)
    luz("faro_bici_luz", "SPOT", (0, 0.66, 0.95), 18.0, (1.0, 0.96, 0.9), radio=0.03, padre=raiz,
        rot=(math.radians(-78), 0, 0), cono=math.radians(40))
    luz("piloto_bici_luz", "POINT", (0, -0.7, 0.75), 0.6, (1.0, 0.05, 0.02), radio=0.02, padre=raiz)
    return raiz


# --------------------------------------------------------------------------- escena del crimen al amanecer

def mat_cinta():
    """Cinta de la policía alemana: franjas diagonales rojas y blancas (a lo largo de la cinta, en UV)."""
    def hacer(a):
        uv = (a.nodo("ShaderNodeUVMap"), "UV")
        u, v, _ = a.separar(uv)
        franja = a.m("GREATER_THAN", a.m("FRACT", a.m("MULTIPLY", a.m("ADD", u, a.m("MULTIPLY", v, 0.08)), 5.0)), 0.5)
        color = a.mezcla((0.75, 0.74, 0.72), (0.55, 0.02, 0.03), franja)
        return a.bsdf(color, 0.35, especular=0.6)
    return material("cinta_policial", hacer)


def cinta(nombre, puntos, M_cinta, ancho=0.075, caida=0.06):
    """Cinta tendida entre postes: cada tramo cuelga un poco (catenaria) y lleva UV a lo largo."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UV")
    largo_acum = 0.0
    for (p0, p1) in zip(puntos[:-1], puntos[1:]):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        n = 16
        lado = d.cross(Vector((0, 0, 1))).normalized() if abs(d.z) < d.length * 0.9 else Vector((1, 0, 0))
        filas = []
        for i in range(n + 1):
            s = i / n
            c = p0 + d * s - Vector((0, 0, caida * d.length * 4 * s * (1 - s)))
            gira = 0.35 * math.sin(s * math.pi * 2 + largo_acum)       # la cinta se tuerce un poco
            arriba = Vector((0, 0, 1)) * math.cos(gira) + lado * math.sin(gira)
            filas.append((bm.verts.new(c + arriba * ancho / 2), bm.verts.new(c - arriba * ancho / 2), largo_acum + d.length * s))
        for (a0, b0, u0), (a1, b1, u1) in zip(filas[:-1], filas[1:]):
            f = bm.faces.new((a0, a1, b1, b0))
            for loop, (uu, vv) in zip(f.loops, ((u0, 1), (u1, 1), (u1, 0), (u0, 0))):
                loop[uv].uv = (uu, vv)
        largo_acum += d.length
    return objeto(nombre, bm, [M_cinta])


def mat_marcador():
    return simple("marcador", (0.85, 0.62, 0.02), 0.45)


def marcador_evidencia(k, pos, numero, M_marcador, M_negro, giro=0.0):
    """Marcador amarillo de evidencia (tienda triangular) con su número."""
    bm = bmesh.new()
    w, h, prof = 0.16, 0.13, 0.12
    vs = [bm.verts.new(v) for v in ((-w / 2, -prof / 2, 0), (w / 2, -prof / 2, 0), (w / 2, prof / 2, 0), (-w / 2, prof / 2, 0),
                                    (-w / 2, 0, h), (w / 2, 0, h))]
    for cara in ((0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)):
        bm.faces.new([vs[i] for i in cara])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = objeto(f"marcador{k}", bm, [M_marcador])
    ob.location = pos
    ob.rotation_euler = (0, 0, giro)
    cu = bpy.data.curves.new(f"num{k}", "FONT")
    cu.body = str(numero)
    cu.size = 0.085
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    t = bpy.data.objects.new(f"num{k}", cu)
    t.data.materials.append(M_negro)
    enlazar(t)
    t.parent = ob
    incl = math.atan2(h, prof / 2)                                  # inclinación de la cara del frente
    t.location = (0, -prof / 4 - 0.004 * math.sin(incl), h / 2 + 0.004 * math.cos(incl))
    t.rotation_euler = (incl, 0, 0)
    return ob

