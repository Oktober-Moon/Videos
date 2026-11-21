"""Planos 3D de la escena 3 (San Bernardino, 2 de diciembre de 2015 y el FBI contra Apple).

Firma: plano(escena, cuadros, fps, **params) -> dict | None

- e03_centro_noche      3.0  El Inland Regional Center de noche, vacío; patrullas a lo lejos.
- e03_iphone_evidencia  3.0  El iPhone 5C apagado, en su bolsa de evidencia sobre la mesa de acero.
- e03_puerto_lightning  3.3  El puerto Lightning de cerca y un cable que se acerca y entra.
- e03_docena_5c         3.7  Una docena de iPhone 5C conectados: el código cae en todos.
- e03_bolsa_faraday     3.11 Un teléfono encendido y cargando dentro de una bolsa de Faraday.
- e03_sala_evidencias   3.12 Estante de evidencias de noche: iPhones que se reinician solos.

La violencia no se muestra: el edificio está vacío, de noche, con las luces de las patrullas lejos.
"""

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

from tres_d import base as B
from tres_d import objetos_e03 as O
from tres_d import pbr as PB


def _suave(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def _clave_valor(mat, nombre, valor, f):
    n = mat.node_tree.nodes[nombre]
    n.outputs[0].default_value = valor
    n.outputs[0].keyframe_insert("default_value", frame=f)


def _clave_emision(mat, fuerza, f):
    n = next(x for x in mat.node_tree.nodes if x.type == "BSDF_PRINCIPLED")
    s = B.entrada(n, "Emission Strength")
    s.default_value = fuerza
    s.keyframe_insert("default_value", frame=f)


def _clave_luz(luz, energia, f):
    luz.data.energy = energia
    luz.data.keyframe_insert("energy", frame=f)


# =========================================================================== interiores


def _cuarto(M, ancho=4.0, fondo=4.0, piso=-0.92, alto=2.9, centro=(0.0, 0.0)):
    """Cuarto cerrado de concreto y paredes de yeso gris (para los planos de mesa y estantes)."""
    cx, cy = centro
    bm = bmesh.new()
    B.caja(bm, (cx, cy, piso - 0.05), (ancho, fondo, 0.1))
    B.objeto("piso", bm, [M["piso"]])
    bm = bmesh.new()
    for x, y, w, d in ((cx, cy + fondo / 2, ancho, 0.1), (cx, cy - fondo / 2, ancho, 0.1),
                       (cx + ancho / 2, cy, 0.1, fondo), (cx - ancho / 2, cy, 0.1, fondo)):
        B.caja(bm, (x, y, piso + alto / 2), (w, d, alto))
    B.objeto("paredes", bm, [M["pared"]])


def _materiales_interior():
    return {
        "piso": PB.material_pbr("piso_e03", "Concrete031_2K-JPG", 2.0, "FLAT", brillo=0.55, relieve=0.4),
        "pared": PB.material_pbr("pared_e03", "Plaster003_2K-JPG", 1.5, "BOX", brillo=0.5, relieve=0.3),
        "acero": O.mat_acero_cepillado(),
        "carton": O.mat_carton(),
        "etiqueta": B.simple("etiqueta_caja", (0.7, 0.7, 0.66), 0.7),
        "estante": O.mat_pintura_metal("estante_e03", (0.20, 0.21, 0.22)),
        "negro": B.simple("plastico_negro", (0.01, 0.01, 0.011), 0.45),
    }


def _mesa(M, w=1.5, d=0.85):
    """Mesa de acero inoxidable (la cara de arriba en z = 0) con su canto doblado."""
    bm = bmesh.new()
    B.caja(bm, (0, 0, -0.02), (w, d, 0.04))
    for x in (-w / 2 + 0.05, w / 2 - 0.05):
        for y in (-d / 2 + 0.05, d / 2 - 0.05):
            B.caja(bm, (x, y, -0.48), (0.04, 0.04, 0.88))
    B.caja(bm, (0, 0, -0.75), (w - 0.1, d - 0.1, 0.02))
    B.objeto("mesa", bm, [M["acero"]])


def _estantes_fondo(M, y, x0, x1, semilla, mirando=1):
    """Estanterías con cajas de archivo contra una pared (fuera de foco, dan profundidad)."""
    rng = random.Random(semilla)
    x = x0
    k = 0
    while x + 1.0 <= x1:
        O.estante(f"estante{semilla}_{k}", x, y - (0.45 if mirando > 0 else 0.0), 1.0,
                  niveles=(-0.88, -0.48, -0.08, 0.32, 0.72, 1.12), mat=M["estante"])
        for z in (-0.87, -0.47, -0.07, 0.33, 0.73):
            xc = x + 0.05
            while xc < x + 0.95:
                wcaja = rng.uniform(0.25, 0.4)
                if xc + wcaja > x + 0.97:
                    break
                if rng.random() < 0.82:
                    alto = rng.uniform(0.24, 0.33)
                    O.caja_archivo(f"caja{semilla}_{k}_{int(z * 100)}_{int(xc * 100)}",
                                   (xc + wcaja / 2, y - 0.22 * (1 if mirando > 0 else -1), z + 0.01),
                                   (wcaja - 0.01, 0.38, alto), M["carton"], M["etiqueta"],
                                   giro=(0.0 if mirando > 0 else math.pi) + rng.uniform(-0.04, 0.04))
                xc += wcaja + rng.uniform(0.0, 0.04)
        x += 1.02
        k += 1


def _monitor(nombre, pos, giro, M, tam=(0.55, 0.32), fuerza=2.5, tinte=(0.55, 0.75, 1.0)):
    """Monitor encendido al fondo: casi siempre fuera de foco, da un punto de luz fría."""
    raiz = B.vacio(nombre, pos)
    raiz.rotation_euler = (0, 0, giro)

    def hacer(a):
        x, y, z = a.separar(B.coord_objeto(a))
        renglon = a.m("MULTIPLY", a.m("GREATER_THAN", a.m("FRACT", a.m("MULTIPLY", z, 1 / 0.018)), 0.55),
                      a.m("GREATER_THAN", a.m("FRACT", a.m("MULTIPLY", a.m("ADD", x, a.m("MULTIPLY", z, 7.0)), 3.1)), 0.3))
        col = a.mezcla((0.05, 0.07, 0.10), tinte, a.m("MULTIPLY", renglon, 0.8))
        return a.bsdf((0.01, 0.01, 0.01), 0.1, emision=col, fuerza=fuerza)
    pant = B.material(f"{nombre}_pantalla", hacer)
    bm = bmesh.new()                                                  # escritorio bajo el monitor
    B.caja(bm, (0, 0.1, -0.02), (1.2, 0.6, 0.04))
    for x in (-0.55, 0.55):
        B.caja(bm, (x, 0.1, -0.47), (0.04, 0.5, 0.9))
    B.objeto(f"{nombre}_escritorio", bm, [M["estante"]], padre=raiz)
    bm = bmesh.new()
    B.caja(bm, (0, 0.01, tam[1] / 2 + 0.12), (tam[0] + 0.03, 0.03, tam[1] + 0.03), 0)
    B.caja(bm, (0, 0.03, 0.06), (0.05, 0.03, 0.12), 0)
    B.caja(bm, (0, 0.03, 0.005), (0.22, 0.16, 0.01), 0)
    B.objeto(f"{nombre}_marco", bm, [M["negro"]], padre=raiz)
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in ((-tam[0] / 2, -0.006, 0.12), (tam[0] / 2, -0.006, 0.12),
                                    (tam[0] / 2, -0.006, 0.12 + tam[1]), (-tam[0] / 2, -0.006, 0.12 + tam[1]))]
    bm.faces.new(vs[::-1])
    B.objeto(f"{nombre}_pantalla", bm, [pant], padre=raiz)
    return raiz


def _escala_forense(nombre, pos, giro):
    """Regla de fotografía forense: una franja de cuadros blancos y negros de medio centímetro."""
    def hacer(a):
        x, y, _ = a.separar(B.coord_objeto(a))
        franja = a.m("GREATER_THAN", a.m("FRACT", a.m("MULTIPLY", x, 100.0)), 0.5)
        borde = a.m("LESS_THAN", a.m("ABSOLUTE", y), 0.004)
        return a.bsdf(a.mezcla((0.45, 0.45, 0.43), a.mezcla((0.02, 0.02, 0.02), (0.5, 0.5, 0.48), franja), borde), 0.55)
    mat = B.material(nombre, hacer)
    bm = bmesh.new()
    B.caja(bm, (0.05, 0, 0.0004), (0.10, 0.016, 0.0008))
    ob = B.objeto(nombre, bm, [mat])
    ob.location = pos
    ob.rotation_euler = (0, 0, giro)
    return ob


def _luces_interior(fria=60.0, calida=18.0, pos_fria=(0.0, 0.1, 1.55), pos_calida=(-0.7, -0.5, 0.75), mira=(0, 0, 0)):
    """Lámpara fluorescente fría arriba y una lámpara cálida de escritorio de lado."""
    l1 = B.luz("fluorescente", "AREA", pos_fria, fria, (0.85, 0.92, 1.0))
    l1.data.shape = "RECTANGLE"
    l1.data.size, l1.data.size_y = 1.2, 0.18
    l2 = B.luz("lampara", "SPOT", pos_calida, calida, (1.0, 0.78, 0.55), radio=0.06, cono=math.radians(70))
    l2.rotation_euler = (Vector(mira) - Vector(pos_calida)).to_track_quat("-Z", "Y").to_euler()
    return l1, l2


def _mundo_interior(escena, fuerza=0.04):
    PB.hdri(escena, "NightEnvironmentHDRI002_4K", fuerza=fuerza, giro_grados=40.0)


# --------------------------------------------------------------------------- 3.0: el iPhone en la mesa


def e03_iphone_evidencia(escena, cuadros, fps):
    """3.0 — «Cuando el FBI lo recoge, está apagado»: el iPhone 5C con la pantalla negra, dentro de
    su bolsa de evidencia, sobre la mesa de acero; la cámara se acerca despacio."""
    _mundo_interior(escena)
    M = _materiales_interior()
    _cuarto(M, 4.2, 4.2)
    _mesa(M)
    _estantes_fondo(M, 2.05, -2.0, 2.0, 31)
    _monitor("monitor", (-0.9, 1.35, -0.12), math.radians(12), M)
    tel, _ = O.iphone_5c("iphone", "azul")
    tel.location = (0.0, 0.0, 0.0004)
    tel.rotation_euler = (0, 0, math.radians(-8))
    bolsa = O.bolsa_evidencia("bolsa", 0.17, 0.27, 0.017)
    bolsa.location = (0.006, -0.03, 0.0)
    bolsa.rotation_euler = (0, 0, math.radians(-6))
    _escala_forense("escala", (0.11, -0.13, 0.0), math.radians(84))
    hoja = O.mat_etiqueta("formulario")
    bm = bmesh.new()
    B.caja(bm, (0, 0, 0.0003), (0.216, 0.279, 0.0006))
    f = B.objeto("formulario", bm, [hoja])
    f.location = (-0.27, 0.06, 0.0)
    f.rotation_euler = (0, 0, math.radians(14))
    _luces_interior(55.0, 14.0, (0.1, 0.25, 1.5), (-0.65, -0.45, 0.7))
    cam, mira = B.camara((0.30, -0.40, 0.40), lente=50, fstop=4.0, distancia_foco=0.5)
    cam.data.clip_start = 0.01
    for fr in range(1, cuadros + 2):
        u = _suave((fr - 1) / max(1, cuadros))
        B.clave(cam, "location", (0.30 - 0.08 * u, -0.40 + 0.11 * u, 0.40 - 0.08 * u), fr)
        B.clave(mira, "location", (0.0, 0.0 + 0.004 * u, 0.006), fr)
        cam.data.dof.focus_distance = (Vector(cam.location) - Vector((0, 0, 0.008))).length
        cam.data.dof.keyframe_insert("focus_distance", frame=fr)
    return dict(exposicion=0.0, exposicion_eevee=-0.9, volumen_fin=20.0)


# --------------------------------------------------------------------------- 3.11: bolsa de Faraday


def e03_bolsa_faraday(escena, cuadros, fps):
    """3.11 — El teléfono incautado sigue encendido y cargando, dentro de una bolsa de Faraday: se
    ve su pantalla por la ventana y el cable que sale por la solapa hacia una batería externa."""
    _mundo_interior(escena)
    M = _materiales_interior()
    _cuarto(M, 4.2, 4.2)
    _mesa(M)
    _estantes_fondo(M, -2.05, -2.0, 2.0, 41, mirando=-1)
    _monitor("monitor", (0.85, -1.35, -0.12), math.radians(180 - 15), M)
    bolsa, _ = O.bolsa_faraday("faraday", 0.105, 0.20, 0.024)
    vidrio = O.mat_vidrio_frente("faraday_vidrio", encendido=1.0, desbloqueo=0.0, brillo=2.2)
    tel, _ = O.iphone_5c("iphone", "azul", pantalla=vidrio, padre=bolsa)
    tel.location = (0.0, -0.012, 0.0006)
    tel.rotation_euler = (0, 0, math.pi)                     # el puerto mira a la boca de la bolsa (+y)
    bolsa.rotation_euler = (0, 0, math.radians(10))
    # cable: del puerto, sale por debajo de la solapa y baja a la mesa hasta la batería
    blanco = B.material("cable_blanco", lambda a: a.bsdf((0.78, 0.78, 0.76), 0.4, coat=0.2))
    bm = bmesh.new()
    pts = O.bezier((0.0, 0.07, 0.0045), (0.0, 0.10, 0.006), (0.004, 0.118, 0.004), (0.01, 0.13, 0.0016), 12)
    pts += O.bezier((0.01, 0.13, 0.0016), (0.02, 0.16, 0.0016), (0.06, 0.22, 0.0016), (0.13, 0.24, 0.0016), 16)[1:]
    O.tubo(bm, pts, 0.0016, 10)
    B.objeto("cable", bm, [blanco], padre=bolsa)
    bat = B.vacio("bateria", (0.17, 0.28, 0.0), padre=bolsa)
    bat.rotation_euler = (0, 0, math.radians(-70))
    gris = B.material("bateria_cuerpo", lambda a: a.bsdf((0.035, 0.036, 0.04), 0.35, coat=0.4))
    bm = bmesh.new()
    O.solido_perfilado(bm, 0.07, 0.14, 0.008, O.perfil_redondo(0.016, 0.004, 3), n=6)
    O.objeto_suave("bateria_cuerpo", bm, [gris], padre=bat)
    led = B.simple("led_bateria", (0.1, 0.3, 0.6), 0.3, emision=(0.2, 0.55, 1.0), fuerza=6.0)
    bm = bmesh.new()
    for k in range(4):
        B.caja(bm, (-0.012 + k * 0.008, -0.05, 0.0162), (0.004, 0.0025, 0.0006))
    B.objeto("leds", bm, [led], padre=bat)
    brillo_pant = B.luz("brillo_pantalla", "AREA", (0.0, -0.012, 0.03), 0.35, (0.55, 0.65, 1.0), padre=bolsa)
    brillo_pant.data.shape = "RECTANGLE"
    brillo_pant.data.size, brillo_pant.data.size_y = 0.05, 0.09
    brillo_pant.rotation_euler = (math.pi, 0, 0)                 # la pantalla alumbra hacia arriba
    _escala_forense("escala", (-0.16, -0.05, 0.0), math.radians(95))
    _luces_interior(45.0, 10.0, (-0.1, -0.3, 1.5), (0.7, 0.55, 0.7))
    cam, mira = B.camara((0.20, 0.40, 0.30), lente=50, fstop=4.0, distancia_foco=0.5)
    cam.data.clip_start = 0.01
    for fr in range(1, cuadros + 2):
        u = _suave((fr - 1) / max(1, cuadros))
        B.clave(cam, "location", (0.20 - 0.07 * u, 0.40 - 0.10 * u, 0.30 - 0.07 * u), fr)
        B.clave(mira, "location", (0.005, 0.01 - 0.01 * u, 0.012), fr)
        cam.data.dof.focus_distance = (Vector(cam.location) - Vector((0.0, -0.005, 0.02))).length
        cam.data.dof.keyframe_insert("focus_distance", frame=fr)
    return dict(exposicion=0.0, exposicion_eevee=-0.3, volumen_fin=20.0)


# --------------------------------------------------------------------------- 3.3: el puerto Lightning


def e03_puerto_lightning(escena, cuadros, fps, llega=4.0):
    """3.3 — «Primero, la puerta»: el borde de abajo de un iPhone 5C de muy cerca; un cable
    Lightning se acerca y entra en el puerto a los `llega` segundos."""
    _mundo_interior(escena, 0.03)
    M = _materiales_interior()
    escritorio = B.material("escritorio", lambda a: a.bsdf(
        a.v("SCALE", (0.03, 0.028, 0.026), escala=a.rango(a.ruido(B.pos_mundo(a), 60.0, 4.0)[0], 0.3, 0.7, 0.8, 1.2)), 0.5,
        normal=a.bump(a.ruido(B.pos_mundo(a), 400.0, 3.0)[0], 0.1, 0.0003)))
    bm = bmesh.new()
    B.caja(bm, (0, 0, -0.01), (1.6, 1.2, 0.02))
    B.objeto("escritorio", bm, [escritorio])
    tel, _ = O.iphone_5c("iphone", "azul", detalles_abajo=True)
    tel.location = (0.0, 0.0, 0.00005)
    plug = O.conector_lightning("lightning", 0.4, caida=-(O.Z_BULTO - 0.0016))
    y_dentro = -O.ALTO / 2 - 0.0004
    for fr in range(1, cuadros + 2):
        t = (fr - 1) / fps
        u = _suave((t - (llega - 2.6)) / 2.6)
        y = y_dentro - 0.028 * (1 - u)
        x = 0.0012 * (1 - u) * math.sin(t * 1.7)
        z = O.Z_BULTO + 0.0009 * (1 - u) * math.sin(t * 1.3 + 0.5)
        B.clave(plug, "location", (x, y, z), fr)
        B.clave(plug, "rotation_euler", (0.0, 0.0, math.radians(3.0) * (1 - u)), fr)
    # luces de estudio: suave arriba a la izquierda, contraluz frío y un relleno bajo de frente
    # la principal, baja y de lado: así su reflejo no cae sobre el vidrio negro del frente
    k = B.luz("principal", "AREA", (-0.20, -0.13, 0.07), 1.5, (1.0, 0.93, 0.85))
    k.data.size = 0.22
    k.rotation_euler = (Vector((0, -0.06, 0.004)) - Vector((-0.20, -0.13, 0.07))).to_track_quat("-Z", "Y").to_euler()
    # contraluz baja: alta se reflejaba en el vidrio negro del frente y lo hacía ver blanco
    c = B.luz("contraluz", "AREA", (0.17, 0.06, 0.025), 1.0, (0.7, 0.8, 1.0))
    c.data.size = 0.12
    c.rotation_euler = (Vector((0, -0.06, 0.004)) - Vector((0.17, 0.06, 0.025))).to_track_quat("-Z", "Y").to_euler()
    r = B.luz("relleno", "AREA", (0.05, -0.20, 0.03), 0.35, (1.0, 0.95, 0.9))
    r.data.size = 0.12
    r.rotation_euler = (Vector((0, -0.062, 0.004)) - Vector((0.05, -0.20, 0.03))).to_track_quat("-Z", "Y").to_euler()
    # luces lejanas del cuarto: fuera de foco, círculos de luz detrás
    for i, (pos, col) in enumerate((((0.35, 0.9, 0.25), (1.0, 0.7, 0.4)), ((-0.5, 1.1, 0.4), (0.5, 0.7, 1.0)),
                                    ((0.9, 0.7, 0.15), (1.0, 0.8, 0.6)), ((-0.15, 1.3, 0.55), (1.0, 0.6, 0.35)))):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.012, matrix=Matrix.Translation(pos))
        B.objeto(f"foco{i}", bm, [B.simple(f"foco{i}", col, 0.5, emision=col, fuerza=40.0)])
    # de frente y desde arriba (unos 30°): el cable llega por la mesa y no tapa el puerto hasta entrar
    cam, mira = B.camara((-0.055, -0.108, 0.042), lente=60, fstop=10.0, distancia_foco=0.075)
    cam.data.clip_start = 0.002
    for fr in range(1, cuadros + 2):
        t = (fr - 1) / fps
        u = _suave(t / (cuadros / fps))
        B.clave(cam, "location", (-0.055 + 0.008 * u, -0.108 + 0.008 * u, 0.042 - 0.006 * u), fr)
        B.clave(mira, "location", (0.0015, -O.ALTO / 2, O.Z_BULTO - 0.0004), fr)
        cam.data.dof.focus_distance = (Vector(cam.location) - Vector((0.0, -O.ALTO / 2, O.Z_BULTO))).length
        cam.data.dof.keyframe_insert("focus_distance", frame=fr)
    return dict(exposicion=0.0, exposicion_eevee=0.0, volumen_fin=10.0, desenfoque_movimiento=False)


# --------------------------------------------------------------------------- 3.7: una docena de 5C


def e03_docena_5c(escena, cuadros, fps, desbloqueos=()):
    """3.7 — «Lo probaron en una docena de iPhone 5C»: doce 5C de colores sobre una mesa de
    laboratorio, conectados por cable; muestran el teclado del código y, uno por uno, a los tiempos
    de `desbloqueos`, la pantalla de inicio."""
    _mundo_interior(escena, 0.05)
    M = _materiales_interior()
    _cuarto(M, 4.4, 4.4)
    tapete = B.material("tapete_esd", lambda a: a.bsdf(
        a.v("SCALE", (0.035, 0.05, 0.06), escala=a.rango(a.ruido(B.pos_mundo(a), 25.0, 4.0)[0], 0.3, 0.7, 0.85, 1.15)), 0.62,
        normal=a.bump(a.ruido(B.pos_mundo(a), 300.0, 2.0)[0], 0.1, 0.0004)))
    _mesa(M, 1.8, 0.95)
    bm = bmesh.new()
    B.caja(bm, (0, 0.0, 0.001), (1.3, 0.75, 0.002))
    B.objeto("tapete", bm, [tapete])
    _estantes_fondo(M, 2.15, -2.1, 2.1, 71)
    blanco = B.material("cables_blancos", lambda a: a.bsdf((0.78, 0.78, 0.76), 0.4, coat=0.2))
    colores = ["blanco", "azul", "rosa", "verde", "amarillo", "azul", "blanco", "rosa", "amarillo", "verde", "azul", "blanco"]
    pantallas = []
    bm_c = bmesh.new()
    for k in range(12):
        fila, col = divmod(k, 6)
        x = -0.2125 + col * 0.085
        y = -0.085 + fila * 0.165
        v = O.mat_vidrio_frente(f"vidrio{k}", encendido=1.0, desbloqueo=0.0, brillo=1.8, tono=k * 0.37)
        tel, _ = O.iphone_5c(f"iphone{k}", colores[k], pantalla=v)
        tel.location = (x, y, 0.0024)
        tel.rotation_euler = (0, 0, math.radians(random.Random(k).uniform(-2.5, 2.5)))
        pantallas.append(v)
        # cable: del puerto hacia el frente, da vuelta por el hueco entre teléfonos y se va atrás
        y0 = y - O.ALTO / 2
        pts = O.bezier((x, y0 - 0.002, 0.0045), (x, y0 - 0.02, 0.004), (x + 0.03, y0 - 0.03, 0.0035), (x + 0.0425, y0 - 0.005, 0.0035), 10)
        pts += O.bezier((x + 0.0425, y0 - 0.005, 0.0035), (x + 0.0425, y0 + 0.08, 0.0035), (x + 0.042, 0.30, 0.0035),
                        (x * 0.4, 0.33, 0.004), 16)[1:]
        O.tubo(bm_c, pts, 0.0014, 8)
    B.objeto("cables", bm_c, [blanco])
    hub = B.material("hub", lambda a: a.bsdf((0.03, 0.03, 0.035), 0.4))
    bm = bmesh.new()
    B.caja(bm, (0, 0.345, 0.014), (0.32, 0.05, 0.028))
    B.objeto("hub", bm, [hub])
    led = B.simple("leds_hub", (0.1, 0.3, 0.1), 0.3, emision=(0.3, 1.0, 0.4), fuerza=8.0)
    bm = bmesh.new()
    for k in range(12):
        B.caja(bm, (-0.14 + k * 0.0255, 0.319, 0.022), (0.003, 0.001, 0.003))
    B.objeto("leds_hub", bm, [led])
    # laptop al fondo, con la terminal del programa
    lap = B.vacio("laptop", (0.42, 0.30, 0.0))
    lap.rotation_euler = (0, 0, math.radians(-25))
    alu = B.material("aluminio", lambda a: a.bsdf((0.45, 0.46, 0.48), 0.35, metal=1.0))
    bm = bmesh.new()
    B.caja(bm, (0, 0, 0.008), (0.32, 0.22, 0.016))
    B.objeto("laptop_base", bm, [alu], padre=lap)
    tapa = B.vacio("laptop_tapa", (0, 0.11, 0.016), padre=lap)
    tapa.rotation_euler = (math.radians(-12), 0, 0)
    bm = bmesh.new()
    B.caja(bm, (0, 0.006, 0.105), (0.32, 0.008, 0.21))
    B.objeto("laptop_tapa", bm, [alu], padre=tapa)

    def terminal(a):
        x, _, z = a.separar(B.coord_objeto(a))
        renglon = a.m("MULTIPLY", a.m("GREATER_THAN", a.m("FRACT", a.m("MULTIPLY", z, 1 / 0.009)), 0.45),
                      a.m("GREATER_THAN", a.m("FRACT", a.m("MULTIPLY", a.m("ADD", x, a.m("MULTIPLY", a.m("FLOOR", a.m("MULTIPLY", z, 1 / 0.009)), 0.37)), 9.0)), 0.25))
        return a.bsdf((0.005, 0.005, 0.005), 0.1, emision=a.mezcla((0.01, 0.02, 0.015), (0.55, 0.95, 0.65), renglon), fuerza=2.0)
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in ((-0.145, 0.0015, 0.012), (0.145, 0.0015, 0.012), (0.145, 0.0015, 0.198), (-0.145, 0.0015, 0.198))]
    bm.faces.new(vs[::-1])
    B.objeto("laptop_pantalla", bm, [B.material("terminal", terminal)], padre=tapa)
    _luces_interior(70.0, 12.0, (0.0, 0.05, 1.55), (-0.8, -0.4, 0.7))
    for k, v in enumerate(pantallas):
        t_k = desbloqueos[k] if k < len(desbloqueos) else None
        if t_k is None or t_k * fps > cuadros:
            marcas = (1, cuadros + 1)
        else:
            marcas = (1, max(1, int(t_k * fps)), max(1, int(t_k * fps)) + 5, cuadros + 1)
        for fr in marcas:
            tt = (fr - 1) / fps
            _clave_valor(v, "desbloqueo", 1.0 if (t_k is not None and tt >= t_k + 0.1) else 0.0, fr)
    cam, mira = B.camara((-0.30, -0.52, 0.34), lente=40, fstop=2.8, distancia_foco=0.6)
    cam.data.clip_start = 0.01
    for fr in range(1, cuadros + 2):
        u = _suave((fr - 1) / max(1, cuadros))
        B.clave(cam, "location", (-0.30 + 0.16 * u, -0.52 + 0.04 * u, 0.34 - 0.03 * u), fr)
        B.clave(mira, "location", (-0.02 + 0.10 * u, 0.02, 0.0), fr)
        cam.data.dof.focus_distance = (Vector(cam.location) - Vector((-0.02 + 0.10 * u, 0.0, 0.0))).length
        cam.data.dof.keyframe_insert("focus_distance", frame=fr)
    return dict(exposicion=0.0, exposicion_eevee=0.3, volumen_fin=20.0)


# --------------------------------------------------------------------------- 3.12: sala de evidencias


def e03_sala_evidencias(escena, cuadros, fps, reinicios=()):
    """3.12 — Detroit, 2024: en el estante de evidencias, iPhones en sus bolsas, apagados y quietos.
    En los tiempos de `reinicios` (índice, segundo) uno se enciende solo: la manzana del arranque y,
    después, la pantalla de bloqueo."""
    _mundo_interior(escena, 0.03)
    M = _materiales_interior()
    _cuarto(M, 6.0, 4.0, piso=0.0, alto=3.0, centro=(0.0, 0.0))
    _estantes_fondo(M, 0.5 + 0.45, -2.6, -0.7, 81)
    _estantes_fondo(M, 0.5 + 0.45, 0.7, 2.7, 82)
    # estante central con el rack de teléfonos
    O.estante("estante_central", -0.65, 0.5, 1.3, niveles=(0.05, 0.45, 0.85, 1.25, 1.65, 2.05), mat=M["estante"])
    respaldo = B.material("respaldo", lambda a: a.bsdf((0.12, 0.12, 0.13), 0.6))
    bm = bmesh.new()
    B.caja(bm, (0.0, 0.88, 1.45), (1.28, 0.02, 0.38))
    B.objeto("respaldo", bm, [respaldo])
    rng = random.Random(12)
    for z in (0.06, 0.46, 0.86, 1.66):
        xc = -0.6
        while xc < 0.55:
            wc = rng.uniform(0.25, 0.38)
            if xc + wc > 0.62:
                break
            O.caja_archivo(f"caja_c{int(z * 100)}_{int(xc * 100)}", (xc + wc / 2, 0.72, z + 0.01),
                           (wc - 0.01, 0.38, rng.uniform(0.24, 0.33)), M["carton"], M["etiqueta"], rng.uniform(-0.03, 0.03))
            xc += wc + 0.02
    pantallas, luces = [], []
    n = 8
    for k in range(n):
        x = -0.50 + k * (1.0 / (n - 1))
        ranura = B.vacio(f"ranura{k}", (x, 0.80, 1.262 + O.ALTO / 2 * math.sin(math.radians(80))))
        ranura.rotation_euler = (math.radians(80), 0, math.radians(rng.uniform(-3, 3)))
        v = O.mat_vidrio_frente(f"vidrio{k}", encendido=0.0, brillo=2.0, tono=k * 0.41)
        tel, _ = O.iphone_5c(f"iphone{k}", ["blanco", "azul", "blanco", "rosa", "blanco", "verde", "azul", "blanco"][k],
                             pantalla=v, padre=ranura)
        tel.location = (0.0, 0.0, -0.011)
        bolsa = O.bolsa_evidencia(f"bolsa{k}", 0.095, 0.26, 0.014, padre=ranura, etiqueta="arriba")
        bolsa.location = (0.0, 0.065, -0.012)
        pantallas.append(v)
        lz = B.luz(f"brillo{k}", "AREA", (0.0, 0.0, 0.012), 0.0, (0.75, 0.82, 1.0), padre=ranura)
        lz.data.size = 0.06
        lz.rotation_euler = (math.pi, 0, 0)                  # la pantalla alumbra hacia afuera, no a la bolsa
        luces.append(lz)
    reinicio = {int(i): float(t) for i, t in reinicios}
    for k, v in enumerate(pantallas):
        t0 = reinicio.get(k)
        for fr in range(1, cuadros + 2, 2):
            t = (fr - 1) / fps
            if t0 is None or t < t0:
                en, arr = 0.0, 1.0
            else:
                x = t - t0
                en = _suave(x / 0.35) * (1.0 if x < 4.5 else 0.75)
                arr = 1.0 if x < 4.3 else 1.0 - _suave((x - 4.3) / 0.4)
            _clave_valor(v, "encendido", en, fr)
            _clave_valor(v, "arranque", arr, fr)
            _clave_luz(luces[k], 0.6 * en, fr)
    tubo_l = B.luz("fluorescente", "AREA", (0.0, -0.5, 2.9), 55.0, (0.82, 0.9, 1.0))
    tubo_l.data.shape = "RECTANGLE"
    tubo_l.data.size, tubo_l.data.size_y = 0.18, 1.2
    tubo_l.rotation_euler = (0, 0, math.radians(90))
    pasillo = B.luz("pasillo", "AREA", (-2.5, -1.6, 2.6), 30.0, (1.0, 0.8, 0.6))
    pasillo.data.size = 0.6
    cam, mira = B.camara((-0.62, -0.62, 1.43), lente=42, fstop=2.0, distancia_foco=1.5)
    for fr in range(1, cuadros + 2):
        u = _suave((fr - 1) / max(1, cuadros))
        B.clave(cam, "location", (-0.62 + 0.55 * u, -0.62 + 0.03 * u, 1.43 - 0.01 * u), fr)
        B.clave(mira, "location", (-0.18 + 0.42 * u, 0.80, 1.30), fr)
        cam.data.dof.focus_distance = (Vector(cam.location) - Vector((-0.18 + 0.42 * u, 0.78, 1.30))).length
        cam.data.dof.keyframe_insert("focus_distance", frame=fr)
    return dict(exposicion=0.0, exposicion_eevee=0.6, volumen_fin=20.0)


# =========================================================================== exterior: 3.0


def _materiales_exterior():
    M = {
        "asfalto": PB.material_pbr("asfalto_e03", "Asphalt010_2K-JPG", 2.5, "FLAT", brillo=0.75, relieve=0.4),
        "concreto": PB.material_pbr("concreto_e03", "Concrete031_2K-JPG", 3.0, "BOX", brillo=0.8, relieve=0.4, sucio_abajo=True),
        "estuco": PB.material_pbr("estuco_e03", "Plaster003_2K-JPG", 2.0, "BOX", tinte_objeto=True, brillo=1.0, relieve=0.5,
                                  sucio_abajo=True),
        "corteza": PB.material_pbr("corteza_e03", "Bark001_2K-JPG", 1.2, "BOX", brillo=0.5, relieve=1.0),
        "seca": B.material("palma_seca", lambda a: a.bsdf(
            a.v("SCALE", (0.16, 0.10, 0.05), escala=a.rango(a.ruido(B.pos_mundo(a), 6.0, 4.0)[0], 0.3, 0.7, 0.5, 1.2)), 0.85,
            normal=a.bump(a.ruido(a.v("MULTIPLY", B.pos_mundo(a), (2.0, 2.0, 30.0)), 2.0, 4.0)[0], 0.8, 0.02))),
        "palma": B.material("palma", lambda a: a.bsdf(
            a.v("SCALE", (0.025, 0.04, 0.018), escala=a.rango(a.ruido(B.pos_mundo(a), 3.0, 3.0)[0], 0.3, 0.7, 0.6, 1.3)), 0.6)),
        "poste": B.simple("poste", (0.12, 0.12, 0.12), 0.5, metal=0.6),
        "lampara": B.simple("lampara_poste", (1, 0.8, 0.6), 0.2, emision=(1.0, 0.72, 0.45), fuerza=40.0),
        "pintura_negra": B.simple("pintura_negra", (0.008, 0.008, 0.01), 0.25, coat=1.0),
        "pintura_blanca": B.simple("pintura_blanca", (0.62, 0.62, 0.6), 0.3, coat=1.0),
        "vidrio_auto": B.simple("vidrio_auto", (0.004, 0.005, 0.006), 0.05),
        "llanta": B.simple("llanta", (0.01, 0.01, 0.01), 0.8),
        "raya": B.material("raya_estacionamiento", lambda a: a.bsdf(
            a.v("SCALE", (0.55, 0.55, 0.5), escala=a.rango(a.ruido(B.pos_mundo(a), 4.0, 5.0)[0], 0.35, 0.65, 0.35, 1.0)), 0.7)),
        "seto": B.material("seto", lambda a: a.bsdf(
            a.v("SCALE", (0.02, 0.04, 0.015), escala=a.rango(a.ruido(B.pos_mundo(a), 4.0, 5.0)[0], 0.3, 0.7, 0.5, 1.3)), 0.8,
            normal=a.bump(a.ruido(B.pos_mundo(a), 9.0, 5.0)[0], 1.0, 0.1))),
        "montes": B.material("montes", lambda a: a.bsdf(                  # más claros abajo: la bruma del valle
            a.mezcla((0.030, 0.028, 0.034), (0.006, 0.007, 0.010), a.rango(a.separar(B.pos_mundo(a))[2], 0.0, 2200.0)), 0.9)),
        "aluminio": B.simple("aluminio", (0.35, 0.36, 0.37), 0.35, metal=1.0),
    }
    M["ventanas"] = _mat_ventanas()
    return M


def _mat_ventanas():
    """Banda de ventanas de vidrio oscuro: cada hoja (1.7 m) con su persiana; unas pocas oficinas
    quedaron con la luz fluorescente prendida (al azar por hoja y piso)."""
    def hacer(a):
        p = B.pos_mundo(a)
        x, y, z = a.separar(p)
        hoja = a.m("FLOOR", a.m("MULTIPLY", a.m("ADD", x, y), 1 / 1.7))
        piso = a.m("FLOOR", a.m("MULTIPLY", z, 1 / 4.0))
        celda = a.nodo("ShaderNodeCombineXYZ")
        a.unir(hoja, celda, 0)
        a.unir(piso, celda, 1)
        azar = a.nodo("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
        a.unir((celda, 0), azar, "Vector")
        prendida = a.m("GREATER_THAN", (azar, "Value"), 0.86)
        persiana = a.rango(a.m("FRACT", a.m("MULTIPLY", z, 1 / 0.06)), 0.0, 1.0, 0.55, 1.0)
        techo = a.rango(a.m("FRACT", a.m("MULTIPLY", z, 1 / 4.0)), 0.25, 0.8, 0.5, 1.2)
        emis = a.v("SCALE", (0.70, 0.82, 1.0), escala=a.m("MULTIPLY", a.m("MULTIPLY", prendida, persiana), a.m("MULTIPLY", techo, 0.16)))
        return a.bsdf((0.006, 0.007, 0.009), 0.06, emision=emis, fuerza=1.0, especular=0.8)
    return B.material("ventanas_e03", hacer)


def _edificio(M, x0, x1, y_frente, fondo, color, nombre, giro=0.0, pivote=(0.0, 0.0)):
    """Edificio de oficinas de dos pisos, de estuco color arena, con bandas de ventanas, pilares,
    pretil y lámparas de pared."""
    raiz = B.vacio(nombre, (pivote[0], pivote[1], 0.0))
    raiz.rotation_euler = (0, 0, giro)
    px, py = pivote
    bm = bmesh.new()
    B.caja(bm, ((x0 + x1) / 2 - px, y_frente + fondo / 2 - py, 4.8), (x1 - x0, fondo, 9.6))
    B.caja(bm, ((x0 + x1) / 2 - px, y_frente - 0.05 - py, 9.65), (x1 - x0 + 0.2, 0.3, 0.3))       # remate del pretil
    B.objeto(f"{nombre}_cuerpo", bm, [M["estuco"]], color=color, padre=raiz)
    bm = bmesh.new()
    bm_m = bmesh.new()
    bahia = 8.0
    x = x0
    while x + bahia <= x1 + 0.01:
        for z0, z1 in ((1.0, 3.3), (5.0, 7.3)):
            B.caja(bm, (x + bahia / 2 - px, y_frente - 0.03 - py, (z0 + z1) / 2), (bahia - 1.4, 0.06, z1 - z0))
            m = x + 0.7
            while m <= x + bahia - 0.7 + 0.01:
                B.caja(bm_m, (m - px, y_frente - 0.07 - py, (z0 + z1) / 2), (0.07, 0.06, z1 - z0 + 0.08))
                m += (bahia - 1.4) / 4
            B.caja(bm_m, (x + bahia / 2 - px, y_frente - 0.07 - py, z0 - 0.04), (bahia - 1.3, 0.08, 0.08))
            B.caja(bm_m, (x + bahia / 2 - px, y_frente - 0.07 - py, z1 + 0.04), (bahia - 1.3, 0.08, 0.08))
        x += bahia
    B.objeto(f"{nombre}_ventanas", bm, [M["ventanas"]], padre=raiz)
    B.objeto(f"{nombre}_marcos", bm_m, [M["aluminio"]], padre=raiz)
    luces = []
    x = x0 + bahia
    k = 0
    while x < x1 - 1:
        if k % 2 == 0:
            bm = bmesh.new()
            B.caja(bm, (x - px, y_frente - 0.12 - py, 3.9), (0.3, 0.22, 0.25), 0)
            B.caja(bm, (x - px, y_frente - 0.2 - py, 3.76), (0.24, 0.1, 0.02), 1)
            B.objeto(f"{nombre}_lampara{k}", bm, [M["poste"], M["lampara"]], padre=raiz)
            l_ = B.luz(f"{nombre}_luz{k}", "SPOT", (x - px, y_frente - 0.3 - py, 3.7), 180.0, (1.0, 0.70, 0.42),
                       radio=0.08, cono=math.radians(110), padre=raiz)
            l_.rotation_euler = (math.radians(-25), 0, 0)
            luces.append(l_)
        x += bahia
        k += 1
    return raiz


def _cinta_policial(nombre, puntos, ancho=0.075, caida=0.05):
    """Cinta amarilla de la policía de EE. UU. entre dos estacas (letras negras sugeridas)."""
    def hacer(a):
        u, v, _ = a.separar((a.nodo("ShaderNodeUVMap"), "UV"))
        letra = a.m("MULTIPLY", a.m("GREATER_THAN", a.m("FRACT", a.m("MULTIPLY", u, 9.0)), 0.35),
                    a.m("MULTIPLY", a.m("GREATER_THAN", v, 0.28), a.m("LESS_THAN", v, 0.72)))
        letra = a.m("MULTIPLY", letra, a.m("GREATER_THAN", a.m("FRACT", a.m("MULTIPLY", u, 0.9)), 0.2))
        return a.bsdf(a.mezcla((0.85, 0.62, 0.02), (0.01, 0.01, 0.01), a.m("MULTIPLY", letra, 0.85)), 0.4, especular=0.6)
    mat = B.material(nombre + "_mat", hacer)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UV")
    largo = 0.0
    for p0, p1 in zip(puntos[:-1], puntos[1:]):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        lado = d.cross(Vector((0, 0, 1))).normalized()
        filas = []
        for i in range(25):
            s = i / 24
            c = p0 + d * s - Vector((0, 0, caida * d.length * 4 * s * (1 - s)))
            gira = 0.3 * math.sin(s * math.pi * 3 + largo)
            arriba = Vector((0, 0, 1)) * math.cos(gira) + lado * math.sin(gira)
            filas.append((bm.verts.new(c + arriba * ancho / 2), bm.verts.new(c - arriba * ancho / 2), largo + d.length * s))
        for (a0, b0, u0), (a1, b1, u1) in zip(filas[:-1], filas[1:]):
            f = bm.faces.new((a0, a1, b1, b0))
            for loop, (uu, vv) in zip(f.loops, ((u0, 1), (u1, 1), (u1, 0), (u0, 0))):
                loop[uv].uv = (uu, vv)
        largo += d.length
    return B.objeto(nombre, bm, [mat])


def _cono_trafico(k, pos, M_naranja, M_blanco):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.17, radius2=0.03, depth=0.7,
                          matrix=Matrix.Translation((pos[0], pos[1], 0.38)))
    B.caja(bm, (pos[0], pos[1], 0.015), (0.4, 0.4, 0.03))
    B.objeto(f"cono{k}", bm, [M_naranja])
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=0.105, radius2=0.085, depth=0.1,
                          matrix=Matrix.Translation((pos[0], pos[1], 0.5)))
    B.objeto(f"cono{k}_franja", bm, [M_blanco])


def e03_centro_noche(escena, cuadros, fps):
    """3.0 — San Bernardino, la noche del 2 de diciembre de 2015: el Inland Regional Center, un
    edificio de oficinas de estuco color arena, vacío; el estacionamiento iluminado por los postes,
    palmeras, los cerros de San Bernardino al fondo y, a lo lejos, las luces de las patrullas. En
    primer plano, fuera de foco, la cinta amarilla de la policía. No hay nadie."""
    PB.hdri(escena, "NightEnvironmentHDRI002_4K", fuerza=0.12, giro_grados=200.0, fondo_camara="madrugada")
    M = _materiales_exterior()
    rng = random.Random(5)
    bm = bmesh.new()
    B.caja(bm, (0, 10, -0.05), (240, 120, 0.1))
    B.objeto("estacionamiento", bm, [M["asfalto"]])
    bm = bmesh.new()
    B.caja(bm, (0, 43.0, 0.07), (110, 5.0, 0.14))                    # banqueta de concreto frente al edificio
    B.caja(bm, (0, 40.45, 0.08), (110, 0.15, 0.16))                  # guarnición
    B.objeto("banqueta", bm, [M["concreto"]])
    bm = bmesh.new()
    for y0, y1 in ((28.0, 38.5), (12.0, 22.5)):                      # dos filas de cajones
        x = -40.0
        while x <= 40.0:
            B.caja(bm, (x, (y0 + y1) / 2, 0.003), (0.1, y1 - y0, 0.006))
            x += 2.7
    B.objeto("rayas", bm, [M["raya"]])
    bm = bmesh.new()                                                 # setos frente a la fachada
    for x0 in (-38, -24, -10, 6, 20, 32):
        B.caja(bm, (x0 + 4.5, 44.2, 0.55), (9.0, 1.3, 0.85))
    B.objeto("setos", bm, [M["seto"]])
    _edificio(M, -40.0, 40.0, 45.0, 28.0, (0.62, 0.50, 0.36), "irc")
    _edificio(M, 44.0, 84.0, 54.0, 24.0, (0.58, 0.47, 0.34), "irc_b", giro=math.radians(-18), pivote=(44.0, 54.0))
    # entrada: puertas de vidrio con el vestíbulo encendido y una marquesina
    vest = B.simple("vestibulo", (0.02, 0.02, 0.02), 0.05, emision=(1.0, 0.85, 0.65), fuerza=0.12)
    bm = bmesh.new()
    B.caja(bm, (0.0, 44.94, 1.6), (5.6, 0.04, 3.0))
    B.objeto("vestibulo", bm, [vest])
    bm = bmesh.new()
    B.caja(bm, (0.0, 43.4, 4.05), (8.0, 3.4, 0.35))
    for x in (-3.6, 3.6):
        B.caja(bm, (x, 42.0, 2.0), (0.35, 0.35, 4.0))
    B.objeto("marquesina", bm, [M["concreto"]])
    for k, (x, alto) in enumerate(((-27.0, 15.5), (-15.5, 17.5), (12.5, 14.5), (25.0, 18.0), (36.0, 16.0))):
        O.palmera(k, x, 42.3 + rng.uniform(-0.3, 0.3), alto, M, rng)
    luces = [O.poste_estacionamiento(k, x, y, M) for k, (x, y) in enumerate(((-30.0, 25.5), (0.0, 25.5), (30.0, 25.5), (-14.0, 4.5), (16.0, 4.5)))]
    # cerros de San Bernardino al fondo
    bm = bmesh.new()
    pts = []
    for i in range(241):
        x = -16000 + 32000 * i / 240
        z = 1700 + 420 * math.sin(i * 0.11) + 260 * math.sin(i * 0.31 + 1.3) + 90 * math.sin(i * 0.9) + rng.uniform(0, 60)
        pts.append((bm.verts.new((x, 10000, -50)), bm.verts.new((x, 10000, z))))
    for (a0, b0), (a1, b1) in zip(pts[:-1], pts[1:]):
        bm.faces.new((a0, a1, b1, b0))
    B.objeto("cerros", bm, [M["montes"]])
    # patrullas a lo lejos, a la izquierda, y una más allá del edificio
    destellos = []
    for k, (x, y, g) in enumerate(((-24.0, 34.0, math.radians(35)), (-19.0, 36.8, math.radians(-15)), (23.5, 35.5, math.radians(200)),
                                   (58.0, 40.0, math.radians(-60)))):
        _, mats, lz = O.patrulla(k, x, y, g, M)
        destellos.append((k, mats, lz, rng.uniform(0, 1)))
    # cinta en primer plano entre dos conos
    naranja = B.simple("cono_naranja", (0.85, 0.18, 0.02), 0.5)
    blanco = B.simple("cono_blanco", (0.8, 0.8, 0.78), 0.4)
    _cono_trafico(0, (-6.8, 4.4), naranja, blanco)
    _cono_trafico(1, (-1.0, 5.6), naranja, blanco)
    _cono_trafico(2, (5.0, 4.8), naranja, blanco)
    _cinta_policial("cinta", [(-6.8, 4.4, 0.74), (-1.0, 5.6, 0.74), (5.0, 4.8, 0.74)])
    B.neblina((0, 20, 12), (180, 120, 24), 0.0016, (0.75, 0.74, 0.78), anisotropia=0.3, nombre="neblina")
    for fr in range(1, cuadros + 2):
        t = (fr - 1) / fps
        for k, (rojo, azul), (lr, la), fase in destellos:
            r_, a_ = O.destello(t, fase, k)
            _clave_emision(rojo, 40.0 * r_ + 1.0, fr)
            _clave_emision(azul, 60.0 * a_ + 1.0, fr)
            _clave_luz(lr, 380.0 * r_, fr)
            _clave_luz(la, 560.0 * a_, fr)
    cam, mira = B.camara((-5.5, -1.5, 1.5), lente=30, fstop=2.8, distancia_foco=45.0)
    cam.data.clip_start, cam.data.clip_end = 0.5, 20000.0
    for fr in range(1, cuadros + 2):
        u = _suave((fr - 1) / max(1, cuadros))
        B.clave(cam, "location", (-5.5 + 2.6 * u, -1.5 + 0.9 * u, 1.5 + 0.04 * u), fr)
        B.clave(mira, "location", (-1.2 + 1.0 * u, 45.0, 6.0), fr)
    return dict(exposicion=0.0, exposicion_eevee=0.2, volumen_fin=260.0)
