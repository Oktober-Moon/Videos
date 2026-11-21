"""Objetos de las escenas 2 y 4 hechos con código: el iPhone de 2016 (cerrado o abierto, con su placa y
su chip de memoria), un Android, la laptop del laboratorio, el cable, la mesa de evidencias de acero
con su bolsa, la regla y la etiqueta, el escritorio y la mesa de noche.

Las medidas y la colocación de teléfonos y pantallas salen de `tres_d/vista_e02.py`, que la escena
usa también para dibujar encima el contenido de cada pantalla. Las pantallas aquí son vidrio negro
que solo refleja; la luz que echan sobre la mesa la da una lámpara de área del tamaño de la pantalla.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

from tres_d import base as B
from tres_d import vista_e02 as V

FUENTES = __import__("pathlib").Path(__file__).resolve().parent.parent / "fuentes"


# --------------------------------------------------------------------------- materiales


def mat_aluminio(nombre="aluminio", color=(0.20, 0.20, 0.21), rug=0.30):
    """Aluminio anodizado con un cepillado fino (la rugosidad cambia en vetas a lo largo)."""
    def hacer(a):
        p = B.coord_objeto(a)
        vetas, _ = a.ruido(a.v("MULTIPLY", p, (900.0, 40.0, 900.0)), 1.0, 3.0, 0.6)
        return a.bsdf(color, a.rango(vetas, 0.3, 0.7, rug - 0.06, rug + 0.08), metal=1.0)
    return B.material(nombre, hacer)


def mat_vidrio_negro(nombre="vidrio_negro", rug=0.035):
    return B.material(nombre, lambda a: a.bsdf((0.004, 0.004, 0.005), rug, coat=1.0, especular=0.5))


def mat_epoxi(nombre="epoxi"):
    def hacer(a):
        f, _ = a.ruido(B.coord_objeto(a), 900.0, 2.0)
        return a.bsdf(a.v("SCALE", (0.018, 0.018, 0.020), escala=a.rango(f, 0.3, 0.7, 0.8, 1.2)), 0.55, especular=0.4)
    return B.material(nombre, hacer)


def mat_pcb(nombre="placa"):
    """Placa de circuito negra-verdosa con pistas finas más claras (patrón de ruido en tiras)."""
    def hacer(a):
        p = B.coord_objeto(a)
        x, y, _ = a.separar(p)
        pistas = a.m("GREATER_THAN", a.m("FRACT", a.m("MULTIPLY", a.m("ADD", x, a.m("MULTIPLY", y, 0.0)), 1400.0)), 0.82)
        zona, _ = a.ruido(p, 260.0, 2.0)
        pistas = a.m("MULTIPLY", pistas, a.m("GREATER_THAN", zona, 0.55))
        col = a.mezcla((0.012, 0.030, 0.018), (0.05, 0.09, 0.05), pistas)
        return a.bsdf(col, 0.32, coat=0.6)
    return B.material(nombre, hacer)


def mat_texto(nombre="tinta", color=(0.55, 0.55, 0.55), rug=0.6):
    return B.simple(nombre, color, rug)


def mat_acero_cepillado(nombre="acero_mesa"):
    """Acero inoxidable cepillado de mesa de laboratorio, con rayones finos y manchas de uso."""
    def hacer(a):
        p = B.pos_mundo(a)
        vetas, _ = a.ruido(a.v("MULTIPLY", p, (2.0, 160.0, 2.0)), 4.0, 4.0, 0.6)
        mancha, _ = a.ruido(p, 6.0, 4.0, 0.5)
        raya = a.nodo("ShaderNodeTexWave", wave_type="BANDS")
        a.unir(a.v("MULTIPLY", p, (1.0, 0.07, 1.0)), raya, "Vector")
        B.entrada(raya, "Scale").default_value = 140.0
        B.entrada(raya, "Distortion").default_value = 9.0
        rug = a.m("ADD", a.rango(vetas, 0.3, 0.7, 0.34, 0.40), a.rango(mancha, 0.5, 0.8, 0.0, 0.08))
        rug = a.m("ADD", rug, a.m("MULTIPLY", a.rango((raya, "Fac"), 0.97, 1.0), 0.03))
        col = a.v("SCALE", (0.44, 0.44, 0.45), escala=a.rango(mancha, 0.3, 0.8, 1.0, 0.88))
        return a.bsdf(col, rug, metal=1.0)
    return B.material(nombre, hacer)


def mat_bolsa(nombre="bolsa"):
    """Plástico de bolsa de evidencias: casi transparente, con reflejo que crece en ángulo rasante
    (Fresnel) y un velo lechoso donde se arruga."""
    def hacer(a):
        p = B.coord_objeto(a)
        arruga, _ = a.ruido(p, 38.0, 4.0, 0.55)
        fres = a.nodo("ShaderNodeFresnel")
        fres.inputs["IOR"].default_value = 1.45
        normal = a.bump(arruga, 0.2, 0.002)
        a.unir(normal, fres, "Normal")
        transp = (a.nodo("ShaderNodeBsdfTransparent"), 0)
        brillo = a.bsdf((0.85, 0.86, 0.88), 0.12, especular=0.7, normal=normal)
        velo = a.rango(arruga, 0.6, 0.85, 0.0, 0.05)
        f = a.m("ADD", a.m("MULTIPLY", (fres, 0), 0.6), velo)
        return a.mezclar_shader(transp, brillo, f)
    mat = B.material(nombre, hacer)
    B.poner(mat, "use_transparent_shadow", True)
    return mat


def mat_papel(nombre="papel", color=(0.78, 0.76, 0.70)):
    def hacer(a):
        f, _ = a.ruido(B.pos_mundo(a), 300.0, 3.0)
        return a.bsdf(a.v("SCALE", color, escala=a.rango(f, 0.3, 0.7, 0.92, 1.04)), 0.8)
    return B.material(nombre, hacer)


def mat_madera_oscura(nombre="escritorio", color=(0.075, 0.065, 0.058)):
    """Laminado de escritorio: veta muy suave, mate con algo de brillo."""
    def hacer(a):
        p = B.pos_mundo(a)
        veta = a.nodo("ShaderNodeTexWave", wave_type="BANDS")
        a.unir(a.v("MULTIPLY", p, (1.0, 0.06, 1.0)), veta, "Vector")
        B.entrada(veta, "Scale").default_value = 45.0
        B.entrada(veta, "Distortion").default_value = 3.0
        mancha, _ = a.ruido(p, 3.0, 4.0)
        col = a.v("SCALE", color, escala=a.rango((veta, "Fac"), 0.0, 1.0, 0.93, 1.06))
        col = a.v("SCALE", col, escala=a.rango(mancha, 0.3, 0.7, 0.9, 1.08))
        return a.bsdf(col, a.rango(mancha, 0.3, 0.7, 0.34, 0.52))
    return B.material(nombre, hacer)


def mat_madera_clara(nombre="madera", color=(0.30, 0.18, 0.09)):
    def hacer(a):
        p = B.pos_mundo(a)
        veta = a.nodo("ShaderNodeTexWave", wave_type="BANDS")
        a.unir(a.v("MULTIPLY", p, (1.0, 0.08, 1.0)), veta, "Vector")
        B.entrada(veta, "Scale").default_value = 30.0
        B.entrada(veta, "Distortion").default_value = 4.0
        col = a.v("SCALE", color, escala=a.rango((veta, "Fac"), 0.0, 1.0, 0.85, 1.08))
        return a.bsdf(col, 0.45, coat=0.3)
    return B.material(nombre, hacer)


def fuente(nombre="Inter-SemiBold.ttf"):
    try:
        return bpy.data.fonts.load(str(FUENTES / nombre), check_existing=True)
    except (RuntimeError, OSError):
        return None


def letrero(nombre, cadena, pos, tam, mat, padre=None, rot=(0, 0, 0), alinear="CENTER", tipo="Inter-SemiBold.ttf"):
    """Texto plano (curva de letras) apoyado en una superficie."""
    cu = bpy.data.curves.new(nombre, "FONT")
    cu.body = cadena
    cu.size = tam
    cu.align_x = alinear
    cu.align_y = "CENTER"
    f = fuente(tipo)
    if f is not None:
        cu.font = f
    ob = bpy.data.objects.new(nombre, cu)
    ob.data.materials.append(mat)
    B.enlazar(ob)
    if padre is not None:
        ob.parent = padre
    ob.location = pos
    ob.rotation_euler = rot
    return ob


# --------------------------------------------------------------------------- geometría


def contorno_redondeado(w, h, r, n=10, cx=0.0, cy=0.0):
    """Rectángulo de esquinas redondeadas (centro cx, cy), en sentido antihorario."""
    pts = []
    for k, (ex, ey) in enumerate(((w / 2 - r, -h / 2 + r), (w / 2 - r, h / 2 - r), (-w / 2 + r, h / 2 - r), (-w / 2 + r, -h / 2 + r))):
        a0 = -math.pi / 2 + k * math.pi / 2
        for i in range(n + 1):
            a = a0 + (math.pi / 2) * i / n
            pts.append((cx + ex + r * math.cos(a), cy + ey + r * math.sin(a)))
    return pts


def losa(bm, contorno, z0, z1):
    """Prisma de base `contorno` entre z0 y z1."""
    abajo = [bm.verts.new((x, y, z0)) for x, y in contorno]
    arriba = [bm.verts.new((x, y, z1)) for x, y in contorno]
    bm.faces.new(abajo[::-1])
    bm.faces.new(arriba)
    n = len(contorno)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((abajo[i], abajo[j], arriba[j], arriba[i]))


def cara(bm, contorno, z):
    vs = [bm.verts.new((x, y, z)) for x, y in contorno]
    bm.faces.new(vs)


def biselar(ob, ancho, segmentos=5, angulo=40.0):
    m = ob.modifiers.new("bisel", "BEVEL")
    m.width = ancho
    m.segments = segmentos
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angulo)
    B.poner(m, "harden_normals", True)
    for pol in ob.data.polygons:
        pol.use_smooth = True
    return m


def area(nombre, pos, energia, color, tam, tam_y=None, apunta=None, padre=None, rot=None):
    ob = B.luz(nombre, "AREA", pos, energia, color, padre=padre)
    ob.data.shape = "RECTANGLE"
    ob.data.size = tam
    ob.data.size_y = tam_y if tam_y is not None else tam
    if apunta is not None:
        ob.rotation_euler = (Vector(apunta) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    elif rot is not None:
        ob.rotation_euler = rot
    return ob


def mundo_liso(escena, color, fuerza):
    mundo, nt, salida = B.mundo_nuevo(escena, "estudio")
    fondo = nt.nodes.new("ShaderNodeBackground")
    fondo.inputs["Color"].default_value = (*color, 1)
    fondo.inputs["Strength"].default_value = fuerza
    nt.links.new(fondo.outputs[0], salida.inputs["Surface"])
    return mundo


# --------------------------------------------------------------------------- teléfonos


def _materiales_telefono(color_cuerpo):
    return dict(cuerpo=mat_aluminio("aluminio_tel", color_cuerpo, 0.28), vidrio=mat_vidrio_negro("vidrio_tel"),
                pantalla=mat_vidrio_negro("pantalla_tel", 0.02), boton=B.simple("anillo_boton", (0.45, 0.45, 0.46), 0.22, metal=1.0),
                oscuro=B.simple("rejilla", (0.02, 0.02, 0.022), 0.6))


def telefono(nombre, modelo=V.IPHONE, centro=(0, 0, 0), giro=0.0, color_cuerpo=(0.20, 0.20, 0.21), boton=True,
             luz_pantalla=0.0, abierto=False):
    """Teléfono acostado boca arriba. Devuelve (raíz, lámpara de la pantalla, bisagra de la pantalla o
    None). Con `abierto`, el cuerpo es una bandeja con la batería y la placa adentro, y el vidrio con
    la pantalla cuelga de una bisagra en el borde de arriba (se anima su giro)."""
    M = _materiales_telefono(color_cuerpo)
    L, A, G, R = modelo["largo"], modelo["ancho"], modelo["grueso"], modelo["radio"]
    raiz = B.vacio(nombre, centro)
    raiz.rotation_euler = (0, 0, math.radians(giro))
    exterior = contorno_redondeado(A, L, R, 12)
    bm = bmesh.new()
    if abierto:                                   # bandeja: piso y paredes de 0.9 mm
        losa(bm, exterior, 0.0, 0.0012)
        interior = contorno_redondeado(A - 0.0018, L - 0.0018, R - 0.0009, 12)
        abajo = [bm.verts.new((x, y, 0.0012)) for x, y in exterior]
        arriba = [bm.verts.new((x, y, G - 0.0008)) for x, y in exterior]
        ai = [bm.verts.new((x, y, 0.0012)) for x, y in interior]
        bi = [bm.verts.new((x, y, G - 0.0008)) for x, y in interior]
        n = len(exterior)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((abajo[i], abajo[j], arriba[j], arriba[i]))
            bm.faces.new((bi[i], bi[j], ai[j], ai[i]))
            bm.faces.new((arriba[i], arriba[j], bi[j], bi[i]))
    else:
        losa(bm, exterior, 0.0, G - 0.0008)
    cuerpo = B.objeto(f"{nombre}_cuerpo", bm, [M["cuerpo"]], padre=raiz)
    biselar(cuerpo, 0.0018, 5)
    # el frente: vidrio con la pantalla, el botón, la bocina y la cámara
    frente = B.vacio(f"{nombre}_frente", (0, L / 2, G - 0.0008), padre=raiz)       # bisagra en el borde de arriba
    bm = bmesh.new()
    losa(bm, [(x, y - L / 2) for x, y in contorno_redondeado(A - 0.0006, L - 0.0006, R - 0.0003, 12)], 0.0, 0.0008)
    vidrio = B.objeto(f"{nombre}_vidrio", bm, [M["vidrio"]], padre=frente)
    biselar(vidrio, 0.00035, 3)
    bm = bmesh.new()
    pw, ph, py = modelo["pant_ancho"], modelo["pant_largo"], modelo["pant_y"]
    cara(bm, [(-pw / 2, py - ph / 2 - L / 2), (pw / 2, py - ph / 2 - L / 2), (pw / 2, py + ph / 2 - L / 2),
              (-pw / 2, py + ph / 2 - L / 2)], 0.00082)
    B.objeto(f"{nombre}_pantalla", bm, [M["pantalla"]], padre=frente)
    if boton:
        bm = bmesh.new()
        yb = -L + 0.0105
        anillo_e = [(0.0056 * math.cos(a), yb + 0.0056 * math.sin(a)) for a in [i * math.tau / 48 for i in range(48)]]
        losa(bm, anillo_e, 0.0006, 0.00085)
        B.objeto(f"{nombre}_boton", bm, [M["boton"]], padre=frente, suave=True)
        bm = bmesh.new()
        dentro = [(0.0050 * math.cos(a), yb + 0.0050 * math.sin(a)) for a in [i * math.tau / 48 for i in range(48)]]
        cara(bm, dentro, 0.00087)
        B.objeto(f"{nombre}_boton_vidrio", bm, [M["vidrio"]], padre=frente)
    bm = bmesh.new()
    yb = -0.0105 if boton else -0.0062
    cara(bm, contorno_redondeado(0.010, 0.0013, 0.00065, 4, 0.0, yb), 0.00083)
    cara(bm, [(-0.0085 + 0.0011 * math.cos(a), yb + 0.0011 * math.sin(a)) for a in [i * math.tau / 20 for i in range(20)]], 0.00083)
    B.objeto(f"{nombre}_bocina", bm, [M["oscuro"]], padre=frente)
    # el área alumbra hacia su −z: volteada, sale de la pantalla hacia arriba
    lampara = area(f"{nombre}_luz", (0, py - L / 2, 0.003), luz_pantalla, (0.75, 0.82, 1.0), pw, ph, padre=frente,
                   rot=(math.pi, 0, 0))
    if abierto:
        _por_dentro(nombre, modelo, raiz)
    return raiz, lampara, frente


def _por_dentro(nombre, modelo, raiz):
    """Lo que se ve al abrir el teléfono: batería, placa con el procesador y la memoria flash,
    blindajes, el motor de vibración y la cámara; también el reverso de la pantalla."""
    L, A = modelo["largo"], modelo["ancho"]
    piso = 0.0012
    epoxi, pcb = mat_epoxi(), mat_pcb()
    blindaje = B.simple("blindaje", (0.62, 0.62, 0.62), 0.32, metal=1.0)
    oro = B.simple("oro", (0.85, 0.62, 0.25), 0.25, metal=1.0)
    bateria = B.simple("bateria", (0.03, 0.03, 0.035), 0.5)
    etiqueta = B.simple("etiqueta_bateria", (0.05, 0.05, 0.055), 0.7)
    tinta = mat_texto("tinta_chip", (0.62, 0.62, 0.60), 0.7)
    bm = bmesh.new()
    B.caja(bm, (-0.0100, -0.006, piso + 0.0019), (0.040, 0.094, 0.0038))
    B.objeto(f"{nombre}_bateria", bm, [bateria], padre=raiz)
    bm = bmesh.new()
    B.caja(bm, (-0.0100, -0.006, piso + 0.00385), (0.034, 0.080, 0.0001))
    B.objeto(f"{nombre}_bateria_etiqueta", bm, [etiqueta], padre=raiz)
    letrero(f"{nombre}_bat_txt", "Li-ion 1960 mAh", (-0.0100, -0.006, piso + 0.0040), 0.0032, tinta, padre=raiz,
            rot=(0, 0, math.pi / 2))
    # placa: una tira a lo largo del lado derecho y otra arriba (forma de L)
    bm = bmesh.new()
    B.caja(bm, (0.0195, 0.010, piso + 0.0006), (0.0240, 0.100, 0.0010))
    B.caja(bm, (0.000, 0.0565, piso + 0.0006), (0.060, 0.019, 0.0010))
    B.objeto(f"{nombre}_placa", bm, [pcb], padre=raiz)
    z = piso + 0.0011
    # procesador y memoria: encapsulados negros con su leyenda
    for nom, (x, y), (w, h), lineas in (("cpu", V.CHIP_CPU[:2], (0.0145, 0.0145), ("A10", "APL1W24", "1640 TW")),
                                        ("flash", V.CHIP_FLASH[:2], (0.0120, 0.0160), ("NAND", "128 GB", "TH58 1643"))):
        bm = bmesh.new()
        B.caja(bm, (x, y, z + 0.0005), (w, h, 0.0010))
        chip = B.objeto(f"{nombre}_{nom}", bm, [epoxi], padre=raiz)
        biselar(chip, 0.0002, 2)
        for k, linea in enumerate(lineas):
            letrero(f"{nombre}_{nom}_t{k}", linea, (x, y + h * 0.22 - k * h * 0.22, z + 0.00102), h * (0.17 if k else 0.21),
                    tinta, padre=raiz, tipo="Inter-Regular.ttf" if k else "Inter-SemiBold.ttf")
        # bolitas de soldadura asomando por los bordes
        bm = bmesh.new()
        for i in range(12):
            for lado in (-1, 1):
                B.caja(bm, (x + lado * (w / 2 + 0.0003), y - h / 2 + h * (i + 0.5) / 12, z + 0.0002), (0.0004, 0.0005, 0.0003))
        B.objeto(f"{nombre}_{nom}_pads", bm, [oro], padre=raiz)
    # componentes chicos y blindajes
    import random
    rng = random.Random(7)
    bm = bmesh.new()
    for _ in range(70):
        x = rng.uniform(0.0090, 0.0300)
        y = rng.uniform(-0.038, 0.062)
        if any(abs(x - cx) < w_ / 2 + 0.001 and abs(y - cy) < h_ / 2 + 0.001 for (cx, cy), (w_, h_) in
               ((V.CHIP_CPU[:2], (0.0145, 0.0145)), (V.CHIP_FLASH[:2], (0.012, 0.016)))):
            continue
        s = rng.uniform(0.0006, 0.0018)
        B.caja(bm, (x, y, z + 0.0003), (s, s * rng.uniform(0.5, 1.4), 0.0006))
    B.objeto(f"{nombre}_componentes", bm, [epoxi], padre=raiz)
    bm = bmesh.new()
    B.caja(bm, (0.0195, -0.030, z + 0.0006), (0.0200, 0.018, 0.0012))
    B.caja(bm, (-0.012, 0.0565, z + 0.0006), (0.022, 0.014, 0.0012))
    B.objeto(f"{nombre}_blindajes", bm, [blindaje], padre=raiz)
    # cámara trasera, motor de vibración y bocina
    bm = bmesh.new()
    B.caja(bm, (-0.0210, 0.0560, z + 0.0018), (0.0110, 0.0110, 0.0036))
    B.caja(bm, (-0.0040, -0.0600, piso + 0.0015), (0.0300, 0.0110, 0.0030))
    B.objeto(f"{nombre}_modulos", bm, [B.simple("modulo", (0.03, 0.03, 0.035), 0.4)], padre=raiz)
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=0.0035,
                            matrix=Matrix.Translation((-0.0210, 0.0560, z + 0.0037)))
    B.objeto(f"{nombre}_lente", bm, [mat_vidrio_negro("lente", 0.02)], padre=raiz)
    bm = bmesh.new()
    B.caja(bm, (0.0200, -0.0570, piso + 0.0015), (0.0160, 0.0140, 0.0030))
    B.objeto(f"{nombre}_bocina_inf", bm, [blindaje], padre=raiz)
    # reverso de la pantalla: una placa de metal gris con su cinta de conexión
    frente = bpy.data.objects[f"{nombre}_frente"]
    bm = bmesh.new()
    B.caja(bm, (0.0, -L / 2, -0.0003), (A - 0.004, L - 0.006, 0.0005))
    B.objeto(f"{nombre}_reverso", bm, [blindaje], padre=frente)
    bm = bmesh.new()
    B.caja(bm, (0.022, -0.010, -0.0007), (0.010, 0.020, 0.0003))
    B.objeto(f"{nombre}_cinta", bm, [B.simple("cinta_flex", (0.35, 0.18, 0.03), 0.4)], padre=frente)


# --------------------------------------------------------------------------- mesa de evidencias (2.0)


def mesa_evidencias():
    """Mesa de acero de la sala de evidencias, con el iPhone en su bolsa sellada, una regla
    fotográfica y la etiqueta de cadena de custodia. Devuelve la lámpara de la pantalla."""
    acero = mat_acero_cepillado()
    bm = bmesh.new()
    B.caja(bm, (0.0, 0.0, -0.02), (1.6, 1.0, 0.04))
    mesa = B.objeto("mesa", bm, [acero])
    biselar(mesa, 0.004, 3)
    bm = bmesh.new()
    B.caja(bm, (0.0, 1.2, 0.6), (4.0, 0.1, 2.0))
    B.objeto("pared", bm, [B.simple("pared", (0.10, 0.105, 0.11), 0.85)])
    (c, giro) = V.MESA_TELEFONO
    raiz, lampara, _ = telefono("iphone", V.IPHONE, c, giro, (0.18, 0.18, 0.19), luz_pantalla=0.0)
    # la bolsa: dos capas de plástico, la de arriba arrugada sobre el teléfono; abajo del teléfono, la
    # zona blanca impresa donde se escribe el número de evidencia
    bolsa = mat_bolsa()
    bw, bh, dy = 0.165, 0.255, -0.0075
    rot = Matrix.Rotation(math.radians(giro + 3.0), 4, "Z")
    rot_y0, rot_y1 = -0.1225, -0.0825                         # zona del rótulo (y, en ejes de la bolsa)
    for capa, z0 in (("abajo", 0.0004), ("arriba", None)):
        bm = bmesh.new()
        nx, ny = 60, 94
        filas = []
        for j in range(ny + 1):
            fila = []
            for i in range(nx + 1):
                x = -bw / 2 + bw * i / nx
                y = -bh / 2 + bh * j / ny + dy
                if z0 is not None:
                    z = z0
                elif rot_y0 - 0.002 < y < rot_y1 + 0.002 and abs(x) < bw / 2 - 0.004:
                    z = 0.0030
                else:
                    sobre = max(0.0, 1 - max(abs(x) / (V.IPHONE["ancho"] / 2 + 0.008), abs(y) / (V.IPHONE["largo"] / 2 + 0.008)) ** 8)
                    borde = min(1.0, (bw / 2 - abs(x)) / 0.012, (bh / 2 - abs(y - dy)) / 0.012)
                    z = 0.0024 + (V.IPHONE["grueso"] + 0.0006) * sobre * max(0.0, borde)
                    z += 0.0016 * noise.noise(Vector((x * 40, y * 40, 0.5))) * (0.4 + 0.6 * sobre) * max(0.0, borde)
                fila.append(bm.verts.new((rot @ Vector((x, y, 0.0))).to_tuple()[:2] + (z,)))
            filas.append(fila)
        for j in range(ny):
            for i in range(nx):
                bm.faces.new((filas[j][i], filas[j][i + 1], filas[j + 1][i + 1], filas[j + 1][i]))
        B.objeto(f"bolsa_{capa}", bm, [bolsa], suave=True)
    roja = B.simple("cierre_rojo", (0.30, 0.012, 0.02), 0.45)
    blanca = mat_papel("rotulo_bolsa", (0.80, 0.80, 0.78))
    tinta = mat_texto("tinta_rotulo", (0.02, 0.02, 0.025), 0.5)
    tinta_azul = mat_texto("tinta_azul", (0.02, 0.04, 0.16), 0.5)
    rotulo = B.vacio("rotulo", (0, 0, 0))
    rotulo.rotation_euler = (0, 0, math.radians(giro + 3.0))
    bm = bmesh.new()
    B.caja(bm, (0.0, bh / 2 + dy - 0.004, 0.0030), (bw, 0.008, 0.0012))
    B.objeto("cierre", bm, [roja], padre=rotulo)
    bm = bmesh.new()
    B.caja(bm, (0.0, (rot_y0 + rot_y1) / 2, 0.0031), (bw - 0.016, rot_y1 - rot_y0, 0.0002))
    B.objeto("zona_rotulo", bm, [blanca], padre=rotulo)
    x0 = -bw / 2 + 0.014
    letrero("rot_t0", "POLIZEI FREIBURG", (x0, rot_y1 - 0.007, 0.0033), 0.0060, tinta, padre=rotulo, alinear="LEFT")
    letrero("rot_t1", "Asservat Nr.", (x0, rot_y1 - 0.019, 0.0033), 0.0048, tinta, padre=rotulo, alinear="LEFT",
            tipo="Inter-Regular.ttf")
    letrero("rot_t2", "17 / 0412", (x0 + 0.036, rot_y1 - 0.0195, 0.0033), 0.0062, tinta_azul, padre=rotulo, alinear="LEFT",
            tipo="Inter-Light.ttf")
    letrero("rot_t3", "Mobiltelefon Apple iPhone", (x0, rot_y1 - 0.031, 0.0033), 0.0048, tinta, padre=rotulo,
            alinear="LEFT", tipo="Inter-Regular.ttf")
    # regla fotográfica en L junto a la bolsa (dos brazos, cada uno con sus marcas a lo largo de y local)
    regla = B.material("regla", _regla)
    for nom, pos, giro_r, largo in (("regla_larga", (0.125, -0.030), 0.0, 0.20), ("regla_corta", (0.075, -0.119), 90.0, 0.10)):
        bm = bmesh.new()
        B.caja(bm, (0.0, 0.0, 0.0008), (0.022, largo, 0.0016))
        ob = B.objeto(nom, bm, [regla])
        q = rot @ Vector((pos[0], pos[1], 0.0))
        ob.location = (q.x, q.y, 0.0)
        ob.rotation_euler = (0, 0, math.radians(giro + 3.0 + giro_r))
    # etiqueta de cartón con su hilo, al otro lado
    carton = mat_papel("carton", (0.55, 0.42, 0.26))
    bm = bmesh.new()
    B.caja(bm, (0.0, 0.0, 0.0004), (0.048, 0.092, 0.0008))
    et = B.objeto("etiqueta", bm, [carton])
    et.location = (-0.135, 0.020, 0.0)
    et.rotation_euler = (0, 0, math.radians(-24))
    letrero("et_t0", "BEWEISMITTEL", (0.0, 0.026, 0.00082), 0.0058, tinta, padre=et)
    letrero("et_t1", "03.12.2016", (0.0, 0.008, 0.00082), 0.0068, tinta_azul, padre=et, tipo="Inter-Light.ttf")
    hilo = bpy.data.curves.new("hilo", "CURVE")
    hilo.dimensions = "3D"
    hilo.bevel_depth = 0.0006
    sp = hilo.splines.new("POLY")
    pts = [(-0.135 + 0.040 * math.sin(math.radians(24)) + 0.004 * k, 0.020 + 0.040 * math.cos(math.radians(24)) + 0.012 * k
            + 0.006 * math.sin(k), 0.0007) for k in range(9)]
    sp.points.add(len(pts) - 1)
    for p_, q in zip(sp.points, pts):
        p_.co = (*q, 1.0)
    ob = bpy.data.objects.new("hilo", hilo)
    ob.data.materials.append(B.simple("hilo", (0.6, 0.55, 0.45), 0.8))
    B.enlazar(ob)
    return lampara


def _regla(a):
    """Regla de fotografía forense: gris claro con marcas negras desde el borde izquierdo: cortas cada
    milímetro, medianas cada medio centímetro y largas cada centímetro."""
    p = B.coord_objeto(a)
    x, y, _ = a.separar(p)
    borde = a.m("ADD", x, 0.011)                                   # distancia al borde izquierdo
    mm = a.m("LESS_THAN", a.m("FRACT", a.m("MULTIPLY", y, 1000.0)), 0.16)
    medio = a.m("LESS_THAN", a.m("FRACT", a.m("MULTIPLY", y, 200.0)), 0.035)
    cm = a.m("LESS_THAN", a.m("FRACT", a.m("MULTIPLY", y, 100.0)), 0.018)
    largo = a.m("MAXIMUM", a.m("MAXIMUM", a.m("MULTIPLY", mm, 0.003), a.m("MULTIPLY", medio, 0.005)),
                a.m("MULTIPLY", cm, 0.008))
    linea = a.m("LESS_THAN", borde, largo)
    col = a.mezcla((0.66, 0.66, 0.64), (0.02, 0.02, 0.02), a.m("MULTIPLY", linea, 0.95))
    return a.bsdf(col, 0.55)


# --------------------------------------------------------------------------- laboratorio (2.2, 2.7, 2.8)


def laptop(nombre, centro, giro, luz=0.0):
    """Laptop de 14 pulgadas abierta. Devuelve la lámpara de la pantalla."""
    L = V.LAPTOP
    alu = mat_aluminio("aluminio_laptop", (0.42, 0.42, 0.43), 0.32)
    raiz = B.vacio(nombre, centro)
    raiz.rotation_euler = (0, 0, math.radians(giro))
    bm = bmesh.new()
    losa(bm, contorno_redondeado(L["ancho"], L["fondo"], 0.010, 8), 0.0, L["grueso"])
    cuerpo = B.objeto(f"{nombre}_cuerpo", bm, [alu], padre=raiz)
    biselar(cuerpo, 0.0025, 4)
    teclas = B.material("teclado", _teclado)
    bm = bmesh.new()
    B.caja(bm, (0.0, 0.030, L["grueso"] + 0.0002), (0.275, 0.105, 0.0006))
    B.objeto(f"{nombre}_teclado", bm, [teclas], padre=raiz)
    bm = bmesh.new()
    B.caja(bm, (0.0, -0.068, L["grueso"] + 0.00005), (0.105, 0.066, 0.0002))
    B.objeto(f"{nombre}_trackpad", bm, [mat_aluminio("trackpad", (0.40, 0.40, 0.41), 0.45)], padre=raiz)
    bisagra = B.vacio(f"{nombre}_bisagra", (0, L["fondo"] / 2, L["grueso"]), padre=raiz)
    bisagra.rotation_euler = (-math.radians(L["abierta"]), 0, 0)
    bm = bmesh.new()
    tapa = [(x, y - L["fondo"] / 2) for x, y in contorno_redondeado(L["ancho"], L["fondo"], 0.010, 8)]
    losa(bm, tapa, 0.0, L["tapa"])
    t = B.objeto(f"{nombre}_tapa", bm, [alu], padre=bisagra)
    biselar(t, 0.002, 3)
    bm = bmesh.new()
    cara(bm, [(x, y) for x, y in reversed(contorno_redondeado(L["ancho"] - 0.004, L["fondo"] - 0.004, 0.008, 8, 0, -L["fondo"] / 2))],
         -0.0002)
    B.objeto(f"{nombre}_marco", bm, [mat_vidrio_negro("marco_laptop", 0.06)], padre=bisagra)
    s0, s1 = V.MARGEN_PANTALLA, V.MARGEN_PANTALLA + L["pant_alto"]
    w = L["pant_ancho"] / 2
    bm = bmesh.new()
    cara(bm, [(-w, -s1), (-w, -s0), (w, -s0), (w, -s1)], -0.0003)
    B.objeto(f"{nombre}_pantalla", bm, [mat_vidrio_negro("pantalla_laptop", 0.12)], padre=bisagra)
    lampara = area(f"{nombre}_luz", (0, -(s0 + s1) / 2, -0.004), luz, (0.80, 0.86, 1.0), L["pant_ancho"], L["pant_alto"],
                   padre=bisagra, rot=(0, 0, 0))
    return lampara


def _teclado(a):
    """Teclas negras en cuadrícula sobre el aluminio (patrón en coordenadas del objeto)."""
    p = B.coord_objeto(a)
    x, y, _ = a.separar(p)
    u = a.m("FRACT", a.m("MULTIPLY", a.m("ADD", x, 0.5), 1 / 0.0190))
    v = a.m("FRACT", a.m("MULTIPLY", a.m("ADD", y, 0.5), 1 / 0.0190))
    tecla = a.m("MULTIPLY", a.m("MULTIPLY", a.m("GREATER_THAN", u, 0.08), a.m("LESS_THAN", u, 0.92)),
                a.m("MULTIPLY", a.m("GREATER_THAN", v, 0.08), a.m("LESS_THAN", v, 0.92)))
    # el aluminio va casi mate: con la sala oscura, un metal pulido solo reflejaba negro y las teclas,
    # que reciben la luz de la pantalla, se veían más claras que la cubierta
    col = a.mezcla((0.50, 0.50, 0.51), (0.004, 0.004, 0.005), tecla)
    return a.bsdf(col, a.rango(tecla, 0, 1, 0.5, 0.9), metal=a.rango(tecla, 0, 1, 0.25, 0.0),
                  especular=a.rango(tecla, 0, 1, 0.5, 0.05))


def cable(nombre, puntos, radio=0.0016, color=(0.82, 0.82, 0.80)):
    """Cable blanco de plástico que pasa por `puntos` (curva suave)."""
    cu = bpy.data.curves.new(nombre, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radio
    cu.bevel_resolution = 4
    sp = cu.splines.new("NURBS")
    sp.points.add(len(puntos) - 1)
    for p_, q in zip(sp.points, puntos):
        p_.co = (*q, 1.0)
    sp.order_u = 4
    sp.use_endpoint_u = True
    sp.resolution_u = 24
    ob = bpy.data.objects.new(nombre, cu)
    ob.data.materials.append(B.simple(f"{nombre}_mat", color, 0.35, coat=0.2))
    B.enlazar(ob)
    return ob


def escritorio_laboratorio(luz_laptop=6.0, luz_telefono=0.0):
    """Escritorio del perito: la laptop, el teléfono conectado por cable, un tapete y un par de
    cosas de trabajo. Devuelve (lámpara de la laptop, lámpara del teléfono, raíz del teléfono)."""
    bm = bmesh.new()
    B.caja(bm, (0.0, 0.1, -0.015), (1.8, 1.0, 0.03))
    B.objeto("escritorio", bm, [mat_madera_oscura()])
    bm = bmesh.new()
    B.caja(bm, (-0.26, -0.03, 0.0008), (0.30, 0.24, 0.0016))
    tapete = B.objeto("tapete", bm, [B.simple("tapete_esd", (0.05, 0.07, 0.10), 0.85)])
    tapete.rotation_euler = (0, 0, math.radians(6))
    bm = bmesh.new()
    B.caja(bm, (0.0, 0.70, 0.7), (3.0, 0.1, 1.6))
    B.objeto("pared", bm, [B.simple("pared_lab", (0.16, 0.17, 0.18), 0.9)])
    luz_l = laptop("laptop", *V.LAB_LAPTOP, luz=luz_laptop)
    (c, giro) = V.LAB_TELEFONO
    c = (c[0], c[1], c[2] + 0.0016)
    raiz, luz_t, _ = telefono("iphone", V.IPHONE, c, giro, (0.18, 0.18, 0.19), luz_pantalla=luz_telefono)
    # cable: del puerto de abajo del teléfono, sobre la mesa, al costado izquierdo de la laptop
    rt = Matrix.Rotation(math.radians(giro), 4, "Z")
    puerto = Vector(c) + rt @ Vector((0.0, -V.IPHONE["largo"] / 2 - 0.004, V.IPHONE["grueso"] / 2))
    salida = Vector(c) + rt @ Vector((0.0, -V.IPHONE["largo"] / 2 - 0.030, 0.0022))
    lc, lg = V.LAB_LAPTOP
    rl = Matrix.Rotation(math.radians(lg), 4, "Z")
    usb = Vector(lc) + rl @ Vector((-V.LAPTOP["ancho"] / 2 - 0.004, 0.02, V.LAPTOP["grueso"] / 2))
    llega = Vector(lc) + rl @ Vector((-V.LAPTOP["ancho"] / 2 - 0.040, 0.03, 0.0018))
    medio = (salida + llega) / 2 + Vector((-0.06, -0.10, 0.0))
    pts = [puerto, salida, Vector((salida.x + 0.01, salida.y - 0.05, 0.0018)), medio,
           Vector((llega.x - 0.05, llega.y - 0.04, 0.0018)), llega, usb]
    cable("cable", [p.to_tuple() for p in pts])
    plastico = B.simple("conector", (0.85, 0.85, 0.83), 0.3)
    for nom, p_, r_, tam in (("conector_tel", puerto, rt, (0.0075, 0.010, 0.0042)), ("conector_usb", usb, rl, (0.016, 0.013, 0.0075))):
        bm = bmesh.new()
        B.caja(bm, (0, 0, 0), tam)
        ob = B.objeto(nom, bm, [plastico])
        ob.location = p_
        ob.rotation_euler = r_.to_euler()
        biselar(ob, 0.0012, 3)
    # una taza y una libreta, desenfocadas al fondo
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=32, radius1=0.040, radius2=0.044, depth=0.095,
                          matrix=Matrix.Translation((-0.45, 0.30, 0.0475)))
    B.objeto("taza", bm, [B.simple("taza", (0.75, 0.74, 0.70), 0.2, coat=0.6)], suave=True)
    bm = bmesh.new()
    B.caja(bm, (-0.52, 0.06, 0.006), (0.15, 0.21, 0.012))
    lib = B.objeto("libreta", bm, [B.simple("libreta", (0.08, 0.09, 0.12), 0.6)])
    lib.rotation_euler = (0, 0, math.radians(-12))
    return luz_l, luz_t, raiz


# --------------------------------------------------------------------------- mesa de noche (2.9)


def cuarto_de_noche():
    """Mesa de noche de madera junto a la cama, en un cuarto a oscuras con luz de luna por la
    ventana; el Android boca arriba. Devuelve (lámpara de la pantalla, raíz del teléfono)."""
    madera = mat_madera_clara()
    bm = bmesh.new()
    B.caja(bm, (0.0, 0.05, -0.30), (0.50, 0.40, 0.60))
    mueble = B.objeto("mesa_noche", bm, [madera])
    biselar(mueble, 0.006, 3)
    # la cama al lado: colchón y sábana
    sabana = B.material("sabana", lambda a: a.bsdf(
        a.v("SCALE", (0.55, 0.57, 0.62), escala=a.rango(a.ruido(B.pos_mundo(a), 9.0, 4.0)[0], 0.3, 0.7, 0.8, 1.05)), 0.9,
        normal=a.bump(a.ruido(B.pos_mundo(a), 4.0, 5.0)[0], 0.6, 0.02)))
    bm = bmesh.new()
    B.caja(bm, (0.95, 0.40, -0.05), (1.30, 2.10, 0.22))
    cama = B.objeto("cama", bm, [sabana])
    biselar(cama, 0.05, 4, 30)
    bm = bmesh.new()
    B.caja(bm, (0.0, 0.62, 0.6), (4.0, 0.1, 2.4))
    B.objeto("pared", bm, [B.simple("pared_cuarto", (0.30, 0.30, 0.32), 0.9)])
    # cable del cargador que cuelga detrás de la mesa
    cable("cargador", [(-0.04, -0.09, 0.0018), (-0.08, -0.04, 0.0018), (-0.16, 0.05, 0.0018), (-0.22, 0.20, 0.0)],
          radio=0.0014, color=(0.05, 0.05, 0.055))
    (c, giro) = V.NOCHE_TELEFONO
    raiz, luz_t, _ = telefono("android", V.ANDROID, c, giro, (0.05, 0.05, 0.055), boton=False, luz_pantalla=0.4)
    # luz de luna: un área fría y alta, como la ventana a la izquierda
    area("luna", (-1.6, -0.6, 1.4), 60.0, (0.55, 0.65, 1.0), 1.0, 1.4, apunta=(0.0, 0.1, 0.0))
    return luz_t, raiz
