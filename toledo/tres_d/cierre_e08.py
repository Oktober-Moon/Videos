"""Lugares del cierre (escena 8): el cielo del atardecer sobre el Dreisam (el río de la escena 1, con
sus mismos taludes, árboles y puente) y la cocina vacía de una casa de Connecticut con la luz de la
mañana entrando por la ventana.
"""

import math

import bmesh
import bpy
from mathutils import Vector

from tres_d import base as B


# =========================================================================== atardecer

def cielo_atardecer(escena, fuerza=1.0):
    """Degradado de atardecer: naranja encendido en el horizonte hacia +y (donde se puso el sol),
    durazno, lila y azul profundo arriba. Ilumina poco: la luz la pone el sol bajo."""
    mundo, nt, salida = B.mundo_nuevo(escena, "atardecer")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(sep.outputs[2], rampa.inputs[0])
    els = rampa.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.95, 0.42, 0.14, 1)
    els[1].position, els[1].color = 1.0, (0.020, 0.035, 0.11, 1)
    els.new(0.06).color = (0.85, 0.40, 0.22, 1)
    els.new(0.16).color = (0.42, 0.26, 0.32, 1)
    els.new(0.38).color = (0.10, 0.12, 0.28, 1)
    punto = nt.nodes.new("ShaderNodeVectorMath")
    punto.operation = "DOT_PRODUCT"
    nt.links.new(coord.outputs["Generated"], punto.inputs[0])
    punto.inputs[1].default_value = (0.0, 1.0, 0.0)
    rango = nt.nodes.new("ShaderNodeMapRange")
    nt.links.new(punto.outputs["Value"], rango.inputs[0])
    rango.inputs[1].default_value, rango.inputs[2].default_value = 0.3, 1.0
    rango.inputs[3].default_value, rango.inputs[4].default_value = 0.35, 1.25
    escala = nt.nodes.new("ShaderNodeVectorMath")
    escala.operation = "SCALE"
    nt.links.new(rampa.outputs["Color"], escala.inputs[0])
    nt.links.new(rango.outputs[0], escala.inputs["Scale"])
    fondo = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(escala.outputs[0], fondo.inputs["Color"])
    fondo.inputs["Strength"].default_value = fuerza
    nt.links.new(fondo.outputs[0], salida.inputs["Surface"])
    return mundo


def sol(rumbo_grados, altura_grados, energia, color, angulo=1.5):
    """Sol (luz direccional) que viene desde el rumbo dado (grados desde +x), a esa altura."""
    ld = bpy.data.lights.new("sol", "SUN")
    ld.energy = energia
    ld.color = color
    B.poner(ld, "angle", math.radians(angulo))
    ob = B.enlazar(bpy.data.objects.new("sol", ld))
    a, h = math.radians(rumbo_grados), math.radians(altura_grados)
    hacia = Vector((math.cos(a) * math.cos(h), math.sin(a) * math.cos(h), math.sin(h)))
    ob.rotation_euler = (-hacia).to_track_quat("-Z", "Y").to_euler()
    return ob


# =========================================================================== la cocina de Connecticut

def mat_piso_madera():
    def hacer(a):
        p = B.pos_mundo(a)
        x, y, _ = a.separar(p)
        tabla = a.m("FLOOR", a.m("MULTIPLY", x, 1 / 0.14))
        vec = a.nodo("ShaderNodeCombineXYZ")
        a.unir(a.m("MULTIPLY", x, 30.0), vec, 0)
        a.unir(a.m("ADD", a.m("MULTIPLY", y, 1.2), a.m("MULTIPLY", tabla, 3.7)), vec, 1)
        a.unir(tabla, vec, 2)
        vet, _ = a.ruido((vec, 0), 2.5, 6.0, 0.62)
        fr = a.m("FRACT", a.m("MULTIPLY", x, 1 / 0.14))
        junta = a.m("MULTIPLY", a.m("GREATER_THAN", fr, 0.02), a.m("LESS_THAN", fr, 0.98))
        azar = a.nodo("ShaderNodeTexWhiteNoise", noise_dimensions="1D")
        a.unir(tabla, azar, "W")
        tono = a.rango((azar, "Value"), 0, 1, 0.8, 1.15)
        c = a.v("SCALE", (0.22, 0.12, 0.06), escala=a.m("MULTIPLY", a.m("MULTIPLY", a.rango(vet, 0.3, 0.7, 0.75, 1.2), tono),
                                                             a.rango(junta, 0, 1, 0.4, 1.0)))
        return a.bsdf(c, a.rango(vet, 0.3, 0.7, 0.28, 0.42), coat=0.25, normal=a.bump(junta, 0.3, 0.001))
    return B.material("piso_madera", hacer)


def gabinete_blanco(bm, x, y, z0, ancho, fondo, alto, mat_cuerpo=0, frente=-1):
    """Gabinete con puerta de tablero (marco y panel hundido) mirando hacia `frente` en y."""
    B.caja(bm, (x, y, z0 + alto / 2), (ancho, fondo, alto), mat_cuerpo)
    yf = y + frente * fondo / 2
    m = 0.06
    for (cx, cz, sx, sz) in ((0, alto - m / 2, ancho - 0.01, m), (0, m / 2, ancho - 0.01, m),
                             (-ancho / 2 + m / 2, alto / 2, m, alto - 0.01), (ancho / 2 - m / 2, alto / 2, m, alto - 0.01)):
        B.caja(bm, (x + cx, yf + frente * 0.008, z0 + cz), (sx, 0.016, sz), mat_cuerpo)


def cocina_dia():
    """Cocina de una casa de Ellington, Connecticut, una mañana de diciembre: nadie. Gabinetes
    blancos, cubierta clara, la ventana sobre el fregadero, la mesa con dos sillas y una taza."""
    from tres_d import pbr as PB
    pared = PB.material_pbr("pared_beige", "Plaster003_2K-JPG", 1.5, "BOX", tinte_objeto=True, brillo=0.9, relieve=0.25)
    blanco = B.simple("laca_blanca", (0.62, 0.60, 0.56), 0.35, coat=0.2)
    cubierta = B.simple("cuarzo", (0.55, 0.53, 0.50), 0.18, coat=0.4)
    metal = B.simple("niquel_cepillado", (0.55, 0.55, 0.53), 0.3, metal=1.0)
    # cuarto: 4.6 x 5 m, ventana en la pared del fondo (y = 2.5)
    bm = bmesh.new()
    B.caja(bm, (0, 0, -0.01), (4.6, 5.0, 0.02), 0)
    B.objeto("piso", bm, [mat_piso_madera()])
    bm = bmesh.new()
    B.caja(bm, (0, 0, 2.55), (4.6, 5.0, 0.02), 0)
    B.objeto("techo", bm, [B.simple("techo", (0.6, 0.58, 0.55), 0.9)])
    for nombre, centro, tam in (("pared_izq", (-2.3, 0, 1.27), (0.04, 5.0, 2.56)), ("pared_der", (2.3, 0, 1.27), (0.04, 5.0, 2.56)),
                                ("pared_atras", (0, -2.5, 1.27), (4.6, 0.04, 2.56))):
        bm = bmesh.new()
        B.caja(bm, centro, tam, 0)
        B.objeto(nombre, bm, [pared], color=(0.85, 0.78, 0.64))
    # pared del fondo con el hueco de la ventana (1.3 x 1.1 m, de z = 1.05 a 2.15)
    bm = bmesh.new()
    for centro, tam in (((-1.475, 2.5, 1.27), (1.65, 0.04, 2.56)), ((1.475, 2.5, 1.27), (1.65, 0.04, 2.56)),
                        ((0, 2.5, 0.525), (1.3, 0.04, 1.05)), ((0, 2.5, 2.35), (1.3, 0.04, 0.42))):
        B.caja(bm, centro, tam, 0)
    B.objeto("pared_fondo", bm, [pared], color=(0.85, 0.78, 0.64))
    bm = bmesh.new()
    for (cx, cz, sx, sz) in ((0, 1.05, 1.42, 0.06), (0, 2.15, 1.42, 0.06), (-0.68, 1.6, 0.06, 1.16), (0.68, 1.6, 0.06, 1.16),
                             (0, 1.6, 0.04, 1.1), (0, 1.6, 1.3, 0.03)):
        B.caja(bm, (cx, 2.5, cz), (sx, 0.10, sz), 0)
    B.objeto("marco_ventana", bm, [B.simple("marco_ventana", (0.7, 0.69, 0.66), 0.4)])
    # afuera: cielo blanco de invierno (solo se ve por la ventana)
    bm = bmesh.new()
    B.caja(bm, (0, 4.5, 1.6), (8.0, 0.05, 5.0), 0)
    afuera = B.objeto("afuera", bm, [B.simple("cielo_invierno", (0.8, 0.82, 0.85), 0.9, emision=(0.86, 0.90, 1.0), fuerza=2.2)])
    afuera.visible_shadow = False                                          # el sol pasa
    # gabinetes bajo la ventana, cubierta y fregadero; gabinetes de arriba a los lados
    bm = bmesh.new()
    for k in range(5):
        gabinete_blanco(bm, -1.6 + k * 0.8, 2.2, 0.1, 0.78, 0.58, 0.78, frente=-1)
    for k in range(2):
        for s in (-1, 1):
            gabinete_blanco(bm, s * (1.25 + k * 0.62), 2.33, 1.45, 0.6, 0.33, 0.8, frente=-1)
    B.caja(bm, (0, 2.2, 0.05), (4.0, 0.5, 0.1), 0)
    B.objeto("gabinetes", bm, [blanco])
    bm = bmesh.new()
    B.caja(bm, (0, 2.18, 0.9), (4.2, 0.64, 0.04), 0)
    B.objeto("cubierta", bm, [cubierta])
    bm = bmesh.new()
    B.caja(bm, (0, 2.15, 0.86), (0.7, 0.42, 0.02), 0)
    B.objeto("tarja", bm, [B.simple("acero_tarja", (0.5, 0.5, 0.5), 0.25, metal=1.0)])
    bm = bmesh.new()
    B.barra(bm, (0, 2.42, 0.92), (0, 2.42, 1.22), 0.012)
    B.barra(bm, (0, 2.42, 1.22), (0, 2.22, 1.24), 0.011)
    for k in range(5):
        x = -1.6 + k * 0.8
        B.barra(bm, (x - 0.1, 1.9, 0.78), (x + 0.1, 1.9, 0.78), 0.006)
    B.objeto("herrajes", bm, [metal])
    # mesa con dos sillas y una taza
    madera = mat_piso_madera()
    bm = bmesh.new()
    B.caja(bm, (0.2, 0.3, 0.75), (1.2, 0.85, 0.04), 0)
    for sx in (-0.52, 0.52):
        for sy in (-0.36, 0.36):
            B.caja(bm, (0.2 + sx, 0.3 + sy, 0.365), (0.06, 0.06, 0.73), 0)
    for k, (sx, giro) in enumerate(((-0.25, 0.0), (0.65, 0.0))):
        cx, cy = 0.2 + sx, 0.3 - 0.62
        B.caja(bm, (cx, cy, 0.46), (0.44, 0.42, 0.04), 0)
        for dx in (-0.19, 0.19):
            for dy in (-0.18, 0.18):
                B.caja(bm, (cx + dx, cy + dy, 0.22), (0.04, 0.04, 0.44), 0)
            B.caja(bm, (cx + dx, cy - 0.19, 0.72), (0.04, 0.04, 0.52), 0)
        B.caja(bm, (cx, cy - 0.19, 0.9), (0.42, 0.03, 0.14), 0)
    B.objeto("mesa_sillas", bm, [madera])
    bm = bmesh.new()
    B.barra(bm, (0.42, 0.42, 0.77), (0.42, 0.42, 0.866), 0.042, lados=32)
    B.objeto("taza", bm, [B.simple("taza", (0.62, 0.60, 0.58), 0.2, coat=0.6)])
    # luz de relleno del cielo por la ventana (el sol lo pone el plano)
    luz = bpy.data.lights.new("cielo_ventana", "AREA")
    luz.shape, luz.size, luz.size_y = "RECTANGLE", 1.3, 1.1
    luz.energy, luz.color = 120.0, (0.85, 0.90, 1.0)
    ob = B.enlazar(bpy.data.objects.new("cielo_ventana", luz))
    ob.location = (0, 2.45, 1.6)
    ob.rotation_euler = (math.radians(-90), 0, 0)
    B.neblina((0, 0, 1.27), (4.5, 4.9, 2.5), 0.012, (0.95, 0.92, 0.88), anisotropia=0.6, nombre="aire_cocina")
