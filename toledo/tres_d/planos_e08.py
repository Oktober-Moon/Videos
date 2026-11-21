"""Planos 3D de la escena 8 — Las 10:05 (cierre).

- El Dreisam al atardecer: el mismo río de la escena 1 (taludes, ciclovía, árboles de octubre,
  puente), ahora con el cielo encendido detrás del puente y las farolas que apenas se prenden.
- La cocina vacía de los Dabate en Ellington, Connecticut (la de la escena 5), la mañana del 23 de
  diciembre de 2015, con la luz gris de la ventana.

Firma: plano(escena, cuadros, fps, **params) -> dict | None.
"""

import math

import bpy

from tres_d import base as B
from tres_d import casa_e05 as CA5
from tres_d import cierre_e08 as CI
from tres_d import rio as RI


def _camara(recorrido, cuadros, fps, fstop, foco_m, clip=0.05):
    pos, mira, lente = recorrido(0.0)
    cam, vacio = B.camara(pos, lente=lente, fstop=fstop, distancia_foco=foco_m)
    cam.data.clip_start = clip
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        pos, mira, lente = recorrido(t)
        B.clave(cam, "location", pos, f)
        B.clave(vacio, "location", mira, f)
        cam.data.lens = lente
        cam.data.keyframe_insert("lens", frame=f)
    return cam


def _suave(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def e08_dreisam_atardecer(escena, cuadros, fps):
    """8.0 — El Dreisam al atardecer, desde la ciclovía: el río quieto refleja el cielo naranja que
    queda detrás del puente; las farolas apenas se encienden. Nadie en el camino."""
    CI.cielo_atardecer(escena, fuerza=1.0)
    M = RI.materiales_rio(libre=True)
    M["lampara"] = B.simple("lampara_tenue", (1, 0.8, 0.6), 0.2, emision=(1.0, 0.70, 0.40), fuerza=6.0)
    RI.armar_rio(M, energia_farola=70.0)
    RI.animar_agua(M["agua"], cuadros, fps, velocidad=0.25)
    CI.sol(92.0, 2.5, 2.2, (1.0, 0.52, 0.24), angulo=2.0)
    B.neblina((0, 130, 15), (120, 440, 30), 0.0018, (1.0, 0.78, 0.6), anisotropia=0.6, nombre="calima")
    dur = cuadros / fps

    def recorrido(t):
        u = _suave(t / dur)
        return ((16.2 - 0.2 * u, -14.0 + 2.0 * u, 1.62), (2.5 - 0.8 * u, 70.0, 3.2 + 0.4 * u), 30.0)
    _camara(recorrido, cuadros, fps, fstop=5.6, foco_m=40.0)
    return dict(exposicion=0.0, exposicion_eevee=-0.6, volumen_fin=300.0)


def e08_cocina(escena, cuadros, fps):
    """8.0 — La cocina vacía de los Dabate en Ellington, la mañana del 23 de diciembre de 2015: la
    misma cocina de la escena 5 (`casa_e05.cocina`), ahora sin nada en el piso, con la luz gris de la
    ventana. Nadie. Si esa cocina no estuviera, se arma una equivalente (`cierre_e08.cocina_dia`)."""
    mundo, nt, salida = B.mundo_nuevo(escena, "dia_invierno")
    fondo = nt.nodes.new("ShaderNodeBackground")
    fondo.inputs["Color"].default_value = (0.55, 0.58, 0.62, 1)
    fondo.inputs["Strength"].default_value = 0.22
    nt.links.new(fondo.outputs[0], salida.inputs["Surface"])
    dur = cuadros / fps
    if hasattr(CA5, "cocina"):
        CA5.cocina(escena)
        if hasattr(CA5, "sin_rayas"):                  # el mismo acabado de interiores que la escena 5
            CA5.sin_rayas(escena)
        # más luz gris de mañana que entra por la ventana y se abre por el cuarto (penumbra que se lee)
        luz = bpy.data.lights.new("manana_gris", "AREA")
        luz.shape, luz.size, luz.size_y = "RECTANGLE", 2.2, 1.6
        luz.energy, luz.color = 90.0, (0.82, 0.87, 0.95)
        ob = B.enlazar(bpy.data.objects.new("manana_gris", luz))
        ob.location = (2.8, 4.45, 1.65)
        ob.rotation_euler = (math.radians(-80), 0.0, 0.0)            # hacia el cuarto, un poco hacia abajo
        B.luz("rebote_techo", "POINT", (2.8, 2.2, 2.3), 35.0, (0.85, 0.88, 0.92), radio=0.8)

        def recorrido(t):                      # desde la puerta del comedor, hacia la ventana del fregadero
            u = _suave(t / dur)
            return ((3.75 - 0.25 * u, 0.35 + 0.5 * u, 1.52 - 0.03 * u), (2.75 - 0.1 * u, 4.6, 1.25 - 0.05 * u), 26.0)
        _camara(recorrido, cuadros, fps, fstop=4.0, foco_m=3.6)
        return dict(exposicion=0.0, exposicion_eevee=-0.45, volumen_fin=12.0)
    CI.cocina_dia()
    CI.sol(112.0, 21.0, 4.5, (1.0, 0.86, 0.70), angulo=0.6)

    def recorrido_propio(t):
        u = _suave(t / dur)
        return ((-0.9 + 0.25 * u, -2.05 + 0.45 * u, 1.48 - 0.04 * u), (0.25 - 0.1 * u, 2.4, 1.05 - 0.05 * u), 28.0)
    _camara(recorrido_propio, cuadros, fps, fstop=4.0, foco_m=2.8)
    return dict(exposicion=0.0, exposicion_eevee=-0.4, volumen_fin=12.0)
