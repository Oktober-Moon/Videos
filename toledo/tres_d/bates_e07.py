"""La casa de James Bates en Bentonville, Arkansas, en noviembre de 2015, hecha con código: la barra
de la cocina de noche con la bocina Amazon Echo (primera generación, con su anillo de luz) y el
patio trasero vacío con la tina de hidromasaje encendida, su vapor en el frío y la luz del porche.

No hay personas: la violencia nunca se muestra; el lugar vacío y sus luces son lo que se ve.
"""

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

from tres_d import base as B
from tres_d import datos_e07 as DT
from tres_d import laboratorio_e07 as LB


# =========================================================================== la bocina Echo

def mat_rejilla_echo():
    """Cuerpo negro mate del Echo con su rejilla de agujeros en los dos tercios de abajo."""
    def hacer(a):
        tc = (a.nodo("ShaderNodeTexCoord"), "Object")
        x, y, z = a.separar(tc)
        ang = a.m("ARCTAN2", y, x)
        u = a.m("FRACT", a.m("MULTIPLY", ang, 72 / math.tau))
        fila = a.m("MULTIPLY", z, 1 / 0.0034)
        desfase = a.m("MULTIPLY", a.m("MODULO", a.m("FLOOR", fila), 2.0), 0.5)
        u = a.m("FRACT", a.m("ADD", u, desfase))
        v = a.m("FRACT", fila)
        du, dv = a.m("SUBTRACT", u, 0.5), a.m("SUBTRACT", v, 0.5)
        r2 = a.m("ADD", a.m("MULTIPLY", du, du), a.m("MULTIPLY", dv, dv))
        en_rejilla = a.m("MULTIPLY", a.m("GREATER_THAN", z, 0.012), a.m("LESS_THAN", z, 0.168))
        agujero = a.m("MULTIPLY", a.m("LESS_THAN", r2, 0.07), en_rejilla)
        color = a.mezcla((0.020, 0.020, 0.022), (0.002, 0.002, 0.002), agujero)
        normal = a.bump(a.m("SUBTRACT", 1.0, agujero), 0.4, 0.0006)
        return a.bsdf(color, a.rango(agujero, 0, 1, 0.42, 0.9), normal=normal)
    return B.material("echo_cuerpo", hacer)


def mat_anillo_echo():
    """El anillo de luz: azul oscuro parejo y un arco cian que gira (nodos «fase», «azul» y «cian»)."""
    def hacer(a):
        tc = (a.nodo("ShaderNodeTexCoord"), "Object")
        x, y, _ = a.separar(tc)
        ang = a.m("ARCTAN2", y, x)
        fase = a.nodo("ShaderNodeValue")
        fase.name = "fase"
        cerca = a.m("COSINE", a.m("SUBTRACT", ang, (fase, 0)))           # 1 en el centro del arco
        arco = a.rango(cerca, math.cos(1.1), 1.0, 0.0, 1.0)
        azul_n = a.nodo("ShaderNodeValue")
        azul_n.name = "azul"
        cian_n = a.nodo("ShaderNodeValue")
        cian_n.name = "cian"
        emis = a.v("ADD", a.v("SCALE", (0.02, 0.18, 1.0), escala=(azul_n, 0)),
                   a.v("SCALE", (0.10, 0.85, 1.0), escala=a.m("MULTIPLY", arco, (cian_n, 0))))
        return a.bsdf((0.02, 0.025, 0.03), 0.25, emision=emis, fuerza=1.0)
    return B.material("echo_anillo", hacer)


def mat_moleteado():
    def hacer(a):
        tc = (a.nodo("ShaderNodeTexCoord"), "Object")
        x, y, _ = a.separar(tc)
        ang = a.m("ARCTAN2", y, x)
        estria = a.m("FRACT", a.m("MULTIPLY", ang, 160 / math.tau))
        return a.bsdf((0.03, 0.03, 0.033), 0.38, metal=0.6, normal=a.bump(estria, 0.3, 0.0002))
    return B.material("echo_aro", hacer)


def echo(pos=DT.ECHO):
    """La bocina Echo de primera generación (23.5 cm de alto, 8.4 de diámetro). Devuelve
    (raíz, material del anillo)."""
    raiz = B.vacio("echo", pos)
    R, A = DT.ECHO_RADIO, DT.ECHO_ALTO
    bm = bmesh.new()
    LB.cilindro(bm, (0, 0, 0.111), R, 0.222, 0, 72)
    B.objeto("echo_cuerpo", bm, [mat_rejilla_echo()], padre=raiz, suave=True)
    anillo = mat_anillo_echo()
    bm = bmesh.new()
    LB.cilindro(bm, (0, 0, 0.224), R + 0.0002, 0.0042, 0, 72)
    B.objeto("echo_anillo", bm, [anillo], padre=raiz, suave=True)
    bm = bmesh.new()
    LB.cilindro(bm, (0, 0, 0.2305), R, 0.0089, 0, 72)
    B.objeto("echo_aro", bm, [mat_moleteado()], padre=raiz, suave=True)
    bm = bmesh.new()
    LB.cilindro(bm, (0, 0, 0.2352), R - 0.0015, 0.0006, 0, 72)
    for k, ang in enumerate((math.radians(60), math.radians(120))):           # botones
        LB.cilindro(bm, (0.026 * math.cos(ang), 0.026 * math.sin(ang), 0.2358), 0.0045, 0.0008, 1, 24)
    B.objeto("echo_tapa", bm, [B.simple("echo_tapa", (0.012, 0.012, 0.013), 0.3, coat=0.4),
                               B.simple("echo_boton", (0.03, 0.03, 0.033), 0.5)], padre=raiz)
    return raiz, anillo


def animar_anillo(mat, cuadros, fps, encendido=None, giro=0.0):
    """El anillo apagado o, desde `encendido` (s), el patrón al oír la palabra: el arco cian gira
    rápido sobre el azul y luego se queda quieto apuntando a quien habla, como el aparato real."""
    nt = mat.node_tree
    fase, azul, cian = nt.nodes["fase"], nt.nodes["azul"], nt.nodes["cian"]
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        if encendido is None or t < encendido:
            va, vc, vf = 0.0, 0.0, giro
        else:
            u = t - encendido
            entra = DT.suave(u / 0.35)
            va = 6.0 * entra
            vc = 14.0 * entra
            vf = giro + 2 * math.tau * DT.suave(u / 1.4) + 0.4 * u
        for n, v in ((fase, vf), (azul, va), (cian, vc)):
            n.outputs[0].default_value = v
            n.outputs[0].keyframe_insert("default_value", frame=f)


# =========================================================================== la cocina de noche

def mat_granito():
    def hacer(a):
        p = B.pos_mundo(a)
        f, _ = a.ruido(p, 260.0, 2.0, 0.5)
        g, _ = a.ruido(p, 40.0, 3.0, 0.6)
        vor = a.nodo("ShaderNodeTexVoronoi")
        a.unir(p, vor, "Vector")
        B.entrada(vor, "Scale").default_value = 180.0
        c = a.mezcla((0.020, 0.016, 0.014), (0.11, 0.09, 0.075), a.rango(f, 0.55, 0.75))
        c = a.mezcla(c, (0.004, 0.004, 0.004), a.m("LESS_THAN", (vor, "Distance"), 0.18))
        return a.bsdf(c, a.rango(g, 0.3, 0.7, 0.10, 0.22), coat=0.3)
    return B.material("granito", hacer)


def mat_azulejo():
    """Azulejo crema del salpicadero con su junta (ladrillo de nodos con hiladas de 7.5 cm)."""
    def hacer(a):
        p = B.pos_mundo(a)
        x, y, z = a.separar(p)
        vec = a.nodo("ShaderNodeCombineXYZ")
        a.unir(a.m("ADD", x, y), vec, 0)
        a.unir(z, vec, 1)
        lad = a.nodo("ShaderNodeTexBrick")
        a.unir((vec, 0), lad, "Vector")
        for k, v in (("Scale", 1.0), ("Mortar Size", 0.003), ("Brick Width", 0.15), ("Row Height", 0.075)):
            B.entrada(lad, k).default_value = v
        lad.offset = 0.5
        B.entrada(lad, "Color1").default_value = (0.50, 0.46, 0.38, 1)
        B.entrada(lad, "Color2").default_value = (0.46, 0.42, 0.35, 1)
        B.entrada(lad, "Mortar").default_value = (0.22, 0.21, 0.19, 1)
        return a.bsdf((lad, "Color"), a.rango((lad, "Fac"), 0, 1, 0.12, 0.7), normal=a.bump((lad, "Fac"), 0.3, 0.002))
    return B.material("azulejo", hacer)


def mat_madera_gabinete():
    def hacer(a):
        p = B.pos_mundo(a)
        x, y, z = a.separar(p)
        vec = a.nodo("ShaderNodeCombineXYZ")
        a.unir(a.m("MULTIPLY", x, 1.0), vec, 0)
        a.unir(a.m("MULTIPLY", z, 0.08), vec, 1)
        vet = a.nodo("ShaderNodeTexWave", wave_type="BANDS")
        a.unir((vec, 0), vet, "Vector")
        B.entrada(vet, "Scale").default_value = 60.0
        B.entrada(vet, "Distortion").default_value = 8.0
        c = a.mezcla((0.10, 0.055, 0.03), (0.16, 0.09, 0.05), (vet, "Fac"))
        return a.bsdf(c, 0.45, coat=0.25)
    return B.material("gabinete", hacer)


def cocina_noche(echo_x=0.0):
    """La barra de la cocina de noche: cubierta de granito, salpicadero de azulejo, gabinetes, una
    ventana con la luz fría de afuera y unos pocos objetos. La bocina queda en DT.ECHO."""
    e = DT.ECHO
    gran, azul, mad = mat_granito(), mat_azulejo(), mat_madera_gabinete()
    bm = bmesh.new()
    LB.caja_m(bm, (e[0], e[1] + 0.05, -0.02), (3.2, 0.66, 0.04), 0)                       # cubierta
    B.objeto("cubierta_granito", bm, [gran])
    bm = bmesh.new()
    LB.caja_m(bm, (e[0], e[1] + 0.05, -0.47), (3.2, 0.62, 0.86), 0)                       # gabinetes de abajo
    B.objeto("gabinetes", bm, [mad])
    bm = bmesh.new()
    LB.caja_m(bm, (e[0], e[1] + 0.39, 0.6), (3.6, 0.02, 1.2), 0)                          # salpicadero
    B.objeto("salpicadero", bm, [azul])
    bm = bmesh.new()
    LB.caja_m(bm, (e[0] + 0.55, e[1] + 0.22, 0.62 + 0.36), (2.0, 0.34, 0.72), 0)          # gabinetes de arriba
    B.objeto("gabinetes_arriba", bm, [mad])
    # ventana a la izquierda con su marco
    bm = bmesh.new()
    LB.caja_m(bm, (e[0] - 1.0, e[1] + 0.385, 0.62), (0.9, 0.03, 0.85), 0)
    vidrio = B.objeto("vidrio_ventana", bm, [B.simple("vidrio_noche", (0.01, 0.015, 0.03), 0.05, emision=(0.08, 0.12, 0.25), fuerza=0.6)])
    vidrio.visible_shadow = False                                          # deja pasar la luz de afuera
    bm = bmesh.new()
    for (cx, cz, sx, sz) in ((0, 0.205, 0.94, 0.04), (0, 1.035, 0.94, 0.04), (-0.45, 0.62, 0.04, 0.87), (0.45, 0.62, 0.04, 0.87), (0, 0.62, 0.03, 0.85)):
        LB.caja_m(bm, (e[0] - 1.0 + cx, e[1] + 0.37, cz), (sx, 0.05, sz), 0)
    B.objeto("marco_ventana", bm, [B.simple("marco", (0.55, 0.53, 0.50), 0.5)])
    # luz de la noche por la ventana (fría) y un resplandor tibio que viene de otra habitación
    ld = bpy.data.lights.new("luz_ventana", "AREA")
    ld.shape, ld.size, ld.size_y = "RECTANGLE", 0.9, 0.85
    ld.energy, ld.color = 14.0, (0.55, 0.68, 1.0)
    ob = B.enlazar(bpy.data.objects.new("luz_ventana", ld))
    ob.location = (e[0] - 1.0, e[1] + 0.55, 0.62)
    ob.rotation_euler = (math.radians(-80), 0.0, math.radians(-25))
    B.luz("pasillo", "POINT", (e[0] + 2.2, e[1] - 1.8, 1.4), 18.0, (1.0, 0.62, 0.32), radio=0.4)
    # la tira de luz bajo los gabinetes, que se queda prendida de noche: baña la barra y el salpicadero
    tira = bpy.data.lights.new("bajo_gabinete", "AREA")
    tira.shape, tira.size, tira.size_y = "RECTANGLE", 1.7, 0.05
    tira.energy, tira.color = 5.0, (1.0, 0.80, 0.58)
    ob = B.enlazar(bpy.data.objects.new("bajo_gabinete", tira))
    ob.location = (e[0] + 0.55, e[1] + 0.30, 0.61)
    # contraluz fría que separa el cilindro negro del fondo
    B.luz("contraluz", "POINT", (e[0] - 0.35, e[1] + 0.32, 0.42), 1.2, (0.6, 0.72, 1.0), radio=0.05)
    # cafetera, frutero y portarrollos
    bm = bmesh.new()
    LB.rect_redondeado(bm, e[0] + 0.75, e[1] + 0.18, 0.0, 0.2, 0.25, 0.02, 0.36, 0)
    B.objeto("cafetera", bm, [B.simple("cafetera", (0.02, 0.02, 0.022), 0.35)])
    bm = bmesh.new()
    LB.cilindro(bm, (e[0] - 0.45, e[1] + 0.02, 0.045), 0.13, 0.09, 0, 48, radio_arriba=0.15)
    B.objeto("frutero", bm, [B.simple("ceramica_blanca", (0.6, 0.58, 0.55), 0.25)])
    bm = bmesh.new()
    LB.cilindro(bm, (e[0] + 0.32, e[1] + 0.24, 0.14), 0.055, 0.27, 0, 32)
    B.objeto("portarrollos", bm, [B.simple("papel_cocina", (0.62, 0.62, 0.60), 0.8)])
    # piso y pared de enfrente (solo para que la luz rebote)
    bm = bmesh.new()
    LB.caja_m(bm, (e[0], e[1] - 1.2, -0.92), (6.0, 4.0, 0.02), 0)
    B.objeto("piso_cocina", bm, [B.simple("piso_cocina", (0.08, 0.07, 0.06), 0.5)])


# =========================================================================== el patio y la tina

def mat_ladrillo():
    def hacer(a):
        p = B.pos_mundo(a)
        x, y, z = a.separar(p)
        vec = a.nodo("ShaderNodeCombineXYZ")
        a.unir(a.m("ADD", x, y), vec, 0)
        a.unir(z, vec, 1)
        lad = a.nodo("ShaderNodeTexBrick")
        a.unir((vec, 0), lad, "Vector")
        for k, v in (("Scale", 1.0), ("Mortar Size", 0.010), ("Brick Width", 0.205), ("Row Height", 0.068),
                     ("Bias", 0.0)):
            B.entrada(lad, k).default_value = v
        B.entrada(lad, "Color1").default_value = (0.24, 0.085, 0.05, 1)
        B.entrada(lad, "Color2").default_value = (0.17, 0.065, 0.045, 1)
        B.entrada(lad, "Mortar").default_value = (0.30, 0.28, 0.25, 1)
        f, _ = a.ruido(p, 30.0, 4.0, 0.6)
        c = a.v("SCALE", (lad, "Color"), escala=a.rango(f, 0.3, 0.7, 0.75, 1.2))
        alto = a.m("ADD", a.m("MULTIPLY", (lad, "Fac"), -1.0), a.m("MULTIPLY", f, 0.3))
        return a.bsdf(c, 0.85, normal=a.bump(alto, 0.5, 0.006))
    return B.material("ladrillo", hacer)


def mat_tablillas(nombre="tablillas", color=(0.10, 0.075, 0.055), ancho=0.09, vertical=True):
    """Tablillas de madera (gabinete de la tina, cerca): franjas con su veta y una junta oscura."""
    def hacer(a):
        p = B.pos_mundo(a)
        x, y, z = a.separar(p)
        s = a.m("ADD", x, y) if vertical else z
        franja = a.m("FRACT", a.m("MULTIPLY", s, 1 / ancho))
        junta = a.m("MULTIPLY", a.m("GREATER_THAN", franja, 0.05), a.m("LESS_THAN", franja, 0.95))
        vec = a.nodo("ShaderNodeCombineXYZ")
        a.unir(a.m("MULTIPLY", s, 40.0), vec, 0)
        a.unir(a.m("MULTIPLY", z if vertical else a.m("ADD", x, y), 1.5), vec, 1)
        a.unir(a.m("FLOOR", a.m("MULTIPLY", s, 1 / ancho)), vec, 2)
        vet, _ = a.ruido((vec, 0), 3.0, 6.0, 0.6)
        c = a.v("SCALE", color, escala=a.m("MULTIPLY", a.rango(vet, 0.3, 0.7, 0.7, 1.25), a.rango(junta, 0, 1, 0.25, 1.0)))
        return a.bsdf(c, 0.75, normal=a.bump(a.m("ADD", junta, a.m("MULTIPLY", vet, 0.3)), 0.4, 0.003))
    return B.material(nombre, hacer)


def mat_agua_tina():
    """Agua de la tina iluminada desde abajo: casi espejo arriba, con un resplandor turquesa que sale
    de adentro; las ondas finas se animan con el nodo «ondas»."""
    def hacer(a):
        p = B.pos_mundo(a)
        mapeo = a.nodo("ShaderNodeMapping")
        mapeo.name = "mov"
        a.unir(p, mapeo, "Vector")
        n = a.nodo("ShaderNodeTexNoise", noise_dimensions="4D")
        n.name = "ondas"
        a.unir((mapeo, 0), n, "Vector")
        for k, v in (("Scale", 3.0), ("Detail", 5.0), ("Roughness", 0.55)):
            B.entrada(n, k).default_value = v
        x, y, _ = a.separar(p)
        r = a.m("SQRT", a.m("ADD", a.m("MULTIPLY", x, x), a.m("MULTIPLY", y, y)))
        brillo = a.rango(r, 0.0, 1.1, 1.0, 0.35)
        emis = a.v("SCALE", (0.10, 0.55, 0.75), escala=a.m("MULTIPLY", brillo, a.rango((n, "Fac"), 0.3, 0.7, 0.8, 1.2)))
        return a.bsdf((0.004, 0.012, 0.016), 0.03, normal=a.bump((n, "Fac"), 0.18, 0.02), especular=0.8,
                      emision=emis, fuerza=0.55)
    return B.material("agua_tina", hacer)


def mat_vapor():
    """Vapor sobre el agua caliente: espeso abajo, se deshace hacia arriba; se mueve con «vapor_w»."""
    mat = bpy.data.materials.new("vapor")
    a = B.Arbol(mat)
    n = a.nodo("ShaderNodeVolumePrincipled")
    B.entrada(n, "Color").default_value = (0.85, 0.9, 0.95, 1)
    B.entrada(n, "Anisotropy").default_value = 0.35
    p = B.pos_mundo(a)
    _, _, z = a.separar(p)
    ruido = a.nodo("ShaderNodeTexNoise", noise_dimensions="4D")
    ruido.name = "vapor_w"
    a.unir(a.v("MULTIPLY", p, (1.0, 1.0, 0.6)), ruido, "Vector")
    B.entrada(ruido, "Scale").default_value = 2.2
    B.entrada(ruido, "Detail").default_value = 4.0
    perfil = a.rango(z, DT.JACUZZI_ALTO - 0.12, DT.JACUZZI_ALTO + 0.9, 1.0, 0.0)
    dens = a.m("MULTIPLY", a.m("MULTIPLY", perfil, a.rango((ruido, "Fac"), 0.45, 0.7, 0.0, 1.0)), 0.9)
    a.unir(dens, n, "Density")
    a.final((n, 0), "Volume")
    return mat


def animar_tina(mat_agua, mat_vapor_, cuadros, fps):
    nt = mat_agua.node_tree
    mov, ondas = nt.nodes["mov"], nt.nodes["ondas"]
    vap = mat_vapor_.node_tree.nodes["vapor_w"]
    mapa_v = None
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        mov.inputs["Location"].default_value = (0.03 * t, 0.02 * t, 0.0)
        mov.inputs["Location"].keyframe_insert("default_value", frame=f)
        ondas.inputs["W"].default_value = 0.35 * t
        ondas.inputs["W"].keyframe_insert("default_value", frame=f)
        vap.inputs["W"].default_value = 0.12 * t
        vap.inputs["W"].keyframe_insert("default_value", frame=f)
    del mapa_v


def tina(centro=DT.JACUZZI):
    """La tina de hidromasaje: gabinete de tablillas, borde de acrílico, asientos, agua iluminada
    desde abajo y el vapor encima. Devuelve los materiales que se animan."""
    cx, cy = centro
    L, A = DT.JACUZZI_LADO, DT.JACUZZI_ALTO
    bm = bmesh.new()                                    # gabinete: cuatro costados huecos (el agua se ve)
    g = 0.1
    for (dx, dy, sx, sy) in ((0, L / 2 - g / 2 - 0.02, L - 0.04, g), (0, -L / 2 + g / 2 + 0.02, L - 0.04, g),
                             (L / 2 - g / 2 - 0.02, 0, g, L - 0.04), (-L / 2 + g / 2 + 0.02, 0, g, L - 0.04)):
        LB.caja_m(bm, (cx + dx, cy + dy, A / 2 - 0.03), (sx, sy, A - 0.06), 0)
    B.objeto("tina_gabinete", bm, [mat_tablillas("gabinete_tina", (0.085, 0.07, 0.06), 0.085)])
    acrilico = B.simple("acrilico", (0.62, 0.64, 0.66), 0.15, coat=0.6)
    bm = bmesh.new()
    pared = 0.16
    for (dx, dy, sx, sy) in ((0, L / 2 - pared / 2, L, pared), (0, -L / 2 + pared / 2, L, pared),
                             (L / 2 - pared / 2, 0, pared, L - 2 * pared), (-L / 2 + pared / 2, 0, pared, L - 2 * pared)):
        LB.caja_m(bm, (cx + dx, cy + dy, A - 0.03), (sx, sy, 0.06), 0)
    # asientos del interior (escalones bajo el agua)
    for (dx, dy, sx, sy) in ((0, L / 2 - 0.42, L - 0.32, 0.5), (-L / 2 + 0.42, 0, 0.5, L - 0.32)):
        LB.caja_m(bm, (cx + dx, cy + dy, 0.45), (sx, sy, 0.06), 0)
    LB.caja_m(bm, (cx, cy, 0.06), (L - 0.32, L - 0.32, 0.04), 0)
    for (dx, dy, sx, sy) in ((0, L / 2 - pared - 0.01, L - 2 * pared, 0.02), (0, -L / 2 + pared + 0.01, L - 2 * pared, 0.02),
                             (L / 2 - pared - 0.01, 0, 0.02, L - 2 * pared), (-L / 2 + pared + 0.01, 0, 0.02, L - 2 * pared)):
        LB.caja_m(bm, (cx + dx, cy + dy, A / 2), (sx, sy, A - 0.08), 0)       # paredes interiores de la tina
    B.objeto("tina_acrilico", bm, [acrilico])
    agua = mat_agua_tina()
    bm = bmesh.new()
    LB.caja_m(bm, (cx, cy, A - 0.11), (L - 2 * pared, L - 2 * pared, 0.004), 0)
    sup = B.objeto("tina_agua", bm, [agua])
    sup.visible_shadow = False                                             # la luz de adentro sale al vapor
    B.luz("luz_tina", "POINT", (cx, cy, A - 0.35), 20.0, (0.35, 0.80, 1.0), radio=0.3)
    B.luz("luz_tina_borde", "POINT", (cx, cy, A + 0.25), 6.0, (0.45, 0.85, 1.0), radio=0.6)
    vapor = mat_vapor()
    bm = bmesh.new()
    LB.caja_m(bm, (cx, cy, A + 0.35), (L - 0.3, L - 0.3, 0.9), 0)
    B.objeto("vapor", bm, [vapor])
    return agua, vapor


def silla_patio(nombre, x, y, giro, metal):
    """Silla de patio de aluminio vacía (marco y tiras)."""
    raiz = B.vacio(nombre, (x, y, 0.0))
    raiz.rotation_euler = (0, 0, math.radians(giro))
    bm = bmesh.new()
    for sx in (-0.25, 0.25):
        B.barra(bm, (sx, -0.25, 0.0), (sx, -0.22, 0.42), 0.012)
        B.barra(bm, (sx, 0.25, 0.0), (sx, 0.24, 0.42), 0.012)
        B.barra(bm, (sx, -0.22, 0.42), (sx, 0.24, 0.42), 0.012)
        B.barra(bm, (sx, 0.24, 0.42), (sx, 0.32, 0.92), 0.012)
        B.barra(bm, (sx, -0.22, 0.62), (sx, 0.10, 0.62), 0.010)
    for k in range(6):
        y0 = -0.2 + k * 0.08
        B.barra(bm, (-0.25, y0, 0.425), (0.25, y0, 0.425), 0.008)
    for z0 in (0.70, 0.88):                             # respaldo: dos travesaños
        yy = 0.24 + (z0 - 0.42) / 0.5 * 0.08
        B.barra(bm, (-0.25, yy, z0), (0.25, yy, z0), 0.012)
    B.objeto(f"{nombre}_marco", bm, [metal], padre=raiz)
    return raiz


def manguera(x, y, mat):
    """Manguera de jardín enrollada en el piso, junto a la llave de la pared."""
    bm = bmesh.new()
    for k in range(4):
        LB.toro(bm, (x, y, 0.016 + k * 0.006), 0.22 - k * 0.025, 0.012, 40, 8)
    B.objeto("manguera", bm, [mat], suave=True)


def patio(escena):
    """El patio trasero de noche: losa de concreto, la pared de ladrillo de la casa con su puerta
    corrediza oscura y la luz del porche, la tina, dos sillas vacías, la manguera enrollada, el pasto
    y la cerca de madera, con árboles pelones detrás."""
    from tres_d import pbr as PB
    PB.hdri(escena, "NightEnvironmentHDRI002_4K", fuerza=0.10, giro_grados=200.0, fondo_camara="madrugada")
    cx, cy = DT.JACUZZI
    concreto = PB.material_pbr("concreto_patio", "Concrete031_2K-JPG", 2.0, "FLAT", brillo=0.75, relieve=0.4)
    pasto = PB.material_pbr("pasto_patio", "Grass004_2K-JPG", 2.0, "FLAT", brillo=0.45, relieve=0.8)
    bm = bmesh.new()
    LB.caja_m(bm, (cx - 0.5, cy + 0.6, -0.05), (7.0, 6.4, 0.1), 0)
    B.objeto("losa", bm, [concreto])
    bm = bmesh.new()
    LB.caja_m(bm, (cx, cy - 4.0, -0.11), (40.0, 30.0, 0.1), 0)
    B.objeto("pasto", bm, [pasto])
    # la casa: pared de ladrillo detrás de la tina
    yp = cy + 3.8
    bm = bmesh.new()
    LB.caja_m(bm, (cx, yp + 0.15, 1.6), (16.0, 0.3, 3.2), 0)
    B.objeto("pared_casa", bm, [mat_ladrillo()])
    bm = bmesh.new()
    LB.caja_m(bm, (cx - 1.9, yp - 0.02, 1.08), (1.9, 0.04, 2.1), 0)
    # vidrio oscuro con cortina detrás: refleja poco y borroso (un reflejo nítido de las luces del patio
    # en la puerta se leía como fuego)
    B.objeto("puerta_corrediza", bm, [B.simple("vidrio_oscuro", (0.006, 0.007, 0.009), 0.28, coat=0.2)])
    bm = bmesh.new()
    for (dx, dz, sx, sz) in ((0, 2.16, 2.0, 0.08), (-0.97, 1.08, 0.06, 2.16), (0.97, 1.08, 0.06, 2.16), (0, 1.08, 0.05, 2.16)):
        LB.caja_m(bm, (cx - 1.9 + dx, yp - 0.04, dz), (sx, 0.06, sz), 0)
    B.objeto("marco_puerta", bm, [B.simple("marco_blanco", (0.55, 0.55, 0.52), 0.5)])
    # una ventana con luz tibia detrás de la cortina
    bm = bmesh.new()
    LB.caja_m(bm, (cx + 2.4, yp - 0.02, 1.55), (1.2, 0.04, 1.1), 0)
    def cortina(a):                                     # luz tibia filtrada: más clara al centro, con pliegues
        p = B.pos_mundo(a)
        x, _, z = a.separar(p)
        pliegue = a.nodo("ShaderNodeTexWave", wave_type="BANDS")
        a.unir(p, pliegue, "Vector")
        B.entrada(pliegue, "Scale").default_value = 9.0
        centro = a.m("MULTIPLY", a.rango(a.m("ABSOLUTE", a.m("SUBTRACT", x, cx + 2.4)), 0.0, 0.6, 1.0, 0.35),
                     a.rango(a.m("ABSOLUTE", a.m("SUBTRACT", z, 1.55)), 0.0, 0.55, 1.0, 0.5))
        fuerza = a.m("MULTIPLY", centro, a.rango((pliegue, "Fac"), 0, 1, 0.7, 1.0))
        return a.bsdf((0.10, 0.07, 0.05), 0.8, emision=a.v("SCALE", (1.0, 0.62, 0.30), escala=fuerza), fuerza=0.09)
    B.objeto("ventana_casa", bm, [B.material("cortina", cortina)])
    bm = bmesh.new()
    for (dx, dz, sx, sz) in ((0, 0.57, 1.3, 0.06), (0, -0.57, 1.36, 0.08), (-0.63, 0, 0.06, 1.16), (0.63, 0, 0.06, 1.16)):
        LB.caja_m(bm, (cx + 2.4 + dx, yp - 0.05, 1.55 + dz), (sx, 0.06, sz), 0)
    B.objeto("marco_ventana_casa", bm, [B.simple("marco_ventana_b", (0.55, 0.55, 0.52), 0.5)])
    # alero del techo sobre la pared
    bm = bmesh.new()
    LB.caja_m(bm, (cx, yp - 0.2, 3.25), (16.4, 0.9, 0.18), 0)
    LB.caja_m(bm, (cx, yp - 0.62, 3.12), (16.4, 0.06, 0.16), 0)
    B.objeto("alero", bm, [B.simple("alero", (0.06, 0.055, 0.05), 0.7)])
    # luz del porche
    bm = bmesh.new()
    LB.caja_m(bm, (cx - 0.55, yp - 0.07, 2.25), (0.16, 0.12, 0.26), 0)
    B.objeto("farol_porche", bm, [B.simple("farol_porche", (1.0, 0.8, 0.5), 0.3, emision=(1.0, 0.72, 0.40), fuerza=6.0)])
    B.luz("luz_porche", "POINT", (cx - 0.55, yp - 0.25, 2.2), 70.0, (1.0, 0.68, 0.38), radio=0.12)
    # llave de la manguera y la manguera
    bm = bmesh.new()
    LB.cilindro(bm, (cx + 1.3, yp - 0.05, 0.45), 0.02, 0.08, 0, 12)
    B.objeto("llave", bm, [B.simple("laton", (0.6, 0.45, 0.2), 0.3, metal=1.0)])
    manguera(cx + 1.45, yp - 0.45, B.simple("manguera", (0.03, 0.12, 0.04), 0.45))
    # la tina
    agua, vapor = tina((cx, cy))
    aluminio = B.simple("aluminio_silla", (0.25, 0.25, 0.26), 0.35, metal=1.0)
    silla_patio("silla1", cx - 2.2, cy - 0.6, 70.0, aluminio)
    silla_patio("silla2", cx - 2.1, cy + 0.6, 100.0, aluminio)
    # cerca de madera al fondo y a los lados, y árboles pelones detrás
    cerca = mat_tablillas("cerca", (0.07, 0.05, 0.035), 0.14)
    bm = bmesh.new()
    LB.caja_m(bm, (cx, cy - 9.5, 0.9), (20.0, 0.05, 1.85), 0)
    LB.caja_m(bm, (cx - 8.0, cy - 3.0, 0.9), (0.05, 13.0, 1.85), 0)
    LB.caja_m(bm, (cx + 8.0, cy - 3.0, 0.9), (0.05, 13.0, 1.85), 0)
    B.objeto("cerca", bm, [cerca])
    corteza = B.simple("corteza_noche", (0.03, 0.025, 0.02), 0.85)
    rng = random.Random(15)
    bm = bmesh.new()
    for k in range(9):
        x = cx - 10 + k * 2.6 + rng.uniform(-0.6, 0.6)
        y = cy + 8.0 + rng.uniform(0, 4)                 # detrás de la casa: asoman sobre el alero
        alto = rng.uniform(6, 9)
        B.barra(bm, (x, y, 0), (x + rng.uniform(-0.3, 0.3), y, alto), rng.uniform(0.12, 0.2), lados=8)
        for _ in range(5):
            z0 = alto * rng.uniform(0.45, 0.85)
            a = rng.uniform(0, math.tau)
            largo = rng.uniform(1.2, 2.6)
            B.barra(bm, (x, y, z0), (x + largo * math.cos(a), y + largo * math.sin(a) * 0.4, z0 + largo * 0.9), 0.04, lados=5)
    B.objeto("arboles", bm, [corteza])
    # neblina muy leve del frío
    B.neblina((cx, cy - 2, 2.0), (30, 26, 4.5), 0.004, (0.55, 0.62, 0.75), anisotropia=0.4, nombre="frio")
    return agua, vapor
