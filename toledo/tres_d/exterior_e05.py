"""Agregados a la vista de afuera de la casa Dabate (escena 5): el farol del andador y la patrulla que
llega por la entrada de autos con las luces encendidas.

Viven aparte de `casa_e05.py` porque la escena 8 usa `casa_e05.cocina`: cualquier cambio en ese
archivo cambia la huella de sus planos y obliga a volver a renderizarlos.
"""

import math

import bmesh
import bpy
from mathutils import Matrix

from tres_d import base as B
from tres_d import casa_e05 as CA

FAROL = (-1.25, -15.4)                       # donde casa_e05 pone el farol del andador


# =========================================================================== el farol del andador


def mat_hierro(nombre="hierro_farol"):
    """Aluminio fundido pintado de negro, como los faroles coloniales de jardín: satinado, con poros."""
    def hacer(a):
        p = B.pos_mundo(a)
        poro, _ = a.ruido(p, 260.0, 2.0, 0.7)
        mancha, _ = a.ruido(p, 6.0, 3.0, 0.6)
        col = a.v("SCALE", (0.022, 0.022, 0.024), escala=a.rango(mancha, 0.3, 0.7, 0.85, 1.25))
        return a.bsdf(col, a.rango(mancha, 0.3, 0.7, 0.32, 0.5), normal=a.bump(poro, 0.15, 0.001), especular=0.5)
    return B.material(nombre, hacer)


def _quitar_farol_viejo():
    """`casa_e05.terreno_y_calle` dibuja el farol como un poste con una caja encima (se leía como
    letrero) dentro del objeto «buzon»: se borran solo esos vértices, el buzón queda igual."""
    ob = bpy.data.objects.get("buzon")
    if ob is None:
        return
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    viejos = [v for v in bm.verts if math.hypot(v.co.x - FAROL[0], v.co.y - FAROL[1]) < 0.4]
    bmesh.ops.delete(bm, geom=viejos, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()


def _piramide(bm, x, y, z0, z1, a0, a1, tapas=True):
    """Tronco de pirámide de base cuadrada alineada con los ejes (semilado a0 abajo, a1 arriba).
    create_cone pone sus vértices sobre los ejes; girado 45°, quedan en las esquinas."""
    bmesh.ops.create_cone(bm, cap_ends=tapas, segments=4, radius1=a0 * math.sqrt(2), radius2=a1 * math.sqrt(2),
                          depth=z1 - z0, matrix=Matrix.Translation((x, y, (z0 + z1) / 2)) @ Matrix.Rotation(math.pi / 4, 4, "Z"))


def farol(x=FAROL[0], y=FAROL[1]):
    """Farol de jardín de Nueva Inglaterra: base acampanada, poste delgado con su barra para apoyar la
    escalera, y una linterna de cuatro vidrios que se abre hacia arriba, con techito y remate."""
    _quitar_farol_viejo()
    hierro = mat_hierro()
    vidrio = B.material("vidrio_farol", lambda a: a.bsdf((0.05, 0.055, 0.06), 0.04, especular=0.9))
    foco = B.simple("foco_farol", (0.75, 0.72, 0.66), 0.35)
    bm = bmesh.new()
    t = CA.tubo
    t(bm, (x, y, 0.0), (x, y, 0.06), 0.13, 0.13, 0, 16)                      # pie
    t(bm, (x, y, 0.06), (x, y, 0.42), 0.11, 0.055, 0, 16)                    # base acampanada
    t(bm, (x, y, 0.42), (x, y, 0.47), 0.07, 0.07, 0, 16)                     # anillo
    t(bm, (x, y, 0.47), (x, y, 1.86), 0.042, 0.036, 0, 14)                   # poste
    t(bm, (x, y, 1.80), (x, y, 1.86), 0.055, 0.055, 0, 14)                   # collarín
    t(bm, (x - 0.24, y, 1.70), (x + 0.24, y, 1.70), 0.013, 0.013, 0, 8)      # barra de la escalera
    for s in (-1, 1):
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.024,
                                  matrix=Matrix.Translation((x + s * 0.245, y, 1.70)))
    # linterna: charola, cuatro vidrios que se abren hacia arriba, marco y techo a cuatro aguas
    z0, z1, a0, a1 = 1.90, 2.30, 0.12, 0.165
    t(bm, (x, y, 1.86), (x, y, z0), 0.06, 0.10, 0, 16)
    CA.cubo(bm, x - a0 - 0.01, x + a0 + 0.01, y - a0 - 0.01, y + a0 + 0.01, z0, z0 + 0.025, 0)
    antes = set(bm.verts)
    _piramide(bm, x, y, z0, z1, a0, a1, tapas=False)
    for f in {f for v in bm.verts if v not in antes for f in v.link_faces}:
        f.material_index = 1
    for sx in (-1, 1):                                                       # postes de las esquinas
        for sy in (-1, 1):
            t(bm, (x + sx * a0, y + sy * a0, z0), (x + sx * a1, y + sy * a1, z1), 0.009, 0.009, 0, 6)
    CA.cubo(bm, x - a1 - 0.02, x + a1 + 0.02, y - a1 - 0.02, y + a1 + 0.02, z1, z1 + 0.03, 0)
    _piramide(bm, x, y, z1 + 0.03, z1 + 0.17, a1 + 0.05, 0.02)              # techo
    t(bm, (x, y, z1 + 0.17), (x, y, z1 + 0.25), 0.012, 0.004, 0, 8)         # remate
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.022,
                              matrix=Matrix.Translation((x, y, z1 + 0.19)))
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.045,
                              matrix=Matrix.Translation((x, y, z0 + 0.14)) @ Matrix.Diagonal((1, 1, 1.3, 1)))
    focos = [f for f in bm.faces if all(abs(v.co.x - x) < 0.05 and abs(v.co.y - y) < 0.05 and z0 + 0.07 < v.co.z < z0 + 0.21
                                        for v in f.verts)]
    for f in focos:
        f.material_index = 2
    return B.objeto("farol", bm, [hierro, vidrio, foco], suave=False)


# =========================================================================== la patrulla


def mat_pintura_patrulla(nombre="pintura_patrulla"):
    """Patrulla blanca y negra: cofre, cajuela, techo y defensas negros; las puertas, blancas. Con
    laca brillante. La máscara va en coordenadas del objeto, así que sigue al auto cuando se mueve."""
    def hacer(a):
        x, y, z = a.separar(B.coord_objeto(a))
        puertas = a.m("MULTIPLY", a.m("LESS_THAN", a.m("ABSOLUTE", y), 1.08),
                      a.m("MULTIPLY", a.m("GREATER_THAN", a.m("ABSOLUTE", x), 0.72), a.m("LESS_THAN", z, 0.985)))
        puertas = a.m("MULTIPLY", puertas, a.m("GREATER_THAN", z, 0.33))
        col = a.mezcla((0.012, 0.012, 0.013), (0.80, 0.80, 0.79), puertas)
        return a.bsdf(col, 0.22, coat=1.0, especular=0.55)
    return B.material(nombre, hacer)


def _extruir_perfil(bm, perfil, ancho, mat):
    """Un sólido a partir de su silueta de costado (y, z), extruido a lo ancho (x) y centrado."""
    vs = [bm.verts.new((-ancho / 2, y, z)) for y, z in perfil]
    cara = bm.faces.new(vs)
    cara.material_index = mat
    r = bmesh.ops.extrude_face_region(bm, geom=[cara])
    nuevos = [g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=nuevos, vec=(ancho, 0, 0))
    if not any(set(f.verts) == set(vs) for f in bm.faces):           # la tapa de origen, si la extrusión la quitó
        bm.faces.new(vs)
    for f in {f for v in vs + nuevos for f in v.link_faces}:
        f.material_index = mat
    return vs + nuevos


def _arco(cy, cz, r, n=9):
    return [(cy + r * math.cos(math.radians(a)), cz + r * math.sin(math.radians(a)))
            for a in [172 - k * (164 / (n - 1)) for k in range(n)]]


def _biselar(ob, ancho=0.03, segmentos=3):
    """Cantos redondeados al renderizar (modificador) con normales endurecidas: las caras planas siguen
    planas y el brillo de la laca corre por las orillas, como en una carrocería."""
    for pol in ob.data.polygons:
        pol.use_smooth = True
    m = ob.modifiers.new("bisel", "BEVEL")
    m.width = ancho
    m.segments = segmentos
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(30)
    B.poner(m, "harden_normals", True)


def auto_patrulla(nombre="patrulla"):
    """Sedán de patrulla (escala real: 5.1 m de largo, 1.88 de ancho) con su barra de luces. El origen
    está en el piso, al centro; el frente mira a +y. Devuelve (raíz, materiales de la barra
    (rojo, azul), luces (roja, azul), material de las calaveras)."""
    raiz = B.vacio(nombre)
    pintura = mat_pintura_patrulla()
    vidrio = B.material("vidrio_patrulla", lambda a: a.bsdf((0.012, 0.013, 0.015), 0.04, especular=0.8))
    negro = B.simple("plastico_negro", (0.015, 0.015, 0.016), 0.55)
    llanta = B.simple("llanta", (0.02, 0.02, 0.021), 0.8)
    rin = CA.mat_acero("rin", (0.28, 0.28, 0.29), 0.35)
    # cuerpo bajo: defensas, salpicaderas con sus arcos, cofre y cajuela
    yt, yd, rr = -1.45, 1.50, 0.40
    perfil = ([(-2.50, 0.30), (-1.92, 0.30)] + _arco(yt, 0.34, rr) + [(-0.98, 0.30), (1.03, 0.30)] + _arco(yd, 0.34, rr)
              + [(1.97, 0.30), (2.46, 0.31), (2.58, 0.47), (2.58, 0.70), (2.47, 0.86), (1.95, 0.95), (1.05, 1.00),
                 (-1.70, 1.02), (-2.05, 1.03), (-2.47, 0.99), (-2.57, 0.82), (-2.57, 0.48)])
    bm = bmesh.new()
    vs = _extruir_perfil(bm, perfil, 1.86, 0)
    for v in vs:                                   # costados que se recogen arriba y esquinas redondeadas
        k = 1.0 - 0.10 * max(0.0, (v.co.z - 0.70) / 0.33)
        k *= 1.0 - 0.10 * max(0.0, (abs(v.co.y) - 2.15) / 0.43) ** 2
        v.co.x *= k
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    cuerpo = B.objeto(f"{nombre}_cuerpo", bm, [pintura], padre=raiz)
    _biselar(cuerpo, 0.05)
    # cabina: parabrisas, ventanas y medallón; techo pintado y postes
    bm = bmesh.new()
    vs = _extruir_perfil(bm, [(1.06, 0.99), (-1.72, 1.01), (-0.98, 1.43), (0.18, 1.45)], 1.66, 0)
    for v in vs:
        if v.co.z > 1.3:
            v.co.x *= 0.82
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    _biselar(B.objeto(f"{nombre}_cabina", bm, [vidrio], padre=raiz), 0.04)
    bm = bmesh.new()
    vs = _extruir_perfil(bm, [(0.22, 1.445), (-1.02, 1.43), (-1.02, 1.475), (0.20, 1.49)], 1.40, 0)
    for s in (-1, 1):                                                       # postes A, B y C
        CA.tubo(bm, (s * 0.83, 1.05, 1.0), (s * 0.69, 0.17, 1.45), 0.035, 0.035, 0, 6)
        CA.tubo(bm, (s * 0.82, -0.42, 1.01), (s * 0.69, -0.40, 1.44), 0.045, 0.045, 0, 6)
        CA.tubo(bm, (s * 0.83, -1.70, 1.02), (s * 0.69, -0.98, 1.43), 0.06, 0.06, 0, 6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    _biselar(B.objeto(f"{nombre}_techo", bm, [pintura], padre=raiz), 0.015, 2)
    # llantas con rin, espejos, manijas y calaveras
    bm = bmesh.new()
    for yr in (yt, yd):
        for s in (-1, 1):
            CA.tubo(bm, (s * 0.70, yr, 0.34), (s * 0.94, yr, 0.34), 0.34, 0.34, 0, 24)
            CA.tubo(bm, (s * 0.94, yr, 0.34), (s * 0.95, yr, 0.34), 0.21, 0.21, 1, 20)
    for s in (-1, 1):
        CA.cubo(bm, s * 0.93 - 0.08, s * 0.93 + 0.08, 0.80, 0.95, 1.00, 1.11, 2)          # espejo
        xa, xb = sorted((s * 0.872, s * 0.895))
        for ym in (0.25, -0.75):                                                   # manijas
            CA.cubo(bm, xa, xb, ym, ym + 0.16, 0.88, 0.91, 2)
    CA.cubo(bm, -0.86, 0.86, 2.50, 2.60, 0.32, 0.48, 2)                         # defensa delantera
    CA.cubo(bm, -0.86, 0.86, -2.62, -2.52, 0.33, 0.50, 2)                       # defensa trasera
    B.objeto(f"{nombre}_detalles", bm, [llanta, rin, negro], padre=raiz)
    calavera = CA.mat_emision("calaveras", (1.0, 0.04, 0.03), 2.0)
    bm = bmesh.new()
    for s in (-1, 1):
        CA.cubo(bm, s * 0.68 - 0.12, s * 0.68 + 0.12, -2.585, -2.555, 0.66, 0.80, 0)
    B.objeto(f"{nombre}_calaveras", bm, [calavera], padre=raiz)
    # barra de luces: base negra; lente roja del lado del conductor (izquierda), azul del otro
    rojo = CA.mat_emision("barra_roja", (1.0, 0.05, 0.05), 0.0)
    azul = CA.mat_emision("barra_azul", (0.12, 0.28, 1.0), 0.0)
    bm = bmesh.new()
    CA.cubo(bm, -0.66, 0.66, -0.52, -0.22, 1.475, 1.50, 2)
    CA.cubo(bm, -0.64, -0.03, -0.50, -0.24, 1.50, 1.585, 0)
    CA.cubo(bm, 0.03, 0.64, -0.50, -0.24, 1.50, 1.585, 1)
    CA.cubo(bm, -0.03, 0.03, -0.50, -0.24, 1.50, 1.585, 2)
    B.objeto(f"{nombre}_barra", bm, [rojo, azul, negro], padre=raiz)
    l_rojo = B.luz(f"{nombre}_luz_roja", "POINT", (-0.34, -0.37, 1.72), 0.0, (1.0, 0.07, 0.06), radio=0.16, padre=raiz)
    l_azul = B.luz(f"{nombre}_luz_azul", "POINT", (0.34, -0.37, 1.72), 0.0, (0.12, 0.28, 1.0), radio=0.16, padre=raiz)
    return raiz, (rojo, azul), (l_rojo, l_azul), calavera, cuerpo


def destellos(t: float) -> tuple[float, float]:
    """(rojo, azul) de una barra de LED: tres destellos rápidos de un lado y luego tres del otro, en un
    ciclo de 0.6 s; con luz de día, un destello de 2 cuadros se ve mejor que uno largo y espaciado."""
    u = (t + 0.016) % 0.6                   # a 30 cuadros/s, cada destello cae en dos cuadros

    def tres(x):
        for c in (0.0, 0.1, 0.2):
            d = x - c
            if 0 <= d < 0.065:
                return math.sin(math.pi * d / 0.065) ** 0.4
        return 0.0
    return tres(u), tres((u + 0.3) % 0.6)


# recorrido: por la calle desde el este, vuelta a la derecha y entrada de autos hasta la cochera
_X_INI, _Y_CALLE, _R = 45.0, -27.0, 5.0
_X_ENTRADA, _Y_ALTO = 8.0, -6.0
_LARGOS = (_X_INI - (_X_ENTRADA + _R), math.pi / 2 * _R, _Y_ALTO - (_Y_CALLE + _R))


def recorrido(s: float) -> tuple[float, float, float]:
    """Posición (x, y) y rumbo (rad, 0 = hacia +y) a `s` metros del inicio."""
    a, b, c = _LARGOS
    s = min(max(s, 0.0), a + b + c)
    if s <= a:
        return _X_INI - s, _Y_CALLE, math.pi / 2
    if s <= a + b:
        phi = -math.pi / 2 - (s - a) / _R
        cx, cy = _X_ENTRADA + _R, _Y_CALLE + _R
        dx, dy = math.sin(phi), -math.cos(phi)
        return cx + _R * math.cos(phi), cy + _R * math.sin(phi), math.atan2(-dx, dy)
    return _X_ENTRADA, _Y_CALLE + _R + (s - a - b), 0.0


def patrulla_llega(cuadros: int, fps: int, t_alto: float, v0=8.0, frenado=14.0, energia=1100.0):
    """La patrulla llega con las luces encendidas: viene a `v0` m/s, frena los últimos `frenado` metros y
    se detiene a los `t_alto` s frente a la cochera. Los destellos bañan su carrocería, la cochera y la
    fachada. Devuelve la raíz del auto."""
    raiz, (m_rojo, m_azul), (l_rojo, l_azul), calavera, _ = auto_patrulla()
    total = sum(_LARGOS)
    acel = v0 * v0 / (2 * frenado)
    t_freno = t_alto - v0 / acel
    vr, va, vc = [], [], []
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        if t < t_freno:
            s = total - frenado - v0 * (t_freno - t)
        else:
            d = min(t - t_freno, v0 / acel)
            s = total - frenado + v0 * d - acel * d * d / 2
        x, y, rumbo = recorrido(s)
        B.clave(raiz, "location", (x, y, 0.0), f)
        B.clave(raiz, "rotation_euler", (0.0, 0.0, rumbo), f)
        r, a = destellos(t)
        B.clave(l_rojo.data, "energy", energia * r, f)
        B.clave(l_azul.data, "energy", energia * 2.0 * a, f)        # el azul se ve menos de día: más fuerte
        vr.append(14.0 * r)                                         # lentes sin quemarse a blanco
        va.append(22.0 * a)
        vc.append(14.0 if t_freno <= t < t_alto + 0.6 else 2.0)            # luz de freno al frenar
    CA.animar_fuerza(m_rojo, vr, fps)
    CA.animar_fuerza(m_azul, va, fps)
    CA.animar_fuerza(calavera, vc, fps)
    return raiz
