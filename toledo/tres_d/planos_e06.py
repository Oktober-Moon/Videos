"""Planos 3D de la escena 6 («La casa declara»): los aparatos de la casa de los Dabate, de cerca.

Firma: plano(escena, cuadros, fps, **params) -> dict | None. Los arma `tres_d/plano.py`.
Los objetos y materiales comunes con la escena 5 están en `tres_d/casa_e05.py`.
"""

import math

import bmesh
from mathutils import Vector

from tres_d import base as B
from tres_d import casa_e05 as CA


def _suave(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def _mundo_gris(escena, fuerza=0.3):
    mundo, nt, salida = B.mundo_nuevo(escena, "interior")
    fondo = nt.nodes.new("ShaderNodeBackground")
    fondo.inputs["Color"].default_value = (0.55, 0.58, 0.62, 1)
    fondo.inputs["Strength"].default_value = fuerza
    nt.links.new(fondo.outputs[0], salida.inputs["Surface"])
    CA.sin_rayas(escena)


def e06_sensor_puerta(escena, cuadros, fps, t_abre=2.0, abre_seg=2.6, grados=48.0):
    """6.2 — El contacto magnético de la alarma en la puerta de la cochera: el interruptor en el marco
    y el imán en la puerta, uno junto al otro. Desde `t_abre` la puerta se abre despacio y el imán se
    aleja del interruptor."""
    _mundo_gris(escena, 0.25)
    M = CA.mats_interior()
    bm = bmesh.new()
    CA.cubo(bm, 0.12, 2.0, -0.02, 0.10, -0.2, 2.6, 0)                    # pared, del lado de la cerradura
    CA.cubo(bm, -2.4, -0.98, -0.02, 0.10, -0.2, 2.6, 0)                  # pared, del lado de las bisagras
    CA.cubo(bm, -0.98, 0.12, -0.02, 0.10, 2.16, 2.6, 0)                  # sobre la puerta
    CA.cubo(bm, 0.0, 0.12, -0.035, 0.10, -0.2, 2.16, 1)                  # jamba y moldura de la cerradura
    CA.cubo(bm, -0.98, 0.12, -0.035, 0.10, 2.06, 2.16, 1)                # cabezal
    CA.cubo(bm, -0.98, -0.86, -0.035, 0.10, -0.2, 2.16, 1)               # jamba de las bisagras
    CA.cubo(bm, 0.12, 0.2, -0.04, -0.02, -0.2, 2.24, 1)                  # moldura exterior
    CA.cubo(bm, -1.06, 0.2, -0.04, -0.02, 2.16, 2.24, 1)
    CA.cubo(bm, -2.4, 2.0, 1.5, 1.6, -0.2, 2.6, 0)                       # pared del cuarto de al lado
    CA.cubo(bm, -2.4, 2.0, -3.0, 1.6, -0.3, -0.2, 2)                     # piso
    marco = B.objeto("pared_y_marco", bm, [M["pared"], M["moldura"], M["piso"]])
    marco.color = (0.66, 0.61, 0.52, 1.0)
    bisagra = B.vacio("bisagra", (-0.86, 0.0, 0.0))
    bm = bmesh.new()
    CA.cubo(bm, 0.0, 0.855, 0.0, 0.044, -0.2, 2.05, 0)                    # la puerta (cara a −y en y = 0)
    for (x0, x1, z0, z1) in ((0.12, 0.735, 1.18, 1.95), (0.12, 0.735, 0.1, 1.05)):
        CA.cubo(bm, x0, x1, -0.004, 0.0, z0, z1, 0)
        CA.cubo(bm, x0 + 0.04, x1 - 0.04, -0.008, -0.004, z0 + 0.04, z1 - 0.04, 0)
    CA.tubo(bm, (0.79, -0.0, 1.0), (0.79, -0.06, 1.0), 0.026, 0.026, 1, 20)          # perilla
    CA.tubo(bm, (0.79, -0.06, 1.0), (0.79, -0.075, 1.0), 0.03, 0.028, 1, 20)
    B.objeto("puerta", bm, [M["puerta"], CA.mat_acero("laton", (0.55, 0.42, 0.22), 0.3)], padre=bisagra)
    # el contacto: interruptor en la moldura del marco, imán en la puerta, a la misma altura
    plastico = CA.mat_plastico("sensor", (0.78, 0.76, 0.62), 0.32)
    ranura = B.simple("ranura", (0.25, 0.24, 0.20), 0.6)
    interruptor, iman = CA.sensor_puerta(plastico, ranura)
    interruptor.location = (0.053, -0.035, 1.86)
    interruptor.rotation_euler = (math.radians(90), 0, 0)
    iman.parent = bisagra
    iman.location = (0.83, 0.0, 1.86)
    iman.rotation_euler = (math.radians(90), 0, 0)
    # luz: la de la cocina (cálida) y la de la cochera que entra cuando se abre
    k = B.luz("cocina", "AREA", (-1.4, -2.2, 2.3), 120.0, (1.0, 0.9, 0.78))
    k.data.size = 1.5
    k.rotation_euler = (Vector((0, 0, 1.6)) - Vector((-1.4, -2.2, 2.3))).to_track_quat("-Z", "Y").to_euler()
    cochera = B.luz("cochera", "AREA", (0.0, 1.2, 2.2), 16.0, (0.8, 0.86, 1.0))
    cochera.data.size = 1.0
    cochera.rotation_euler = (math.radians(-60), 0, 0)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        a = _suave((t - t_abre) / abre_seg) if t_abre >= 0 else 0.0
        B.clave(bisagra, "rotation_euler", (0, 0, math.radians(grados * a)), f)
    objetivo = Vector((0.03, -0.03, 1.86))
    cam, mira = B.camara((0.42, -0.62, 1.70), lente=50, fstop=3.2, distancia_foco=0.7)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        u = _suave(t / (cuadros / fps))
        p = Vector((0.42 - 0.06 * u, -0.62 + 0.08 * u, 1.70 + 0.03 * u))
        B.clave(cam, "location", tuple(p), f)
        B.clave(mira, "location", tuple(objetivo + Vector((-0.06 * u, 0, 0))), f)
        cam.data.dof.focus_distance = (objetivo - p).length
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
    return dict(exposicion=0.0, exposicion_eevee=0.0)


def _mat_buro(nombre="buro_nogal", tono=(0.15, 0.085, 0.045)):
    """Chapa de nogal de un buró, vista a 25 cm: vetas finas a lo largo, la figura de catedral de los
    anillos, poros abiertos y laca satinada. La escala va en milímetros, no en tablas de piso."""
    def hacer(a):
        p = B.pos_mundo(a)
        torcer, _ = a.ruido(p, 6.0, 3.0, 0.6)
        q = a.v("ADD", p, a.v("SCALE", (0.0, 0.012, 0.0), escala=torcer))
        vetas, _ = a.ruido(a.v("MULTIPLY", q, (4.0, 260.0, 4.0)), 1.0, 5.0, 0.62)
        anillos = a.nodo("ShaderNodeTexWave", wave_type="BANDS", bands_direction="Y")
        a.unir(a.v("MULTIPLY", q, (0.35, 1.0, 1.0)), anillos, "Vector")
        B.entrada(anillos, "Scale").default_value = 9.0
        B.entrada(anillos, "Distortion").default_value = 7.0
        B.entrada(anillos, "Detail").default_value = 3.0
        poros, _ = a.ruido(a.v("MULTIPLY", p, (60.0, 1800.0, 60.0)), 1.0, 2.0, 0.5)
        col = a.v("SCALE", tono, escala=a.rango(vetas, 0.3, 0.7, 0.72, 1.22))
        col = a.v("SCALE", col, escala=a.rango((anillos, "Fac"), 0.0, 1.0, 0.80, 1.12))
        col = a.v("SCALE", col, escala=a.rango(poros, 0.55, 0.75, 1.0, 0.7))
        rug = a.rango(vetas, 0.3, 0.7, 0.30, 0.40)
        normal = a.bump(a.rango(poros, 0.55, 0.75, 1.0, 0.0), 0.25, 0.0003)
        return a.bsdf(col, rug, normal=normal, especular=0.4)
    return B.material(nombre, hacer)


def e06_fitbit_mesa(escena, cuadros, fps):
    """6.4 — Un Fitbit One como el de Connie, sobre una mesa de nogal junto a su clip y a un llavero
    (es del mismo tamaño), con la luz gris de una ventana de costado, que deja ver la veta y no lava la
    madera con su reflejo. La cámara gira muy despacio alrededor."""
    _mundo_gris(escena, 0.3)
    madera = _mat_buro()
    bm = bmesh.new()
    CA.cubo(bm, -1.0, 1.0, -0.6, 0.6, -0.04, 0.0)
    B.objeto("mesa", bm, [madera])
    negro = B.material("fitbit_negro", lambda a: a.bsdf((0.008, 0.008, 0.009), 0.08, coat=1.0, especular=0.7))
    pantalla = B.material("fitbit_pantalla", lambda a: a.bsdf((0.003, 0.003, 0.004), 0.03, especular=0.8))
    goma = CA.mat_plastico("clip_goma", (0.03, 0.032, 0.035), 0.65)
    cuerpo, clip = CA.fitbit_one(negro, pantalla, goma)
    cuerpo.location = (0.0, 0.0, 0.0)
    cuerpo.rotation_euler = (0, 0, math.radians(-18))
    clip.location = (-0.012, 0.045, 0.0)
    clip.rotation_euler = (0, 0, math.radians(22))
    ctrl, argolla = CA.llavero(B.simple("control", (0.012, 0.012, 0.013), 0.4), CA.mat_acero("argolla", (0.6, 0.6, 0.6), 0.25))
    for o in (ctrl, argolla):
        o.location = (0.075, -0.02, 0.0)
        o.rotation_euler = (0, 0, math.radians(-35))
    taza = bmesh.new()
    CA.tubo(taza, (-0.46, 0.50, 0.0), (-0.46, 0.50, 0.095), 0.042, 0.045, 0, 32)
    B.objeto("taza", taza, [CA.mat_plastico("ceramica", (0.72, 0.70, 0.66), 0.2)])
    pv = Vector((-0.95, 0.10, 0.75))
    v = B.luz("ventana", "AREA", tuple(pv), 90.0, (0.86, 0.9, 1.0))
    v.data.size = 1.2
    v.rotation_euler = (Vector((0, 0, 0)) - pv).to_track_quat("-Z", "Y").to_euler()
    relleno = B.luz("relleno", "AREA", (0.6, -0.6, 0.5), 12.0, (1.0, 0.85, 0.7))
    relleno.data.size = 0.8
    relleno.rotation_euler = (Vector((0, 0, 0)) - Vector((0.6, -0.6, 0.5))).to_track_quat("-Z", "Y").to_euler()
    objetivo = Vector((0.0, 0.004, 0.006))
    cam, mira = B.camara((0.10, -0.26, 0.12), lente=85, fstop=3.5, distancia_foco=0.3)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        u = _suave(t / (cuadros / fps))
        ang = math.radians(-70 + 22 * u)
        r = 0.29 - 0.04 * u
        p = Vector((r * math.cos(ang), r * math.sin(ang), 0.12 - 0.02 * u))
        B.clave(cam, "location", tuple(p), f)
        B.clave(mira, "location", tuple(objetivo), f)
        cam.data.dof.focus_distance = (objetivo - p).length
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
    return dict(exposicion=0.0, exposicion_eevee=-0.5)


def e06_modem(escena, cuadros, fps):
    """6.0 — El módem de la casa sobre un mueble del estudio: sus luces verdes parpadean con el tráfico
    y por un solo cable entra internet para todos los aparatos. La cámara se acerca despacio."""
    import random
    _mundo_gris(escena, 0.22)
    M = CA.mats_interior()
    bm = bmesh.new()
    CA.cubo(bm, -1.5, 1.5, 0.30, 0.42, -0.9, 1.6, 0)                      # pared
    CA.cubo(bm, -0.9, 0.9, -0.15, 0.30, -0.04, 0.0, 1)                     # repisa de madera
    pared = B.objeto("pared_modem", bm, [M["pared"], CA.mat_madera_piso("repisa", (0.22, 0.12, 0.06))])
    pared.color = (0.60, 0.57, 0.50, 1.0)
    negro = B.material("modem_negro", lambda a: a.bsdf((0.012, 0.012, 0.014), 0.3, especular=0.5))
    bm = bmesh.new()
    CA.caja_redonda(bm, 0.0, 0.08, 0.0, 0.24, 0.17, 0.045, 0.02, 0)        # cuerpo, acostado
    for k in range(9):                                                     # rejilla de ventilación
        CA.cubo(bm, -0.09 + k * 0.022, -0.082 + k * 0.022, 0.03, 0.14, 0.0449, 0.0456, 1)
    B.objeto("modem", bm, [negro, B.simple("rejilla", (0.004, 0.004, 0.005), 0.6)])
    # antenas del router
    bm = bmesh.new()
    for x in (-0.09, 0.09):
        CA.tubo(bm, (x, 0.155, 0.03), (x * 1.15, 0.17, 0.2), 0.007, 0.006, 0, 12)
    B.objeto("antenas", bm, [negro])
    # cables: coaxial blanco y uno de red azul que salen por detrás hacia la pared
    bm = bmesh.new()
    for k, (x, col) in enumerate(((-0.06, 0), (0.05, 1))):
        pts = [Vector((x, 0.165, 0.02)), Vector((x, 0.22, 0.01)), Vector((x * 1.4, 0.27, -0.0)), Vector((x * 1.6, 0.29, -0.2))]
        for p0, p1 in zip(pts[:-1], pts[1:]):
            CA.tubo(bm, p0, p1, 0.0035, None, col, 8)
    B.objeto("cables", bm, [B.simple("coaxial", (0.7, 0.7, 0.68), 0.5), B.simple("cable_red", (0.05, 0.12, 0.35), 0.45)])
    # luces: encendido fijo; internet y wifi parpadean con el tráfico
    rng = random.Random(60)
    for k, (nombre, x, patron) in enumerate((("encendido", -0.07, "fijo"), ("internet", -0.035, "rapido"),
                                              ("wifi", 0.0, "rapido"), ("red", 0.035, "lento"))):
        bm = bmesh.new()
        CA.cubo(bm, x - 0.004, x + 0.004, -0.0055, -0.004, 0.022, 0.026)
        m = CA.mat_emision(f"led_{nombre}", (0.25, 1.0, 0.35), 0.0)
        B.objeto(f"led_{nombre}", bm, [m])
        valores, v = [], 1.0
        for f in range(1, cuadros + 2):
            if patron == "fijo":
                v = 1.0
            elif patron == "rapido":
                v = 1.0 if rng.random() < 0.55 else 0.08
            else:
                v = 1.0 if ((f // 9) % 3) else 0.1
            valores.append(6.0 * v)
        CA.animar_fuerza(m, valores, fps)
    v = B.luz("ventana", "AREA", (-1.4, -1.2, 1.2), 40.0, (0.86, 0.9, 1.0))
    v.data.size = 1.0
    v.rotation_euler = (Vector((0, 0.1, 0.0)) - Vector((-1.4, -1.2, 1.2))).to_track_quat("-Z", "Y").to_euler()
    objetivo = Vector((-0.02, 0.0, 0.03))
    cam, mira = B.camara((0.30, -0.42, 0.16), lente=55, fstop=2.4, distancia_foco=0.5)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        u = _suave(t / (cuadros / fps))
        p = Vector((0.30 - 0.12 * u, -0.42 + 0.10 * u, 0.16 - 0.02 * u))
        B.clave(cam, "location", tuple(p), f)
        B.clave(mira, "location", tuple(objetivo), f)
        cam.data.dof.focus_distance = (objetivo - p).length
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
    return dict(exposicion=0.0, exposicion_eevee=-0.2)
