"""El laboratorio forense de la escena 7, hecho con código: la mesa con su tapete antiestático y la
lámpara de anillo, una placa de circuito de un aparato IoT (máscara verde, pistas, chips con su
marca, componentes de montaje superficial, puntos de prueba JTAG), el cautín y los cables finos, la
estación de aire caliente con sus pinzas, el programador de memorias con su adaptador y los aparatos
de la mesa de evidencias (dos teléfonos, una cámara barata, un reloj, una bocina, un termostato y un
sensor industrial).

Las posiciones salen de `tres_d/datos_e07.py`, que también usan los rótulos 2D.
"""

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from tres_d import base as B
from tres_d import datos_e07 as DT

MM = DT.MM


# =========================================================================== materiales

def mat_mascara(nombre="mascara", color=(0.008, 0.060, 0.024), clara=False):
    """Máscara de soldar verde: brillante, con una variación muy leve del grosor de la laca."""
    def hacer(a):
        p = B.pos_mundo(a)
        f, _ = a.ruido(p, 900.0, 3.0, 0.6)
        base = (0.016, 0.105, 0.038) if clara else color
        c = a.v("SCALE", base, escala=a.rango(f, 0.3, 0.7, 0.9, 1.08))
        return a.bsdf(c, a.rango(f, 0.3, 0.7, 0.14, 0.24), coat=0.8, normal=a.bump(f, 0.05, 0.00002))
    return B.material(nombre, hacer)


def mat_metal_rugoso(nombre, color, rug=0.25, escala=1500.0, bump=0.15):
    """Metal con su textura fina (estaño, oro, acero cepillado)."""
    def hacer(a):
        p = B.pos_mundo(a)
        f, _ = a.ruido(p, escala, 3.0, 0.6)
        return a.bsdf(color, a.rango(f, 0.3, 0.7, rug * 0.7, rug * 1.4), metal=1.0, normal=a.bump(f, bump, 0.00002))
    return B.material(nombre, hacer)


def mat_epoxi(nombre="epoxi", color=(0.014, 0.014, 0.016)):
    """Encapsulado negro de los chips: mate, con el granito del molde."""
    def hacer(a):
        p = B.pos_mundo(a)
        f, _ = a.ruido(p, 4000.0, 2.0, 0.5)
        return a.bsdf(color, 0.55, normal=a.bump(f, 0.12, 0.00001), especular=0.35)
    return B.material(nombre, hacer)


def mat_fr4():
    return B.simple("fr4", (0.32, 0.27, 0.12), 0.6)


def mat_tapete():
    """Tapete antiestático gris azulado, de hule mate, con su retícula de broches apenas visible."""
    def hacer(a):
        p = B.pos_mundo(a)
        f, _ = a.ruido(p, 90.0, 4.0, 0.6)
        g, _ = a.ruido(p, 3.0, 3.0, 0.5)
        c = a.v("SCALE", (0.030, 0.038, 0.048), escala=a.rango(g, 0.3, 0.7, 0.85, 1.15))
        return a.bsdf(c, a.rango(f, 0.3, 0.7, 0.62, 0.85), normal=a.bump(f, 0.15, 0.0004))
    return B.material("tapete", hacer)


def mat_texto(nombre, color, rug=0.6, emision=None, fuerza=0.0):
    return B.simple(nombre, color, rug, emision=emision, fuerza=fuerza)


def materiales() -> dict:
    return {
        "mascara": mat_mascara(),
        "pista": mat_mascara("pista", clara=True),
        "fr4": mat_fr4(),
        "oro": mat_metal_rugoso("oro", (1.0, 0.74, 0.36), 0.18, bump=0.05),
        "estano": mat_metal_rugoso("estano", (0.78, 0.78, 0.76), 0.2, bump=0.04),
        "acero": mat_metal_rugoso("acero", (0.62, 0.62, 0.62), 0.3, escala=600.0, bump=0.02),
        "cobre": mat_metal_rugoso("cobre", (0.95, 0.55, 0.32), 0.22, escala=400.0, bump=0.05),
        "epoxi": mat_epoxi(),
        "marcado": mat_texto("marcado", (0.16, 0.16, 0.17), 0.7),
        "serigrafia": mat_texto("serigrafia", (0.62, 0.63, 0.60), 0.7),
        "ceramica": B.simple("ceramica", (0.30, 0.20, 0.10), 0.45),
        "resistor": B.simple("resistor", (0.025, 0.025, 0.027), 0.5),
        "bobina": mat_epoxi("bobina", (0.04, 0.04, 0.045)),
        "hueco": B.simple("hueco", (0.002, 0.002, 0.002), 0.9),
        "tapete": mat_tapete(),
        "plastico_negro": B.simple("plastico_negro", (0.018, 0.018, 0.02), 0.45),
        "goma": B.simple("goma", (0.02, 0.022, 0.025), 0.7),
    }


# =========================================================================== geometría auxiliar

def caja_m(bm, centro, tam, mat=0):
    return B.caja(bm, centro, tam, mat)


def cilindro(bm, centro, radio, alto, mat=0, lados=24, radio_arriba=None):
    M = Matrix.Translation(Vector(centro))
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=lados, radius1=radio,
                              radius2=radio if radio_arriba is None else radio_arriba, depth=alto, matrix=M)
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mat
    return r["verts"]


def rect_redondeado(bm, cx, cy, z0, w, h, r, alto, mat=0, lados_esquina=6, giro=0.0):
    """Losa de esquinas redondeadas (de z0 a z0+alto), girada `giro` radianes alrededor de su centro."""
    pts = []
    for k, (ex, ey) in enumerate(((w / 2 - r, h / 2 - r), (-w / 2 + r, h / 2 - r), (-w / 2 + r, -h / 2 + r), (w / 2 - r, -h / 2 + r))):
        a0 = k * math.pi / 2
        for i in range(lados_esquina + 1):
            a = a0 + (math.pi / 2) * i / lados_esquina
            pts.append((ex + r * math.cos(a), ey + r * math.sin(a)))
    c, s = math.cos(giro), math.sin(giro)
    abajo = [bm.verts.new((cx + x * c - y * s, cy + x * s + y * c, z0)) for x, y in pts]
    arriba = [bm.verts.new((cx + x * c - y * s, cy + x * s + y * c, z0 + alto)) for x, y in pts]
    caras = [bm.faces.new(arriba), bm.faces.new(abajo[::-1])]
    n = len(pts)
    for i in range(n):
        caras.append(bm.faces.new((abajo[i], abajo[(i + 1) % n], arriba[(i + 1) % n], arriba[i])))
    for f in caras:
        f.material_index = mat
    return caras


def texto3d(nombre, cuerpo, pos, tam, mat, giro=0.0, padre=None, alinear="CENTER", negrita=False):
    """Texto plano (serigrafía, marca láser de un chip, etiqueta) acostado sobre una superficie."""
    cu = bpy.data.curves.new(nombre, "FONT")
    cu.body = cuerpo
    cu.size = tam
    cu.align_x = alinear
    cu.align_y = "CENTER"
    if negrita:
        cu.offset = tam * 0.012
    cu.materials.append(mat)
    ob = bpy.data.objects.new(nombre, cu)
    B.enlazar(ob)
    ob.location = pos
    ob.rotation_euler = (0.0, 0.0, giro)
    if padre is not None:
        ob.parent = padre
    return ob


def tubo(nombre, puntos, radio, mat, padre=None, resolucion=4):
    """Cable o manguera que pasa por `puntos` (curva con grosor)."""
    cu = bpy.data.curves.new(nombre, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radio
    cu.bevel_resolution = resolucion
    cu.use_fill_caps = True
    sp = cu.splines.new("NURBS")
    sp.points.add(len(puntos) - 1)
    for i, p in enumerate(puntos):
        sp.points[i].co = (*p, 1.0)
    sp.order_u = min(4, len(puntos))
    sp.use_endpoint_u = True
    cu.materials.append(mat)
    ob = bpy.data.objects.new(nombre, cu)
    B.enlazar(ob)
    if padre is not None:
        ob.parent = padre
    return ob


def desplazar(polilinea, d):
    """Polilínea paralela a `d` mm (uniones en inglete): así un bus de pistas dobla a 45° sin
    acercarse ni separarse."""
    p = [np.asarray(q, float) for q in polilinea]
    salida = []
    for i in range(len(p)):
        normales = []
        if i > 0:
            t = p[i] - p[i - 1]
            normales.append(np.array([-t[1], t[0]]) / np.linalg.norm(t))
        if i < len(p) - 1:
            t = p[i + 1] - p[i]
            normales.append(np.array([-t[1], t[0]]) / np.linalg.norm(t))
        m = sum(normales)
        m = m / np.linalg.norm(m)
        salida.append(p[i] + m * d / max(0.3, float(np.dot(m, normales[0]))))
    return salida


def recorrido(inicio, pasos):
    """Polilínea desde `inicio` con pasos (dirección en grados, largo en mm)."""
    pts = [np.asarray(inicio, float)]
    for ang, largo in pasos:
        a = math.radians(ang)
        pts.append(pts[-1] + largo * np.array([math.cos(a), math.sin(a)]))
    return pts


# =========================================================================== la placa

# Buses de pistas: (inicio del trazo de referencia, pasos, cuántas pistas, separación, ancho) en mm.
BUSES = [
    ((-6.6, 10.0), [(0, 4.0), (45, 4.0), (0, 10.5)], 9, 0.55, 0.22),            # U1 -> U2
    ((-6.6, 1.0), [(0, 5.0), (-45, 3.0), (0, 9.0), (45, 6.0)], 6, 0.55, 0.22),   # U1 -> U2 (abajo)
    ((-18.0, -0.6), [(-90, 3.0), (-90, 7.6)], 8, 0.6, 0.22),                     # U1 -> U3
    ((-21.4, 2.0), [(180, 5.0), (225, 4.0), (180, 13.0), (270, 5.0)], 5, 0.6, 0.25),   # U1 -> USB
    ((-10.0, 13.4), [(90, 4.0), (135, 6.0), (180, 14.0), (90, 1.0)], 5, 0.55, 0.22),   # U1 -> JTAG
    ((15.0, 15.6), [(90, 3.0), (45, 4.0), (0, 10.0)], 6, 0.55, 0.22),           # U2 -> borde
    ((26.8, 4.0), [(0, 4.0), (-45, 6.0), (-90, 4.0)], 5, 0.6, 0.22),            # U2 -> wifi
    ((-9.4, -18.0), [(0, 6.0), (45, 3.0), (0, 4.0)], 4, 0.6, 0.25),             # U3 -> U4
    ((8.0, -20.0), [(-90, 3.0), (-45, 4.0), (0, 12.0)], 4, 0.7, 0.35),          # U4 -> wifi
    ((2.0, -14.0), [(90, 6.0), (135, 4.0), (90, 3.0)], 3, 0.7, 0.45),           # alimentación
    ((-38.0, 20.0), [(-90, 9.0), (-45, 6.0), (-90, 14.0)], 3, 0.8, 0.5),        # alimentación a la izquierda
    ((40.0, 10.0), [(90, 8.0), (135, 5.0), (90, 6.0)], 3, 0.6, 0.25),
    ((-30.0, -26.0), [(0, 10.0), (45, 4.0), (0, 8.0)], 4, 0.6, 0.25),
]


def _pistas(M, centro):
    """Las pistas de cobre bajo la máscara: tiras planas apenas más claras que la placa, con un
    redondeo en cada vértice y una vía al final de cada una."""
    z = DT.GROSOR + 0.012
    verts, caras = [], []
    vias = []

    def tira(a, b, ancho):
        a, b = np.asarray(a), np.asarray(b)
        t = b - a
        largo = np.linalg.norm(t)
        if largo < 1e-6:
            return
        t = t / largo
        n = np.array([-t[1], t[0]]) * ancho / 2
        k = len(verts)
        for q in (a + n, b + n, b - n, a - n):
            verts.append((centro[0] + q[0] * MM, centro[1] + q[1] * MM, centro[2] + z * MM))
        caras.append((k, k + 3, k + 2, k + 1))

    def disco(q, r, lados=8):
        k = len(verts)
        verts.append((centro[0] + q[0] * MM, centro[1] + q[1] * MM, centro[2] + z * MM))
        for i in range(lados):
            a = math.tau * i / lados
            verts.append((centro[0] + (q[0] + r * math.cos(a)) * MM, centro[1] + (q[1] + r * math.sin(a)) * MM,
                          centro[2] + z * MM))
        for i in range(lados):
            caras.append((k, k + 1 + (i + 1) % lados, k + 1 + i))

    for inicio, pasos, n, sep, ancho in BUSES:
        ref = recorrido(inicio, pasos)
        for i in range(n):
            pl = desplazar(ref, (i - (n - 1) / 2) * sep)
            for a, b in zip(pl, pl[1:]):
                tira(a, b, ancho)
            for q in pl[1:-1]:
                disco(q, ancho / 2)
            vias.append(pl[-1])
    me = bpy.data.meshes.new("pistas")
    me.from_pydata(verts, [], caras)
    me.update()
    me.materials.append(M["pista"])
    ob = bpy.data.objects.new("pistas", me)
    B.enlazar(ob)
    # vías: anillo de estaño con su hueco
    bm = bmesh.new()
    for q in vias:
        cilindro(bm, en_m(q, DT.GROSOR + 0.02, centro), 0.32 * MM, 0.04 * MM, 0, lados=10)
        cilindro(bm, en_m(q, DT.GROSOR + 0.045, centro), 0.15 * MM, 0.02 * MM, 1, lados=8)
    B.objeto("vias", bm, [M["estano"], M["hueco"]])


def en_m(q, z_mm, centro):
    return (centro[0] + q[0] * MM, centro[1] + q[1] * MM, centro[2] + z_mm * MM)


def _contorno(bm, x, y, w, h, grosor=0.13, mat=0):
    """Rectángulo de serigrafía alrededor de un componente (cuatro tiras)."""
    z = DT.GROSOR + 0.02
    for cx, cy, sw, sh in ((x, y + h / 2, w + grosor, grosor), (x, y - h / 2, w + grosor, grosor),
                           (x - w / 2, y, grosor, h), (x + w / 2, y, grosor, h)):
        caja_m(bm, (cx * MM, cy * MM, z * MM), (sw * MM, sh * MM, 0.03 * MM), mat)


def placa(M, centro=(0.0, 0.0, 0.0), sin_chip_u2=False, tp_mat=None):
    """La placa completa. Devuelve un diccionario con los objetos que se animan: el chip de memoria
    (U2, con sus esferas de soldadura debajo) y los cinco puntos de prueba JTAG.

    `tp_mat`: material propio para los puntos JTAG (para que se enciendan)."""
    raiz = B.vacio("placa", centro)
    cero = (0.0, 0.0, 0.0)
    # tablero: máscara arriba y abajo, fibra de vidrio en los cantos
    bm = bmesh.new()
    vs = caja_m(bm, (0, 0, DT.GROSOR / 2 * MM), (DT.LARGO * MM, DT.ANCHO * MM, DT.GROSOR * MM), 0)
    for f in {f for v in vs for f in v.link_faces}:
        f.normal_update()
        f.material_index = 0 if abs(f.normal.z) > 0.5 else 1
    tablero = B.objeto("tablero", bm, [M["mascara"], M["fr4"]], padre=raiz)
    del tablero
    _pistas(M, centro)

    # serigrafía: contornos y nombres
    bm = bmesh.new()
    for nombre, (x, y, w, h, alto, _) in DT.CHIPS.items():
        _contorno(bm, x, y, w + 1.2, h + 1.2)
        cilindro(bm, ((x - w / 2 - 1.1) * MM, (y + h / 2 + 1.1) * MM, (DT.GROSOR + 0.03) * MM), 0.3 * MM, 0.03 * MM, 0, 10)
    for x, y, w, h, _ in (DT.BLINDAJE, DT.CRISTAL, DT.BOBINA):
        _contorno(bm, x, y, w + 1.0, h + 1.0)
    B.objeto("serigrafia", bm, [M["serigrafia"]], padre=raiz)
    for nombre, (x, y, w, h, alto, _) in DT.CHIPS.items():
        texto3d(f"ref_{nombre}", nombre, ((x - w / 2 - 0.6) * MM, (y - h / 2 - 2.0) * MM, (DT.GROSOR + 0.05) * MM),
                1.5 * MM, M["serigrafia"], padre=raiz, alinear="LEFT")
    for nombre, (x, y, w, h, _) in (("L1", DT.BOBINA), ("Y1", DT.CRISTAL), ("SH1", DT.BLINDAJE)):
        texto3d(f"ref_{nombre}", nombre, ((x - w / 2) * MM, (y - h / 2 - 1.6) * MM, (DT.GROSOR + 0.05) * MM),
                1.2 * MM, M["serigrafia"], padre=raiz, alinear="LEFT")
    texto3d("rev", "MB-IOT  REV 1.2", (30.0 * MM, -31.0 * MM, (DT.GROSOR + 0.05) * MM), 2.0 * MM, M["serigrafia"], padre=raiz)
    texto3d("fecha", "2019.04", (40.0 * MM, 29.0 * MM, (DT.GROSOR + 0.05) * MM), 1.6 * MM, M["serigrafia"], padre=raiz)

    # agujeros de montaje
    bm = bmesh.new()
    for x, y in DT.AGUJEROS:
        cilindro(bm, (x * MM, y * MM, (DT.GROSOR + 0.02) * MM), 2.6 * MM, 0.05 * MM, 0, 24)
        cilindro(bm, (x * MM, y * MM, (DT.GROSOR + 0.05) * MM), 1.6 * MM, 0.04 * MM, 1, 24)
    B.objeto("agujeros", bm, [M["estano"], M["hueco"]], padre=raiz)

    # chips
    piezas = {}
    for nombre, (x, y, w, h, alto, marca) in DT.CHIPS.items():
        if nombre == "U2" and sin_chip_u2:
            continue
        piezas[nombre] = _chip(M, nombre, x, y, w, h, alto, marca, raiz, bolas=(nombre == "U2"),
                               patas_qfn=(nombre == "U4"))
    # huella de U2: pastillas de estaño donde va soldada (se ven cuando el chip se levanta)
    x, y, w, h, alto, _ = DT.CHIPS["U2"]
    bm = bmesh.new()
    for i in range(12):
        for j in range(14):
            px, py = x - 4.4 + i * 0.8, y - 5.2 + j * 0.8
            cilindro(bm, (px * MM, py * MM, (DT.GROSOR + 0.02) * MM), 0.2 * MM, 0.05 * MM, 0, 8)
    B.objeto("huella_U2", bm, [M["estano"]], padre=raiz)

    # blindaje del wifi, cristal, bobina y USB
    x, y, w, h, alto = DT.BLINDAJE
    bm = bmesh.new()
    caja_m(bm, (x * MM, y * MM, (DT.GROSOR + alto / 2) * MM), (w * MM, h * MM, alto * MM), 0)
    B.objeto("blindaje", bm, [M["estano"]], padre=raiz)
    x, y, w, h, alto = DT.CRISTAL
    bm = bmesh.new()
    caja_m(bm, (x * MM, y * MM, (DT.GROSOR + alto / 2) * MM), (w * MM, h * MM, alto * MM), 0)
    B.objeto("cristal", bm, [M["acero"]], padre=raiz)
    x, y, w, h, alto = DT.BOBINA
    bm = bmesh.new()
    caja_m(bm, (x * MM, y * MM, (DT.GROSOR + alto / 2) * MM), (w * MM, h * MM, alto * MM), 0)
    B.objeto("bobina", bm, [M["bobina"]], padre=raiz)
    texto3d("bobina_marca", "4R7", (x * MM, y * MM, (DT.GROSOR + alto + 0.03) * MM), 1.3 * MM, M["marcado"], padre=raiz)
    x, y, w, h, alto = DT.USB
    bm = bmesh.new()
    caja_m(bm, (x * MM, y * MM, (DT.GROSOR + alto / 2) * MM), (w * MM, h * MM, alto * MM), 0)
    caja_m(bm, ((x - w / 2 + 0.3) * MM, y * MM, (DT.GROSOR + alto / 2) * MM), (0.8 * MM, (h - 1.4) * MM, (alto - 1.2) * MM), 1)
    B.objeto("usb", bm, [M["acero"], M["hueco"]], padre=raiz)

    # componentes pasivos (0402 y 0603) en hileras junto a los chips
    _pasivos(M, raiz)

    # puntos de prueba
    tps = []
    m_tp = tp_mat or M["oro"]
    bm = bmesh.new()
    for x, y in DT.OTROS_TP:
        cilindro(bm, (x * MM, y * MM, (DT.GROSOR + 0.02) * MM), 0.75 * MM, 0.04 * MM, 0, 20)
    B.objeto("otros_tp", bm, [M["oro"]], padre=raiz)
    for k, (x, y) in enumerate(DT.JTAG):
        bm = bmesh.new()
        cilindro(bm, (x * MM, y * MM, (DT.GROSOR + 0.02) * MM), 0.75 * MM, 0.04 * MM, 0, 24)
        tps.append(B.objeto(f"tp_jtag{k}", bm, [m_tp], padre=raiz))
    piezas["jtag"] = tps
    piezas["raiz"] = raiz
    del cero
    return piezas


def _chip(M, nombre, x, y, w, h, alto, marca, raiz, bolas=False, patas_qfn=False):
    """Un chip negro con su marca láser. Si `bolas`, lleva debajo su rejilla de esferas de soldadura
    (BGA) y todo cuelga de un vacío que se puede levantar."""
    pivote = B.vacio(f"chip_{nombre}", (x * MM, y * MM, DT.GROSOR * MM))
    pivote.parent = raiz
    hueco = 0.25 if bolas else 0.0
    bm = bmesh.new()
    # cuerpo con los cantos apenas biselados (sustrato abajo, molde arriba)
    caja_m(bm, (0, 0, (hueco + 0.15) * MM), (w * MM, h * MM, 0.3 * MM), 1)
    caja_m(bm, (0, 0, (hueco + 0.3 + (alto - 0.3) / 2) * MM), ((w - 0.3) * MM, (h - 0.3) * MM, (alto - 0.3) * MM), 0)
    B.objeto(f"{nombre}_cuerpo", bm, [M["epoxi"], M["resistor"] if bolas else M["epoxi"]], padre=pivote)
    if bolas:
        bm = bmesh.new()
        for i in range(12):
            for j in range(14):
                px, py = -4.4 + i * 0.8, -5.2 + j * 0.8
                M_ = Matrix.Translation(Vector((px * MM, py * MM, 0.13 * MM)))
                bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=0.16 * MM, matrix=M_)
        B.objeto(f"{nombre}_bolas", bm, [M["estano"]], padre=pivote, suave=True)
    if patas_qfn:
        bm = bmesh.new()
        for k in range(6):
            u = (-w / 2 + 0.75 + k * (w - 1.5) / 5)
            for (px, py, sx, sy) in ((u, -h / 2, 0.25, 0.5), (u, h / 2, 0.25, 0.5), (-w / 2, u, 0.5, 0.25), (w / 2, u, 0.5, 0.25)):
                caja_m(bm, (px * MM, py * MM, 0.05 * MM), (sx * MM, sy * MM, 0.1 * MM), 0)
        B.objeto(f"{nombre}_patas", bm, [M["estano"]], padre=pivote)
    z = (hueco + alto + 0.01) * MM
    texto3d(f"{nombre}_marca1", marca[0], (0, 0.9 * MM, z), min(w, h) * 0.13 * MM, M["marcado"], padre=pivote)
    if marca[1]:
        texto3d(f"{nombre}_marca2", marca[1], (0, -1.1 * MM, z), min(w, h) * 0.11 * MM, M["marcado"], padre=pivote)
    bm = bmesh.new()                                                   # punto del pin 1
    cilindro(bm, ((-w / 2 + 1.2) * MM, (h / 2 - 1.2) * MM, z), 0.35 * MM, 0.01 * MM, 0, 12)
    B.objeto(f"{nombre}_pin1", bm, [M["marcado"]], padre=pivote)
    return pivote


def _pasivos(M, raiz):
    rng = np.random.default_rng(7)
    hileras = [  # (x0, y0, dirección en grados, cuántos, paso, tamaño 0402/0603, girar 90)
        (-23.5, -4.0, 90, 10, 1.6, "0402", True), (-4.5, -3.0, 90, 9, 1.6, "0402", True),
        (-19.0, 15.0, 0, 7, 1.6, "0402", False), (13.5, 18.0, 0, 8, 1.4, "0402", False),
        (28.5, 0.0, 90, 8, 1.5, "0402", True), (-19.5, -26.0, 0, 6, 1.8, "0603", False),
        (-7.5, -24.0, 90, 5, 1.6, "0402", True), (1.0, -23.5, 0, 6, 1.6, "0402", False),
        (22.0, -26.0, 0, 6, 2.0, "0603", False), (-36.0, 10.0, -90, 6, 2.0, "0603", True),
        (35.0, 18.0, 0, 5, 1.6, "0402", False), (-30.0, 26.0, 0, 4, 1.8, "0603", False),
        (9.0, 3.0, 90, 4, 1.6, "0402", True),
    ]
    bm_cuerpo, bm_metal, bm_pad = bmesh.new(), bmesh.new(), bmesh.new()
    cuerpos_negros = bmesh.new()
    for x0, y0, ang, n, paso, tam, girar in hileras:
        a = math.radians(ang)
        L, A, Al = (1.0, 0.5, 0.35) if tam == "0402" else (1.6, 0.8, 0.45)
        for i in range(n):
            x, y = x0 + i * paso * math.cos(a), y0 + i * paso * math.sin(a)
            lx, ly = (A, L) if girar else (L, A)
            es_res = rng.random() < 0.35
            destino = cuerpos_negros if es_res else bm_cuerpo
            caja_m(destino, (x * MM, y * MM, (DT.GROSOR + 0.04 + Al / 2) * MM), (lx * MM, ly * MM, Al * MM), 0)
            for s in (-1, 1):
                ex, ey = (0, s * (L / 2 - 0.1)) if girar else (s * (L / 2 - 0.1), 0)
                ex2, ey2 = (0, s * (L / 2 + 0.05)) if girar else (s * (L / 2 + 0.05), 0)
                tx, ty = (A + 0.02, 0.2) if girar else (0.2, A + 0.02)
                caja_m(bm_metal, ((x + ex) * MM, (y + ey) * MM, (DT.GROSOR + 0.04 + Al / 2) * MM),
                       (tx * MM, ty * MM, (Al + 0.02) * MM), 0)
                px, py = (A + 0.15, 0.45) if girar else (0.45, A + 0.15)
                caja_m(bm_pad, ((x + ex2) * MM, (y + ey2) * MM, (DT.GROSOR + 0.03) * MM), (px * MM, py * MM, 0.04 * MM), 0)
    B.objeto("capacitores", bm_cuerpo, [M["ceramica"]], padre=raiz)
    B.objeto("resistores", cuerpos_negros, [M["resistor"]], padre=raiz)
    B.objeto("terminales", bm_metal, [M["estano"]], padre=raiz)
    B.objeto("pastillas", bm_pad, [M["estano"]], padre=raiz)


# =========================================================================== mesa, luz y fondo

def mesa(M, ancho=1.4, fondo=0.9):
    """Mesa de trabajo con el tapete antiestático encima (su cara de arriba en z = 0)."""
    bm = bmesh.new()
    caja_m(bm, (0, 0.1, -0.0015), (ancho, fondo, 0.003), 0)
    B.objeto("tapete", bm, [M["tapete"]])
    bm = bmesh.new()
    caja_m(bm, (0, 0.1, -0.023), (ancho + 0.2, fondo + 0.2, 0.04), 0)
    B.objeto("cubierta", bm, [B.simple("cubierta", (0.06, 0.058, 0.055), 0.5)])


def mundo_oscuro(escena, color=(0.003, 0.0035, 0.004)):
    mundo, nt, salida = B.mundo_nuevo(escena, "laboratorio")
    fondo = nt.nodes.new("ShaderNodeBackground")
    fondo.inputs["Color"].default_value = (*color, 1.0)
    fondo.inputs["Strength"].default_value = 1.0
    nt.links.new(fondo.outputs[0], salida.inputs["Surface"])
    return mundo


def panel_reflejo(alto=0.8, lado=1.2, fuerza=0.6, y=0.1):
    """Plafón grande del techo del laboratorio que la cámara no ve: solo aparece reflejado en el
    acero, el estaño, los vidrios y la máscara brillante (en un cuarto negro, el metal se ve negro)."""
    bm = bmesh.new()
    caja_m(bm, (0.0, y, alto), (lado, lado * 0.7, 0.01), 0)
    ob = B.objeto("plafon", bm, [B.simple("plafon", (1, 1, 1), 0.5, emision=(0.92, 0.95, 1.0), fuerza=fuerza)])
    B.poner(ob, "visible_camera", False)
    B.poner(ob, "visible_shadow", False)
    return ob


def lampara_anillo(centro=(0.0, 0.0), alto=0.34, energia=6.0, visible=True):
    """Lámpara de lupa con aro de LED sobre la mesa: luz blanca, suave y pareja desde arriba."""
    ld = bpy.data.lights.new("aro_led", "AREA")
    ld.shape = "DISK"
    ld.size = 0.17
    ld.energy = energia
    ld.color = (0.95, 0.97, 1.0)
    ob = bpy.data.objects.new("aro_led", ld)
    B.enlazar(ob)
    ob.location = (centro[0], centro[1], alto)
    if visible:
        bm = bmesh.new()
        toro(bm, (centro[0], centro[1], alto + 0.004), 0.095, 0.008)
        B.objeto("aro", bm, [B.simple("aro_emisor", (1, 1, 1), 0.3, emision=(0.95, 0.97, 1.0), fuerza=8.0)], suave=True)
    return ob


def toro(bm, centro, r_mayor, r_menor, n_mayor=48, n_menor=12, mat=0):
    """Toro acostado (aro) alrededor de `centro`."""
    filas = []
    for i in range(n_mayor):
        a = math.tau * i / n_mayor
        fila = []
        for j in range(n_menor):
            b = math.tau * j / n_menor
            r = r_mayor + r_menor * math.cos(b)
            fila.append(bm.verts.new((centro[0] + r * math.cos(a), centro[1] + r * math.sin(a),
                                      centro[2] + r_menor * math.sin(b))))
        filas.append(fila)
    for i in range(n_mayor):
        for j in range(n_menor):
            a, b = filas[i], filas[(i + 1) % n_mayor]
            f = bm.faces.new((a[j], b[j], b[(j + 1) % n_menor], a[(j + 1) % n_menor]))
            f.material_index = mat


def luz_lateral(pos, mira, energia=1.5, color=(1.0, 0.82, 0.62), tam=0.25):
    """Luz rasante cálida desde un lado (saca el relieve de las pistas y el brillo del estaño)."""
    ld = bpy.data.lights.new("lateral", "AREA")
    ld.shape = "RECTANGLE"
    ld.size, ld.size_y = tam, tam * 0.5
    ld.energy = energia
    ld.color = color
    ob = bpy.data.objects.new("lateral", ld)
    B.enlazar(ob)
    ob.location = pos
    d = Vector(mira) - Vector(pos)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def mat_pantalla_terminal(fuerza=1.6):
    """Pantalla de monitor con renglones de texto verde de terminal (patrón, no texto real)."""
    def hacer(a):
        tc = (a.nodo("ShaderNodeTexCoord"), "Object")
        x, y, z = a.separar(tc)
        renglon = a.m("FRACT", a.m("MULTIPLY", z, 90.0))
        en_renglon = a.m("LESS_THAN", renglon, 0.55)
        letra = a.nodo("ShaderNodeTexWhiteNoise", noise_dimensions="2D")
        comb = a.nodo("ShaderNodeCombineXYZ")
        a.unir(a.m("FLOOR", a.m("MULTIPLY", x, 160.0)), comb, 0)
        a.unir(a.m("FLOOR", a.m("MULTIPLY", z, 90.0)), comb, 1)
        a.unir((comb, 0), letra, "Vector")
        largo = a.nodo("ShaderNodeTexWhiteNoise", noise_dimensions="2D")
        comb2 = a.nodo("ShaderNodeCombineXYZ")
        a.unir(a.m("FLOOR", a.m("MULTIPLY", z, 90.0)), comb2, 1)
        a.unir((comb2, 0), largo, "Vector")
        corto = a.m("LESS_THAN", a.m("ADD", x, 0.5), a.m("ADD", a.m("MULTIPLY", (largo, "Value"), 0.8), 0.15))
        hay = a.m("MULTIPLY", a.m("MULTIPLY", en_renglon, a.m("GREATER_THAN", (letra, "Value"), 0.35)), corto)
        emis = a.v("SCALE", (0.20, 1.0, 0.40), escala=a.m("ADD", a.m("MULTIPLY", hay, 1.0), 0.03))
        return a.bsdf((0.005, 0.006, 0.006), 0.15, emision=emis, fuerza=fuerza)
    return B.material("pantalla_terminal", hacer)


def fondo_laboratorio(M, y=0.75, ancho=1.2):
    """Detrás, desenfocado: un monitor con texto de terminal, un osciloscopio, carretes de cable de
    cobre, cajas y un anaquel. Solo se adivinan."""
    bm = bmesh.new()
    caja_m(bm, (-0.25, y, 0.21), (0.56, 0.03, 0.34), 0)                      # monitor
    caja_m(bm, (-0.25, y + 0.03, 0.03), (0.06, 0.05, 0.06), 0)
    caja_m(bm, (-0.25, y + 0.02, 0.003), (0.24, 0.16, 0.006), 0)
    B.objeto("monitor", bm, [M["plastico_negro"]])
    bm = bmesh.new()
    caja_m(bm, (-0.25, y - 0.017, 0.215), (0.52, 0.002, 0.30), 0)
    pant = B.objeto("pantalla", bm, [mat_pantalla_terminal()])
    del pant
    bm = bmesh.new()                                                           # osciloscopio
    caja_m(bm, (0.36, y - 0.05, 0.09), (0.32, 0.16, 0.18), 0)
    B.objeto("osciloscopio", bm, [B.simple("osc", (0.10, 0.11, 0.12), 0.5)])
    bm = bmesh.new()
    caja_m(bm, (0.30, y - 0.131, 0.11), (0.15, 0.002, 0.10), 0)
    B.objeto("osc_pantalla", bm, [B.simple("osc_pant", (0.01, 0.01, 0.01), 0.2, emision=(0.25, 0.6, 1.0), fuerza=0.9)])
    for k, (cx, col) in enumerate(((0.10, M["cobre"]), (0.18, M["cobre"]))):       # carretes de cobre
        bm = bmesh.new()
        M_ = Matrix.Translation(Vector((cx, y - 0.10, 0.035))) @ Matrix.Rotation(math.pi / 2, 4, "Y")
        r = bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.035, radius2=0.035, depth=0.05, matrix=M_)
        del r
        B.objeto(f"carrete{k}", bm, [col], suave=True)
    bm = bmesh.new()                                                           # anaquel con cajas
    for k in range(5):
        caja_m(bm, (-0.62 + k * 0.14, y + 0.12, 0.45 + (k % 2) * 0.02), (0.12, 0.2, 0.09 + (k % 3) * 0.02), 0)
    caja_m(bm, (-0.35, y + 0.12, 0.395), (0.8, 0.26, 0.012), 0)
    B.objeto("anaquel", bm, [B.simple("cajas", (0.08, 0.075, 0.07), 0.7)])
    bm = bmesh.new()
    caja_m(bm, (0, y + 0.35, 0.6), (3.0, 0.05, 1.6), 0)
    B.objeto("pared", bm, [B.simple("pared_lab", (0.05, 0.055, 0.06), 0.85)])


# =========================================================================== herramientas

def cautin(M, punta, inclinacion=38.0, rumbo=150.0):
    """Cautín con la punta en `punta`; el mango sube en la dirección `rumbo` (grados desde +x),
    inclinado `inclinacion` grados sobre la mesa. Devuelve el vacío de la punta (para animarlo)."""
    raiz = B.vacio("cautin", punta)
    a, r = math.radians(inclinacion), math.radians(rumbo)
    d = Vector((math.cos(a) * math.cos(r), math.cos(a) * math.sin(r), math.sin(a)))
    giro = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bm = bmesh.new()

    def tramo(z0, z1, r0, r1, mat, lados=24):
        M_ = giro @ Matrix.Translation(Vector((0, 0, (z0 + z1) / 2)))
        rr = bmesh.ops.create_cone(bm, cap_ends=True, segments=lados, radius1=r0, radius2=r1, depth=z1 - z0, matrix=M_)
        for f in {f for v in rr["verts"] for f in v.link_faces}:
            f.material_index = mat
    tramo(0.0, 0.004, 0.00025, 0.0011, 0)           # punta estañada
    tramo(0.004, 0.012, 0.0011, 0.0018, 1)         # punta de cobre niquelado
    tramo(0.012, 0.075, 0.0024, 0.0026, 2)         # vaina de acero
    tramo(0.075, 0.090, 0.0045, 0.0085, 3)         # protector
    tramo(0.090, 0.180, 0.0085, 0.0095, 4)         # mango de goma
    tramo(0.180, 0.200, 0.0095, 0.005, 3)
    mats = [M["estano"], B.simple("niquel", (0.45, 0.42, 0.40), 0.35, metal=1.0), M["acero"],
            B.simple("protector", (0.05, 0.05, 0.055), 0.4), B.simple("mango", (0.03, 0.10, 0.18), 0.6)]
    B.objeto("cautin_cuerpo", bm, mats, padre=raiz, suave=True)
    fin = d * 0.2
    tubo("cautin_cable", [tuple(fin), tuple(fin + Vector((0.02, 0.03, 0.03))), tuple(fin + Vector((0.06, 0.12, 0.02))),
                          tuple(fin + Vector((0.08, 0.30, -0.10)))], 0.0022, M["goma"], padre=raiz)
    return raiz


def soldadura(nombre, centro_m, radio, mat):
    """Gota de soldadura brillante sobre una pastilla (casquete aplastado)."""
    bm = bmesh.new()
    M_ = Matrix.Translation(Vector(centro_m)) @ Matrix.Diagonal((1.0, 1.0, 0.45, 1.0))
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=radio, matrix=M_)
    del mat
    return B.objeto(nombre, bm, [B.simple("soldadura", (0.50, 0.50, 0.49), 0.32, metal=1.0)], suave=True)


def cables_jtag(M, centro, cuantos=5, destino=(-0.03, 0.16, 0.012)):
    """Cables de cobre esmaltado muy finos que salen de cada punto JTAG hacia la interfaz."""
    obs = []
    for k, (x, y) in enumerate(DT.JTAG[:cuantos]):
        p0 = Vector(DT.en_placa(x, y, DT.GROSOR + 0.25, centro))
        p1 = p0 + Vector((0.0005 * (k - 2), 0.003, 0.0035))
        p2 = p0 + Vector((0.002 * (k - 2), 0.018, 0.009))
        p3 = Vector(destino) + Vector((0.0025 * (k - 2), -0.02, 0.006))
        p4 = Vector(destino) + Vector((0.0025 * (k - 2), 0.0, 0.0))
        obs.append(tubo(f"cable{k}", [tuple(p0), tuple(p1), tuple(p2), tuple(p3), tuple(p4)], 0.00018,
                        M["cable_esmalte"] if "cable_esmalte" in M else M["cobre"], resolucion=2))
    return obs


def interfaz_jtag(M, pos):
    """Adaptador JTAG: cajita negra con su conector, un LED verde y el cable USB."""
    raiz = B.vacio("interfaz", pos)
    bm = bmesh.new()
    rect_redondeado(bm, 0, 0, 0, 0.055, 0.032, 0.004, 0.014, 0)
    B.objeto("interfaz_caja", bm, [M["plastico_negro"]], padre=raiz)
    bm = bmesh.new()
    caja_m(bm, (0, -0.017, 0.007), (0.026, 0.004, 0.006), 0)
    B.objeto("interfaz_conector", bm, [M["oro"]], padre=raiz)
    led = B.simple("led_verde", (0.1, 1.0, 0.3), 0.2, emision=(0.2, 1.0, 0.4), fuerza=12.0)
    bm = bmesh.new()
    cilindro(bm, (0.018, 0.006, 0.0145), 0.0012, 0.001, 0, 12)
    B.objeto("interfaz_led", bm, [led], padre=raiz)
    texto3d("interfaz_rotulo", "JTAG", (-0.008, 0.004, 0.0142), 0.006, M["serigrafia"], padre=raiz)
    tubo("interfaz_usb", [(0, 0.016, 0.006), (0.0, 0.05, 0.004), (0.03, 0.12, 0.002), (0.10, 0.25, 0.002)],
         0.0018, M["goma"], padre=raiz)
    return raiz, led


def boquilla_aire(M, centro_m, alto=0.006):
    """Estación de aire caliente: boquilla cuadrada sobre el chip y el tubo que sube al mango."""
    raiz = B.vacio("boquilla", centro_m)
    bm = bmesh.new()
    lado, pared = 0.0155, 0.0006
    for (cx, cy, sx, sy) in ((0, lado / 2, lado, pared), (0, -lado / 2, lado, pared), (lado / 2, 0, pared, lado), (-lado / 2, 0, pared, lado)):
        caja_m(bm, (cx, cy, alto + 0.006), (sx, sy, 0.012), 0)
    caja_m(bm, (0, 0, alto + 0.0125), (lado, lado, 0.001), 0)
    M_ = Matrix.Translation(Vector((0, 0, alto + 0.025)))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.0045, radius2=0.0055, depth=0.024, matrix=M_)
    B.objeto("boquilla_metal", bm, [B.simple("acero_boquilla", (0.78, 0.78, 0.78), 0.16, metal=1.0)], padre=raiz, suave=False)
    tubo("aire_mango", [(0, 0, alto + 0.037), (0.0, 0.0, alto + 0.07), (0.03, 0.05, alto + 0.12), (0.08, 0.12, alto + 0.17)],
         0.011, B.simple("mango_aire", (0.04, 0.04, 0.045), 0.5), padre=raiz)
    return raiz


def pinzas(M, punta):
    """Pinzas antiestáticas de punta curva, abiertas en V; cuelgan de un vacío en la punta."""
    raiz = B.vacio("pinzas", punta)
    bm = bmesh.new()
    for s in (-1, 1):
        p0 = Vector((s * 0.0062, 0.0, 0.0))
        p1 = Vector((s * 0.0075, 0.012, 0.022))
        p2 = Vector((s * 0.006, 0.050, 0.100))
        for a, b, r in ((p0, p1, 0.0007), (p1, p2, 0.0016)):
            d = b - a
            M_ = Matrix.Translation((a + b) / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4() @ Matrix.Diagonal((1.0, 0.45, 1.0, 1.0))
            bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=r, radius2=r * 1.15, depth=d.length, matrix=M_)
    B.objeto("pinzas_metal", bm, [B.simple("acero_pinzas", (0.72, 0.72, 0.72), 0.22, metal=1.0)], padre=raiz)
    return raiz


def programador(M, pos=(0.0, 0.0, 0.0)):
    """Programador de memorias con su adaptador BGA abierto en la tapa (el chip va adentro)."""
    raiz = B.vacio("programador", pos)
    bm = bmesh.new()
    rect_redondeado(bm, 0, 0.0, 0.0, 0.13, 0.09, 0.008, 0.024, 0)
    B.objeto("prog_caja", bm, [B.simple("prog_plastico", (0.055, 0.075, 0.10), 0.45)], padre=raiz)
    bm = bmesh.new()
    rect_redondeado(bm, 0, 0.0, 0.024, 0.042, 0.042, 0.002, 0.008, 0)                # zócalo
    caja_m(bm, (0, 0, 0.0325), (0.0135, 0.0150, 0.001), 1)                              # cavidad
    B.objeto("zocalo", bm, [M["plastico_negro"], B.simple("cavidad", (0.03, 0.03, 0.03), 0.6)], padre=raiz)
    bm = bmesh.new()
    for i in range(12):
        for j in range(14):
            cilindro(bm, (-0.0044 + i * 0.0008, -0.0052 + j * 0.0008, 0.0331), 0.00012, 0.0002, 0, 6)
    B.objeto("zocalo_contactos", bm, [M["oro"]], padre=raiz)
    tapa = B.vacio("tapa_bisagra", (0.0, 0.021, 0.032))
    tapa.parent = raiz
    bm = bmesh.new()
    rect_redondeado(bm, 0, -0.021, 0.0, 0.04, 0.04, 0.002, 0.004, 0)
    cilindro(bm, (0, -0.021, 0.004), 0.007, 0.004, 0, 24)
    B.objeto("tapa", bm, [M["plastico_negro"]], padre=tapa)
    tapa.rotation_euler = (math.radians(-105), 0, 0)
    texto3d("prog_rotulo", "eMMC  BGA153", (0.0, -0.033, 0.0242), 0.0045, M["serigrafia"], padre=raiz)
    led = B.simple("led_lectura", (1.0, 0.6, 0.1), 0.2, emision=(1.0, 0.55, 0.1), fuerza=0.0)
    bm = bmesh.new()
    cilindro(bm, (0.050, -0.032, 0.0245), 0.0018, 0.001, 0, 12)
    B.objeto("prog_led", bm, [led], padre=raiz)
    led2 = B.simple("led_listo", (0.1, 1.0, 0.3), 0.2, emision=(0.2, 1.0, 0.35), fuerza=10.0)
    bm = bmesh.new()
    cilindro(bm, (0.042, -0.032, 0.0245), 0.0018, 0.001, 0, 12)
    B.objeto("prog_led2", bm, [led2], padre=raiz)
    tubo("prog_usb", [(-0.065, 0.02, 0.012), (-0.09, 0.03, 0.010), (-0.14, 0.10, 0.003), (-0.30, 0.20, 0.003)],
         0.0022, M["goma"], padre=raiz)
    return raiz, led


# =========================================================================== aparatos de la mesa (7.0)

def _girar(ob, grados):
    ob.rotation_euler = (0.0, 0.0, math.radians(grados))


def telefono(M, nombre, x, y, giro, w=0.0715, h=0.147, grosor=0.0078, marco=(0.05, 0.05, 0.055)):
    raiz = B.vacio(nombre, (x, y, 0.0))
    _girar(raiz, giro)
    bm = bmesh.new()
    rect_redondeado(bm, 0, 0, 0.0, w, h, 0.009, grosor, 0, 8)
    B.objeto(f"{nombre}_cuerpo", bm, [B.simple(f"{nombre}_marco", marco, 0.3, metal=0.9)], padre=raiz)
    bm = bmesh.new()
    rect_redondeado(bm, 0, 0, grosor, w - 0.001, h - 0.001, 0.0085, 0.0003, 0, 8)
    B.objeto(f"{nombre}_vidrio", bm, [B.simple(f"{nombre}_pantalla", (0.004, 0.004, 0.005), 0.04, coat=1.0)], padre=raiz)
    return raiz


def camara_wifi(M, x, y, giro):
    raiz = B.vacio("camara_wifi", (x, y, 0.0))
    _girar(raiz, giro)
    blanco = B.simple("plastico_blanco", (0.72, 0.72, 0.70), 0.4)
    bm = bmesh.new()
    rect_redondeado(bm, 0, 0, 0.0, 0.05, 0.05, 0.008, 0.006, 0)                 # base
    cilindro(bm, (0, 0, 0.018), 0.005, 0.026, 0, 16)                             # cuello
    B.objeto("cam_base", bm, [blanco], padre=raiz)
    cabeza = B.vacio("cam_cabeza", (0, 0, 0.055))
    cabeza.parent = raiz
    cabeza.rotation_euler = (math.radians(-8), 0, 0)
    bm = bmesh.new()
    rect_redondeado(bm, 0, 0, -0.026, 0.052, 0.046, 0.009, 0.052, 0)
    B.objeto("cam_caja", bm, [blanco], padre=cabeza)
    bm = bmesh.new()
    caja_m(bm, (0, -0.0232, 0.0), (0.044, 0.0006, 0.044), 0)
    B.objeto("cam_frente", bm, [B.simple("frente_negro", (0.006, 0.006, 0.007), 0.1, coat=1.0)], padre=cabeza)
    bm = bmesh.new()
    M_ = Matrix.Translation(Vector((0, -0.0238, 0.005))) @ Matrix.Rotation(math.pi / 2, 4, "X")
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.0105, radius2=0.0095, depth=0.003, matrix=M_)
    B.objeto("cam_aro_lente", bm, [B.simple("aro_lente", (0.35, 0.35, 0.37), 0.25, metal=1.0)], padre=cabeza)
    bm = bmesh.new()
    M_ = Matrix.Translation(Vector((0, -0.0252, 0.005))) @ Matrix.Rotation(math.pi / 2, 4, "X")
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.0075, radius2=0.0075, depth=0.001, matrix=M_)
    B.objeto("cam_lente", bm, [B.simple("lente", (0.01, 0.015, 0.04), 0.03, metal=0.3, coat=1.0)], padre=cabeza)
    return raiz


def reloj(M, x, y, giro):
    raiz = B.vacio("reloj", (x, y, 0.0))
    _girar(raiz, giro)
    bm = bmesh.new()
    rect_redondeado(bm, 0, 0, 0.0035, 0.040, 0.044, 0.010, 0.0105, 0, 8)
    B.objeto("reloj_caja", bm, [B.simple("aluminio", (0.30, 0.30, 0.32), 0.35, metal=1.0)], padre=raiz)
    bm = bmesh.new()
    rect_redondeado(bm, 0, 0, 0.014, 0.036, 0.040, 0.008, 0.0005, 0, 8)
    B.objeto("reloj_pantalla", bm, [B.simple("reloj_vidrio", (0.003, 0.003, 0.004), 0.03, coat=1.0)], padre=raiz)
    correa = B.simple("correa", (0.035, 0.04, 0.05), 0.65)
    for s in (-1, 1):                                                       # correa acostada, en curva
        bm = bmesh.new()
        n = 10
        filas = []
        for i in range(n + 1):
            u = i / n
            yy = s * (0.021 + 0.085 * u)
            zz = 0.0075 * (1 - u) ** 2 + 0.0015
            filas.append([bm.verts.new((xx, yy, zz)) for xx in (-0.011, 0.011)] +
                         [bm.verts.new((xx, yy, zz + 0.0025)) for xx in (0.011, -0.011)])
        for i in range(n):
            a, b = filas[i], filas[i + 1]
            for k in range(4):
                cara = (a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k])
                bm.faces.new(cara if s > 0 else cara[::-1])
        B.objeto(f"correa{s}", bm, [correa], padre=raiz, suave=True)
    return raiz


def bocina_pastilla(M, x, y, giro):
    """Bocina inteligente redonda, forrada de tela gris, con su aro de luz apagado."""
    raiz = B.vacio("bocina", (x, y, 0.0))
    _girar(raiz, giro)
    def tela(a):
        p = B.pos_mundo(a)
        f, _ = a.ruido(p, 2500.0, 2.0, 0.6)
        tr = a.nodo("ShaderNodeTexWave", wave_type="BANDS")
        a.unir(p, tr, "Vector")
        B.entrada(tr, "Scale").default_value = 1800.0
        alto = a.m("ADD", (tr, "Fac"), f)
        return a.bsdf((0.12, 0.12, 0.125), 0.85, normal=a.bump(alto, 0.25, 0.0002))
    bm = bmesh.new()
    cilindro(bm, (0, 0, 0.021), 0.049, 0.042, 0, 48)
    B.objeto("bocina_tela", bm, [B.material("tela_bocina", tela)], padre=raiz, suave=True)
    bm = bmesh.new()
    cilindro(bm, (0, 0, 0.0425), 0.046, 0.0012, 0, 48)
    B.objeto("bocina_tapa", bm, [B.simple("tapa_bocina", (0.10, 0.10, 0.105), 0.5)], padre=raiz)
    return raiz


def termostato(M, x, y, giro):
    raiz = B.vacio("termostato", (x, y, 0.0))
    _girar(raiz, giro)
    bm = bmesh.new()
    cilindro(bm, (0, 0, 0.0035), 0.035, 0.007, 0, 48)
    B.objeto("termo_base", bm, [B.simple("base_blanca", (0.7, 0.7, 0.68), 0.5)], padre=raiz)
    bm = bmesh.new()
    cilindro(bm, (0, 0, 0.018), 0.041, 0.022, 0, 64)
    B.objeto("termo_aro", bm, [B.simple("acero_pulido", (0.75, 0.75, 0.75), 0.12, metal=1.0)], padre=raiz, suave=True)
    bm = bmesh.new()
    cilindro(bm, (0, 0, 0.0292), 0.037, 0.0005, 0, 64)
    B.objeto("termo_cara", bm, [B.simple("termo_vidrio", (0.004, 0.004, 0.005), 0.03, coat=1.0)], padre=raiz)
    return raiz


def sensor_industrial(M, x, y, giro):
    raiz = B.vacio("sensor", (x, y, 0.0))
    _girar(raiz, giro)
    gris = B.simple("policarbonato", (0.42, 0.43, 0.42), 0.45)
    bm = bmesh.new()
    rect_redondeado(bm, 0, 0, 0.0, 0.095, 0.065, 0.006, 0.045, 0)
    rect_redondeado(bm, 0, 0, 0.045, 0.091, 0.061, 0.005, 0.004, 0)
    B.objeto("sensor_caja", bm, [gris], padre=raiz)
    bm = bmesh.new()
    for (cx, cy) in ((-0.042, -0.027), (0.042, -0.027), (-0.042, 0.027), (0.042, 0.027)):
        cilindro(bm, (cx, cy, 0.0495), 0.0022, 0.001, 0, 12)
    B.objeto("sensor_tornillos", bm, [M["acero"]], padre=raiz)
    bm = bmesh.new()
    M_ = Matrix.Translation(Vector((0.052, 0.0, 0.02))) @ Matrix.Rotation(math.pi / 2, 4, "Y")
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.008, radius2=0.008, depth=0.012, matrix=M_)
    B.objeto("prensaestopa", bm, [M["goma"]], padre=raiz)
    tubo("sensor_cable", [(0.058, 0.0, 0.02), (0.08, 0.0, 0.012), (0.11, 0.03, 0.004), (0.13, 0.09, 0.004)], 0.003, M["goma"], padre=raiz)
    bm = bmesh.new()
    M_ = Matrix.Translation(Vector((-0.03, 0.033 + 0.05, 0.006))) @ Matrix.Rotation(math.pi / 2, 4, "X")
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.0045, radius2=0.003, depth=0.1, matrix=M_)
    B.objeto("antena", bm, [M["goma"]], padre=raiz, suave=True)
    bm = bmesh.new()
    caja_m(bm, (0.0, 0.0, 0.0492), (0.05, 0.022, 0.0003), 0)
    B.objeto("sensor_etiqueta", bm, [B.simple("etiqueta_amarilla", (0.70, 0.52, 0.04), 0.5)], padre=raiz)
    texto3d("sensor_texto", "IP67", (0.0, 0.0, 0.04955), 0.008, M["plastico_negro"], padre=raiz)
    return raiz


def etiqueta_evidencia(M, x, y, numero, giro=0.0):
    """Tarjetita blanca de evidencia con su número."""
    raiz = B.vacio(f"etiqueta{numero}", (x, y, 0.0))
    _girar(raiz, giro)
    bm = bmesh.new()
    caja_m(bm, (0, 0, 0.00025), (0.032, 0.022, 0.0005), 0)
    B.objeto(f"etiqueta{numero}_papel", bm, [B.simple("papel", (0.75, 0.74, 0.70), 0.8)], padre=raiz)
    texto3d(f"etiqueta{numero}_n", str(numero), (0.0, 0.0, 0.00055), 0.014, M["plastico_negro"], padre=raiz, negrita=True)
    return raiz


def mesa_aparatos(M):
    A = DT.APARATOS
    telefono(M, "iphone", *A["iphone"], marco=(0.20, 0.20, 0.21))
    telefono(M, "android", *A["android"], w=0.074, h=0.158, grosor=0.0085, marco=(0.03, 0.035, 0.04))
    camara_wifi(M, *A["camara"])
    reloj(M, *A["reloj"])
    bocina_pastilla(M, *A["bocina"])
    termostato(M, *A["termostato"])
    sensor_industrial(M, *A["sensor"])
    for k, nombre in enumerate(("iphone", "android", "camara", "reloj", "bocina", "termostato", "sensor")):
        x, y, g = A[nombre]
        abajo = 0.11 if nombre in ("iphone", "android") else 0.075
        etiqueta_evidencia(M, x, y - abajo, k + 1, giro=math.radians(-4 + 3 * (k % 3)))
