"""Objetos 3D de la escena 3 (San Bernardino): el iPhone 5C, su pantalla, el conector Lightning,
la bolsa de evidencia, la bolsa de Faraday, la mesa de acero, los estantes, las palmeras y las
patrullas. Todo hecho con código; las medidas van en metros, como el objeto real.

El iPhone 5C mide 124.4 × 59.2 × 8.97 mm. Su cuerpo es de policarbonato brillante con los costados
redondeados; el frente es de vidrio negro. La pantalla no es una imagen: se dibuja en el material
con la posición sobre el vidrio (pantalla de bloqueo con el código, pantalla de inicio con íconos o
el arranque), y tres valores con cuadros clave deciden qué se ve y cuánto brilla.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from tres_d import base as B

# --------------------------------------------------------------------------- medidas del iPhone 5C

ALTO = 0.1244            # a lo largo de y
ANCHO = 0.0592           # a lo largo de x
GRUESO = 0.00897         # a lo largo de z (z = 0 es la espalda)
R_ESQ = 0.0085           # radio de las esquinas vistas de frente
Z_BULTO = 0.0043         # altura del punto más saliente del costado
PANT_W, PANT_H, PANT_Y = 0.0249, 0.0443, 0.0005       # media pantalla (4 pulgadas) y su centro
COLORES_5C = {                                         # policarbonato (lineal)
    "blanco": (0.80, 0.80, 0.78), "rosa": (0.85, 0.22, 0.30), "amarillo": (0.90, 0.68, 0.10),
    "azul": (0.03, 0.30, 0.85), "verde": (0.22, 0.70, 0.22),
}


def _contorno(w, h, r, n=12):
    """Rectángulo de esquinas redondeadas (centro en 0), en el sentido contrario al reloj."""
    r = max(1e-5, min(r, w / 2 - 1e-6, h / 2 - 1e-6))
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def solido_perfilado(bm, w, h, r, perfil, n=12, centro=(0.0, 0.0), mat=0):
    """Sólido de planta redondeada (w × h, radio r) con un perfil de costado: lista de (z, metido)
    de abajo arriba. Cierra abajo y arriba con una cara."""
    anillos = []
    for z, d in perfil:
        anillos.append([bm.verts.new((centro[0] + x, centro[1] + y, z)) for x, y in _contorno(w - 2 * d, h - 2 * d, r - d, n)])
    caras = []
    for a0, a1 in zip(anillos[:-1], anillos[1:]):
        m = len(a0)
        for i in range(m):
            caras.append(bm.faces.new((a0[i], a0[(i + 1) % m], a1[(i + 1) % m], a1[i])))
    caras.append(bm.faces.new(anillos[0][::-1]))
    caras.append(bm.faces.new(anillos[-1]))
    for f in caras:
        f.material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=caras)
    return caras


def perfil_redondo(alto, radio, pasos=5, z0=0.0):
    """Costado recto con los dos bordes redondeados (cuarto de círculo de `radio`)."""
    radio = min(radio, alto / 2)
    abajo = [(z0 + radio - radio * math.cos(math.radians(90 * i / pasos)), radio - radio * math.sin(math.radians(90 * i / pasos)))
             for i in range(pasos + 1)]
    arriba = [(z0 + alto - radio + radio * math.sin(math.radians(90 * i / pasos)), radio - radio * math.cos(math.radians(90 * i / pasos)))
              for i in range(pasos + 1)]
    return abajo + arriba


def objeto_suave(nombre, bm, mats, padre=None, plano=0.985):
    """Objeto con sombreado suave en los costados y plano en las caras grandes (normal casi en z)."""
    ob = B.objeto(nombre, bm, mats, padre=padre)
    for p in ob.data.polygons:
        p.use_smooth = abs(p.normal.z) < plano
    return ob


def tubo(bm, puntos, radio, lados=10, mat=0, tapas=True):
    """Tubo (cable) a lo largo de una polilínea, con marcos que no se tuercen."""
    pts = [Vector(p) for p in puntos]
    anillos = []
    normal = None
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        if normal is None:
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            normal = (ref - t * ref.dot(t)).normalized()
        else:
            normal = (normal - t * normal.dot(t)).normalized()
        bin_ = t.cross(normal)
        anillos.append([bm.verts.new(p + radio * (math.cos(a) * normal + math.sin(a) * bin_))
                        for a in [k * math.tau / lados for k in range(lados)]])
    for a0, a1 in zip(anillos[:-1], anillos[1:]):
        for k in range(lados):
            f = bm.faces.new((a0[k], a0[(k + 1) % lados], a1[(k + 1) % lados], a1[k]))
            f.material_index = mat
            f.smooth = True
    if tapas:
        for anillo, rev in ((anillos[0], True), (anillos[-1], False)):
            f = bm.faces.new(anillo[::-1] if rev else anillo)
            f.material_index = mat


def bezier(p0, p1, p2, p3, n=24):
    p0, p1, p2, p3 = map(Vector, (p0, p1, p2, p3))
    return [(1 - u) ** 3 * p0 + 3 * (1 - u) ** 2 * u * p1 + 3 * (1 - u) * u * u * p2 + u ** 3 * p3
            for u in [i / n for i in range(n + 1)]]


# --------------------------------------------------------------------------- materiales

def suave_rango(a, x, de0, de1, a0=0.0, a1=1.0):
    n = a.nodo("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
    a.dar(n, 0, x)
    for i, v in enumerate((de0, de1, a0, a1), start=1):
        n.inputs[i].default_value = v
    return (n, 0)


def _dentro(a, d, limite, borde):
    """1 si d < limite (con un borde suave de `borde`), 0 afuera."""
    return suave_rango(a, d, limite - borde, limite + borde, 1.0, 0.0)


def _mm(a):
    """Posición local sobre el vidrio, en milímetros: (X, Y) con el centro del teléfono en 0."""
    x, y, _ = a.separar(B.coord_objeto(a))
    return a.m("MULTIPLY", x, 1000.0), a.m("MULTIPLY", y, 1000.0)


def _dist(a, dx, dy):
    return a.m("SQRT", a.m("ADD", a.m("MULTIPLY", dx, dx), a.m("MULTIPLY", dy, dy)))


def _celda(a, coord, origen, paso):
    """Índice de celda y desplazamiento dentro de ella (centrado) a lo largo de un eje."""
    q = a.m("DIVIDE", a.m("SUBTRACT", coord, origen), paso)
    k = a.m("FLOOR", q)
    f = a.m("MULTIPLY", a.m("SUBTRACT", a.m("FRACT", q), 0.5), paso)
    return k, f


def _entre(a, k, lo, hi):
    return a.m("MULTIPLY", a.m("GREATER_THAN", k, lo - 0.5), a.m("LESS_THAN", k, hi + 0.5))


def _valor(a, nombre, v):
    n = a.nodo("ShaderNodeValue")
    n.name = nombre
    n.label = nombre
    n.outputs[0].default_value = v
    return (n, 0)


def mat_vidrio_frente(nombre="vidrio_5c", encendido=0.0, desbloqueo=0.0, arranque=0.0, brillo=4.0, tono=0.0):
    """Frente del iPhone: vidrio negro, botón de inicio, auricular y la pantalla dibujada.

    Valores con nombre (para animarlos): «encendido» (0 apagada … 1), «desbloqueo» (0 código de
    bloqueo … 1 pantalla de inicio) y «arranque» (1 = pantalla negra con la manzana del arranque)."""
    def hacer(a):
        X, Y = _mm(a)
        sY = a.m("SUBTRACT", Y, PANT_Y * 1000)
        en = _valor(a, "encendido", encendido)
        desb = _valor(a, "desbloqueo", desbloqueo)
        arr = _valor(a, "arranque", arranque)
        pant = a.m("MULTIPLY", _dentro(a, a.m("ABSOLUTE", X), PANT_W * 1000, 0.08),
                   _dentro(a, a.m("ABSOLUTE", sY), PANT_H * 1000, 0.08))
        # --- pantalla de bloqueo: fondo azul oscuro con manchas, la línea del título, el código y el teclado
        v = a.rango(sY, -44.0, 44.0)
        fondo_b = a.mezcla((0.06, 0.03, 0.12), (0.01, 0.05, 0.20), v)
        manchas, _ = a.ruido(a.v("SCALE", B.coord_objeto(a), escala=tono * 3.0 + 40.0), 1.0, 2.0)
        fondo_b = a.v("SCALE", fondo_b, escala=a.rango(manchas, 0.3, 0.7, 0.6, 1.5))
        titulo = a.m("MULTIPLY", _dentro(a, a.m("ABSOLUTE", X), 8.0, 0.3), _dentro(a, a.m("ABSOLUTE", a.m("SUBTRACT", sY, 31.0)), 0.7, 0.2))
        k, fx = _celda(a, X, -13.5, 4.5)
        punto = a.m("MULTIPLY", _entre(a, k, 0, 5),
                    _dentro(a, a.m("ABSOLUTE", a.m("SUBTRACT", _dist(a, fx, a.m("SUBTRACT", sY, 23.0)), 1.05)), 0.22, 0.12))
        col, gx = _celda(a, X, -19.5, 13.0)
        fila, gy = _celda(a, a.m("SUBTRACT", 14.0, sY), 0.0, 12.0)
        valida = a.m("MAXIMUM", a.m("MULTIPLY", _entre(a, col, 0, 2), _entre(a, fila, 0, 2)),
                     a.m("MULTIPLY", _entre(a, col, 1, 1), _entre(a, fila, 3, 3)))
        dk = _dist(a, gx, gy)
        tecla = a.m("MULTIPLY", valida, a.m("ADD", _dentro(a, a.m("ABSOLUTE", a.m("SUBTRACT", dk, 4.6)), 0.3, 0.15),
                                            a.m("MULTIPLY", _dentro(a, dk, 4.6, 0.2), 0.16)))
        trazos = a.m("MINIMUM", a.m("ADD", a.m("ADD", titulo, punto), tecla), 1.0)
        bloqueo = a.mezcla(fondo_b, (0.85, 0.88, 0.95), trazos)
        # --- pantalla de inicio: fondo claro y una cuadrícula de íconos de colores
        fondo_i = a.mezcla((0.55, 0.20, 0.08), (0.05, 0.25, 0.55), v)
        ci, ix = _celda(a, X, -22.0, 11.0)
        fi, iy = _celda(a, a.m("SUBTRACT", 40.0, sY), 0.0, 12.0)
        en_rejilla = a.m("MULTIPLY", _entre(a, ci, 0, 3), _entre(a, fi, 0, 4))
        dock = a.m("MULTIPLY", _entre(a, ci, 0, 3), _dentro(a, a.m("ABSOLUTE", a.m("ADD", sY, 37.0)), 4.6, 0.2))
        icono = a.m("MULTIPLY", _dentro(a, a.m("ABSOLUTE", ix), 4.0, 0.35), _dentro(a, a.m("ABSOLUTE", iy), 4.0, 0.35))
        icono_d = a.m("MULTIPLY", dock, _dentro(a, a.m("ABSOLUTE", ix), 4.0, 0.35))
        hay = a.m("MAXIMUM", a.m("MULTIPLY", en_rejilla, icono), icono_d)
        celda = a.nodo("ShaderNodeCombineXYZ")
        a.unir(ci, celda, 0)
        a.unir(a.m("ADD", fi, a.m("MULTIPLY", dock, 9.0)), celda, 1)
        azar = a.nodo("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
        a.unir((celda, 0), azar, "Vector")
        hsv = a.nodo("ShaderNodeCombineColor", mode="HSV")
        a.unir((azar, "Value"), hsv, 0)
        hsv.inputs[1].default_value = 0.65
        hsv.inputs[2].default_value = 0.95
        franja_dock = a.m("MULTIPLY", _dentro(a, a.m("ABSOLUTE", a.m("ADD", sY, 37.0)), 6.0, 0.2), 0.25)
        inicio = a.mezcla(a.mezcla(fondo_i, (0.8, 0.8, 0.85), franja_dock), (hsv, 0), hay)
        # --- arranque: negro con la manzana blanca
        dm = _dist(a, X, a.m("SUBTRACT", sY, 2.0))
        mordida = _dist(a, a.m("SUBTRACT", X, 4.6), a.m("SUBTRACT", sY, 3.6))
        hoja = _dist(a, a.m("MULTIPLY", a.m("SUBTRACT", X, 0.9), 1.0), a.m("MULTIPLY", a.m("SUBTRACT", sY, 8.3), 1.9))
        manzana = a.m("MAXIMUM", a.m("MULTIPLY", _dentro(a, dm, 4.0, 0.15), a.m("SUBTRACT", 1.0, _dentro(a, mordida, 1.8, 0.15))),
                      _dentro(a, hoja, 1.6, 0.15))
        arranq = a.v("SCALE", (1.0, 1.0, 1.0), escala=manzana)
        imagen = a.mezcla(a.mezcla(bloqueo, inicio, desb), arranq, arr)
        emis = a.v("SCALE", imagen, escala=a.m("MULTIPLY", a.m("MULTIPLY", pant, en), brillo))
        # --- vidrio negro, botón de inicio y auricular
        boton = _dentro(a, a.m("ABSOLUTE", a.m("SUBTRACT", _dist(a, X, a.m("ADD", Y, 52.6)), 5.2)), 0.25, 0.1)
        auricular = a.m("MULTIPLY", _dentro(a, a.m("ABSOLUTE", X), 5.0, 0.3), _dentro(a, a.m("ABSOLUTE", a.m("SUBTRACT", Y, 52.3)), 0.65, 0.15))
        base_c = a.mezcla((0.004, 0.004, 0.005), (0.05, 0.05, 0.055), boton)
        base_c = a.mezcla(base_c, (0.0, 0.0, 0.0), auricular)
        rug = a.m("ADD", 0.035, a.m("MULTIPLY", a.m("ADD", boton, auricular), 0.4))
        return a.bsdf(base_c, rug, emision=emis, fuerza=1.0, especular=0.6)
    return B.material(nombre, hacer)


def mat_policarbonato(nombre, color):
    """Plástico duro y brillante del 5C, con una capa transparente encima (coat)."""
    def hacer(a):
        fino, _ = a.ruido(B.coord_objeto(a), 900.0, 2.0)
        normal = a.bump(fino, 0.02, 0.0002)
        return a.bsdf(color, 0.32, coat=0.8, normal=normal, especular=0.5)
    return B.material(nombre, hacer)


def mat_metal(nombre, color=(0.6, 0.6, 0.62), rug=0.25):
    return B.simple(nombre, color, rug, metal=1.0)


# --------------------------------------------------------------------------- el iPhone 5C

def _perfil_5c(pasos=7):
    """Costado del 5C: sale curvo desde la espalda, llega a lo más ancho a 4.3 mm y vuelve a entrar
    hasta el borde del vidrio."""
    pts = []
    for i in range(pasos + 1):                                         # mitad de abajo
        th = math.radians(-90 + 90 * i / pasos)
        pts.append((Z_BULTO + Z_BULTO * math.sin(th), 0.0022 * (1 - math.cos(th))))
    arriba = GRUESO - Z_BULTO
    for i in range(1, pasos + 1):                                      # mitad de arriba
        th = math.radians(90 * i / pasos)
        pts.append((Z_BULTO + arriba * math.sin(th), 0.0010 * (1 - math.cos(th))))
    return pts


def iphone_5c(nombre, color="blanco", pantalla=None, padre=None, detalles_abajo=False):
    """Un iPhone 5C con la espalda en z = 0 y el centro en el origen. `pantalla`: material del
    frente (si no, uno apagado). Devuelve (raíz, material del frente)."""
    raiz = B.vacio(nombre, padre=padre)
    cuerpo_mat = mat_policarbonato(f"{nombre}_cuerpo", COLORES_5C.get(color, color))
    bm = bmesh.new()
    solido_perfilado(bm, ANCHO, ALTO, R_ESQ, _perfil_5c(), n=12)
    objeto_suave(f"{nombre}_cuerpo", bm, [cuerpo_mat], padre=raiz)
    vidrio = pantalla or mat_vidrio_frente(f"{nombre}_vidrio")
    bm = bmesh.new()
    pts = _contorno(ANCHO - 0.002, ALTO - 0.002, R_ESQ - 0.001, 12)
    bm.faces.new([bm.verts.new((x, y, GRUESO + 0.00003)) for x, y in pts])
    B.objeto(f"{nombre}_frente", bm, [vidrio], padre=raiz)
    if detalles_abajo:
        abajo(nombre, raiz)
    return raiz, vidrio


def _disco(bm, centro, radio, normal, lados=20, mat=0):
    c = Vector(centro)
    n = Vector(normal).normalized()
    ref = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
    u = (ref - n * ref.dot(n)).normalized()
    w = n.cross(u)
    vs = [bm.verts.new(c + radio * (math.cos(a) * u + math.sin(a) * w)) for a in [k * math.tau / lados for k in range(lados)]]
    f = bm.faces.new(vs)
    f.material_index = mat
    f.normal_update()
    if f.normal.dot(n) < 0:
        f.normal_flip()


def abajo(nombre, raiz):
    """El borde de abajo del 5C: puerto Lightning, tornillos, conector de audífonos, micrófono y
    bocina (todo en y = −ALTO/2, mirando hacia −y)."""
    y = -ALTO / 2 - 0.00002
    z = Z_BULTO
    negro = B.simple(f"{nombre}_hueco", (0.002, 0.002, 0.002), 0.6)
    borde = B.simple(f"{nombre}_borde_puerto", (0.05, 0.05, 0.055), 0.35, metal=0.6)
    tornillo = mat_metal(f"{nombre}_tornillo", (0.55, 0.55, 0.56), 0.3)
    # puerto: un borde fino y, adentro, el hueco negro (rectángulo de puntas redondas)
    bm = bmesh.new()
    for capa, (w, h, dy, mat) in enumerate(((0.0081, 0.0021, 0.0, 1), (0.0077, 0.00165, -0.00001, 0))):
        pts = _contorno(w, h, h / 2 - 1e-6, 8)
        f = bm.faces.new([bm.verts.new((px, y + dy, z + pz)) for px, pz in pts])
        f.material_index = mat
        f.normal_update()
        if f.normal.y > 0:
            f.normal_flip()
    for x in (-0.0056, 0.0056):                                        # tornillos pentalobulares
        _disco(bm, (x, y - 0.000005, z), 0.00068, (0, -1, 0), 18, 2)
        _disco(bm, (x, y - 0.00001, z), 0.00026, (0, -1, 0), 10, 0)
    _disco(bm, (-0.0190, y, z), 0.0017, (0, -1, 0), 28, 1)            # audífonos
    _disco(bm, (-0.0190, y - 0.00001, z), 0.00128, (0, -1, 0), 24, 0)
    for k in range(4):                                                 # micrófono
        _disco(bm, (-0.0128 + k * 0.0012, y, z), 0.00042, (0, -1, 0), 10, 0)
    for k in range(8):                                                 # bocina
        _disco(bm, (0.0105 + k * 0.0013, y, z), 0.00048, (0, -1, 0), 10, 0)
    B.objeto(f"{nombre}_abajo", bm, [negro, borde, tornillo], padre=raiz)


# --------------------------------------------------------------------------- conector Lightning

def conector_lightning(nombre="lightning", largo_cable=0.35, caida=-0.004):
    """Conector Lightning blanco con su lengüeta y el cable. Apunta hacia +y: la punta de la
    lengüeta queda en y = +7.7 mm y la cara de la funda en y = 0. El cable sale hacia −y y baja a
    la mesa (`caida`, en z relativa al centro del conector)."""
    raiz = B.vacio(nombre)
    blanco = B.material(f"{nombre}_funda", lambda a: a.bsdf((0.78, 0.78, 0.76), 0.38, coat=0.3, especular=0.5))
    lengueta = mat_metal(f"{nombre}_lengueta", (0.62, 0.62, 0.64), 0.22)
    oro = mat_metal(f"{nombre}_oro", (0.95, 0.68, 0.30), 0.18)
    # lengüeta: plana (gruesa en z), con la punta redondeada
    bm = bmesh.new()
    solido_perfilado(bm, 0.0067, 0.0077, 0.0012, perfil_redondo(0.0015, 0.0004, 3, z0=-0.00075), n=6,
                     centro=(0.0, 0.00385), mat=0)
    for lado in (1, -1):                                               # 8 contactos de cada lado
        for k in range(8):
            x = -0.00228 + k * 0.00065
            B.caja(bm, (x, 0.0051, lado * 0.000765), (0.00048, 0.0024, 0.00004), 1)
    objeto_suave(f"{nombre}_lengueta", bm, [lengueta, oro], padre=raiz)
    # funda: sección redondeada de 11.8 × 6.6 mm a lo largo de −y (se arma en z y se gira)
    bm = bmesh.new()
    solido_perfilado(bm, 0.0118, 0.0066, 0.0025, perfil_redondo(0.019, 0.0018, 4, z0=-0.019), n=8)
    bm2 = bmesh.new()
    solido_perfilado(bm2, 0.0050, 0.0040, 0.0019, perfil_redondo(0.006, 0.0008, 3, z0=-0.025), n=8)   # alivio del cable
    for b in (bm, bm2):
        bmesh.ops.rotate(b, verts=b.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(-90), 3, "X"))

    objeto_suave(f"{nombre}_funda", bm, [blanco], padre=raiz, plano=2.0)
    objeto_suave(f"{nombre}_alivio", bm2, [blanco], padre=raiz, plano=2.0)
    for ob in (bpy.data.objects[f"{nombre}_funda"], bpy.data.objects[f"{nombre}_alivio"]):
        for p in ob.data.polygons:
            p.use_smooth = abs(p.normal.y) < 0.985
    # cable: sale derecho y cae a la mesa, luego se aleja
    bm = bmesh.new()
    pts = bezier((0, -0.024, 0), (0, -0.05, 0), (0.004, -0.07, caida), (0.012, -0.11, caida), 16)
    pts += bezier((0.012, -0.11, caida), (0.02, -0.15, caida), (0.06, -0.22, caida), (0.10, -largo_cable, caida), 16)[1:]
    tubo(bm, pts, 0.0015, 12)
    B.objeto(f"{nombre}_cable", bm, [blanco], padre=raiz)
    return raiz


# --------------------------------------------------------------------------- bolsas

def mat_plastico_evidencia(nombre="bolsa_evidencia", w=0.23, h=0.30, cierre="arriba"):
    """Plástico transparente de la bolsa de evidencia: casi todo deja ver, con reflejo rasante, y la
    franja roja del cierre de seguridad. Se compone por mezcla (no por puntos al azar), para que el
    plástico no salga granuloso."""
    def hacer(a):
        x, y, _ = a.separar(B.coord_objeto(a))
        fres = a.nodo("ShaderNodeFresnel")
        fres.inputs["IOR"].default_value = 1.45
        transp = (a.nodo("ShaderNodeBsdfTransparent"), 0)
        arrugas, _ = a.ruido(B.coord_objeto(a), 4.0, 3.0, 0.5)
        brillo = a.bsdf((0.6, 0.6, 0.62), 0.06, especular=0.8, normal=a.bump(arrugas, 0.08, 0.004))
        plastico = a.mezclar_shader(transp, brillo, a.m("ADD", a.m("MULTIPLY", (fres, 0), 0.4), 0.02))
        yc = h / 2 - 0.028 if cierre == "arriba" else (h / 2 - 0.012 if cierre == "borde" else -h / 2 + 0.028)
        franja = a.m("LESS_THAN", a.m("ABSOLUTE", a.m("SUBTRACT", y, yc)), 0.0075)
        franja = a.m("MULTIPLY", franja, a.m("LESS_THAN", a.m("ABSOLUTE", x), w / 2 - 0.004))
        rojo = a.bsdf((0.30, 0.008, 0.012), 0.45)
        return a.mezclar_shader(plastico, rojo, franja)
    mat = B.material(nombre, hacer)
    B.poner(mat, "use_transparent_shadow", True)
    B.poner(mat, "surface_render_method", "BLENDED")
    return mat


def mat_etiqueta(nombre="etiqueta_evidencia"):
    """Etiqueta de papel de la bolsa: franja de título y renglones para llenar a mano."""
    def hacer(a):
        _, y, _ = a.separar(B.coord_objeto(a))
        renglon = a.m("LESS_THAN", a.m("FRACT", a.m("MULTIPLY", a.m("ADD", y, 1.0), 1 / 0.0085)), 0.1)
        renglon = a.m("MULTIPLY", renglon, a.m("LESS_THAN", y, 0.012))
        fibra, _ = a.ruido(B.coord_objeto(a), 300.0, 3.0)
        papel = a.v("SCALE", (0.62, 0.61, 0.57), escala=a.rango(fibra, 0.3, 0.7, 0.94, 1.03))
        return a.bsdf(a.mezcla(papel, (0.12, 0.12, 0.14), a.m("MULTIPLY", renglon, 0.8)), 0.75)
    return B.material(nombre, hacer)


def _almohada(bm, w, h, alto, nx=40, ny=50, potencia=6.0, arrugas=0.0, semilla=0.0, z0=0.0):
    """Superficie de bolsa: alta en el centro y que baja a z0 en los bordes, con arrugas."""
    from mathutils import noise
    filas = []
    for j in range(ny + 1):
        y = -h / 2 + h * j / ny
        fila = []
        for i in range(nx + 1):
            x = -w / 2 + w * i / nx
            fx = max(0.0, 1 - abs(2 * x / w) ** potencia)
            fy = max(0.0, 1 - abs(2 * y / h) ** potencia)
            z = alto * (fx * fy) ** 0.35
            z += arrugas * (fx * fy) ** 0.5 * noise.noise(Vector((x * 18 + semilla, y * 18, 0.5)))
            fila.append(bm.verts.new((x, y, z0 + z)))
        filas.append(fila)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((filas[j][i], filas[j][i + 1], filas[j + 1][i + 1], filas[j + 1][i]))


def bolsa_evidencia(nombre="bolsa", w=0.23, h=0.30, alto=0.016, padre=None, etiqueta="abajo"):
    """Bolsa de evidencia de plástico sobre la mesa, con su etiqueta de papel (la palabra EVIDENCE
    y renglones) apoyada encima. `etiqueta`: «abajo» o «arriba» (y el cierre rojo, del otro lado)."""
    mat = mat_plastico_evidencia(f"{nombre}_plastico", w, h, "arriba" if etiqueta == "abajo" else "borde")
    bm = bmesh.new()
    _almohada(bm, w, h, alto, 46, 60, 8.0, 0.0012, 3.0, 0.0002)
    ob = B.objeto(nombre, bm, [mat], padre=padre, suave=True)
    lw, lh = w - 0.04, 0.062
    yc = (-h / 2 + 0.03 + lh / 2) if etiqueta == "abajo" else (h / 2 - 0.03 - lh / 2)
    zc = alto + 0.0016
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, 0.0)) for x, y in ((-lw / 2, -lh / 2), (lw / 2, -lh / 2), (lw / 2, lh / 2), (-lw / 2, lh / 2))]
    bm.faces.new(vs)
    papel = B.objeto(f"{nombre}_etiqueta", bm, [mat_etiqueta(f"{nombre}_papel")], padre=ob)
    papel.location = (0.0, yc, zc)
    rojo = B.simple(f"{nombre}_letras", (0.4, 0.01, 0.02), 0.5)
    cu = bpy.data.curves.new(f"{nombre}_texto", "FONT")
    cu.body = "EVIDENCE"
    cu.size = min(0.016, lw * 0.11)
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    t = bpy.data.objects.new(f"{nombre}_texto", cu)
    t.data.materials.append(rojo)
    B.enlazar(t)
    t.parent = papel
    t.location = (0.0, lh * 0.3, 0.0003)
    return ob


def mat_nylon(nombre="nylon_faraday", color=(0.009, 0.0095, 0.011)):
    """Tela de nylon negro tipo ripstop: cuadrícula fina en relieve y un brillo suave de tela."""
    def hacer(a):
        p = B.coord_objeto(a)
        x, y, _ = a.separar(p)
        cx = a.m("GREATER_THAN", a.m("FRACT", a.m("MULTIPLY", x, 1 / 0.006)), 0.9)
        cy = a.m("GREATER_THAN", a.m("FRACT", a.m("MULTIPLY", y, 1 / 0.006)), 0.9)
        trama = a.nodo("ShaderNodeTexWave", wave_type="BANDS")
        a.unir(p, trama, "Vector")
        B.entrada(trama, "Scale").default_value = 900.0
        alto = a.m("ADD", a.m("MULTIPLY", a.m("MAXIMUM", cx, cy), 0.6), a.m("MULTIPLY", (trama, "Fac"), 0.3))
        b = a.nodo("ShaderNodeBsdfPrincipled")
        a.dar(b, "Base Color", (*color, 1.0))
        a.dar(b, "Roughness", 0.55)
        if "Sheen Weight" in b.inputs:
            b.inputs["Sheen Weight"].default_value = 0.6
        a.unir(a.bump(alto, 0.3, 0.0006), b, "Normal")
        return (b, 0)
    return B.material(nombre, hacer)


def mat_ventana_faraday(nombre="ventana_faraday"):
    """La ventana transparente de la bolsa (para ver la pantalla sin abrirla)."""
    def hacer(a):
        fres = a.nodo("ShaderNodeFresnel")
        fres.inputs["IOR"].default_value = 1.5
        transp = (a.nodo("ShaderNodeBsdfTransparent"), 0)
        arrugas, _ = a.ruido(B.coord_objeto(a), 14.0, 3.0)
        brillo = a.bsdf((0.5, 0.5, 0.52), 0.08, especular=0.9, normal=a.bump(arrugas, 0.15, 0.002))
        return a.mezclar_shader(transp, brillo, a.m("ADD", a.m("MULTIPLY", (fres, 0), 0.75), 0.08))
    mat = B.material(nombre, hacer)
    B.poner(mat, "use_transparent_shadow", True)
    B.poner(mat, "surface_render_method", "BLENDED")
    return mat


def bolsa_faraday(nombre="faraday", w=0.105, h=0.20, alto=0.024, padre=None):
    """Bolsa de Faraday negra con ventana transparente sobre la pantalla y la solapa doblada con su
    forro plateado; el teléfono va adentro (se arma aparte). Su boca está del lado +y."""
    raiz = B.vacio(nombre, padre=padre)
    nylon = mat_nylon(f"{nombre}_nylon")
    ventana = mat_ventana_faraday(f"{nombre}_ventana")
    plata = B.material(f"{nombre}_forro", lambda a: a.bsdf((0.55, 0.56, 0.58), 0.45, metal=0.85,
                                                            normal=a.bump(a.ruido(B.coord_objeto(a), 400.0, 3.0)[0], 0.4, 0.0005)))
    # cuerpo: superficie de arriba como almohada; la ventana es un hueco en ella con su propio material
    bm = bmesh.new()
    _almohada(bm, w, h, alto, 40, 70, 7.0, 0.0018, 7.0, 0.0)
    vw, vh, vy = ANCHO * 0.82, ALTO * 0.70, -0.01
    for f in bm.faces:
        c = f.calc_center_median()
        f.material_index = 1 if (abs(c.x) < vw / 2 and abs(c.y - vy) < vh / 2) else 0
    B.objeto(f"{nombre}_cuerpo", bm, [nylon, ventana], padre=raiz, suave=True)
    # marco cosido alrededor de la ventana (un poco más claro)
    costura = B.simple(f"{nombre}_costura", (0.05, 0.05, 0.055), 0.6)
    bm = bmesh.new()
    zv = alto * 0.97
    for (x0, y0), (x1, y1) in zip(((-vw / 2, vy - vh / 2), (vw / 2, vy - vh / 2), (vw / 2, vy + vh / 2), (-vw / 2, vy + vh / 2)),
                                  ((vw / 2, vy - vh / 2), (vw / 2, vy + vh / 2), (-vw / 2, vy + vh / 2), (-vw / 2, vy - vh / 2))):
        tubo(bm, [(x0, y0, zv), (x1, y1, zv)], 0.0012, 6)
    B.objeto(f"{nombre}_costura", bm, [costura], padre=raiz)
    # solapa doblada sobre la boca: una capa de nylon que se apoya sobre la bolsa y, en el doblez
    # del extremo, un rollo donde asoma el forro plateado
    def z_bolsa(x, y):
        fx = max(0.0, 1 - abs(2 * x / w) ** 7.0)
        fy = max(0.0, 1 - abs(2 * min(y, h / 2) / h) ** 7.0)
        return alto * (fx * fy) ** 0.35

    largo_sol = 0.048
    bm = bmesh.new()
    nx, ny = 30, 14
    filas = []
    for j in range(ny + 1):
        y = h / 2 - largo_sol + largo_sol * j / ny
        fila = []
        for i in range(nx + 1):
            x = -w / 2 * 1.02 + w * 1.02 * i / nx
            borde = max(0.0, 1 - abs(2 * x / (w * 1.02)) ** 8)
            z = max(z_bolsa(x * 0.98, y - 0.004), 0.004 * borde) + 0.0028 * borde ** 0.3
            z += 0.0008 * math.sin(x * 140 + j)
            fila.append(bm.verts.new((x, y, z)))
        filas.append(fila)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((filas[j][i], filas[j][i + 1], filas[j + 1][i + 1], filas[j + 1][i]))
    sol = B.objeto(f"{nombre}_solapa", bm, [nylon], padre=raiz, suave=True)
    bm = bmesh.new()                                                   # el doblez: medio tubo achatado
    radio = 0.0065
    for i in range(16):
        x0 = -w / 2 * 0.98 + w * 0.98 * i / 16
        x1 = -w / 2 * 0.98 + w * 0.98 * (i + 1) / 16
        anillo0, anillo1 = [], []
        for k in range(9):
            a = math.radians(-90 + 180 * k / 8)
            for x, anillo in ((x0, anillo0), (x1, anillo1)):
                b = max(0.0, 1 - abs(2 * x / (w * 0.98)) ** 8) ** 0.3
                anillo.append(bm.verts.new((x, h / 2 + radio * 0.6 * math.cos(a) * b, radio + radio * math.sin(a) * b * 0.95)))
        for k in range(8):
            bm.faces.new((anillo0[k], anillo1[k], anillo1[k + 1], anillo0[k + 1]))
    B.objeto(f"{nombre}_pliegue", bm, [plata], padre=raiz, suave=True)
    return raiz, sol


# --------------------------------------------------------------------------- mesa y sala de evidencias

def mat_acero_cepillado(nombre="acero_mesa"):
    """Acero inoxidable cepillado de mesa de laboratorio: vetas finas a lo largo de x y rayones."""
    def hacer(a):
        p = B.pos_mundo(a)
        q = a.v("MULTIPLY", p, (2.0, 160.0, 2.0))
        veta, _ = a.ruido(q, 3.0, 6.0, 0.7)
        mancha, _ = a.ruido(p, 6.0, 3.0)
        color = a.v("SCALE", (0.50, 0.51, 0.53), escala=a.rango(mancha, 0.3, 0.7, 0.85, 1.0))
        rug = a.m("ADD", a.rango(veta, 0.3, 0.7, 0.26, 0.33), a.m("MULTIPLY", a.rango(mancha, 0.4, 0.7), 0.06))
        normal = a.bump(veta, 0.03, 0.0005)
        return a.bsdf(color, rug, metal=1.0, normal=normal)
    return B.material(nombre, hacer)


def mat_carton(nombre="carton"):
    def hacer(a):
        p = B.pos_mundo(a)
        info = a.nodo("ShaderNodeObjectInfo")
        f, _ = a.ruido(p, 12.0, 4.0)
        color = a.v("SCALE", a.mezcla((0.30, 0.18, 0.08), (0.36, 0.24, 0.12), (info, "Random")), escala=a.rango(f, 0.3, 0.7, 0.8, 1.1))
        return a.bsdf(color, 0.85, normal=a.bump(f, 0.1, 0.002))
    return B.material(nombre, hacer)


def mat_pintura_metal(nombre, color, rug=0.5):
    def hacer(a):
        f, _ = a.ruido(B.pos_mundo(a), 30.0, 3.0)
        return a.bsdf(a.v("SCALE", color, escala=a.rango(f, 0.3, 0.7, 0.85, 1.1)), rug, metal=0.3, normal=a.bump(f, 0.05, 0.001))
    return B.material(nombre, hacer)


def estante(nombre, x0, y0, largo, niveles=(0.05, 0.45, 0.85, 1.25, 1.65, 2.05), fondo=0.45, mat=None):
    """Estantería metálica gris: postes en las esquinas y entrepaños, a lo largo de x."""
    mat = mat or mat_pintura_metal(f"{nombre}_pintura", (0.22, 0.23, 0.24))
    bm = bmesh.new()
    for x in (x0, x0 + largo):
        for y in (y0, y0 + fondo):
            B.caja(bm, (x, y, 1.05), (0.035, 0.035, 2.1))
    for z in niveles:
        B.caja(bm, (x0 + largo / 2, y0 + fondo / 2, z), (largo, fondo, 0.02))
        B.caja(bm, (x0 + largo / 2, y0, z - 0.03), (largo, 0.01, 0.05))
    return B.objeto(nombre, bm, [mat])


def caja_archivo(nombre, centro, tam, mat_carton_, mat_etiqueta, giro=0.0):
    bm = bmesh.new()
    B.caja(bm, (0, 0, tam[2] / 2), tam, 0)
    B.caja(bm, (0, -tam[1] / 2 - 0.001, tam[2] * 0.55), (tam[0] * 0.45, 0.002, tam[2] * 0.25), 1)
    ob = B.objeto(nombre, bm, [mat_carton_, mat_etiqueta])
    ob.location = centro
    ob.rotation_euler = (0, 0, giro)
    return ob


# --------------------------------------------------------------------------- exterior: palmeras, postes, patrullas

def palmera(k, x, y, alto, M, rng):
    """Palmera de abanico (Washingtonia), como las de San Bernardino: tronco delgado y alto, la
    falda de hojas secas y una copa de hojas en abanico."""
    bm = bmesh.new()
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.30, radius2=0.20, depth=alto,
                              matrix=Matrix.Translation((x, y, alto / 2)))
    B.objeto(f"palmera_tronco{k}", bm, [M["corteza"]], suave=True)
    bm = bmesh.new()                                     # falda de hojas secas que cuelga bajo la copa
    bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=0.62, radius2=0.40, depth=2.8,
                          matrix=Matrix.Translation((x, y, alto - 1.3)))
    B.objeto(f"palmera_falda{k}", bm, [M["seca"]], suave=True)
    bm = bmesh.new()
    tope = Vector((x, y, alto + 0.15))
    n_hojas = 36
    for i in range(n_hojas):
        fi = i * math.tau * 0.618 + rng.uniform(-0.15, 0.15)            # filotaxia: hojas repartidas
        e = math.radians(rng.uniform(-55, 65))
        d = Vector((math.cos(e) * math.cos(fi), math.cos(e) * math.sin(fi), math.sin(e)))
        P = tope + d * rng.uniform(1.1, 1.7)
        B.barra(bm, tope, P, 0.03, lados=5)
        lat = Vector((-math.sin(fi), math.cos(fi), 0.0))
        n = d.cross(lat).normalized()
        Rr = rng.uniform(0.95, 1.3)
        cae = 0.35 + 0.4 * max(0.0, -math.sin(e))
        centro = bm.verts.new(P)
        anillo = []
        for j in range(23):
            al = math.radians(-85 + 170 * j / 22)
            r = Rr * (1.0 if j % 2 == 0 else 0.78)                   # puntas partidas del abanico
            q = P + r * (math.cos(al) * d + math.sin(al) * lat) + n * (0.07 if j % 2 else -0.07)                 - Vector((0, 0, cae * r * (0.3 + abs(math.sin(al)))))
            anillo.append(bm.verts.new(q))
        for a0, a1 in zip(anillo[:-1], anillo[1:]):
            bm.faces.new((centro, a0, a1))
    B.objeto(f"palmera_copa{k}", bm, [M["palma"]])


def poste_estacionamiento(k, x, y, M, alto=9.0, energia=2600.0, color=(1.0, 0.80, 0.58)):
    bm = bmesh.new()
    B.caja(bm, (x, y, alto / 2), (0.16, 0.16, alto), 0)
    B.caja(bm, (x, y, 0.35), (0.5, 0.5, 0.7), 2)
    B.caja(bm, (x, y - 0.55, alto - 0.05), (0.45, 0.75, 0.14), 0)
    B.caja(bm, (x, y - 0.55, alto - 0.13), (0.38, 0.62, 0.02), 1)
    B.objeto(f"poste{k}", bm, [M["poste"], M["lampara"], M["concreto"]])
    return B.luz(f"luz_poste{k}", "SPOT", (x, y - 0.55, alto - 0.2), energia, color, radio=0.25, cono=math.radians(105))


def patrulla(k, x, y, giro, M):
    """Patrulla negra y blanca vista de lejos, con la barra de luces en el techo. Devuelve los
    materiales y las luces de la barra para hacerlas destellar."""
    raiz = B.vacio(f"patrulla{k}", (x, y, 0))
    raiz.rotation_euler = (0, 0, giro)
    bm = bmesh.new()
    solido_perfilado(bm, 1.95, 4.95, 0.35, perfil_redondo(0.75, 0.12, 3, z0=0.38), n=5, mat=0)
    B.objeto(f"patrulla{k}_bajo", bm, [M["pintura_negra"]], padre=raiz, suave=False)
    bm = bmesh.new()
    solido_perfilado(bm, 1.75, 2.5, 0.25, perfil_redondo(0.62, 0.1, 3, z0=1.12), n=5, centro=(0.0, -0.2), mat=0)
    B.objeto(f"patrulla{k}_cabina", bm, [M["vidrio_auto"]], padre=raiz)
    bm = bmesh.new()
    for lado in (-1, 1):                                                 # puertas blancas
        B.caja(bm, (lado * 0.985, -0.1, 0.78), (0.02, 1.9, 0.5))
    B.objeto(f"patrulla{k}_puertas", bm, [M["pintura_blanca"]], padre=raiz)
    bm = bmesh.new()
    for xr in (-0.82, 0.82):
        for yr in (-1.55, 1.55):
            bmesh.ops.create_cone(bm, cap_ends=True, segments=14, radius1=0.36, radius2=0.36, depth=0.25,
                                  matrix=Matrix.Translation((xr, yr, 0.36)) @ Matrix.Rotation(math.radians(90), 4, "Y"))
    B.objeto(f"patrulla{k}_llantas", bm, [M["llanta"]], padre=raiz)
    rojo = B.simple(f"barra_roja{k}", (0.3, 0.0, 0.0), 0.3, emision=(1.0, 0.02, 0.02), fuerza=0.0)
    azul = B.simple(f"barra_azul{k}", (0.0, 0.0, 0.3), 0.3, emision=(0.05, 0.18, 1.0), fuerza=0.0)
    bm = bmesh.new()
    B.caja(bm, (-0.32, -0.2, 1.79), (0.6, 0.28, 0.1), 0)
    B.caja(bm, (0.32, -0.2, 1.79), (0.6, 0.28, 0.1), 1)
    B.objeto(f"patrulla{k}_barra", bm, [rojo, azul], padre=raiz)
    l_rojo = B.luz(f"luz_roja{k}", "POINT", (-0.4, -0.2, 2.0), 0.0, (1.0, 0.05, 0.03), radio=0.2, padre=raiz)
    l_azul = B.luz(f"luz_azul{k}", "POINT", (0.4, -0.2, 2.0), 0.0, (0.1, 0.25, 1.0), radio=0.2, padre=raiz)
    return raiz, (rojo, azul), (l_rojo, l_azul)


def destello(t: float, fase: float, k: int) -> tuple[float, float]:
    """Intensidad (rojo, azul) de una barra de luces: destellos dobles que se alternan."""
    def doble(x):
        x %= 1.0
        return 1.0 if (x < 0.08 or 0.16 < x < 0.24) else 0.0
    ciclo = 0.85 + 0.07 * k
    u = t / ciclo + fase
    return doble(u), doble(u + 0.5)
