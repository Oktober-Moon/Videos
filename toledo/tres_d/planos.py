"""Los planos 3D del video. Cada función arma su escena y su animación en Blender y devuelve los
ajustes de render que cambian (exposición, distancia del volumen…). Las llama `tres_d/plano.py`.

Firma: plano(escena, cuadros, fps, **params) -> dict | None
"""

import math

import bmesh
import bpy
from mathutils import Vector

from tres_d import base as B
from tres_d import bolsillo as BO
from tres_d import calle as CA
from tres_d import calle_datos as CD
from tres_d import pbr as PB
from tres_d import rio as RI


def _suave(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# --------------------------------------------------------------------------- escena 1

def calle_madrugada(escena, cuadros, fps):
    """1.0 — Friburgo, 16 de octubre de 2016, de madrugada: el casco viejo vacío, mojado y quieto."""
    CA.armar_calle(escena, "madrugada", con_tranvia=False, neblina_densidad=0.006, libre=True)
    cam, mira = B.camara((1.1, -6.0, 1.7), lente=30, fstop=4.0, distancia_foco=25.0)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        y = -6.0 + 0.5 * t                                       # avance lento, como caminando despacio
        B.clave(cam, "location", (1.1 + 0.04 * math.sin(t * 0.5), y, 1.7 + 0.01 * math.sin(t * 1.6)), f)
        B.clave(mira, "location", (-0.9 + 0.15 * t, y + 45.0, 3.4 - 0.05 * t), f)
    return dict(exposicion=0.0, exposicion_eevee=-0.75, volumen_fin=200.0)


def _rio_de_noche(escena, cuadros, fps, niebla_agua=0.05, pareja=False):
    """El Dreisam de noche. Con `pareja`, las dos neblinas (la bruma baja sobre el agua y la general)
    van juntas en un solo volumen de densidad uniforme: cuesta la mitad en Cycles y, donde el fondo
    está desenfocado, se ve igual."""
    # la foto de noche ilumina y se refleja en el agua; la cámara ve el cielo de madrugada
    PB.hdri(escena, "NightEnvironmentHDRI002_4K", fuerza=0.22, giro_grados=90.0, fondo_camara="madrugada")
    M = RI.materiales_rio(libre=True)
    RI.armar_rio(M)
    RI.animar_agua(M["agua"], cuadros, fps)
    if pareja:                          # a la altura del camino la bruma vale ~0.2 de su densidad
        B.neblina((0, 130, 15), (120, 440, 30), 0.0025 + 0.2 * niebla_agua, (0.70, 0.74, 0.84), nombre="neblina")
        return M
    B.neblina((0, 130, 0.6), (40, 440, 6.4), niebla_agua, (0.70, 0.74, 0.82), z_espesa=(RI.AGUA_Z, 1.5), nombre="bruma_rio")
    B.neblina((0, 130, 15), (120, 440, 30), 0.0025, (0.70, 0.74, 0.86), nombre="neblina")
    return M


def dreisam_noche(escena, cuadros, fps, bici_inicio=0.3, bici_vel=5.2, bici_y0=-18.0):
    """1.0 — 2:37 a. m.: desde la orilla de enfrente, una bicicleta avanza por la ciclovía junto al
    Dreisam; solo se ven su luz roja, el faro que alumbra el camino y su reflejo en el agua. Pasa
    bajo el puente y ya no sale: el camino queda vacío."""
    _rio_de_noche(escena, cuadros, fps)
    bici = RI.bicicleta(B.simple("silueta", (0.008, 0.008, 0.009), 0.7))
    x_bici = sum(RI.CAMINO) / 2 + 0.6
    cam, mira = B.camara((-14.2, -9.0, 1.0), lente=32, fstop=2.8, distancia_foco=34.0)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        y = bici_y0 + bici_vel * max(0.0, t - bici_inicio)
        B.clave(bici, "location", (x_bici, y, 0.0), f)
        u = _suave(t / (cuadros / fps))
        B.clave(cam, "location", (-14.2 + 0.4 * u, -9.0 + 2.5 * u, 1.0 + 0.3 * u), f)
        y_mira = min(y + 2.0, RI.PUENTE_Y - 1.0)                   # deja aire hacia donde va la bici
        B.clave(mira, "location", (x_bici - 5.0, y_mira, -0.6), f)
        cam.data.dof.focus_distance = max(12.0, math.dist((x_bici, y, 0.5), cam.location))
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
        cam.data.lens = 50.0 - 18.0 * _suave((t - 2.0) / 9.0)          # se abre despacio hasta ver el puente
        cam.data.keyframe_insert("lens", frame=f)
    return dict(exposicion=1.4, exposicion_eevee=-1.0, volumen_fin=320.0)


def orilla_amanecer(escena, cuadros, fps):
    """1.1 — Horas después: la misma orilla al amanecer, gris y con neblina; la cinta de la policía
    cierra el talud y unos marcadores amarillos señalan dónde se encontraron indicios. Nadie."""
    B.cielo(escena, "amanecer_gris")
    M = RI.materiales_rio(libre=True)
    M["lampara"] = B.simple("lampara_apagada", (0.4, 0.4, 0.38), 0.3)
    RI.armar_rio(M, energia_farola=0.0)
    RI.animar_agua(M["agua"], cuadros, fps)
    B.neblina((0, 130, 0.6), (40, 440, 6.4), 0.045, (0.80, 0.82, 0.86), z_espesa=(RI.AGUA_Z, 0.0), nombre="bruma_rio")
    B.neblina((0, 130, 15), (120, 440, 30), 0.0075, (0.82, 0.84, 0.88), anisotropia=0.2, nombre="neblina")
    # cinta: estacas a lo largo del camino y una vuelta que baja por el talud hasta el agua
    def z_talud(x):
        return -1.75 + (x - 10.6) / 4.4 * 1.75
    estacas = [(15.25, y) for y in (6.0, 10.0, 14.0)] + [(13.4, 16.0), (11.4, 18.5), (11.0, 23.5), (12.9, 27.0)] + \
              [(15.25, y) for y in (29.0, 33.0)]
    metal = B.simple("estaca", (0.5, 0.5, 0.5), 0.4, metal=0.8)
    bm = bmesh.new()
    for x, y in estacas:
        z0 = 0.0 if x >= 15.0 else z_talud(x)
        B.barra(bm, (x, y, z0 - 0.2), (x, y, z0 + 1.05), 0.014, lados=6)
    B.objeto("estacas", bm, [metal])
    puntos = [(x, y, (0.0 if x >= 15.0 else z_talud(x)) + 0.95) for x, y in estacas]
    m_cinta = RI.mat_cinta()
    RI.cinta("cinta", puntos, m_cinta)
    RI.cinta("cinta_baja", [(15.25, 6.0, 0.45), (15.25, 14.0, 0.45)], m_cinta, caida=0.1)
    negro = B.simple("negro", (0.01, 0.01, 0.01), 0.6)
    amarillo = RI.mat_marcador()
    for k, (x, y, n) in enumerate(((13.0, 17.2, 1), (12.3, 19.6, 2), (13.4, 22.4, 3))):
        m = RI.marcador_evidencia(k, (x, y, z_talud(x) + 0.01), n, amarillo, negro, giro=math.radians(160 + 10 * k))
        m.scale = (1.4, 1.4, 1.4)

    cam, mira = B.camara((16.9, 3.0, 1.7), lente=35, fstop=4.0, distancia_foco=18.0)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        u = _suave(t / (cuadros / fps))
        B.clave(cam, "location", (16.9 - 0.3 * u, 3.0 + 2.5 * u, 1.7 + 0.008 * math.sin(t * 1.3)), f)
        B.clave(mira, "location", (10.8 + 0.5 * u, 21.0 + 1.0 * u, -1.5), f)
    return dict(exposicion=0.7, exposicion_eevee=-1.25, volumen_fin=260.0)


def tranvia_noche(escena, cuadros, fps, t0=2.6):
    """1.1 — Las cámaras de los tranvías: un tranvía iluminado que llega de madrugada por la calle vacía."""
    tranvia, foco = CA.armar_calle(escena, "madrugada", con_tranvia=True, neblina_densidad=0.005, libre=True)
    # domo de la cámara de seguridad en el techo, detrás del parabrisas
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.07)
    domo = B.objeto("domo_camara", bm, [B.simple("domo", (0.01, 0.01, 0.012), 0.08)], padre=tranvia, suave=True)
    domo.location = (0.55, 1.3, CD.BASE_T + CD.ALTO_T - 0.12)
    cam, mira = B.camara(CD.CAMARA, lente=CD.LENTE, fstop=2.2, foco=foco)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps + t0
        B.clave(tranvia, "location", (0.0, CD.frente(t), 0.0), f)
        B.clave(mira, "location", CD.mira(t), f)
        B.clave(cam, "location", (CD.CAMARA[0] + 0.012 * math.sin(t * 1.3), CD.CAMARA[1] + 0.01 * math.sin(t * 0.7 + 1),
                                  CD.CAMARA[2] + 0.008 * math.sin(t * 1.9 + 2)), f)
    return dict(exposicion=0.1, exposicion_eevee=-0.65)


def bolsillo(escena, cuadros, fps, latidos=(), pasos=()):
    """1.2 — El testigo en el bolsillo: el costado de alguien que camina de noche junto al río; el
    teléfono late con luz a través de la tela de la chamarra, paso a paso."""
    _rio_de_noche(escena, cuadros, fps, niebla_agua=0.06, pareja=True)     # el fondo va desenfocado
    andar = B.vacio("caminante")
    cadera = B.vacio("cadera", padre=andar)
    tela, pantalla = BO.armar_bolsillo(cadera)
    a = BO.ANGULO_BOLSILLO
    cam = bpy.data.objects.new("camara", bpy.data.cameras.new("camara"))
    B.enlazar(cam)
    escena.camera = cam
    cam.data.lens, cam.data.sensor_width = 50.0, 36.0
    cam.data.clip_start = 0.02
    cam.data.dof.use_dof = True
    cam.data.dof.aperture_fstop = 1.8
    cam.parent = andar                                      # la cámara acompaña al que camina
    destino = (BO.R * math.cos(a), BO.R * math.sin(a), BO.Z_BOLSILLO - 0.07)
    cam.location = (1.15 * math.cos(a + 0.5), 1.15 * math.sin(a + 0.5), BO.Z_BOLSILLO - 0.01)
    d = Vector(destino) - Vector(cam.location)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.dof.focus_distance = d.length
    x0, y0, vel = sum(RI.CAMINO) / 2, -14.0, 1.35
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        B.clave(andar, "location", (x0, y0 + vel * t, 0.0), f)
    BO.animar_bolsillo(tela, pantalla, cadera, cuadros, fps, list(latidos), list(pasos))
    # los brillos de los charcos, desenfocados detrás, salían como chispas sueltas en Cycles
    B.poner(escena.cycles, "sample_clamp_direct", 6.0)
    return dict(exposicion=-0.4, exposicion_eevee=-2.0, volumen_fin=260.0, muestras_cycles=128)     # el fondo desenfocado pide más muestras


# --------------------------------------------------------------------------- pruebas de realismo

def prueba_realismo(escena, cuadros, fps, libre=False):
    """El mismo plano del tranvía que llega de madrugada, con todo hecho a mano (`libre=False`) o con
    texturas escaneadas, cielo fotográfico y detalles extra (`libre=True`)."""
    tranvia, foco = CA.armar_calle(escena, "madrugada", con_tranvia=True, neblina_densidad=0.005, libre=libre)
    cam, mira = B.camara(CD.CAMARA, lente=CD.LENTE, fstop=2.2, foco=foco)
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        B.clave(tranvia, "location", (0.0, CD.frente(t), 0.0), f)
        B.clave(mira, "location", CD.mira(t), f)
        B.clave(cam, "location", (CD.CAMARA[0] + 0.012 * math.sin(t * 1.3), CD.CAMARA[1] + 0.01 * math.sin(t * 0.7 + 1),
                                  CD.CAMARA[2] + 0.008 * math.sin(t * 1.9 + 2)), f)
    return dict(exposicion=0.4)


def prueba_persona(escena, cuadros, fps, cerca=False):
    """Una persona (MPFB) que camina por la banqueta mojada del casco viejo de madrugada, bajo un
    farol, con texturas escaneadas y cielo real. `cerca` acerca la cámara a la cara."""
    from tres_d import persona as PE
    CA.armar_calle(escena, "madrugada", con_tranvia=False, neblina_densidad=0.004, libre=True)
    cuerpo, esqueleto = PE.crear_persona()
    raiz = esqueleto or cuerpo
    raiz.location = (4.85, 7.6, CD.ACERA_ALTO)
    raiz.rotation_euler = (0, 0, math.radians(8))           # camina hacia la cámara, un poco de lado
    if esqueleto:
        PE.posar_caminando(esqueleto, 0.0)
    if cerca:
        cam, mira = B.camara((4.25, 6.0, 1.66), lente=55, fstop=2.0, distancia_foco=1.75)
        mira.location = (4.85, 7.55, 1.70)
    else:
        cam, mira = B.camara((2.5, 0.9, 1.45), lente=50, fstop=2.0, distancia_foco=7.1)
        mira.location = (4.75, 7.6, 1.05)
        return dict(exposicion=1.1)
    return dict(exposicion=0.4)


def prueba_caminata(escena, cuadros, fps, vista="espalda", brazos=None, cuerpo=None):
    """Prueba: una persona (MPFB) camina de espaldas por la banqueta mojada del casco viejo con una
    caminata real grabada (captura de movimiento de CMU); la cámara la sigue a unos 7 m."""
    from tres_d import mocap as MC
    from tres_d import persona as PE
    CA.armar_calle(escena, "madrugada", con_tranvia=False, neblina_densidad=0.004, libre=True)
    _, esqueleto = PE.crear_persona(**(cuerpo or {}))
    direccion, recorrido = MC.aplicar(esqueleto, fps, cuadros, brazos=brazos)
    esqueleto.location = (4.85, 3.0, CD.ACERA_ALTO)
    esqueleto.rotation_euler = (0, 0, math.radians(90.0 - direccion))       # se aleja hacia +y
    bpy.context.view_layer.update()
    mundo = [esqueleto.matrix_world @ v for v in recorrido]
    y0, y1 = mundo[0].y, mundo[-1].y
    lado = vista == "lado"                                        # de perfil, para revisar el braceo
    cam, mira = B.camara((3.6, y0 - 7.0, 1.55), lente=32 if lado else 50, fstop=4.0 if lado else 2.0,
                         distancia_foco=4.0 if lado else 7.0)
    for f in range(1, cuadros + 2):
        y = y0 + (y1 - y0) * (f - 1) / cuadros                     # la cámara avanza parejo, sin el vaivén
        B.clave(cam, "location", (0.9, y, 1.2) if lado else (3.6, y - 7.0, 1.55), f)
        B.clave(mira, "location", (4.85, y, 0.95) if lado else (4.7, y, 1.15), f)
    return dict(exposicion=0.6, exposicion_eevee=-0.8)

