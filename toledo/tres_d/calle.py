"""Calle del casco viejo de Friburgo en 3D: empedrado mojado, aceras, casas con ventanas, toldos y
tejados, faroles, catenaria y el tranvía (azul y verde, como los Urbos) con su interior iluminado.

Viene de la prueba de estilo (`pruebas_estilo/estilo2_blender.py`), que se eligió para el video.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from tres_d import calle_datos as C
from tres_d.base import (barra, caja, cielo, coord_objeto, enlazar, entrada, luz, material, neblina, objeto,
                         poner, pos_mundo, simple, vacio)


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


def mat_vitrina(fuerza: float = 1.3, nombre: str = "vitrina"):
    """Vitrina encendida de noche: el fondo en penumbra y, sobre los estantes, productos de alto y
    ancho variables (con huecos) que reciben la luz de los focos de arriba; el tono cambia de una
    tienda a otra (Object Info › Random)."""
    def hacer(a):
        p = pos_mundo(a)
        info = a.nodo("ShaderNodeObjectInfo")
        _, _, z = a.separar(p)
        w = a.m("FRACT", a.m("MULTIPLY", a.m("SUBTRACT", z, 1.0), 1 / 0.62))          # altura dentro del estante
        estante = a.m("GREATER_THAN", w, 0.93)
        x, y, _ = a.separar(p)
        plano = a.nodo("ShaderNodeCombineXYZ")
        a.unir(a.m("ADD", x, y), plano, 0)
        a.unir(a.m("SUBTRACT", z, 1.0), plano, 1)
        prod = a.nodo("ShaderNodeTexBrick", offset=0.37, offset_frequency=1)
        a.unir((plano, 0), prod, "Vector")
        for k, v in {"Color1": (1, 1, 1, 1), "Color2": (0, 0, 0, 1), "Mortar": (1, 1, 1, 1),
                     "Scale": 1.0, "Mortar Size": 0.04, "Mortar Smooth": 0.1, "Bias": 0.0,
                     "Brick Width": 0.26, "Row Height": 0.62}.items():
            entrada(prod, k).default_value = v
        azar = a.separar((prod, "Color"))[0]                                         # un valor al azar por producto
        alto = a.m("ADD", 0.30, a.m("MULTIPLY", azar, 0.50))
        hay = a.m("MULTIPLY", a.m("GREATER_THAN", azar, 0.22), a.m("SUBTRACT", 1.0, (prod, "Fac")))
        cosas = a.m("MULTIPLY", hay, a.m("LESS_THAN", w, alto))
        arriba = a.rango(z, 1.6, 3.4)
        tinte = a.mezcla((1.0, 0.60, 0.30), (0.95, 0.88, 0.78), (info, "Random"))
        fondo_c = a.v("SCALE", tinte, escala=a.m("ADD", a.m("ADD", 0.03, a.m("MULTIPLY", arriba, 0.22)),
                                                   a.m("MULTIPLY", estante, 0.12)))
        prod_c = a.mezcla((0.75, 0.72, 0.68), tinte, azar)                      # colores apagados, no de catálogo
        prod_c = a.v("SCALE", prod_c, escala=a.m("MULTIPLY", a.m("ADD", 0.25, a.m("MULTIPLY", arriba, 0.55)),
                                                   a.m("ADD", 0.6, a.m("MULTIPLY", azar, 0.5))))
        emis = a.mezcla(fondo_c, prod_c, cosas)
        return a.bsdf((0.01, 0.01, 0.01), 0.04, emision=emis, fuerza=fuerza, especular=0.6)
    return material(nombre, hacer)


BACHLE = 0.46        # ancho del Bächle con sus bordes de granito


def construir_calle(M):
    largo = C.Y_MAX - C.Y_MIN
    yc = (C.Y_MIN + C.Y_MAX) / 2
    bm = bmesh.new()
    caja(bm, (0, yc, -0.05), (2 * C.BORDILLO, largo, 0.1))
    objeto("calzada", bm, [M["adoquin"]])
    for lado in (-1, 1):
        bm = bmesh.new()
        borde = C.BORDILLO + 0.22 + (BACHLE if lado > 0 and "agua_bachle" in M else 0.0)
        ancho = C.FACHADA + 0.6 - borde
        caja(bm, (lado * (borde + ancho / 2), yc, C.ACERA_ALTO / 2 - 0.05), (ancho, largo, C.ACERA_ALTO + 0.1))
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


RETRO_ABAJO, RETRO_ARRIBA = 0.08, 0.48


CURVA = 0.0          # cuánto se retrasan las esquinas de la nariz (0 = frente plano); lo fija armar_calle


def cara_y(zl: float, x: float = 0.0) -> float:
    """y (desde el frente del tranvía) de la cara frontal a la altura local zl del tramo y a lo ancho x."""
    return (RETRO_ABAJO + (RETRO_ARRIBA - RETRO_ABAJO) * (zl + C.ALTO_T / 2) / C.ALTO_T
            + CURVA * (x / (C.ANCHO_T / 2)) ** 2)


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
        if CURVA and (es_frente or es_cola):            # tiras a lo ancho para poder curvar la nariz
            a_lo_ancho = [e for e in bm.edges if abs(e.verts[0].co.x - e.verts[1].co.x) > 0.1]
            bmesh.ops.subdivide_edges(bm, edges=a_lo_ancho, cuts=10, use_grid_fill=True)
        # La cola es igual al frente (los tranvías de Friburgo andan en los dos sentidos): se
        # modela con la punta en y negativa, como el frente, y después se gira media vuelta.
        for v in bm.verts:
            if (es_frente or es_cola) and v.co.y < 0:
                v.co.y += CURVA * (v.co.x / (C.ANCHO_T / 2)) ** 2       # frente redondeado en planta
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
        caja(bm, (x, cara_y(-0.95, x) - 0.01, zc - 0.95), (0.24, 0.06, 0.13), 0)
    objeto("faros", bm, [M["faro"]], padre=raiz)
    bm = bmesh.new()
    for x in (-0.5, 0.5):
        caja(bm, (x, cara_y(-1.12, x) - 0.01, zc - 1.12), (0.10, 0.06, 0.07), 0)
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
    enlazar(txt)
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
        luz("faro", "SPOT", (x, cara_y(-0.95, x) - 0.12, zc - 0.95), 260.0, (1.0, 0.93, 0.82), radio=0.05,
            padre=raiz, rot=(math.radians(84), 0, math.pi), cono=math.radians(55))
    foco = vacio("foco", (0, 0.2, zc), padre=raiz)
    return raiz, foco


# --------------------------------------------------------------------------- escena completa

HORAS = {
    # vitrinas (intensidad), ventanas encendidas (fracción), faroles (W)
    "hora_azul": dict(vitrina=1.3, ventanas=0.30, farol=140.0),
    "madrugada": dict(vitrina=0.22, ventanas=0.07, farol=150.0),     # 2:30 a. m.: tiendas cerradas
}


def materiales_calle(hora: str, libre: bool = False) -> dict:
    h = HORAS[hora]
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
        "vitrina": mat_vitrina(h["vitrina"]),
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
    if libre:                                   # texturas escaneadas en vez de patrones calculados
        from tres_d.pbr import material_pbr
        M["adoquin"] = material_pbr("adoquin_escaneado", "PavingStones119_2K-JPG", 1.1, "FLAT", charcos=True, brillo=0.8)
        M["acera"] = material_pbr("losas_escaneadas", "PavingStones109_2K-JPG", 1.4, "FLAT", charcos=True, brillo=0.85, relieve=0.5)
        M["fachada"] = material_pbr("revoque_escaneado", "Plaster003_2K-JPG", 2.0, "BOX", tinte_objeto=True, relieve=0.6,
                                    sucio_abajo=True)
        M["tejado"] = material_pbr("tejas_escaneadas", "RoofingTiles007_2K-JPG", 2.4, "BOX", relieve=1.0, brillo=0.8)
        M["agua_bachle"] = simple("agua_bachle", (0.01, 0.012, 0.012), 0.02)
        M["zinc"] = simple("zinc", (0.32, 0.33, 0.34), 0.45, metal=0.9)
    return M


def armar_calle(escena, hora: str, con_tranvia: bool = True, neblina_densidad: float = 0.0035, libre: bool = False):
    """La calle entera a la hora pedida. Devuelve (tranvía, foco) o (None, None). Con `libre`, usa
    texturas escaneadas, el cielo fotográfico y los detalles extra (Bächle, bajantes, bolardos…)."""
    global CURVA
    CURVA = 0.30 if libre else 0.0
    if libre:
        from tres_d.pbr import hdri
        hdri(escena, "NightEnvironmentHDRI002_4K", fuerza=0.22, giro_grados=90.0, fondo_camara=hora)
    else:
        cielo(escena, hora)
    M = materiales_calle(hora, libre)
    construir_calle(M)
    edificios = C.edificios(fraccion_luces=HORAS[hora]["ventanas"])
    for i, e in enumerate(edificios):
        construir_edificio(i, e, M)
    if libre:
        detalles_libres(M, edificios)
    bm = bmesh.new()
    caja(bm, (0, C.Y_MAX + 8, 9), (40, 6, 18))
    objeto("fondo", bm, [M["fachada"]], color=(0.7, 0.66, 0.6))
    neblina((0, (C.Y_MIN + C.Y_MAX) / 2, 7), (30, C.Y_MAX - C.Y_MIN + 20, 14), neblina_densidad, (0.70, 0.76, 0.90))
    for k, (lado, y) in enumerate(C.faroles()):
        (farol_hexagonal if libre else construir_farol)(k, lado, y, M)
        bpy.data.lights[f"luz_farol{k}"].energy = HORAS[hora]["farol"]
    if con_tranvia:
        return construir_tranvia(M)
    return None, None


# --------------------------------------------------------------------------- detalles del nivel «libre»

def detalles_libres(M, edificios):
    """Lo que hace que una calle de Friburgo parezca de Friburgo y no una maqueta."""
    largo = C.Y_MAX - C.Y_MIN
    yc = (C.Y_MIN + C.Y_MAX) / 2
    # Bächle: el canalito de agua que corre junto a la banqueta en el casco viejo, con bordes de granito
    x0 = C.BORDILLO + 0.22
    bm = bmesh.new()
    for x in (x0 + 0.04, x0 + 0.42):
        caja(bm, (x, yc, C.ACERA_ALTO / 2 + 0.005), (0.08, largo, C.ACERA_ALTO + 0.01))
    caja(bm, (x0 + 0.23, yc, 0.0), (0.30, largo, 0.04))
    objeto("bachle_bordes", bm, [M["granito"]])
    bm = bmesh.new()
    caja(bm, (x0 + 0.23, yc, 0.075), (0.30, largo, 0.01))
    objeto("bachle_agua", bm, [M["agua_bachle"]])
    # bajantes de zinc en el borde de cada casa, con sus abrazaderas
    bm = bmesh.new()
    for e in edificios:
        x = e.x - e.lado * 0.08
        y = e.y0 + 0.25
        barra(bm, (x, y, 0.1), (x, y, e.alto - 0.2), 0.05, lados=10)
        for z in range(1, int(e.alto // 2)):
            caja(bm, (e.x - e.lado * 0.04, y, z * 2.0), (0.08, 0.13, 0.03))
    objeto("bajantes", bm, [M["zinc"]])
    # bolardos en el bordillo izquierdo
    bm = bmesh.new()
    y = C.Y_MIN + 2
    while y < 120:
        barra(bm, (-C.BORDILLO - 0.25, y, C.ACERA_ALTO), (-C.BORDILLO - 0.25, y, C.ACERA_ALTO + 0.85), 0.07, lados=12)
        y += 4.0
    objeto("bolardos", bm, [M["metal_oscuro"]])


def farol_hexagonal(k, lado, y, M):
    """Farol de pared del casco viejo: brazo con voluta, linterna hexagonal de vidrio y techito."""
    fx = lado * C.FACHADA
    hacia = -lado
    cx = fx + hacia * 0.95
    bm = bmesh.new()
    barra(bm, (fx, y, 4.9), (cx, y, 4.9), 0.022, 0)
    for i in range(10):                                                     # voluta bajo el brazo
        a0, a1 = i / 10 * math.pi, (i + 1) / 10 * math.pi
        r = 0.22
        barra(bm, (fx + hacia * (0.35 + r * math.cos(a0)), y, 4.68 + r * math.sin(a0)),
              (fx + hacia * (0.35 + r * math.cos(a1)), y, 4.68 + r * math.sin(a1)), 0.012, 0, lados=6)
    barra(bm, (cx, y, 4.9), (cx, y, 4.72), 0.018, 0)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.22, radius2=0.02, depth=0.16,
                          matrix=Matrix.Translation((cx, y, 4.68)))                 # techito
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.12, radius2=0.16, depth=0.05,
                          matrix=Matrix.Translation((cx, y, 4.15)))                 # base
    for i in range(6):                                                      # parantes de la linterna
        a = i / 6 * math.tau
        barra(bm, (cx + 0.13 * math.cos(a), y + 0.13 * math.sin(a), 4.17),
              (cx + 0.18 * math.cos(a), y + 0.18 * math.sin(a), 4.6), 0.008, 0, lados=4)
    for f in bm.faces:
        f.material_index = 0
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.125, radius2=0.17, depth=0.42,
                              matrix=Matrix.Translation((cx, y, 4.385)))          # vidrio encendido
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = 1
    objeto(f"farol{k}", bm, [M["metal_oscuro"], M["farol"]])
    luz(f"luz_farol{k}", "POINT", (cx, y, 4.35), 140.0, (1.0, 0.70, 0.42), radio=0.12)
