"""Primer plano del costado de alguien que camina de noche: la chamarra oscura, el cierre del bolsillo y,
adentro, la pantalla del teléfono que late con luz a través de la tela. No se ve la cara ni el cuerpo
entero: solo la cadera y el bolsillo, que suben y bajan con cada paso.
"""

import math

import bmesh
from mathutils import Vector, noise

from tres_d.base import barra, caja, entrada, luz, material, objeto, simple

R = 0.165                     # radio de la chamarra a la altura de la cadera
ANGULO_BOLSILLO = math.radians(40)
Z_BOLSILLO = 1.02
TEL_ANCHO, TEL_ALTO = 0.075, 0.150


def _rect_suave(s, z, cx, cz, w, h, borde):
    """1 dentro del rectángulo (centrado en cx, cz), 0 afuera, con un borde suave."""
    def paso(d, lim):
        x = min(1.0, max(0.0, (lim + borde - d) / (2 * borde)))
        return x * x * (3 - 2 * x)
    return paso(abs(s - cx), w / 2) * paso(abs(z - cz), h / 2)


def _malla_cilindro(nombre, r0, z0, z1, ang0, ang1, nu, nv, relieve, mats):
    bm = bmesh.new()
    filas = []
    for j in range(nv + 1):
        z = z0 + (z1 - z0) * j / nv
        fila = []
        for i in range(nu + 1):
            a = ang0 + (ang1 - ang0) * i / nu
            r = r0 + relieve(a, z)
            fila.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
        filas.append(fila)
    for j in range(nv):
        for i in range(nu):
            bm.faces.new((filas[j][i], filas[j][i + 1], filas[j + 1][i + 1], filas[j + 1][i]))
    return objeto(nombre, bm, mats, suave=True)


def mat_tela(nombre="chamarra", color=(0.045, 0.048, 0.056), brillo_tel=True):
    """Tela de nylon oscuro con su trama; donde está el teléfono, la luz de la pantalla pasa a través
    (emisión enmascarada con un rectángulo de esquinas suaves, que late con el nodo «pulso»)."""
    def hacer(a):
        tc = (a.nodo("ShaderNodeTexCoord"), "Object")
        x, y, z = a.separar(tc)
        trama = a.nodo("ShaderNodeTexWave", wave_type="BANDS")
        a.unir(tc, trama, "Vector")
        entrada(trama, "Scale").default_value = 260.0
        entrada(trama, "Distortion").default_value = 1.5
        fino, _ = a.ruido(tc, 180.0, 2.0, 0.6)
        altura = a.m("ADD", a.m("MULTIPLY", (trama, "Fac"), 0.6), a.m("MULTIPLY", fino, 0.4))
        normal = a.bump(altura, 0.25, 0.002)
        b = a.nodo("ShaderNodeBsdfPrincipled")
        a.dar(b, "Base Color", (*color, 1.0))
        a.dar(b, "Roughness", 0.62)
        if "Sheen Weight" in b.inputs:
            b.inputs["Sheen Weight"].default_value = 0.5
        a.unir(normal, b, "Normal")
        if brillo_tel:
            ang = a.m("ARCTAN2", y, x)
            s = a.m("MULTIPLY", a.m("SUBTRACT", ang, ANGULO_BOLSILLO), R)    # largo de arco sobre la tela
            dz = a.m("ABSOLUTE", a.m("SUBTRACT", z, Z_BOLSILLO))
            ds = a.m("ABSOLUTE", s)
            mx = a.nodo("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
            a.unir(ds, mx, 0)
            for i, v in enumerate((TEL_ANCHO / 2 - 0.03, TEL_ANCHO / 2 + 0.05, 1.0, 0.0), start=1):
                mx.inputs[i].default_value = v
            mz = a.nodo("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
            a.unir(dz, mz, 0)
            for i, v in enumerate((TEL_ALTO / 2 - 0.035, TEL_ALTO / 2 + 0.06, 1.0, 0.0), start=1):
                mz.inputs[i].default_value = v
            mascara = a.m("MULTIPLY", (mx, 0), (mz, 0))
            # la tela deja pasar más luz donde es más delgada (trama) y un halo alrededor
            mascara = a.m("MULTIPLY", a.m("MULTIPLY", mascara, mascara), a.rango((trama, "Fac"), 0.0, 1.0, 0.45, 1.0))
            pulso = a.nodo("ShaderNodeValue")
            pulso.name = "pulso"
            fuerza = a.m("MULTIPLY", a.m("MULTIPLY", mascara, (pulso, 0)), 0.18)       # la tela deja pasar poca luz
            entrada(b, "Emission Color", "Emission").default_value = (0.55, 0.72, 1.0, 1)    # luz fría de pantalla
            a.unir(fuerza, b, "Emission Strength")
        return (b, 0)
    return material(nombre, hacer)


def armar_bolsillo(padre):
    """Cadera con chamarra, bolsillo con cierre y la pierna con jeans; todo hijo de `padre`."""
    def relieve(a, z):
        s = (a - ANGULO_BOLSILLO) * R
        pliegue = 0.006 * math.sin(z * 48 + 2.5 * noise.noise(Vector((a * 2, z * 4, 0.3))))
        pliegue += 0.006 * noise.noise(Vector((a * 3.0, z * 9.0, 1.7)))
        pliegue += 0.004 * math.sin((s * 0.8 + z) * 70)                    # pliegues en diagonal hacia la cadera
        bulto = 0.011 * _rect_suave(s, z, 0.0, Z_BOLSILLO, TEL_ANCHO, TEL_ALTO, 0.02)
        dobladillo = 0.006 if z < 0.86 else 0.0
        return pliegue * (1 - 0.7 * _rect_suave(s, z, 0.0, Z_BOLSILLO, TEL_ANCHO, TEL_ALTO, 0.02)) + bulto + dobladillo
    tela = mat_tela()
    ob = _malla_cilindro("chamarra", R, 0.80, 1.40, ANGULO_BOLSILLO - 1.9, ANGULO_BOLSILLO + 1.9, 160, 120, relieve, [tela])
    ob.parent = padre
    jeans = material("jeans", lambda a: a.bsdf(
        a.v("SCALE", (0.025, 0.035, 0.06), escala=a.rango(a.ruido((a.nodo("ShaderNodeTexCoord"), "Object"), 90.0, 3.0)[0], 0.3, 0.7, 0.7, 1.2)),
        0.8, normal=a.bump(a.ruido((a.nodo("ShaderNodeTexCoord"), "Object"), 300.0, 2.0)[0], 0.3, 0.002)))

    def relieve_j(a, z):
        return 0.004 * noise.noise(Vector((a * 4, z * 12, 5.0)))
    pierna = _malla_cilindro("jeans", 0.145, 0.45, 0.84, ANGULO_BOLSILLO - 1.6, ANGULO_BOLSILLO + 1.6, 80, 40, relieve_j, [jeans])
    pierna.parent = padre

    # cierre en diagonal sobre el bolsillo: dientes metálicos, la tira y el jalador
    metal = simple("cierre", (0.35, 0.34, 0.32), 0.3, metal=1.0)
    cinta_ = simple("cinta_cierre", (0.01, 0.01, 0.012), 0.7)
    bm_d, bm_c = bmesh.new(), bmesh.new()
    largo = 0.17

    def punto_cierre(u, r):
        s, z = u * largo * 0.25 - 0.004, Z_BOLSILLO + TEL_ALTO / 2 + 0.03 + u * largo * 0.97
        a = ANGULO_BOLSILLO + s / R + 0.03
        return Vector((r * math.cos(a), r * math.sin(a), z))
    for i in range(40):                                        # la cadena de dientes: un cordón metálico fino
        barra(bm_d, punto_cierre(i / 40 - 0.5, R + 0.0125), punto_cierre((i + 1) / 40 - 0.5, R + 0.0125), 0.0022, lados=6)
    for i in range(40):                                        # la tira de tela del cierre, a los dos lados
        for dr in (-0.004, 0.004):
            barra(bm_c, punto_cierre(i / 40 - 0.5, R + 0.0105) + Vector((0, 0, dr)),
                  punto_cierre((i + 1) / 40 - 0.5, R + 0.0105) + Vector((0, 0, dr)), 0.003, lados=5)
    dientes = objeto("dientes", bm_d, [metal])
    tira = objeto("tira", bm_c, [cinta_])
    for o in (dientes, tira):
        o.parent = padre
    bm = bmesh.new()
    a = ANGULO_BOLSILLO + 0.03
    zt = Z_BOLSILLO + TEL_ALTO / 2 + 0.03 + 0.5 * largo * 0.97
    caja(bm, Vector(((R + 0.016) * math.cos(a), (R + 0.016) * math.sin(a), zt - 0.018)), (0.009, 0.009, 0.03))
    jalador = objeto("jalador", bm, [metal])
    jalador.parent = padre
    # la luz que sale de la pantalla y alumbra la tela de alrededor
    centro = Vector(((R + 0.03) * math.cos(ANGULO_BOLSILLO), (R + 0.03) * math.sin(ANGULO_BOLSILLO), Z_BOLSILLO))
    pant = luz("pantalla", "AREA", centro, 0.0, (0.6, 0.75, 1.0), padre=padre)
    pant.data.shape = "RECTANGLE"
    pant.data.size, pant.data.size_y = 0.06, 0.12
    afuera = Vector((math.cos(ANGULO_BOLSILLO), math.sin(ANGULO_BOLSILLO), 0))
    pant.rotation_euler = afuera.to_track_quat("-Z", "Y").to_euler()          # alumbra hacia afuera de la tela
    # contraluz cálido de una farola de atrás: dibuja el borde de la chamarra y sus pliegues
    contra = luz("contraluz", "AREA", Vector((-0.9, -1.2, 1.6)), 220.0, (1.0, 0.72, 0.45), padre=padre)
    contra.data.size = 0.6
    contra.rotation_euler = (Vector((0.1, 0.1, 1.0)) - Vector((-0.9, -1.2, 1.6))).to_track_quat("-Z", "Y").to_euler()
    # farola de adelante, alta y suave: dibuja los pliegues del lado que ve la cámara
    p_farola = Vector((1.7 * math.cos(ANGULO_BOLSILLO + 1.0), 1.7 * math.sin(ANGULO_BOLSILLO + 1.0), 2.3))
    frente = luz("farola_frente", "AREA", p_farola, 15.0, (1.0, 0.74, 0.48), padre=padre)
    frente.data.size = 1.0
    frente.rotation_euler = (Vector((0.0, 0.0, Z_BOLSILLO)) - p_farola).to_track_quat("-Z", "Y").to_euler()
    return tela, pant


def pulso(t: float, latidos) -> float:
    """El mismo latido doble que dibuja el contador: un golpe y su eco, que se apagan rápido."""
    v = 0.0
    for tb in latidos:
        for dt, amp in ((0.0, 1.0), (0.28, 0.6)):
            x = t - tb - dt
            if 0 <= x < 0.7:
                v += amp * math.exp(-x / 0.16) * (1 - math.exp(-x / 0.02))
    return min(v, 1.2)


def animar_bolsillo(tela, pantalla, cadera, cuadros, fps, latidos, pasos):
    nodo = tela.node_tree.nodes["pulso"]
    for f in range(1, cuadros + 2):
        t = (f - 1) / fps
        p = pulso(t, latidos)
        nodo.outputs[0].default_value = 0.7 + 1.6 * p                  # la pantalla nunca se apaga del todo
        nodo.outputs[0].keyframe_insert("default_value", frame=f)
        pantalla.data.energy = 0.05 + 0.5 * p
        pantalla.data.keyframe_insert("energy", frame=f)
        # cada paso: la cadera baja y sube, y se ladea un poco hacia el pie que apoya
        dz, giro = 0.0, 0.0
        for k, tp in enumerate(pasos):
            x = t - tp
            if 0 <= x < 0.9:
                golpe = math.exp(-x / 0.16) * (1 - math.exp(-x / 0.03))
                dz -= 0.014 * golpe
                giro += (0.025 if k % 2 else -0.025) * golpe
        cadera.location = (0.0, 0.0, dz + 0.004 * math.sin(t * 2.1))
        cadera.keyframe_insert("location", frame=f)
        cadera.rotation_euler = (giro * 0.4, giro, 0.0)
        cadera.keyframe_insert("rotation_euler", frame=f)

