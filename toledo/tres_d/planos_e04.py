"""Planos 3D de la escena 4 (Escaleras donde no hay escaleras). Los llama `tres_d/plano.py`.

Firma: plano(escena, cuadros, fps, **params) -> dict | None

El Dreisam es el mismo de la escena 1 (`tres_d/rio.py`, con sus taludes, ciclovías, árboles de
octubre y el puente), ahora de día: las farolas apagadas, un cielo de tarde con sol bajo o uno nublado.
"""

import math

import bpy
from mathutils import Vector

from tres_d import base as B
from tres_d import mocap as MC
from tres_d import persona as PE
from tres_d import rio as RI


def _suave(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# Cielos de día: (horizonte, 12 %, 35 %, cenit, fuerza)
CIELOS_DIA = {
    "tarde_clara": ((0.70, 0.79, 0.90), (0.45, 0.60, 0.84), (0.26, 0.42, 0.76), (0.12, 0.26, 0.62), 1.1),
    "nublado": ((0.72, 0.74, 0.77), (0.64, 0.66, 0.70), (0.56, 0.58, 0.63), (0.47, 0.50, 0.56), 1.3),
}


def _cielo_dia(escena, nombre: str):
    """Degradado de cielo de día (de `CIELOS_DIA`), que es fondo y luz ambiente a la vez."""
    horizonte, bajo, medio, cenit, fuerza = CIELOS_DIA[nombre]
    mundo, nt, salida = B.mundo_nuevo(escena, nombre)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(sep.outputs[2], rampa.inputs[0])
    els = rampa.color_ramp.elements
    els[0].position, els[0].color = 0.0, (*horizonte, 1)
    els[1].position, els[1].color = 1.0, (*cenit, 1)
    els.new(0.10).color = (*bajo, 1)
    els.new(0.35).color = (*medio, 1)
    fondo = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(rampa.outputs["Color"], fondo.inputs["Color"])
    fondo.inputs["Strength"].default_value = fuerza
    nt.links.new(fondo.outputs[0], salida.inputs["Surface"])
    return mundo


def _sol(altura: float, rumbo: float, fuerza: float, color=(1.0, 0.93, 0.82)):
    """Sol a `altura` grados sobre el horizonte, desde el rumbo `rumbo` (grados; 0 = +y, 90 = +x)."""
    ob = B.luz("sol", "SUN", (0.0, 0.0, 50.0), fuerza, color)
    B.poner(ob.data, "angle", math.radians(1.2))
    a, r = math.radians(altura), math.radians(rumbo)
    hacia_sol = Vector((math.sin(r) * math.cos(a), math.cos(r) * math.cos(a), math.sin(a)))
    ob.rotation_euler = (-hacia_sol).to_track_quat("-Z", "Y").to_euler()
    return ob


def _fachada_de_dia():
    """Fachadas lejanas de día: el mismo patrón de ventanas que `rio.mat_edificio_lejano`, pero con
    los vidrios oscuros que reflejan el cielo y sin ninguna encendida (de noche brillaban)."""
    def hacer(a):
        info = a.nodo("ShaderNodeObjectInfo")
        x, y, z = a.separar(B.pos_mundo(a))
        u = a.m("FRACT", a.m("MULTIPLY", a.m("ADD", x, y), 1 / 2.6))
        w = a.m("FRACT", a.m("MULTIPLY", z, 1 / 3.1))
        dentro = a.m("MULTIPLY", a.m("MULTIPLY", a.m("GREATER_THAN", u, 0.28), a.m("LESS_THAN", u, 0.72)),
                     a.m("MULTIPLY", a.m("GREATER_THAN", w, 0.28), a.m("LESS_THAN", w, 0.76)))
        fachada = a.v("SCALE", (info, "Color"), escala=0.55)
        color = a.mezcla(fachada, (0.02, 0.025, 0.03), dentro)
        return a.bsdf(color, a.rango(dentro, 0, 1, 0.85, 0.06), especular=0.5)
    return B.material("edificio_dia", hacer)


def _rio_de_dia(escena, cuadros, fps, cielo="tarde_clara"):
    _cielo_dia(escena, cielo)
    M = RI.materiales_rio(libre=True)
    M["lampara"] = B.simple("lampara_apagada", (0.4, 0.4, 0.38), 0.3)
    M["edificio"] = _fachada_de_dia()
    RI.armar_rio(M, energia_farola=0.0)
    RI.animar_agua(M["agua"], cuadros, fps, velocidad=0.6)
    # aire de lejos: las lomas y el puente se aclaran un poco con la distancia
    B.neblina((0, 130, 15), (120, 440, 30), 0.0010, (0.80, 0.85, 0.92), anisotropia=0.3, nombre="aire")
    return M


def e04_dreisam_dia(escena, cuadros, fps):
    """4.0 — De vuelta en Friburgo, de día: una tarde clara de otoño en la ciclovía del Dreisam, con el
    sol bajo entre los árboles; la cámara avanza despacio por el camino hacia el puente."""
    _rio_de_dia(escena, cuadros, fps, "tarde_clara")
    _sol(22.0, 300.0, 6.0)
    cam, mira = B.camara((16.3, -14.0, 1.65), lente=30, fstop=5.6, distancia_foco=30.0)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        u = _suave(t / (cuadros / fps))
        B.clave(cam, "location", (16.3 - 0.3 * u, -14.0 + 3.0 * u, 1.65 + 0.01 * math.sin(t * 1.2)), f)
        B.clave(mira, "location", (3.0 + 1.0 * u, 48.0, 0.6), f)
    return dict(exposicion=-0.6, exposicion_eevee=-1.0, volumen_fin=300.0)


def e04_orilla_pendiente(escena, cuadros, fps):
    """4.3 — La orilla donde «no hay escaleras»: el talud de pasto baja del camino hasta el agua, vacío,
    en un día nublado. Un acercamiento muy lento (la escena lo congela en la pausa)."""
    _rio_de_dia(escena, cuadros, fps, "nublado")
    _sol(30.0, 200.0, 0.8, (0.95, 0.96, 1.0))
    # a lo largo de la orilla, como en el amanecer de la escena 1: el talud se ve de perfil, del camino al agua
    cam, mira = B.camara((16.8, 3.0, 1.65), lente=32, fstop=6.3, distancia_foco=16.0)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        u = _suave(t / (cuadros / fps))
        B.clave(cam, "location", (16.8 - 0.3 * u, 3.0 + 1.8 * u, 1.65 + 0.006 * math.sin(t * 1.3)), f)
        B.clave(mira, "location", (10.8 + 0.4 * u, 21.0 + 0.8 * u, -1.5), f)
    return dict(exposicion=-0.4, exposicion_eevee=-0.9, volumen_fin=300.0)


def e04_policia_orilla(escena, cuadros, fps):
    """4.4 — Un investigador camina por la ciclovía de la misma orilla, de espaldas y a distancia
    media, con el teléfono en el bolsillo; la cámara lo sigue a unos ocho metros."""
    _rio_de_dia(escena, cuadros, fps, "nublado")
    _sol(30.0, 200.0, 0.8, (0.95, 0.96, 1.0))
    # con la persona, Eevee llenaba el depósito de sombras (unas 2 200 de 2 048) y avisaba que podían
    # faltar sombras: se le da el doble
    B.poner(escena.eevee, "shadow_pool_size", "1024")
    _, esqueleto = PE.crear_persona("investigador", edad=0.5, peso=0.55, musculo=0.55, estatura=0.55)
    direccion, recorrido = MC.aplicar(esqueleto, fps, cuadros)
    esqueleto.location = (16.1, 2.0, 0.0)
    esqueleto.rotation_euler = (0, 0, math.radians(90.0 - direccion))       # se aleja hacia +y
    bpy.context.view_layer.update()
    mundo = [esqueleto.matrix_world @ v for v in recorrido]
    y0, y1 = mundo[0].y, mundo[-1].y
    cam, mira = B.camara((17.2, y0 - 8.0, 1.6), lente=45, fstop=3.5, distancia_foco=8.0)
    for f in range(1, cuadros + 2):
        y = y0 + (y1 - y0) * (f - 1) / cuadros                     # la cámara avanza parejo, sin el vaivén
        B.clave(cam, "location", (17.3, y - 8.2, 1.6), f)
        B.clave(mira, "location", (15.6, y + 4.0, 0.9), f)
    return dict(exposicion=-0.4, exposicion_eevee=-0.9, volumen_fin=300.0)


# --------------------------------------------------------------------------- prueba de aspecto


def e04_muestras(escena, cuadros, fps):
    """Prueba de aspecto (no va al video): el río de día con los tres encuadres de la escena 4 en
    cuadros seguidos (1: tarde clara; 2 y 3: nublado, con el investigador caminando), con un solo
    Blender. Los dos cielos están en el mismo mundo y se cambian con un factor animado."""
    M = RI.materiales_rio(libre=True)
    M["lampara"] = B.simple("lampara_apagada", (0.4, 0.4, 0.38), 0.3)
    M["edificio"] = _fachada_de_dia()
    RI.armar_rio(M, energia_farola=0.0)
    RI.animar_agua(M["agua"], cuadros, fps, velocidad=0.6)
    B.neblina((0, 130, 15), (120, 440, 30), 0.0010, (0.80, 0.85, 0.92), anisotropia=0.3, nombre="aire")
    mundo, nt, salida = B.mundo_nuevo(escena, "dos_cielos")
    fondos = []
    for nombre in ("tarde_clara", "nublado"):
        horizonte, bajo, medio, cenit, fuerza = CIELOS_DIA[nombre]
        coord = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(coord.outputs["Generated"], sep.inputs[0])
        rampa = nt.nodes.new("ShaderNodeValToRGB")
        nt.links.new(sep.outputs[2], rampa.inputs[0])
        els = rampa.color_ramp.elements
        els[0].position, els[0].color = 0.0, (*horizonte, 1)
        els[1].position, els[1].color = 1.0, (*cenit, 1)
        els.new(0.10).color = (*bajo, 1)
        els.new(0.35).color = (*medio, 1)
        fondo = nt.nodes.new("ShaderNodeBackground")
        nt.links.new(rampa.outputs["Color"], fondo.inputs["Color"])
        fondo.inputs["Strength"].default_value = fuerza
        fondos.append(fondo)
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(fondos[0].outputs[0], mix.inputs[1])
    nt.links.new(fondos[1].outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], salida.inputs["Surface"])
    sol = _sol(22.0, 300.0, 6.0)
    _, esqueleto = PE.crear_persona("investigador", edad=0.5, peso=0.55, musculo=0.55, estatura=0.55)
    direccion, recorrido = MC.aplicar(esqueleto, fps, max(cuadros, 4))
    esqueleto.location = (16.1, 2.0, 0.0)
    esqueleto.rotation_euler = (0, 0, math.radians(90.0 - direccion))
    bpy.context.view_layer.update()
    y3 = (esqueleto.matrix_world @ recorrido[2]).y
    tomas = [((16.3, -14.0, 1.65), (3.0, 48.0, 0.6), 30.0, 0.0, 6.0, (22.0, 300.0)),
             ((16.8, 3.0, 1.65), (10.8, 21.0, -1.5), 32.0, 1.0, 0.8, (30.0, 200.0)),
             ((17.3, y3 - 8.2, 1.6), (15.6, y3 + 4.0, 0.9), 45.0, 1.0, 0.8, (30.0, 200.0))]
    cam, mira = B.camara((0.0, 0.0, 2.0), lente=30, fstop=5.6, distancia_foco=20.0)
    for f, (pos, m, lente, cielo, fuerza, (alt, rumbo)) in enumerate(tomas, start=1):
        B.clave(cam, "location", pos, f)
        B.clave(mira, "location", m, f)
        cam.data.lens = lente
        cam.data.keyframe_insert("lens", frame=f)
        cam.data.dof.focus_distance = math.dist(pos, m) * (0.5 if f == 3 else 1.0)
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
        mix.inputs[0].default_value = cielo
        mix.inputs[0].keyframe_insert("default_value", frame=f)
        sol.data.energy = fuerza
        sol.data.keyframe_insert("energy", frame=f)
        a, r = math.radians(alt), math.radians(rumbo)
        hacia = Vector((math.sin(r) * math.cos(a), math.cos(r) * math.cos(a), math.sin(a)))
        sol.rotation_euler = (-hacia).to_track_quat("-Z", "Y").to_euler()
        sol.keyframe_insert("rotation_euler", frame=f)
    return dict(exposicion=-0.6, exposicion_eevee=-1.0, volumen_fin=300.0, desenfoque_movimiento=False)
