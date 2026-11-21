"""Planos 3D de la escena 5 (caso Dabate: la casa de Ellington, Connecticut, 23 de diciembre de 2015).

Firma: plano(escena, cuadros, fps, **params) -> dict | None. Los arma `tres_d/plano.py`.
La casa y sus interiores están en `tres_d/casa_e05.py` (también los usa la escena 6).
Connie Dabate nunca aparece como personaje 3D y la violencia no se muestra: solo el lugar vacío.
"""

import math

import bmesh
import bpy
from mathutils import Vector

from tres_d import base as B
from tres_d import casa_e05 as CA
from tres_d import exterior_e05 as EX
from tres_d import mocap as MC
from tres_d import persona as PE


def _suave(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def _mundo_gris(escena, fuerza=0.35):
    """Interiores: el mundo casi no se ve; da una luz ambiente gris muy baja."""
    mundo, nt, salida = B.mundo_nuevo(escena, "interior")
    fondo = nt.nodes.new("ShaderNodeBackground")
    fondo.inputs["Color"].default_value = (0.55, 0.58, 0.62, 1)
    fondo.inputs["Strength"].default_value = fuerza
    nt.links.new(fondo.outputs[0], salida.inputs["Surface"])
    CA.sin_rayas(escena)


# --------------------------------------------------------------------------- exterior


def e05_casa_manana(escena, cuadros, fps, t_patrulla=-1.0):
    """5.0 — Ellington, 23 de diciembre de 2015, poco después de las diez: la casa colonial de los
    Dabate en una mañana gris y templada, sin nieve. Desde `t_patrulla` (s) entra por la derecha una
    patrulla con las luces encendidas, sube por la entrada de autos y se detiene frente a la cochera;
    la cámara la sigue con un paneo lento. Los destellos se ven en su carrocería, la cochera y la fachada."""
    CA.armar_exterior(escena)
    EX.farol()
    cam, mira = B.camara((-5.5, -31.5, 1.62), lente=30, fstop=5.6, distancia_foco=33.0)
    dur = cuadros / fps
    destino = Vector((9.0, 0.0, 2.4))                      # la casa a la izquierda, la cochera y la patrulla al centro
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        u = _suave(t / dur)
        B.clave(cam, "location", (-5.5 + 1.1 * u, -31.5 + 1.6 * u, 1.62 + 0.004 * math.sin(t * 1.1)), f)
        antes = Vector((2.6 - 0.6 * u, 4.0, 3.6 - 0.2 * u))
        w = _suave((t - (t_patrulla - 0.6)) / 2.9) if t_patrulla >= 0 else 0.0
        B.clave(mira, "location", tuple(antes.lerp(destino, w)), f)
    if t_patrulla >= 0:
        EX.patrulla_llega(cuadros, fps, t_alto=t_patrulla + 2.3, v0=8.0, frenado=11.0)
    return dict(exposicion=0.0, exposicion_eevee=0.15, volumen_fin=220.0)


def e05_casa_calle(escena, cuadros, fps):
    """5.1 — La versión de Richard: la misma casa, tranquila, vista desde el final de la entrada de
    autos, junto a la calle por la que dijo haberse ido al trabajo. La cámara se desliza despacio."""
    CA.armar_exterior(escena)
    EX.farol()
    cam, mira = B.camara((15.5, -27.5, 1.55), lente=35, fstop=5.6, distancia_foco=30.0)
    dur = cuadros / fps
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        u = _suave(t / dur)
        B.clave(cam, "location", (15.5 - 2.8 * u, -27.5 + 0.4 * u, 1.55), f)
        B.clave(mira, "location", (3.0 - 1.0 * u, 3.0, 3.0), f)
    return dict(exposicion=0.0, exposicion_eevee=0.15, volumen_fin=220.0)


# --------------------------------------------------------------------------- interiores


def e05_cocina_silla(escena, cuadros, fps):
    """5.0 — La cocina vacía: en el piso de duela, la silla plegable tumbada, los cinchos de plástico
    cortados y los marcadores amarillos de evidencia. La cámara, baja, se acerca despacio."""
    _mundo_gris(escena, 0.15)
    M = CA.cocina(escena)
    CA.escena_silla(M, (3.0, 2.0))
    cam, mira = B.camara((0.75, 0.25, 0.62), lente=30, fstop=2.8, distancia_foco=2.6)
    dur = cuadros / fps
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        u = _suave(t / dur)
        p = Vector((0.75 + 0.5 * u, 0.25 + 0.45 * u, 0.62 - 0.08 * u))
        B.clave(cam, "location", tuple(p), f)
        B.clave(mira, "location", (3.0, 2.15, 0.25), f)
        cam.data.dof.focus_distance = (Vector((3.0, 2.0, 0.22)) - p).length
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
    return dict(exposicion=0.0, exposicion_eevee=-0.15)


def mat_camuflaje():
    """Tela de camuflaje boscoso: manchas grandes de verde oliva, café y casi negro."""
    def hacer(a):
        p = B.pos_mundo(a)
        f1, _ = a.ruido(p, 4.0, 2.0, 0.5)
        f2, _ = a.ruido(a.v("ADD", p, (3.1, 1.7, 0.4)), 5.5, 2.0, 0.5)
        fino, _ = a.ruido(p, 300.0, 2.0, 0.7)
        col = a.mezcla((0.050, 0.055, 0.030), (0.065, 0.045, 0.025), a.m("GREATER_THAN", f1, 0.52))
        col = a.mezcla(col, (0.012, 0.013, 0.010), a.m("GREATER_THAN", f2, 0.58))
        return a.bsdf(col, 0.9, normal=a.bump(fino, 0.3, 0.002), especular=0.2)
    return B.material("camuflaje", hacer)


def e05_intruso(escena, cuadros, fps, inicio_y=9.7):
    """5.1 — El intruso de la historia de Richard: arriba, al fondo del pasillo, la silueta borrosa de
    un hombre grande con máscara y traje de camuflaje, a contraluz de la ventana, que avanza despacio.
    Nunca se le ve la cara: está desenfocado y la luz le llega por detrás."""
    _mundo_gris(escena, 0.12)
    CA.pasillo_arriba()
    cuerpo, esqueleto = PE.crear_persona("intruso", musculo=0.85, peso=0.72, estatura=0.82, edad=0.45,
                                         ropa=("male_worksuit01.mhclo", "shoes06.mhclo"), pelo="short02.mhclo")
    camo = mat_camuflaje()
    oscuro = B.simple("pasamontanas", (0.012, 0.012, 0.013), 0.85)
    for ob in [o for o in bpy.data.objects if o.type == "MESH" and (o == cuerpo or o.parent in (cuerpo, esqueleto))]:
        nuevo = camo if "worksuit" in ob.name.lower() else oscuro
        ob.data.materials.clear()
        ob.data.materials.append(nuevo)
    # a media velocidad: el recuerdo de Richard, lento y borroso
    direccion, recorrido = MC.aplicar(esqueleto, fps * 3, cuadros)
    esqueleto.location = (0.0, inicio_y, 0.0)
    esqueleto.rotation_euler = (0, 0, math.radians(-90.0 - direccion))
    cam, mira = B.camara((0.18, 0.55, 1.58), lente=35, fstop=1.8, distancia_foco=1.9)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        u = t / (cuadros / fps)
        B.clave(cam, "location", (0.18 - 0.05 * u, 0.4 - 2.9 * u, 1.58), f)
        B.clave(mira, "location", (0.0, 9.0, 1.35), f)
    return dict(exposicion=0.0, exposicion_eevee=0.4)


def e05_escalera_sotano(escena, cuadros, fps, t_soplete=-1.0, t_fin=-1.0):
    """5.2 — La escalera al sótano, desde arriba: escalones de madera que bajan a la penumbra del
    sótano. Desde `t_soplete`, abajo, a la vuelta, un resplandor azul y naranja que tiembla en las
    paredes (el soplete de la historia de Richard), y se apaga en `t_fin`. No se ve a nadie."""
    _mundo_gris(escena, 0.06)
    CA.escalera_sotano()
    zf = -13 * 0.19
    largo = 13 * 0.255
    # la luz del pasillo de arriba, detrás de la cámara
    arriba = B.luz("luz_pasillo", "AREA", (0.0, -1.6, 2.4), 24.0, (1.0, 0.84, 0.64))
    arriba.data.size = 1.2
    arriba.rotation_euler = (math.radians(35), 0, 0)
    # un poco de luz fría que baja del sótano (una ventanita de ras de suelo, fuera de cuadro)
    sotano = B.luz("ventanita", "AREA", (-3.4, largo + 1.2, zf + 2.0), 6.0, (0.75, 0.82, 1.0))
    sotano.data.size = 0.6
    sotano.rotation_euler = (Vector((-1.0, largo + 0.6, zf)) - Vector((-3.4, largo + 1.2, zf + 2.0))).to_track_quat("-Z", "Y").to_euler()
    llama = B.luz("soplete", "POINT", (-1.8, largo + 0.8, zf + 0.85), 0.0, (0.30, 0.48, 1.0), radio=0.04)
    brasa = B.luz("soplete_calido", "POINT", (-1.6, largo + 0.65, zf + 0.7), 0.0, (1.0, 0.42, 0.10), radio=0.08)
    B.neblina((-1.0, largo + 0.6, zf + 1.1), (5.0, 2.4, 2.2), 0.035, (0.8, 0.82, 0.86), anisotropia=0.3, nombre="polvo")
    import random
    rng = random.Random(52)
    temblor = 1.0
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        if t_soplete >= 0 and t >= t_soplete:
            sube = min(1.0, (t - t_soplete) / 0.35)
            baja = 1.0 if t_fin < 0 else max(0.0, 1.0 - (t - t_fin) / 1.2)
            temblor = 0.6 * temblor + 0.4 * rng.uniform(0.55, 1.25)
            e = sube * baja * temblor
        else:
            e = 0.0
        B.clave(llama.data, "energy", 48.0 * e, f)
        B.clave(brasa.data, "energy", 14.0 * e * rng.uniform(0.7, 1.15), f)
    cam, mira = B.camara((0.08, -0.85, 1.52), lente=24, fstop=4.0, distancia_foco=3.6)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        u = _suave(t / (cuadros / fps))
        B.clave(cam, "location", (0.08 - 0.04 * u, -0.85 + 0.35 * u, 1.52 - 0.04 * u), f)
        B.clave(mira, "location", (-0.15 - 0.15 * u, largo + 0.6, zf + 0.4), f)
    return dict(exposicion=0.0, exposicion_eevee=0.2, volumen_fin=30.0)


# --------------------------------------------------------------------------- el seguro y la alarma


def mat_papel():
    def hacer(a):
        p = B.pos_mundo(a)
        fibra, _ = a.ruido(p, 600.0, 2.0, 0.7)
        m, _ = a.ruido(p, 20.0, 3.0, 0.6)
        col = a.v("SCALE", (0.80, 0.79, 0.75), escala=a.rango(m, 0.3, 0.7, 0.95, 1.02))
        return a.bsdf(col, 0.85, normal=a.bump(fibra, 0.15, 0.0004), especular=0.25)
    return B.material("papel", hacer)


def e05_documento(escena, cuadros, fps):
    """5.3 — La solicitud de pago del seguro de vida, cinco días después: el formulario sobre un
    escritorio, una pluma encima, y la cifra de 475,000 dólares a la que llega la cámara."""
    _mundo_gris(escena, 0.3)
    madera = CA.mat_madera_piso("escritorio", (0.16, 0.085, 0.04))
    tinta = B.material("tinta", lambda a: a.bsdf((0.006, 0.006, 0.01), 0.92, especular=0.08))       # tinta mate: sin reflejo
    gris = B.material("tinta_gris", lambda a: a.bsdf((0.11, 0.11, 0.12), 0.92, especular=0.08))
    azul = B.simple("tinta_azul", (0.02, 0.05, 0.16), 0.5)
    bm = bmesh.new()
    CA.cubo(bm, -1.2, 1.2, -0.8, 0.8, -0.04, 0.0)
    B.objeto("escritorio", bm, [madera])
    hoja = bpy.data.objects.new("hoja", None)
    B.enlazar(hoja)
    hoja.rotation_euler = (0, 0, math.radians(-7))
    bm = bmesh.new()
    CA.cubo(bm, -0.108, 0.108, -0.1395, 0.1395, 0.0, 0.0003)
    B.objeto("papel", bm, [mat_papel()]).parent = hoja
    bm = bmesh.new()
    CA.cubo(bm, -0.104, 0.102, -0.143, 0.136, -0.0002, 0.0001)        # una segunda hoja debajo, chueca
    otra = B.objeto("papel2", bm, [mat_papel()])
    otra.rotation_euler = (0, 0, math.radians(3))
    z = 0.00035

    def t3(nombre, cadena, x, y, tam, mat, fuente="Inter-Regular.ttf"):
        return CA.texto3d(nombre, cadena, tam, mat, fuente, padre=hoja, pos=(x, y, z))
    t3("titulo", "SEGURO DE VIDA", -0.088, 0.112, 0.0085, tinta, "Inter-SemiBold.ttf")
    t3("sub", "Solicitud de pago al beneficiario", -0.088, 0.100, 0.0052, gris)
    # solo lo que dice la narración: quién es la asegurada, quién cobra y la cifra; los demás
    # renglones del formulario son líneas grises, sin fechas ni datos que el guion no da
    filas = [("Asegurada", "Connie Dabate", 0.074), ("Beneficiario", "Richard Dabate", 0.058)]
    for k, (et, val, y) in enumerate(filas):
        t3(f"et{k}", et, -0.088, y, 0.0045, gris)
        t3(f"val{k}", val, -0.020, y, 0.0058, tinta)
    bm = bmesh.new()
    for y in (0.069, 0.053, 0.037, 0.021):
        CA.cubo(bm, -0.022, 0.088, y, y + 0.0004, 0.0, z)
    for y in (0.042, 0.026):                                            # renglones sin datos legibles
        CA.cubo(bm, -0.088, -0.036, y, y + 0.0018, 0.0, z)
        CA.cubo(bm, -0.020, 0.030, y, y + 0.0024, 0.0, z)
    CA.cubo(bm, -0.09, 0.09, 0.091, 0.0918, 0.0, z)
    for k in range(9):                                                 # letra chica (renglones grises)
        y = -0.062 - k * 0.0072
        CA.cubo(bm, -0.088, -0.088 + (0.17 if k % 4 != 3 else 0.09), y, y + 0.0022, 0.0, z)
    B.objeto("renglones", bm, [gris]).parent = hoja
    t3("monto_et", "Suma asegurada", -0.088, -0.006, 0.0050, gris)
    bm = bmesh.new()
    CA.cubo(bm, -0.09, 0.09, -0.044, -0.014, 0.0, z * 0.6)
    CA.cubo(bm, -0.09, 0.09, -0.0445, -0.0442, 0.0, z)
    CA.cubo(bm, -0.09, 0.09, -0.0138, -0.0135, 0.0, z)
    B.objeto("recuadro", bm, [B.simple("recuadro", (0.70, 0.70, 0.67), 0.8)]).parent = hoja
    t3("monto", "$475,000", -0.084, -0.036, 0.0165, tinta, "Inter-SemiBold.ttf")
    t3("moneda", "USD", 0.042, -0.036, 0.0065, gris)
    # firma a mano (una línea curva de tinta azul) y la pluma
    bm = bmesh.new()
    pts = [Vector((0.02 + 0.06 * i / 30, -0.12 + 0.006 * math.sin(i * 0.9) + 0.002 * math.sin(i * 2.7), z)) for i in range(31)]
    for p0, p1 in zip(pts[:-1], pts[1:]):
        CA.tubo(bm, p0, p1, 0.0004, None, 0, 4)
    B.objeto("firma", bm, [azul]).parent = hoja
    bm = bmesh.new()
    CA.tubo(bm, (0.0, 0.0, 0.0), (0.135, 0.0, 0.0), 0.0045, 0.0045, 0, 16)
    CA.tubo(bm, (0.135, 0.0, 0.0), (0.150, 0.0, 0.0), 0.0045, 0.0012, 1, 16)
    CA.tubo(bm, (-0.003, 0.0, 0.0), (0.0, 0.0, 0.0), 0.004, 0.0045, 1, 16)
    pluma = B.objeto("pluma", bm, [B.simple("pluma", (0.01, 0.01, 0.012), 0.25), CA.mat_acero("punta", (0.7, 0.7, 0.68), 0.25)])
    pluma.location = (0.035, -0.095, 0.0049)
    pluma.rotation_euler = (0, 0, math.radians(32))
    # luz de ventana de un lado y una lámpara cálida del otro
    v = B.luz("ventana", "AREA", (-0.9, 0.5, 0.9), 45.0, (0.86, 0.9, 1.0))
    v.data.size = 1.0
    v.rotation_euler = (Vector((0, 0, 0)) - Vector((-0.9, 0.5, 0.9))).to_track_quat("-Z", "Y").to_euler()
    lamp = B.luz("lampara", "SPOT", (0.45, 0.35, 0.55), 6.0, (1.0, 0.78, 0.55), radio=0.05, cono=math.radians(70))
    lamp.rotation_euler = (Vector((0.0, -0.03, 0)) - Vector((0.45, 0.35, 0.55))).to_track_quat("-Z", "Y").to_euler()
    objetivo = Vector((-0.045, -0.034, 0.0))
    cam, mira = B.camara((0.16, -0.30, 0.20), lente=60, fstop=2.8, distancia_foco=0.4)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        u = _suave(t / (cuadros / fps))
        p = Vector((0.16 - 0.10 * u, -0.30 + 0.07 * u, 0.20 - 0.03 * u))
        B.clave(cam, "location", tuple(p), f)
        B.clave(mira, "location", tuple(objetivo + Vector((0.0, 0.02 * (1 - u), 0))), f)
        cam.data.dof.focus_distance = (objetivo - p).length
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
    return dict(exposicion=0.0, exposicion_eevee=-0.55)


def e05_teclado_alarma(escena, cuadros, fps, parpadeo=0.9):
    """5.3 — «Y la casa lo había registrado»: el teclado de la alarma junto a la puerta de la cochera,
    con su pantalla verde encendida y la luz que parpadea. La cámara se acerca muy despacio."""
    _mundo_gris(escena, 0.3)
    M = CA.mats_interior()
    bm = bmesh.new()
    CA.cubo(bm, -1.5, 1.5, 0.0, 0.1, -0.2, 2.6, 0)
    CA.cubo(bm, 0.30, 0.42, -0.02, 0.0, -0.2, 2.2, 1)                     # marco de la puerta
    CA.cubo(bm, 0.42, 1.4, -0.04, 0.02, -0.2, 2.1, 2)                     # la puerta, cerrada
    pared = B.objeto("pared", bm, [M["pared"], M["moldura"], M["puerta"]])
    pared.color = (0.66, 0.60, 0.50, 1.0)
    cuerpo = CA.mat_plastico("teclado", (0.70, 0.68, 0.62), 0.35)
    teclas = CA.mat_plastico("teclas", (0.62, 0.60, 0.55), 0.45)
    lcd = CA.mat_emision("lcd", (0.22, 0.55, 0.16), 0.55)
    letras = B.simple("letras_lcd", (0.01, 0.03, 0.01), 0.5)
    etiqueta = B.simple("etiqueta", (0.15, 0.15, 0.15), 0.6)
    raiz = B.vacio("teclado")
    raiz.location = (0.0, -0.001, 1.42)
    raiz.rotation_euler = (math.radians(90), 0, 0)                          # su frente mira hacia −y
    bm = bmesh.new()
    CA.caja_redonda(bm, 0.0, 0.0, 0.0, 0.150, 0.118, 0.024, 0.012, 0)
    B.objeto("caja_teclado", bm, [cuerpo], padre=raiz)
    bm = bmesh.new()
    CA.cubo(bm, -0.052, 0.052, 0.020, 0.044, 0.024, 0.0245)
    B.objeto("lcd", bm, [lcd], padre=raiz)
    CA.texto3d("lcd1", "DESARMADO", 0.0058, letras, "Inter-SemiBold.ttf", "CENTER", raiz, (0.0, 0.034, 0.0247))
    CA.texto3d("lcd2", "LISTO PARA ARMAR", 0.0048, letras, "Inter-Regular.ttf", "CENTER", raiz, (0.0, 0.025, 0.0247))
    bm = bmesh.new()
    for fila in range(4):
        for col in range(3):
            x, y = -0.028 + col * 0.028, 0.004 - fila * 0.016
            CA.caja_redonda(bm, x, y, 0.024, 0.022, 0.011, 0.004, 0.003, 0)
    B.objeto("teclas", bm, [teclas], padre=raiz)
    for k, ch in enumerate("123456789*0#"):
        x, y = -0.028 + (k % 3) * 0.028, 0.004 - (k // 3) * 0.016
        CA.texto3d(f"tecla{k}", ch, 0.0065, etiqueta, "Inter-SemiBold.ttf", "CENTER", raiz, (x, y - 0.0025, 0.0282))
    for k, (nombre, x, color) in enumerate((("listo", 0.058, (0.2, 1.0, 0.25)), ("armado", 0.058, (1.0, 0.08, 0.05)))):
        bm = bmesh.new()
        CA.tubo(bm, (x, 0.040 - k * 0.012, 0.024), (x, 0.040 - k * 0.012, 0.0265), 0.0022, 0.002, 0, 12)
        m = CA.mat_emision(f"led_{nombre}", color, 0.0)
        B.objeto(f"led_{nombre}", bm, [m], padre=raiz)
        valores = []
        for f in range(1, cuadros + 2):
            t = (f - 1) / fps
            if nombre == "listo":
                valores.append(9.0)
            else:                                                            # la memoria de eventos parpadea
                valores.append(14.0 if (t % (2 * parpadeo)) < parpadeo * 0.5 else 0.15)
        CA.animar_fuerza(m, valores, fps)
    v = B.luz("ventana", "AREA", (-1.6, -1.4, 1.9), 60.0, (0.85, 0.9, 1.0))
    v.data.size = 1.2
    v.rotation_euler = (Vector((0, 0, 1.4)) - Vector((-1.6, -1.4, 1.9))).to_track_quat("-Z", "Y").to_euler()
    objetivo = Vector((0.0, -0.025, 1.43))
    cam, mira = B.camara((-0.25, -0.62, 1.47), lente=50, fstop=2.2, distancia_foco=0.6)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        u = _suave(t / (cuadros / fps))
        p = Vector((-0.25 + 0.08 * u, -0.62 + 0.16 * u, 1.47))
        B.clave(cam, "location", tuple(p), f)
        B.clave(mira, "location", tuple(objetivo), f)
        cam.data.dof.focus_distance = (objetivo - p).length
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
    return dict(exposicion=0.0, exposicion_eevee=0.0)
