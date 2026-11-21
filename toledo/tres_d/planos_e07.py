"""Planos 3D de la escena 7 — Cuando el aparato no quiere hablar.

Laboratorio forense (7.0 a 7.4): la mesa de evidencias con aparatos IoT, la placa de circuito con sus
puntos de prueba JTAG, la soldadura de los cables finos, el chip-off con aire caliente y el chip en
el programador. Bentonville (7.6 a 7.8): la bocina Echo en la barra de la cocina de noche y el patio
vacío con la tina de hidromasaje.

Firma: plano(escena, cuadros, fps, **params) -> dict | None (ajustes de render).
Las cámaras salen de `tres_d/datos_e07.py`, que también usan los rótulos 2D de la escena.
"""

import math

from mathutils import Vector

from tres_d import base as B
from tres_d import bates_e07 as BA
from tres_d import datos_e07 as DT
from tres_d import laboratorio_e07 as LB


# --------------------------------------------------------------------------- piezas comunes

def _camara_animada(recorrido, cuadros, fps, fstop, foco=None, clip=0.002):
    """Cámara que sigue `recorrido(t) -> (pos, mira, lente)` cuadro por cuadro; el foco cae en la
    mira (o en `foco(t)`)."""
    pos, mira, lente = recorrido(0.0)
    cam, vacio = B.camara(pos, lente=lente, fstop=fstop, distancia_foco=0.3)
    cam.data.clip_start, cam.data.clip_end = clip, 60.0
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        pos, mira, lente = recorrido(t)
        B.clave(cam, "location", pos, f)
        B.clave(vacio, "location", mira, f)
        cam.data.lens = lente
        cam.data.keyframe_insert("lens", frame=f)
        objetivo = foco(t) if foco else mira
        cam.data.dof.focus_distance = math.dist(pos, objetivo)
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
    return cam


def _laboratorio(escena, M, energia_aro=0.9, lateral=0.25, centro_luz=(0.0, 0.0)):
    LB.mundo_oscuro(escena)
    LB.panel_reflejo()
    LB.mesa(M)
    LB.fondo_laboratorio(M)
    LB.lampara_anillo(centro_luz, energia=energia_aro)
    LB.luz_lateral((-0.45, -0.25, 0.16), (0.0, 0.0, 0.0), energia=lateral)
    LB.luz_lateral((0.5, 0.45, 0.25), (0.0, 0.0, 0.0), energia=lateral * 0.6, color=(0.65, 0.8, 1.0))


def _emisor(mat, valores, cuadros, fps):
    """Anima la fuerza de emisión de un material simple con `valores(t)`."""
    nodo = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    sock = nodo.inputs["Emission Strength"]
    for f in range(1, cuadros + 2):
        sock.default_value = valores((f - 1) / fps)
        sock.keyframe_insert("default_value", frame=f)


def _ajustes_lab(exposicion=0.0):
    return dict(exposicion=exposicion, exposicion_eevee=exposicion, volumen_fin=5.0, desenfoque_movimiento=False)


# --------------------------------------------------------------------------- 7.0

def e07_mesa(escena, cuadros, fps, marcas=None):
    """7.0 — La mesa de evidencias del laboratorio: dos teléfonos y, a su lado, aparatos IoT que no se
    parecen en nada (una cámara barata, un reloj, una bocina, un termostato, un sensor industrial),
    cada uno con su tarjetita de evidencia, bajo la lámpara de aro."""
    marcas = marcas or {"telefonos": 3.0, "iot": 11.0, "fin": cuadros / fps}
    M = LB.materiales()
    LB.mundo_oscuro(escena)
    LB.panel_reflejo(alto=1.2, lado=2.0)
    LB.panel_reflejo(alto=0.75, lado=2.6, fuerza=0.35, y=1.5)            # lo reflejan las pantallas de los teléfonos
    LB.mesa(M)
    LB.fondo_laboratorio(M, y=0.62)
    LB.mesa_aparatos(M)
    LB.lampara_anillo((0.0, 0.02), alto=0.75, energia=7.0, visible=False)
    LB.luz_lateral((-0.9, -0.4, 0.35), (0.0, 0.0, 0.0), energia=1.6, tam=0.6)
    LB.luz_lateral((0.9, 0.6, 0.45), (0.0, 0.0, 0.0), energia=0.8, color=(0.6, 0.78, 1.0), tam=0.6)
    _camara_animada(lambda t: DT.cam_mesa(t, marcas), cuadros, fps, fstop=2.8)
    return _ajustes_lab(0.3)


# --------------------------------------------------------------------------- 7.2

def e07_placa(escena, cuadros, fps, marcas=None):
    """7.2 — La placa de un aparato IoT bajo la lámpara: la cámara pasa sobre sus chips y llega a la
    esquina donde están los cinco puntos de prueba JTAG, que se encienden uno tras otro."""
    marcas = marcas or {"puertos": 8.0}
    M = LB.materiales()
    _laboratorio(escena, M)
    mats = [B.simple(f"tp_luz{k}", (1.0, 0.74, 0.36), 0.18, metal=1.0, emision=(0.25, 1.0, 0.45), fuerza=0.0) for k in range(5)]
    piezas = LB.placa(M)
    for k, (tp, mat) in enumerate(zip(piezas["jtag"], mats)):
        tp.data.materials[0] = mat
        t0 = marcas["puertos"] + 0.35 * k
        _emisor(mat, lambda t, t0=t0: 0.9 * DT.suave((t - t0) / 0.5) * (0.85 + 0.15 * math.sin(3.0 * t + k)), cuadros, fps)
        x, y = DT.JTAG[k]
        luz = B.luz(f"brillo_tp{k}", "POINT", DT.en_placa(x, y, DT.GROSOR + 1.2), 0.0, (0.3, 1.0, 0.5), radio=0.0006)
        for f in range(1, cuadros + 2):
            t = (f - 1) / fps
            luz.data.energy = 0.003 * DT.suave((t - t0) / 0.5)
            luz.data.keyframe_insert("energy", frame=f)
    _camara_animada(lambda t: DT.cam_placa(t, cuadros / fps, marcas), cuadros, fps, fstop=3.2)
    return _ajustes_lab(0.0)


# --------------------------------------------------------------------------- 7.3

def e07_soldar(escena, cuadros, fps, t_toque=4.0):
    """7.3 — Los puntos de prueba de cerca: cuatro ya tienen su cable de cobre esmaltado soldado; el
    cautín baja al cuarto, la soldadura se funde y el cautín se retira. Los cables van a la interfaz
    JTAG."""
    M = LB.materiales()
    M["cable_esmalte"] = LB.mat_metal_rugoso("esmalte", (0.85, 0.42, 0.18), 0.12, escala=300.0, bump=0.02)
    _laboratorio(escena, M, energia_aro=0.8, lateral=0.3, centro_luz=(-0.03, 0.02))
    LB.placa(M)
    LB.cables_jtag(M, (0.0, 0.0, 0.0), destino=(-0.040, 0.080, 0.016))
    LB.interfaz_jtag(M, (-0.040, 0.085, 0.0))
    for k, (x, y) in enumerate(DT.JTAG):
        gota = LB.soldadura(f"gota{k}", DT.en_placa(x, y, DT.GROSOR + 0.08), 0.62 * DT.MM, M["estano"])
        if k == 3:                                   # esta se funde en el plano
            for f in range(1, cuadros + 2):
                t = (f - 1) / fps
                s = 0.15 + 0.85 * DT.suave((t - t_toque - 0.2) / 0.9)
                gota.scale = (s, s, s)
                gota.keyframe_insert("scale", frame=f)
    x, y = DT.JTAG[3]
    punta = Vector(DT.en_placa(x, y, DT.GROSOR + 0.35))
    raiz = LB.cautin(M, tuple(punta), inclinacion=40.0, rumbo=-35.0)
    lejos = punta + Vector((0.030, -0.022, 0.030))
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        baja = DT.suave((t - (t_toque - 1.4)) / 1.2)
        sube = DT.suave((t - (t_toque + 1.7)) / 1.3)
        u = baja * (1 - sube)
        B.clave(raiz, "location", tuple(lejos + (punta - lejos) * u), f)
    _camara_animada(lambda t: DT.cam_soldar(t, cuadros / fps), cuadros, fps, fstop=4.0)
    return _ajustes_lab(0.1)


# --------------------------------------------------------------------------- 7.4

def e07_aire(escena, cuadros, fps, t_pinzas=3.5, t_levanta=5.2):
    """7.4 — Chip-off: la boquilla de aire caliente cubre la memoria; la soldadura se funde, la
    boquilla se aparta y las pinzas levantan el chip, con sus esferas de soldadura debajo."""
    M = LB.materiales()
    _laboratorio(escena, M, energia_aro=0.9, lateral=0.3, centro_luz=(0.02, 0.01))
    piezas = LB.placa(M)
    chip = piezas["U2"]
    u2 = Vector(DT.en_placa(DT.CHIPS["U2"][0], DT.CHIPS["U2"][1], DT.GROSOR))
    boquilla = LB.boquilla_aire(M, tuple(u2), alto=0.0022)
    pinzas = LB.pinzas(M, tuple(u2 + Vector((0, 0, 0.0008))))
    base_chip = Vector(chip.location)
    pinza_lejos = Vector((0.025, 0.05, 0.05))
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        aparta = DT.suave((t - (t_pinzas - 0.6)) / 0.7)            # la boquilla calienta hasta que llegan las pinzas
        B.clave(boquilla, "location", tuple(u2 + Vector((-0.012, 0.03, 0.035)) * aparta), f)
        llega = DT.suave((t - (t_pinzas - 0.2)) / 0.9)
        sube = DT.suave((t - t_levanta) / 1.2)
        pz = u2 + Vector((0, 0, 0.0008)) + pinza_lejos * (1 - llega) + Vector((-0.004, 0.006, 0.012)) * sube
        B.clave(pinzas, "location", tuple(pz), f)
        B.clave(chip, "location", tuple(base_chip + Vector((-0.004, 0.006, 0.012)) * sube), f)
    _camara_animada(lambda t: DT.cam_aire(t, cuadros / fps), cuadros, fps, fstop=4.0)
    return _ajustes_lab(0.0)


def e07_lector(escena, cuadros, fps, t_lee=1.2):
    """7.4 — El chip en el adaptador del programador: la tapa abierta, el LED que parpadea mientras
    lee; al lado, la placa con el hueco donde estaba la memoria."""
    M = LB.materiales()
    _laboratorio(escena, M, energia_aro=0.9, lateral=0.3)
    _, led = LB.programador(M)
    LB._chip(M, "U2b", 0.0, 0.0, 11.5, 13.0, 1.0, DT.CHIPS["U2"][5], B.vacio("zocalo_chip", (0.0, 0.0, 0.0330 - 0.0016)),
             bolas=True)
    placa = LB.placa(M, centro=(-0.10, 0.075, 0.0), sin_chip_u2=True)
    placa["raiz"].rotation_euler = (0, 0, math.radians(-14))
    _emisor(led, lambda t: 9.0 * (t > t_lee) * (0.5 + 0.5 * math.copysign(1.0, math.sin(t * 2 * math.pi * 3.2))), cuadros, fps)
    _camara_animada(lambda t: DT.cam_lector(t, cuadros / fps), cuadros, fps, fstop=3.5)
    return _ajustes_lab(0.0)


# --------------------------------------------------------------------------- 7.6 y 7.7

# Cada toma tiene su propio nombre de plano: `Plano3D.asegurar` borra las carpetas de otras versiones
# del mismo nombre, así que dos tomas con el mismo nombre (y distintos parámetros) se borrarían
# entre sí durante el render.

def e07_echo_repisa(escena, cuadros, fps):
    """7.6 — La bocina Echo de los Bates en la barra de la cocina, de noche, apagada: la cámara se
    acerca despacio desde lejos."""
    return _echo(escena, cuadros, fps, "repisa", None)


def e07_echo_anillo(escena, cuadros, fps, encendido=1.5):
    """7.7 — La bocina de cerca: en `encendido` (s) el anillo de luz azul se prende como cuando oye
    «Alexa»."""
    return _echo(escena, cuadros, fps, "anillo", encendido)


def _echo(escena, cuadros, fps, toma, encendido):
    """La barra de la cocina de noche con la bocina; `encendido` (s) prende el anillo."""
    BA.cocina_noche()
    raiz, anillo = BA.echo()
    raiz.rotation_euler = (0, 0, math.radians(-30))
    BA.animar_anillo(anillo, cuadros, fps, encendido, giro=math.radians(-60))
    mundo, nt, salida = B.mundo_nuevo(escena, "noche_cocina")
    fondo = nt.nodes.new("ShaderNodeBackground")
    fondo.inputs["Color"].default_value = (0.004, 0.005, 0.009, 1)
    nt.links.new(fondo.outputs[0], salida.inputs["Surface"])
    luz = B.luz("luz_anillo", "POINT", (DT.ECHO[0], DT.ECHO[1], DT.ECHO[2] + 0.235), 0.0, (0.15, 0.55, 1.0), radio=0.04)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        luz.data.energy = 0.0 if encendido is None else 2.5 * DT.suave((t - encendido) / 0.35)
        luz.data.keyframe_insert("energy", frame=f)
    _camara_animada(lambda t: DT.cam_echo(t, cuadros / fps, toma), cuadros, fps,
                    fstop=2.0 if toma == "anillo" else 2.8,
                    foco=lambda t: (DT.ECHO[0], DT.ECHO[1], DT.ECHO[2] + 0.15), clip=0.01)
    return dict(exposicion=0.0, exposicion_eevee=0.4, volumen_fin=10.0)


# --------------------------------------------------------------------------- 7.6 y 7.8

def e07_patio_llegada(escena, cuadros, fps):
    """7.6 — Bentonville, noviembre de 2015: el patio trasero de la casa de Bates de noche, vacío,
    visto desde el pasto; la tina encendida, su vapor, la luz del porche."""
    return _patio(escena, cuadros, fps, "llegada")


def e07_patio_tina(escena, cuadros, fps):
    """7.6 — La tina vacía de cerca, con el agua iluminada y el vapor en el frío."""
    return _patio(escena, cuadros, fps, "tina")


def e07_patio_piso(escena, cuadros, fps):
    """7.8 — A ras del piso del patio: la tina a un lado y, contra la pared, la llave y la manguera."""
    return _patio(escena, cuadros, fps, "piso")


def _patio(escena, cuadros, fps, toma):
    """El patio trasero de la casa de Bates de noche, vacío: la tina encendida con su vapor en el
    frío de noviembre, las sillas vacías, la luz del porche."""
    agua, vapor = BA.patio(escena)
    BA.animar_tina(agua, vapor, cuadros, fps)
    _camara_animada(lambda t: DT.cam_patio(t, cuadros / fps, toma), cuadros, fps, fstop=2.8,
                    foco=lambda t: (DT.JACUZZI[0], DT.JACUZZI[1], 0.8), clip=0.05)
    return dict(exposicion=0.0, exposicion_eevee=0.0, volumen_fin=40.0)
