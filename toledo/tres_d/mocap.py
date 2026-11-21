"""Captura de movimiento real (base pública de Carnegie Mellon, formato ASF/AMC) pasada al esqueleto
de una persona de MPFB, para que camine como una persona y no como un muñeco animado a mano.

Los archivos están en `recursos_3d/mocap/` (fuente y licencia en `recursos_3d/LEEME.txt`).

Cómo se pasa el movimiento de un esqueleto al otro: para cada hueso de la grabación se calcula
cuánto giró en el mundo desde su pose de reposo (la «T», brazos abiertos) y se aplica ese mismo giro
al hueso equivalente de MPFB, después de alinear su reposo (la «A», brazos a 45°) con el de la
grabación. Así los brazos no atraviesan el cuerpo aunque las dos poses de reposo sean distintas.
La cadera se traslada según la grabación, escalada por el largo de las piernas de cada esqueleto.
"""

import math
from pathlib import Path

import numpy as np
from mathutils import Matrix, Quaternion, Vector

MOCAP = Path(__file__).resolve().parent.parent / "recursos_3d" / "mocap"
ESCALA = 0.0254 / 0.45                         # unidades de CMU -> metros
P = np.array([[1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])      # CMU (y arriba) -> Blender (z arriba)

# hueso de MPFB <- hueso de la grabación
MAPA = {
    "root": "root",
    "upperleg01.L": "lfemur", "upperleg02.L": "lfemur", "lowerleg01.L": "ltibia", "lowerleg02.L": "ltibia",
    "foot.L": "lfoot",
    "upperleg01.R": "rfemur", "upperleg02.R": "rfemur", "lowerleg01.R": "rtibia", "lowerleg02.R": "rtibia",
    "foot.R": "rfoot",
    "spine05": "lowerback", "spine04": "lowerback", "spine03": "upperback", "spine02": "upperback",
    "spine01": "thorax", "neck01": "lowerneck", "neck02": "upperneck", "neck03": "upperneck", "head": "head",
    "upperarm01.L": "lhumerus", "upperarm02.L": "lhumerus",
    "lowerarm01.L": "lradius", "lowerarm02.L": "lradius", "wrist.L": "lhand",
    "upperarm01.R": "rhumerus", "upperarm02.R": "rhumerus",
    "lowerarm01.R": "rradius", "lowerarm02.R": "rradius", "wrist.R": "rhand",
}
# La columna, el cuello y la cabeza conservan su curva de reposo (MPFB la trae, con la espalda alta
# inclinada unos 17° hacia adelante) y solo reciben el giro de la grabación. Alinearlas con las
# vértebras de CMU, casi rectas en reposo, enderezaba la espalda y sacaba el pecho.
COLUMNA = {"spine05", "spine04", "spine03", "spine02", "spine01", "neck01", "neck02", "neck03", "head"}

# Las clavículas y los hombros de MPFB no se copian: su reposo apunta hacia abajo y, alineado con la
# clavícula horizontal de la grabación, subía los hombros hasta las orejas. Siguen al tronco.

# Mano relajada: cuánto se doblan las falanges hacia la palma (grados), base, media y punta.
CURVA_DEDOS = {"finger1": (5, 10, 10), "finger2": (15, 30, 20), "finger3": (18, 32, 22),
               "finger4": (20, 35, 24), "finger5": (22, 38, 26)}


def _dedos_relajados(huesos) -> dict:
    """Giro local de cada falange para que la mano cuelgue con los dedos un poco cerrados (en reposo
    MPFB los tiene estirados y abiertos). El eje sale del plano de la palma; la palma mira al cuerpo."""
    giros = {}
    for lado, hacia_cuerpo in ((".L", -1.0), (".R", 1.0)):
        if f"finger2-1{lado}" not in huesos or f"finger5-1{lado}" not in huesos:
            continue
        a_lo_ancho = huesos[f"finger5-1{lado}"].head_local - huesos[f"finger2-1{lado}"].head_local
        a_lo_largo = huesos[f"finger3-1{lado}"].head_local - huesos[f"wrist{lado}"].head_local
        palma = a_lo_ancho.cross(a_lo_largo).normalized()
        if palma.x * hacia_cuerpo < 0:
            palma.negate()
        for dedo, angulos in CURVA_DEDOS.items():
            for k, grados in enumerate(angulos, start=1):
                b = huesos.get(f"{dedo}-{k}{lado}")
                if b is None:
                    continue
                d = (b.tail_local - b.head_local).normalized()
                eje = d.cross(palma)
                if eje.length < 1e-6:
                    continue
                R = Matrix.Rotation(math.radians(grados), 3, eje.normalized())
                B = b.matrix_local.to_3x3()
                giros[b.name] = B.transposed() @ R @ B
    return giros


def _euler(rx: float, ry: float, rz: float) -> np.ndarray:
    """Giro en grados, x, luego y, luego z sobre ejes fijos (Rz·Ry·Rx), como en ASF/AMC."""
    x, y, z = np.radians([rx, ry, rz])
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    rx_ = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry_ = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz_ = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rz_ @ ry_ @ rx_


def leer_asf(ruta: Path) -> dict:
    """Esqueleto: por hueso, dirección y largo en reposo, ejes locales (C), grados de libertad y padre."""
    huesos, actual, seccion = {"root": dict(dir=np.zeros(3), largo=0.0, C=np.eye(3), dof=[], padre=None)}, None, None
    jerarquia = []
    for linea in ruta.read_text(encoding="latin-1").splitlines():
        t = linea.split()
        if not t or t[0].startswith("#"):
            continue
        if t[0].startswith(":"):
            seccion = t[0]
            continue
        if seccion == ":bonedata":
            if t[0] == "begin":
                actual = dict(dir=np.zeros(3), largo=0.0, C=np.eye(3), dof=[], padre=None)
            elif t[0] == "name":
                huesos[t[1]] = actual
            elif t[0] == "direction":
                actual["dir"] = np.array([float(v) for v in t[1:4]])
            elif t[0] == "length":
                actual["largo"] = float(t[1]) * ESCALA
            elif t[0] == "axis":
                actual["C"] = _euler(*[float(v) for v in t[1:4]])
            elif t[0] == "dof":
                actual["dof"] = [d.lower() for d in t[1:]]
        elif seccion == ":hierarchy" and t[0] not in ("begin", "end"):
            jerarquia.append(t)
    orden = ["root"]
    for padre, *hijos in jerarquia:
        for h in hijos:
            huesos[h]["padre"] = padre
            orden.append(h)
    return dict(huesos=huesos, orden=orden)


def leer_amc(ruta: Path) -> list[dict]:
    cuadros, actual = [], None
    for linea in ruta.read_text(encoding="latin-1").splitlines():
        t = linea.split()
        if not t or t[0].startswith(("#", ":")):
            continue
        if len(t) == 1 and t[0].isdigit():
            actual = {}
            cuadros.append(actual)
        elif actual is not None:
            actual[t[0]] = [float(v) for v in t[1:]]
    return cuadros


def cinematica(asf: dict, cuadro: dict) -> dict:
    """Giro en el mundo (desde el reposo) y extremos de cada hueso, ya en ejes de Blender y metros."""
    H = asf["huesos"]
    giro, fin = {}, {}
    raiz = cuadro["root"]
    giro["root"] = _euler(*raiz[3:6])
    fin["root"] = np.array(raiz[:3]) * ESCALA
    for nombre in asf["orden"][1:]:
        h = H[nombre]
        rot = {"rx": 0.0, "ry": 0.0, "rz": 0.0}
        for d, v in zip(h["dof"], cuadro.get(nombre, [])):
            rot[d] = v
        giro[nombre] = giro[h["padre"]] @ h["C"] @ _euler(rot["rx"], rot["ry"], rot["rz"]) @ h["C"].T
        fin[nombre] = fin[h["padre"]] + h["largo"] * giro[nombre] @ h["dir"]
    return {n: (P @ giro[n] @ P.T, P @ fin[n]) for n in giro}


# Corrección del braceo. En la grabación 08_01 el hombro casi no se mueve y el codo se dobla hasta
# 60°: de espaldas se veía balancear solo el antebrazo. En una caminata relajada el brazo entero
# oscila desde el hombro, como péndulo, y el codo apenas se dobla. Se conserva el ritmo grabado y se
# cambia el reparto: más vaivén del hombro, menos doblez del codo, brazos un poco más pegados.
BRAZOS = dict(hombro=1.2, codo=0.45, abrir=0.8)


def _rodrigues(eje: np.ndarray, ang: float) -> np.ndarray:
    x, y, z = eje
    K = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K


def _de_a(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Giro mínimo que lleva la dirección u a la v."""
    eje = np.cross(u, v)
    s = np.linalg.norm(eje)
    if s < 1e-9:
        return np.eye(3)
    return _rodrigues(eje / s, math.atan2(s, float(u @ v)))


def _brazo(pose: dict, lado: str) -> tuple:
    """Ejes del tronco y dirección de brazo y antebrazo; ángulos del brazo: adelante/atrás (desde la
    vertical del tronco) y hacia afuera."""
    D = pose["thorax"][0]
    adelante, arriba, izq = D @ np.array([0, -1.0, 0]), D @ np.array([0, 0, 1.0]), D @ np.array([1.0, 0, 0])
    afuera = izq if lado == "l" else -izq
    hombro = pose[f"{lado}clavicle"][1]
    codo, muneca = pose[f"{lado}humerus"][1], pose[f"{lado}radius"][1]
    h = (codo - hombro) / np.linalg.norm(codo - hombro)
    r = (muneca - codo) / np.linalg.norm(muneca - codo)
    vaiven = math.atan2(float(h @ adelante), float(-(h @ arriba)))
    abre = math.atan2(float(h @ afuera), float(-(h @ arriba)))
    return adelante, arriba, afuera, h, r, vaiven, abre


def corregir_brazos(poses: list[dict], a: int, b: int, hombro: float, codo: float, abrir: float) -> dict:
    """Cambia el reparto del braceo (ver BRAZOS). Devuelve cuánto se movían hombro y codo antes y
    después, en grados de punta a punta, para revisarlo."""
    medidas = {}
    for lado in "lr":
        hum, rad, mano = f"{lado}humerus", f"{lado}radius", f"{lado}hand"
        vaiven0 = float(np.mean([_brazo(p, lado)[5] for p in poses[a:b]]))
        antes_v, antes_c, despues_v, despues_c = [], [], [], []
        for p in poses:
            adelante, arriba, afuera, h, r, vaiven, abre = _brazo(p, lado)
            v = vaiven0 + hombro * (vaiven - vaiven0)
            ab = abre * abrir
            hn = -math.cos(v) * math.cos(ab) * arriba + math.sin(v) * adelante + math.cos(v) * math.sin(ab) * afuera
            hn /= np.linalg.norm(hn)
            R = _de_a(h, hn)
            r1 = R @ r
            fl = math.acos(max(-1.0, min(1.0, float(hn @ r1))))
            fl_n = fl if fl < math.radians(6) else math.radians(6) + codo * (fl - math.radians(6))
            n = np.cross(hn, r1)
            Q = _rodrigues(n / np.linalg.norm(n), fl_n - fl) if np.linalg.norm(n) > 1e-6 else np.eye(3)
            p[hum] = (R @ p[hum][0], p[hum][1])
            p[rad] = (Q @ R @ p[rad][0], p[rad][1])
            p[mano] = (Q @ R @ p[mano][0], p[mano][1])
            antes_v.append(vaiven); antes_c.append(fl); despues_v.append(v); despues_c.append(fl_n)
        rango = lambda xs: round(math.degrees(max(xs) - min(xs)))          # noqa: E731
        medidas[lado] = dict(hombro=(rango(antes_v[a:b]), rango(despues_v[a:b])),
                             codo=(round(math.degrees(max(antes_c[a:b]))), round(math.degrees(max(despues_c[a:b])))))
    return medidas


def _ciclo(poses: list[dict]) -> tuple[int, int]:
    """Un ciclo de marcha completo (dos pasos): entre dos momentos en que el pie izquierdo está más
    adelante respecto de la cadera, medido en la dirección en que se camina."""
    raiz = np.array([p["root"][1] for p in poses])
    avance = raiz[-1] - raiz[0]
    avance[2] = 0.0
    avance /= np.linalg.norm(avance)
    pie = np.array([(p["ltibia"][1] - p["root"][1]) @ avance for p in poses])
    picos = [i for i in range(2, len(pie) - 2) if pie[i] == max(pie[i - 2:i + 3])]
    return picos[0], picos[1]


def aplicar(esqueleto, fps: int, cuadros: int, asf_nombre: str = "08.asf", amc_nombre: str = "08_01.amc",
            fps_grabacion: int = 120, brazos: dict | None = None) -> tuple[float, list[Vector]]:
    """Pone la caminata grabada en el esqueleto (cuadros 1..cuadros), repitiendo el ciclo de marcha
    y sumando el avance de cada vuelta. Devuelve hacia dónde camina (ángulo en grados sobre z, en
    los ejes del esqueleto), para girar el objeto hacia donde haga falta en la escena, y dónde va la
    cadera en cada cuadro (en los ejes del esqueleto), para que la cámara la siga."""
    asf = leer_asf(MOCAP / asf_nombre)
    poses = [cinematica(asf, c) for c in leer_amc(MOCAP / amc_nombre)]
    a, b = _ciclo(poses)
    corregir_brazos(poses, a, b, **(brazos or BRAZOS))      # brazos: otra corrección, p. ej. sin corregir
    paso_grab = fps_grabacion / fps
    largo_ciclo = (b - a) / paso_grab                       # en cuadros del video
    avance_ciclo = poses[b]["root"][1] - poses[a]["root"][1]
    avance_ciclo[2] = 0.0
    direccion = math.degrees(math.atan2(avance_ciclo[1], avance_ciclo[0]))

    huesos = esqueleto.data.bones
    pierna_mpfb = huesos["upperleg01.L"].head_local.z - huesos["foot.L"].head_local.z
    H = asf["huesos"]
    pierna_cmu = H["lfemur"]["largo"] + H["ltibia"]["largo"]
    k = pierna_mpfb / pierna_cmu
    # altura de la cadera sobre el piso: en la grabación, respecto del punto más bajo de los pies
    piso = min(min(p["ltoes"][1][2], p["rtoes"][1][2]) for p in poses)
    reposo = cinematica(asf, {"root": [0.0] * 6})
    cadera_reposo = -min(reposo["ltoes"][1][2], reposo["rtoes"][1][2])

    # alinear el reposo de cada hueso de MPFB con el del hueso grabado (solo dirección); la columna no
    alinear = {}
    for t, s in MAPA.items():
        if s == "root" or t not in huesos or t in COLUMNA:
            alinear[t] = Matrix.Identity(3)
            continue
        dir_t = (huesos[t].tail_local - huesos[t].head_local).normalized()
        dir_s = Vector(P @ H[s]["dir"]).normalized()
        alinear[t] = dir_t.rotation_difference(dir_s).to_matrix()

    dedos = _dedos_relajados(huesos)

    def profundidad(b_):
        n = 0
        while b_.parent:
            b_, n = b_.parent, n + 1
        return n
    en_orden = sorted(huesos, key=profundidad)
    previo: dict[str, Quaternion] = {}
    recorrido = []
    raiz_b = huesos["root"]
    for f in range(1, cuadros + 2):
        x = (f - 1) % largo_ciclo
        vuelta = int((f - 1) // largo_ciclo)
        g = a + x * paso_grab
        i0 = min(int(g), len(poses) - 2)
        pose = poses[min(int(round(g)), len(poses) - 1)]
        # cadera: posición grabada (interpolada), más el avance de las vueltas anteriores
        u = g - i0
        pos = (1 - u) * poses[i0]["root"][1] + u * poses[i0 + 1]["root"][1] + vuelta * avance_ciclo
        delta = pos - poses[a]["root"][1]
        delta[2] = (pos[2] - piso) - cadera_reposo
        delta *= k
        mundo: dict[str, Matrix] = {}
        for b_ in en_orden:
            B = b_.matrix_local.to_3x3()
            if b_.parent:
                Pr = b_.parent.matrix_local.to_3x3()
                Pp = mundo[b_.parent.name]
            else:
                Pr = Pp = Matrix.Identity(3)
            if b_.name in MAPA and MAPA[b_.name] in pose:
                M = Matrix(pose[MAPA[b_.name]][0].tolist()) @ alinear[b_.name] @ B
                L = B.transposed() @ Pr @ Pp.transposed() @ M
            else:
                L = dedos.get(b_.name, Matrix.Identity(3))
                M = Pp @ Pr.transposed() @ B @ L
            mundo[b_.name] = M
            pb = esqueleto.pose.bones[b_.name]
            q = L.to_quaternion()
            if b_.name in previo and q.dot(previo[b_.name]) < 0:      # sin saltos de signo entre cuadros
                q.negate()
            previo[b_.name] = q
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=f)
        pr = esqueleto.pose.bones["root"]
        pr.location = raiz_b.matrix_local.to_3x3().transposed() @ Vector(delta.tolist())
        pr.keyframe_insert("location", frame=f)
        recorrido.append(raiz_b.head_local + Vector(delta.tolist()))
    return direccion, recorrido
