"""Planos 3D de la escena 2 (Un chip que no obedece). Los llama `tres_d/plano.py`.

Firma: plano(escena, cuadros, fps, **params) -> dict | None

Las cámaras salen de `tres_d/vista_e02.py`: la escena usa las mismas cuentas para dibujar el
contenido de cada pantalla encima del cuadro renderizado. Por eso estos planos van sin desenfoque de
movimiento: la pantalla dibujada tiene que caer justo sobre el vidrio.
"""

import math

import bmesh
import bpy

from tres_d import base as B
from tres_d import calle as CA
from tres_d import calle_datos as CD
from tres_d import mocap as MC
from tres_d import objetos_e02 as OB
from tres_d import persona as PE
from tres_d import vista_e02 as V


def _camara(fn, cuadros, fps, fstop=5.6, clip=0.004):
    """Cámara que sigue `fn(t) -> (pos, mira, lente)` cuadro por cuadro, con el foco en la mira."""
    cam, mira = B.camara((0.0, -1.0, 1.0), lente=50.0, fstop=fstop, distancia_foco=0.4)
    cam.data.clip_start = clip
    cam.data.clip_end = 200.0
    for f in range(1, cuadros + 2):
        pos, m, lente = fn((f - 1) / fps)
        B.clave(cam, "location", pos, f)
        B.clave(mira, "location", m, f)
        cam.data.lens = lente
        cam.data.keyframe_insert("lens", frame=f)
        cam.data.dof.focus_distance = math.dist(pos, m)
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
    return cam


# --------------------------------------------------------------------------- 2.0


def e02_tranvia_cctv(escena, cuadros, fps):
    """2.0 — Lo que grabó la cámara de un tranvía de madrugada: desde el techo del frente, la calle
    del casco viejo que avanza y, en la banqueta, alguien que camina de espaldas. La escena lo pasa
    a imagen de cámara de seguridad (gris, ruido, poca definición)."""
    CA.armar_calle(escena, "madrugada", con_tranvia=False, neblina_densidad=0.005, libre=True)
    _, esqueleto = PE.crear_persona("caminante", estatura=0.6, peso=0.45, musculo=0.5, edad=0.35)
    direccion, recorrido = MC.aplicar(esqueleto, fps, cuadros)
    esqueleto.location = (4.55, 17.0, CD.ACERA_ALTO)
    esqueleto.rotation_euler = (0, 0, math.radians(90.0 - direccion))
    cam, mira = B.camara((0.3, 0.0, 3.35), lente=17.0, fstop=8.0, distancia_foco=14.0)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        y = 2.9 * t                                               # el tranvía avanza despacio, a unos 10 km/h
        B.clave(cam, "location", (0.3, y, 3.35), f)
        B.clave(mira, "location", (0.9, y + 18.0, 0.7), f)
    return dict(exposicion=0.1, exposicion_eevee=-0.4)


def e02_mesa_evidencias(escena, cuadros, fps):
    """2.0 — «Tiene un iPhone»: el teléfono de Khavari en su bolsa de evidencia sellada, sobre la
    mesa de acero, con la regla y la etiqueta; luz fría desde arriba. La cámara se acerca despacio."""
    OB.mundo_liso(escena, (0.02, 0.022, 0.026), 0.35)
    OB.mesa_evidencias()
    # el número de evidencia y la fecha de la etiqueta no están en el guion: los renglones quedan vacíos
    for nombre in ("rot_t2", "et_t1"):
        bpy.data.objects[nombre].data.body = ""
    OB.area("caja_de_luz", (0.10, 0.16, 0.95), 28.0, (0.86, 0.92, 1.0), 0.9, 0.5, apunta=(0.0, 0.0, 0.0))
    OB.area("borde", (-0.70, 0.55, 0.32), 18.0, (1.0, 0.82, 0.62), 0.5, apunta=(0.0, 0.0, 0.02))
    OB.area("relleno", (0.6, -0.6, 0.5), 4.0, (0.8, 0.85, 1.0), 0.8, apunta=(0.0, 0.0, 0.0))
    dur = cuadros / fps
    _camara(lambda t: V.camara_mesa(t, dur), cuadros, fps, fstop=7.0)
    return dict(exposicion=-1.6, exposicion_eevee=-1.6, desenfoque_movimiento=False, muestras=64)


# --------------------------------------------------------------------------- 2.1


def e02_iphone_abierto(escena, cuadros, fps, t_abre=2.0, t_acerca=9.0):
    """2.1 — Se abre un iPhone: la pantalla gira sobre su borde de arriba y deja ver la batería y la
    placa; la cámara se mete hasta el chip de memoria flash."""
    OB.mundo_liso(escena, (0.015, 0.016, 0.02), 0.3)
    bm = bmesh.new()
    B.caja(bm, (0.0, 0.05, -0.002), (1.2, 0.9, 0.004))
    B.objeto("tapete", bm, [B.simple("tapete_esd", (0.035, 0.05, 0.075), 0.8)])
    c, giro = V.ABIERTO_TELEFONO
    _, _, frente = OB.telefono("iphone", V.IPHONE, c, giro, (0.18, 0.18, 0.19), abierto=True)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        u = V.coseno((t - t_abre) / 2.2)
        B.clave(frente, "rotation_euler", (-math.radians(112.0) * u, 0.0, 0.0), f)
    OB.area("caja_de_luz", (0.05, 0.10, 0.70), 30.0, (0.88, 0.92, 1.0), 0.6, 0.4, apunta=(0.0, 0.0, 0.0))
    OB.area("borde", (-0.45, 0.35, 0.18), 10.0, (1.0, 0.85, 0.65), 0.3, apunta=(0.0, 0.02, 0.0))
    OB.area("chip", (V.CHIP_FLASH[0] + 0.05, V.CHIP_FLASH[1] - 0.08, 0.12), 1.5, (0.9, 0.95, 1.0), 0.1,
            apunta=V.CHIP_FLASH)
    dur = cuadros / fps
    _camara(lambda t: V.camara_abierto(t, t_acerca, dur), cuadros, fps, fstop=8.0, clip=0.002)
    return dict(exposicion=-1.8, exposicion_eevee=-1.8, desenfoque_movimiento=False)


# --------------------------------------------------------------------------- laboratorio: 2.2, 2.7, 2.8


def _laboratorio(escena, luz_laptop=1.5):
    OB.mundo_liso(escena, (0.02, 0.024, 0.03), 0.25)
    luz_l, luz_t, raiz = OB.escritorio_laboratorio(luz_laptop=luz_laptop)
    OB.area("lampara_techo", (-0.10, -0.15, 1.25), 26.0, (1.0, 0.93, 0.84), 0.5, 0.5, apunta=(-0.05, 0.05, 0.0))
    OB.area("ventana", (-1.2, 0.2, 0.7), 10.0, (0.75, 0.82, 1.0), 1.0, 0.8, apunta=(0.0, 0.0, 0.05))
    return luz_l, luz_t, raiz


def e02_laboratorio(escena, cuadros, fps, marcas=(3.0, 10.0, 14.0, 30.0, 42.0)):
    """2.2 — La extracción física: el teléfono conectado por cable a la laptop del perito; la cámara
    sigue el cable hasta la pantalla (la escena dibuja ahí la copia, los archivos y la búsqueda de
    contraseñas) y al final se aleja."""
    _laboratorio(escena)
    claves = V.claves_laboratorio(marcas)
    _camara(lambda t: V.recorrido(t, claves), cuadros, fps, fstop=4.0)
    return dict(exposicion=-0.3, exposicion_eevee=-0.3, desenfoque_movimiento=False)


def e02_laboratorio_cifrado(escena, cuadros, fps):
    """2.7 — La misma mesa: en la laptop solo hay datos cifrados; el teléfono, al lado."""
    _laboratorio(escena)
    dur = cuadros / fps
    _camara(lambda t: V.camara_cifrado(t, dur), cuadros, fps, fstop=4.5)
    return dict(exposicion=-0.3, exposicion_eevee=-0.3, desenfoque_movimiento=False)


def e02_telefono_errores(escena, cuadros, fps, golpes=()):
    """2.8 — El teléfono sobre la mesa, visto casi desde arriba; vibra con cada contraseña errónea
    (la escena dibuja la pantalla de bloqueo con los tiempos de espera)."""
    _, _, raiz = _laboratorio(escena, luz_laptop=1.0)
    c, _ = V.LAB_TELEFONO
    base = (c[0], c[1], c[2] + 0.0016)
    for f in range(1, cuadros + 2):
        d = V.vibracion((f - 1) / fps, golpes)
        B.clave(raiz, "location", (base[0] + d[0], base[1] + d[1], base[2]), f)
    dur = cuadros / fps
    _camara(lambda t: V.camara_errores(t, dur), cuadros, fps, fstop=6.0)
    return dict(exposicion=-0.3, exposicion_eevee=-0.3, desenfoque_movimiento=False)


# --------------------------------------------------------------------------- 2.9


def e02_android_noche(escena, cuadros, fps):
    """2.9 — Un Android sobre la mesa de noche, a oscuras: se reinició de madrugada y espera el PIN;
    la alarma no va a sonar."""
    OB.mundo_liso(escena, (0.004, 0.006, 0.014), 0.5)
    OB.cuarto_de_noche()
    dur = cuadros / fps
    _camara(lambda t: V.camara_noche(t, dur), cuadros, fps, fstop=3.2)
    return dict(exposicion=-2.2, exposicion_eevee=-2.2, desenfoque_movimiento=False)


# --------------------------------------------------------------------------- prueba de aspecto


def _aparte(desplazamiento, construir):
    """Arma un conjunto con `construir()` y lo corre `desplazamiento` (todo lo nuevo sin padre pasa a
    colgar de un vacío en esa posición). Devuelve lo que devuelva `construir`."""
    antes = set(bpy.data.objects)
    r = construir()
    raiz = B.vacio(f"conjunto_{desplazamiento[0]:.0f}", desplazamiento)
    for ob in set(bpy.data.objects) - antes:
        if ob.parent is None and ob is not raiz:
            ob.parent = raiz
    return r


def e02_muestras(escena, cuadros, fps):
    """Prueba de aspecto (no va al video): todos los objetos de la escena 2 en una sola escena, cada
    conjunto a 20 m del anterior, y una cámara que salta de uno a otro en cada cuadro; así se revisan
    con un solo Blender. La pantalla abierta del teléfono queda a medio abrir."""
    OB.mundo_liso(escena, (0.02, 0.022, 0.026), 0.3)
    _aparte((0.0, 0.0, 0.0), OB.mesa_evidencias)

    def luces_mesa():
        OB.area("caja_de_luz", (0.10, 0.16, 0.95), 55.0, (0.86, 0.92, 1.0), 0.9, 0.5, apunta=(0.0, 0.0, 0.0))
        OB.area("borde", (-0.70, 0.55, 0.32), 18.0, (1.0, 0.82, 0.62), 0.5, apunta=(0.0, 0.0, 0.02))
        OB.area("relleno", (0.6, -0.6, 0.5), 4.0, (0.8, 0.85, 1.0), 0.8, apunta=(0.0, 0.0, 0.0))
    _aparte((0.0, 0.0, 0.0), luces_mesa)

    def abierto():
        bm = bmesh.new()
        B.caja(bm, (0.0, 0.05, -0.002), (1.2, 0.9, 0.004))
        B.objeto("tapete", bm, [B.simple("tapete_esd", (0.035, 0.05, 0.075), 0.8)])
        _, _, frente = OB.telefono("iphone_abierto", V.IPHONE, (0, 0, 0), 0.0, (0.18, 0.18, 0.19), abierto=True)
        frente.rotation_euler = (-math.radians(112.0), 0.0, 0.0)
        OB.area("caja_de_luz", (0.05, 0.10, 0.70), 30.0, (0.88, 0.92, 1.0), 0.6, 0.4, apunta=(0.0, 0.0, 0.0))
        OB.area("borde", (-0.45, 0.35, 0.18), 10.0, (1.0, 0.85, 0.65), 0.3, apunta=(0.0, 0.02, 0.0))
    _aparte((20.0, 0.0, 0.0), abierto)
    _aparte((40.0, 0.0, 0.0), lambda: _laboratorio(escena))
    _aparte((60.0, 0.0, 0.0), OB.cuarto_de_noche)
    D2 = lambda p, dx: (p[0] + dx, p[1], p[2])                       # noqa: E731
    tomas = [(V.camara_mesa(0.5, 6.0), 0.0), (V.camara_mesa(5.5, 6.0), 0.0),
             (V.camara_abierto(1.0, 9.0, 14.0), 20.0), (V.camara_abierto(10.5, 9.0, 14.0), 20.0),
             (V.recorrido(1.0, V.claves_laboratorio((3.1, 11.3, 16.6, 45.2, 53.1))), 40.0),
             (V.recorrido(20.0, V.claves_laboratorio((3.1, 11.3, 16.6, 45.2, 53.1))), 40.0),
             (V.camara_cifrado(2.0, 18.0), 40.0), (V.camara_errores(2.0, 31.0), 40.0),
             (V.camara_noche(2.0, 29.0), 60.0)]
    cam, mira = B.camara((0.0, -1.0, 1.0), lente=50.0, fstop=5.6, distancia_foco=0.4)
    cam.data.clip_start = 0.002
    exposiciones = (-1.6, -1.6, -0.6, -0.6, -0.3, -0.3, -0.3, -0.3, -2.2)        # las de cada plano
    for f, e in enumerate(exposiciones, start=1):
        escena.view_settings.exposure = e
        escena.keyframe_insert("view_settings.exposure", frame=f)
    for f, ((pos, m, lente), dx) in enumerate(tomas, start=1):
        B.clave(cam, "location", D2(pos, dx), f)
        B.clave(mira, "location", D2(m, dx), f)
        cam.data.lens = lente
        cam.data.keyframe_insert("lens", frame=f)
        cam.data.dof.focus_distance = math.dist(pos, m)
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
    return dict(desenfoque_movimiento=False, muestras=64)
