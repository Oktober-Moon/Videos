"""Siluetas tipo recorte de papel y tinta, dibujadas con cairo.

Convenciones:
- Coordenadas de pantalla con y hacia abajo.
- Las figuras miran hacia +x; `espejo=True` las voltea.
- Cada función rellena con el color que ya tenga el contexto: una silueta es la unión de
  muchas piezas del mismo color sobre una capa propia, y luego la capa se compone completa.
- Personas históricas: siempre silueta, sin rasgos del rostro más allá del perfil.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cairo
import numpy as np

TAU = math.tau


# --------------------------------------------------------------------------- lienzo


def lienzo(w: int, h: int) -> tuple[cairo.ImageSurface, cairo.Context]:
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(w), int(h))
    c = cairo.Context(s)
    c.set_antialias(cairo.ANTIALIAS_GOOD)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    return s, c


def _datos(s: cairo.ImageSurface) -> np.ndarray:
    s.flush()
    h, w, st = s.get_height(), s.get_width(), s.get_stride()
    return np.ndarray((h, st // 4, 4), np.uint8, s.get_data())[:, :w]


def a_rgba(s: cairo.ImageSurface) -> np.ndarray:
    """Superficie cairo -> float32 RGBA premultiplicado."""
    return _datos(s)[..., [2, 1, 0, 3]].astype(np.float32) * (1.0 / 255.0)


def a_alfa(s: cairo.ImageSurface) -> np.ndarray:
    return _datos(s)[..., 3].astype(np.float32) * (1.0 / 255.0)


def tinta(c: cairo.Context, col, a: float = 1.0) -> None:
    c.set_source_rgba(float(col[0]), float(col[1]), float(col[2]), a)


# --------------------------------------------------------------------------- trazos básicos


def camino(c: cairo.Context, pts, cerrado: bool = True, tension: float = 1.0) -> None:
    """Curva Catmull-Rom que pasa por todos los puntos (convertida a Bézier)."""
    p = [np.asarray(q, float) for q in pts]
    n = len(p)
    if n < 2:
        return
    c.move_to(*p[0])
    tramos = n if cerrado else n - 1
    for i in range(tramos):
        p0 = p[i - 1] if (i > 0 or cerrado) else p[i]
        p1, p2 = p[i], p[(i + 1) % n]
        p3 = p[(i + 2) % n] if (i + 2 < n or cerrado) else p2
        c1 = p1 + (p2 - p0) / 6.0 * tension
        c2 = p2 - (p3 - p1) / 6.0 * tension
        c.curve_to(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    if cerrado:
        c.close_path()


def rellenar(c: cairo.Context, pts, suave_: bool = True, tension: float = 1.0) -> None:
    if suave_:
        camino(c, pts, True, tension)
    else:
        c.move_to(*pts[0])
        for q in pts[1:]:
            c.line_to(*q)
        c.close_path()
    c.fill()


def rugoso(pts, paso: float, amp: float, semilla: int, cerrado: bool = True,
           frecuencia: int = 6) -> np.ndarray:
    """Remuestrea un contorno y lo desplaza por su normal: borde de papel cortado a mano."""
    p = np.asarray(pts, float)
    if cerrado:
        p = np.vstack([p, p[:1]])
    seg = np.diff(p, axis=0)
    largos = np.hypot(seg[:, 0], seg[:, 1])
    acum = np.concatenate([[0], np.cumsum(largos)])
    total = acum[-1]
    n = max(8, int(total / paso))
    s = np.linspace(0, total, n, endpoint=not cerrado)
    x = np.interp(s, acum, p[:, 0])
    y = np.interp(s, acum, p[:, 1])
    dx = np.gradient(x)
    dy = np.gradient(y)
    nl = np.hypot(dx, dy) + 1e-9
    nx, ny = -dy / nl, dx / nl
    r = np.random.default_rng(semilla)
    k = max(2, n // frecuencia)
    gruesa = np.interp(np.arange(n), np.linspace(0, n - 1, k), r.uniform(-1, 1, k))
    fina = r.uniform(-1, 1, n) * 0.35
    d = (gruesa + fina) * amp
    return np.stack([x + nx * d, y + ny * d], axis=1)


def capsula(c: cairo.Context, p1, p2, r1: float, r2: float) -> None:
    """Segmento redondeado de grosor variable (miembros, postes, astas)."""
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    largo = math.hypot(dx, dy) or 1e-6
    nx, ny = -dy / largo, dx / largo
    c.move_to(x1 + nx * r1, y1 + ny * r1)
    c.line_to(x2 + nx * r2, y2 + ny * r2)
    c.line_to(x2 - nx * r2, y2 - ny * r2)
    c.line_to(x1 - nx * r1, y1 - ny * r1)
    c.close_path()
    c.fill()
    c.arc(x1, y1, r1, 0, TAU)
    c.fill()
    c.arc(x2, y2, r2, 0, TAU)
    c.fill()


def elipse(c: cairo.Context, x, y, rx, ry, ang: float = 0.0) -> None:
    c.save()
    c.translate(x, y)
    c.rotate(ang)
    c.scale(max(rx, 1e-6), max(ry, 1e-6))
    c.arc(0, 0, 1, 0, TAU)
    c.restore()
    c.fill()


def rot(v, ang):
    ca, sa = math.cos(ang), math.sin(ang)
    return np.array([v[0] * ca - v[1] * sa, v[0] * sa + v[1] * ca])


def dirv(ang_desde_abajo: float) -> np.ndarray:
    """Vector unitario a `ang` radianes de la vertical hacia abajo (+ hacia adelante = +x)."""
    return np.array([math.sin(ang_desde_abajo), math.cos(ang_desde_abajo)])


# --------------------------------------------------------------------------- armas y objetos


def lanza(c, base, ang: float, largo: float, grosor: float, punta: float = 0.11) -> np.ndarray:
    """Lanza desde `base` (extremo trasero) en dirección `ang` (radianes, 0 = +x). Devuelve la punta."""
    d = np.array([math.cos(ang), math.sin(ang)])
    n = np.array([-d[1], d[0]])
    b = np.asarray(base, float)
    cuello = b + d * largo * (1 - punta)
    extremo = b + d * largo
    capsula(c, b, cuello, grosor * 0.5, grosor * 0.5)
    hoja = largo * punta
    pts = [cuello - n * grosor * 0.6, cuello + d * hoja * 0.35 + n * grosor * 1.9, extremo,
           cuello + d * hoja * 0.35 - n * grosor * 1.9, cuello + n * grosor * 0.6]
    c.move_to(*pts[0])
    for q in pts[1:]:
        c.line_to(*q)
    c.close_path()
    c.fill()
    return extremo


def escudo_oval(c, cx, cy, w, h, ang: float = 0.0) -> None:
    elipse(c, cx, cy, w / 2, h / 2, ang)


def escudo_romano(c, cx, cy, w, h, ang: float = 0.0) -> None:
    """Escudo oblongo de esquinas redondeadas (scutum de la República tardía)."""
    c.save()
    c.translate(cx, cy)
    c.rotate(ang)
    r = w * 0.35
    x0, y0, x1, y1 = -w / 2, -h / 2, w / 2, h / 2
    c.move_to(x0 + r, y0)
    c.line_to(x1 - r, y0)
    c.arc(x1 - r, y0 + r, r, -math.pi / 2, 0)
    c.line_to(x1, y1 - r)
    c.arc(x1 - r, y1 - r, r, 0, math.pi / 2)
    c.line_to(x0 + r, y1)
    c.arc(x0 + r, y1 - r, r, math.pi / 2, math.pi)
    c.line_to(x0, y0 + r)
    c.arc(x0 + r, y0 + r, r, math.pi, 1.5 * math.pi)
    c.close_path()
    c.restore()
    c.fill()


def carnyx(c, base, alto: float, ang: float = 0.0) -> None:
    """Trompeta de guerra celta: tubo largo con cabeza de jabalí en lo alto."""
    b = np.asarray(base, float)
    d = np.array([math.sin(ang), -math.cos(ang)])
    n = np.array([-d[1], d[0]])
    tope = b + d * alto
    capsula(c, b, tope, alto * 0.012, alto * 0.016)
    s = alto * 0.09
    cabeza = [tope + n * s * 0.2, tope + d * s * 0.9 + n * s * 0.6, tope + d * s * 1.4 + n * s * 1.6,
              tope + d * s * 1.05 + n * s * 2.1, tope + d * s * 0.5 + n * s * 1.5,
              tope + d * s * 0.2 + n * s * 2.0, tope - d * s * 0.1 + n * s * 1.2,
              tope - d * s * 0.3 - n * s * 0.3]
    rellenar(c, cabeza, suave_=False)
    # cresta de la cabeza de jabalí
    for k in range(4):
        q = tope + d * s * (0.3 + 0.25 * k) - n * s * 0.1
        c.move_to(*q)
        c.line_to(*(q - n * s * 0.45 + d * s * 0.15))
        c.line_to(*(q + d * s * 0.22))
        c.close_path()
        c.fill()


def estandarte(c, base, alto: float, t: float, ancho: float = 0.35, semilla: int = 0):
    """Asta con travesaño y paño colgante que ondea. Devuelve el contorno del paño (para teñirlo)."""
    b = np.asarray(base, float)
    tope = b + np.array([0, -alto])
    capsula(c, b, tope, alto * 0.012, alto * 0.010)
    travesano_y = tope[1] + alto * 0.08
    a = alto * ancho
    capsula(c, (tope[0] - a / 2, travesano_y), (tope[0] + a / 2, travesano_y), alto * 0.008, alto * 0.008)
    pano = []
    largo = alto * 0.42
    for k in range(11):
        u = k / 10
        x = tope[0] - a / 2 + a * u
        onda = math.sin(t * 2.1 + u * 4 + semilla) * alto * 0.012
        pano.append((x + onda * 0.5, travesano_y))
    for k in range(10, -1, -1):
        u = k / 10
        x = tope[0] - a / 2 + a * u
        fleco = (0.04 if k % 2 else 0.0) * alto
        onda = math.sin(t * 2.3 + u * 5 + 1.7 + semilla) * alto * 0.035
        pano.append((x + onda, travesano_y + largo + fleco + onda * 0.4))
    return pano


def vela(c, x, y_base, ancho, alto) -> tuple[float, float]:
    """Cuerpo de la vela con cera derretida; devuelve la posición de la mecha."""
    c.rectangle(x - ancho / 2, y_base - alto, ancho, alto)
    c.fill()
    elipse(c, x, y_base - alto, ancho / 2, ancho * 0.16)
    gotas = [(-0.35, 0.18), (0.3, 0.32)]
    for gx, gl in gotas:
        capsula(c, (x + gx * ancho, y_base - alto), (x + gx * ancho, y_base - alto + gl * alto),
                ancho * 0.09, ancho * 0.07)
    mecha = (x, y_base - alto - ancho * 0.35)
    capsula(c, (x, y_base - alto), mecha, ancho * 0.03, ancho * 0.03)
    return mecha


# --------------------------------------------------------------------------- figura humana


@dataclass
class Pose:
    torso: float = 0.0        # grados; + se inclina hacia adelante
    cabeza: float = 0.0       # grados; + levanta la vista, - la baja
    hombro_c: float = 8.0     # brazo cercano: grados desde la vertical (+ adelante, 180 = arriba)
    codo_c: float = 12.0      # flexión del codo (+ el antebrazo sube hacia adelante)
    hombro_l: float = -8.0    # brazo lejano
    codo_l: float = 12.0
    cadera_c: float = 4.0     # muslo cercano (+ adelante)
    rodilla_c: float = 2.0    # flexión de rodilla (+ la pantorrilla va hacia atrás)
    cadera_l: float = -4.0
    rodilla_l: float = 2.0

    def mezcla(self, otra: "Pose", x: float) -> "Pose":
        vals = {k: getattr(self, k) + (getattr(otra, k) - getattr(self, k)) * x for k in self.__dataclass_fields__}
        return Pose(**vals)


@dataclass
class Atavio:
    vista: str = "perfil"     # "perfil" | "frente"
    pelo: str = "corto"       # "corto" | "largo" | "erizado" | "casco" | "calvo"
    bigote: bool = False
    capa: float = 0.0         # 0 sin capa; 1 hasta las pantorrillas
    viento: float = 0.0       # empuja capa y pelo hacia atrás
    tunica: float = 0.0       # faldón: 0 nada, 1 hasta la rodilla
    corpulencia: float = 1.0
    cresta: bool = False


def esqueleto(p: Pose, a: Atavio) -> dict[str, np.ndarray]:
    """Articulaciones en unidades de figura (altura 1, pies en y≈0, mirando a +x)."""
    rad = math.radians
    frente = a.vista == "frente"
    P = np.array([0.0, -0.50])
    t = rad(p.torso)
    u = np.array([math.sin(t), -math.cos(t)])
    n = np.array([math.cos(t), math.sin(t)])
    N = P + u * 0.31
    S = P + u * 0.275
    j: dict[str, np.ndarray] = {"P": P, "N": N, "S": S, "u": u, "n": n}
    lat_h = 0.115 * a.corpulencia if frente else 0.0
    lat_c = 0.05 if frente else 0.0
    for lado, signo in (("c", 1), ("l", -1)):
        hombro = S + np.array([signo * lat_h, 0.0]) if frente else S + n * 0.005 * signo
        ua = rad(getattr(p, f"hombro_{lado}"))
        if frente:
            ua *= signo
        codo = hombro + dirv(ua) * 0.16
        fa = ua + rad(getattr(p, f"codo_{lado}")) * (signo if frente else 1)
        muneca = codo + dirv(fa) * 0.14
        mano = muneca + dirv(fa) * 0.05
        cadera = P + np.array([signo * lat_c, 0.0])
        ta = rad(getattr(p, f"cadera_{lado}"))
        if frente:
            ta *= signo
        rodilla = cadera + dirv(ta) * 0.245
        sa = ta - rad(getattr(p, f"rodilla_{lado}")) * (signo if frente else 1)
        tobillo = rodilla + dirv(sa) * 0.235
        j.update({f"hombro_{lado}": hombro, f"codo_{lado}": codo, f"muneca_{lado}": muneca,
                  f"mano_{lado}": mano, f"cadera_{lado}": cadera, f"rodilla_{lado}": rodilla,
                  f"tobillo_{lado}": tobillo, f"ang_mano_{lado}": np.array([fa, 0.0])})
    cab = rad(p.cabeza)
    th = t * 0.5 - cab * 0.25
    j["cabeza"] = N + np.array([math.sin(th), -math.cos(th)]) * 0.075
    j["mirada"] = np.array([t * 0.4 - cab, 0.0])
    return j


def figura(c: cairo.Context, x: float, y: float, altura: float, pose: Pose, atavio: Atavio,
           espejo: bool = False, apoyar: bool = True) -> dict[str, np.ndarray]:
    """Dibuja una persona en silueta con los pies en (x, y). Devuelve articulaciones en pantalla."""
    j = esqueleto(pose, atavio)
    dy = 0.0
    if apoyar:
        dy = -max(j["tobillo_c"][1], j["tobillo_l"][1]) - 0.025
    sx = -1.0 if espejo else 1.0
    c.save()
    c.translate(x, y + dy * altura)
    c.scale(sx * altura, altura)
    _cuerpo(c, j, atavio)
    c.restore()
    salida = {}
    for k, v in j.items():
        if k in ("u", "n") or k.startswith("ang_") or k == "mirada":
            salida[k] = v
        else:
            salida[k] = np.array([x + sx * v[0] * altura, y + (v[1] + dy) * altura])
    salida["escala"] = np.array([altura, sx])
    return salida


def _cuerpo(c: cairo.Context, j: dict, a: Atavio) -> None:
    frente = a.vista == "frente"
    k = a.corpulencia
    P, N, S, u, n = j["P"], j["N"], j["S"], j["u"], j["n"]
    # capa por detrás de todo
    if a.capa > 0:
        _capa(c, j, a)
    # pelo largo por detrás de la cabeza
    if a.pelo == "largo":
        _pelo_largo(c, j, a)
    # piernas y brazos lejanos
    for lado in ("l", "c"):
        _pierna(c, j, lado, k)
    _brazo(c, j, "l", k)
    # torso
    if frente:
        pts = [N + np.array([0.035, 0.0]), S + np.array([0.12 * k, 0.0]) - u * 0.01,
               S + np.array([0.105 * k, 0.08]), P + u * 0.12 + np.array([0.085 * k, 0]),
               P + np.array([0.095 * k, 0.0]), P + np.array([0.0, 0.05]),
               P + np.array([-0.095 * k, 0.0]), P + u * 0.12 + np.array([-0.085 * k, 0]),
               S + np.array([-0.105 * k, 0.08]), S + np.array([-0.12 * k, 0.0]) - u * 0.01,
               N + np.array([-0.035, 0.0])]
    else:
        pts = [N + n * 0.025 + u * 0.02, N + n * 0.045 - u * 0.012, S + n * 0.072 * k - u * 0.035,
               P + u * 0.14 + n * 0.066 * k, P + n * 0.062 * k + u * 0.02, P - u * 0.04,
               P - n * 0.075 * k, P + u * 0.12 - n * 0.058 * k, S - n * 0.07 * k - u * 0.06,
               N - n * 0.066 * k - u * 0.015, N - n * 0.03 + u * 0.02]
    rellenar(c, pts)
    if a.tunica > 0:
        _tunica(c, j, a)
    # cuello y cabeza
    capsula(c, N - u * 0.01, j["cabeza"], 0.03, 0.028)
    _cabeza(c, j, a)
    _brazo(c, j, "c", k)


def _pierna(c, j, lado, k):
    cad, rod, tob = j[f"cadera_{lado}"], j[f"rodilla_{lado}"], j[f"tobillo_{lado}"]
    capsula(c, cad, rod, 0.052 * k, 0.036)
    capsula(c, rod, tob, 0.035, 0.022)
    punta = tob + np.array([0.075, 0.012])
    capsula(c, tob + np.array([-0.012, 0.004]), punta, 0.024, 0.012)


def _brazo(c, j, lado, k):
    h, co, mu, ma = j[f"hombro_{lado}"], j[f"codo_{lado}"], j[f"muneca_{lado}"], j[f"mano_{lado}"]
    capsula(c, h, co, 0.034 * k, 0.026)
    capsula(c, co, mu, 0.026, 0.019)
    capsula(c, mu, ma, 0.021, 0.017)


def _cabeza(c, j, a):
    hc = j["cabeza"]
    phi = float(j["mirada"][0])
    f = np.array([math.cos(phi), math.sin(phi)])
    d = np.array([-math.sin(phi), math.cos(phi)])
    if a.vista == "frente":
        elipse(c, hc[0], hc[1], 0.054, 0.066, 0)
    else:
        elipse(c, hc[0], hc[1], 0.056, 0.064, phi)
        # perfil: nariz y mentón apenas sugeridos
        nariz = [hc + f * 0.045 - d * 0.012, hc + f * 0.071 + d * 0.012, hc + f * 0.048 + d * 0.022]
        rellenar(c, nariz, suave_=False)
        menton = [hc + f * 0.02 + d * 0.04, hc + f * 0.05 + d * 0.052, hc + f * 0.035 + d * 0.068,
                  hc - f * 0.01 + d * 0.06]
        rellenar(c, menton)
        if a.bigote:
            rellenar(c, [hc + f * 0.05 + d * 0.026, hc + f * 0.066 + d * 0.052,
                         hc + f * 0.058 + d * 0.072, hc + f * 0.038 + d * 0.04], suave_=False)
    if a.pelo == "erizado":
        for i in range(7):
            ang = math.radians(-150 + i * 22) + phi * 0.4
            v = np.array([math.cos(ang), math.sin(ang)])
            base = hc + v * 0.05
            w = np.array([-v[1], v[0]]) * 0.016
            rellenar(c, [base + w, hc + v * (0.105 + 0.012 * (i % 2)), base - w], suave_=False)
    elif a.pelo == "casco":
        elipse(c, hc[0] - 0.004, hc[1] - 0.012, 0.064, 0.06, phi)
        tope = hc - d * 0.072 - f * 0.004
        capsula(c, hc - d * 0.055, tope, 0.008, 0.012)
        rellenar(c, [hc - f * 0.055 - d * 0.0, hc - f * 0.09 + d * 0.035, hc - f * 0.04 + d * 0.03],
                 suave_=False)
        if a.cresta:
            rellenar(c, [tope - f * 0.01, tope - d * 0.03 + f * 0.02, tope - d * 0.04 - f * 0.05,
                         tope - d * 0.02 - f * 0.11, hc - f * 0.08 - d * 0.04])
    elif a.pelo == "largo":
        elipse(c, hc[0] - 0.006, hc[1] - 0.01, 0.06, 0.06, phi)


def _pelo_largo(c, j, a):
    hc, N = j["cabeza"], j["N"]
    v = a.viento
    pts = [hc + np.array([0.01, -0.07]), hc + np.array([-0.06, -0.045]),
           hc + np.array([-0.085 - v * 0.04, 0.03]), N + np.array([-0.075 - v * 0.08, 0.075]),
           N + np.array([-0.05 - v * 0.05, 0.11]), N + np.array([-0.035, 0.06]),
           N + np.array([-0.005, 0.02]), hc + np.array([0.0, 0.02])]
    rellenar(c, pts)


def _capa(c, j, a):
    P, N, S, u, n = j["P"], j["N"], j["S"], j["u"], j["n"]
    v = a.viento
    largo = 0.30 * a.capa
    if a.vista == "frente":
        pts = [N + np.array([-0.1, 0.0]), N + np.array([0.1, 0.0]),
               P + np.array([0.17 + v * 0.05, largo]), P + np.array([0.08, largo + 0.02]),
               P + np.array([0.0, largo - 0.01]), P + np.array([-0.08, largo + 0.03]),
               P + np.array([-0.17 - v * 0.08, largo])]
        rellenar(c, pts)
        return
    pts = [N + n * 0.05, N - n * 0.075, S - n * 0.13 - u * 0.04 + np.array([-v * 0.06, 0]),
           P - n * 0.16 + np.array([-v * 0.22, -v * 0.02]),
           P + np.array([-0.2 - v * 0.38, largo - v * 0.12]),
           P + np.array([-0.13 - v * 0.30, largo + 0.02 - v * 0.08]),
           P + np.array([-0.07 - v * 0.2, largo - 0.01 - v * 0.04]),
           P + np.array([-0.01, largo + 0.01]), P + n * 0.03, S + n * 0.03]
    rellenar(c, pts)


def _tunica(c, j, a):
    P, u, n = j["P"], j["u"], j["n"]
    hem = 0.24 * a.tunica
    rods = [j["rodilla_c"], j["rodilla_l"]]
    xs = [r[0] for r in rods]
    izq = min(xs + [P[0] - 0.09]) - 0.04
    der = max(xs + [P[0] + 0.08]) + 0.04
    pts = [P + u * 0.10 - n * 0.075, P + u * 0.10 + n * 0.07, np.array([der, P[1] + hem]),
           np.array([(izq + der) / 2, P[1] + hem + 0.015]), np.array([izq, P[1] + hem])]
    rellenar(c, pts, suave_=False)


# --------------------------------------------------------------------------- caballo


@dataclass
class _Pata:
    base: tuple[float, float]
    largos: tuple[float, float, float]
    quieta: tuple[float, float, float]   # ángulo absoluto del segmento 1 y relativos de 2 y 3 (grados)
    grosor: tuple[float, float, float]
    fase: float
    delantera: bool


_PATAS = {
    "tl": _Pata((-0.33, 0.36), (0.30, 0.24, 0.085), (-22, 24, 24), (0.085, 0.045, 0.036), 0.00, False),
    "tc": _Pata((-0.30, 0.37), (0.30, 0.24, 0.085), (-22, 24, 24), (0.085, 0.045, 0.036), 0.10, False),
    "dl": _Pata((0.36, 0.42), (0.27, 0.19, 0.085), (0, 0, 26), (0.068, 0.038, 0.032), 0.40, True),
    "dc": _Pata((0.39, 0.42), (0.27, 0.19, 0.085), (0, 0, 26), (0.068, 0.038, 0.032), 0.50, True),
}


def _angulos_galope(pata: _Pata, fase: float) -> tuple[float, float, float]:
    phi = (fase - pata.fase) % 1.0
    apoyo = 0.40
    if pata.delantera:
        adelante, atras, pliegue1, pliegue2 = 34.0, -38.0, -105.0, -40.0
    else:
        adelante, atras, pliegue1, pliegue2 = 22.0, -48.0, -55.0, -35.0
    if phi < apoyo:
        x = phi / apoyo
        a1 = adelante + (atras - adelante) * x
        s = 0.0
        extra = 22 * math.sin(math.pi * x)       # el menudillo cede al cargar peso
    else:
        x = (phi - apoyo) / (1 - apoyo)
        # la pata se recoge pronto y se estira al final para buscar el suelo
        a1 = atras + (adelante + 12 - atras) * (0.5 - 0.5 * math.cos(math.pi * min(1.0, x * 1.1)))
        s = math.sin(math.pi * min(1.0, x * 1.25)) if x < 0.8 else max(0.0, 1 - (x - 0.8) / 0.2) * 0.59
        extra = 0.0
    return a1, pata.quieta[1] + pliegue1 * s, pata.quieta[2] + pliegue2 * s + extra


def caballo(c: cairo.Context, x: float, y: float, escala: float, *, fase: float | None = None,
            t: float = 0.0, cuello: float = 0.0, viento: float = 0.6, espejo: bool = False,
            cabriola: float = 0.0) -> dict[str, np.ndarray]:
    """Caballo de perfil con los cascos en y. `escala` = largo del cuerpo en px.

    fase: None = de pie; 0..1 = punto del ciclo de galope. cabriola: 0..1 levanta las manos.
    Devuelve puntos útiles en pantalla (montura, cabeza, cola, cruz).
    """
    sx = -1.0 if espejo else 1.0
    galope = fase is not None
    f = fase or 0.0
    bote = 0.035 * math.cos(TAU * (f - 0.15)) if galope else 0.0
    cabeceo = math.radians(3.5 * math.sin(TAU * f)) if galope else 0.0
    cabeceo -= math.radians(26) * cabriola
    c.save()
    c.translate(x, y)
    c.scale(sx * escala, escala)
    c.translate(0, -0.97 + bote - 0.10 * cabriola)
    c.translate(-0.25, 0.35)
    c.rotate(cabeceo)
    c.translate(0.25, -0.35)
    for nombre in ("tl", "dl"):
        _pata(c, _PATAS[nombre], f if galope else None, cabriola)
    cuerpo = [(0.28, -0.07), (0.05, 0.0), (-0.18, -0.01), (-0.36, -0.045), (-0.49, 0.02),
              (-0.555, 0.14), (-0.53, 0.30), (-0.45, 0.45), (-0.30, 0.47), (-0.22, 0.42),
              (-0.05, 0.43), (0.12, 0.45), (0.30, 0.47), (0.43, 0.47), (0.50, 0.38),
              (0.54, 0.24), (0.54, 0.11), (0.48, 0.0)]
    rellenar(c, cuerpo)
    ang_cuello = math.radians(cuello) + (math.radians(6 * math.sin(TAU * (f + 0.3))) if galope else 0.0)
    ang_cuello += math.radians(12) * cabriola
    c.save()
    c.translate(0.42, 0.10)
    c.rotate(-ang_cuello)
    c.translate(-0.42, -0.10)
    cuello_pts = [(0.20, -0.04), (0.34, -0.19), (0.49, -0.35), (0.62, -0.47), (0.70, -0.47),
                  (0.75, -0.31), (0.66, -0.14), (0.58, 0.04), (0.50, 0.14), (0.38, 0.10)]
    rellenar(c, cuello_pts)
    cabeza = [(0.615, -0.49), (0.70, -0.52), (0.78, -0.45), (0.88, -0.34), (0.96, -0.24),
              (0.975, -0.185), (0.94, -0.15), (0.87, -0.155), (0.80, -0.20), (0.73, -0.25),
              (0.69, -0.33)]
    rellenar(c, cabeza)
    for ox in (0.0, 0.03):
        rellenar(c, [(0.63 + ox, -0.50), (0.625 + ox, -0.60), (0.665 + ox, -0.51)], suave_=False)
    # crin: el borde interior queda dentro del cuello para que no haya rendija
    crin = []
    for k in range(10):
        u_ = k / 9
        crin.append((0.64 - 0.42 * u_ + 0.03, -0.46 + 0.42 * u_ + 0.03))
    for k in range(9, -1, -1):
        u_ = k / 9
        ondea = viento * 0.05 * (0.6 + 0.4 * math.sin(t * 9 + k * 1.3))
        crin.append((0.64 - 0.42 * u_ - 0.035 - ondea, -0.46 + 0.42 * u_ - 0.02 + (0.03 if k % 2 else 0.0)))
    rellenar(c, crin)
    punto_cabeza = (0.82, -0.36)
    c.restore()
    ondula = math.sin(t * 7.0) * 0.04 * viento
    cola = [(-0.47, 0.0), (-0.62 - 0.2 * viento, 0.06 + ondula), (-0.80 - 0.25 * viento, 0.22 + ondula * 2),
            (-0.78 - 0.25 * viento, 0.32 + ondula), (-0.64 - 0.12 * viento, 0.28),
            (-0.56, 0.18), (-0.51, 0.08)]
    rellenar(c, cola)
    for nombre in ("tc", "dc"):
        _pata(c, _PATAS[nombre], f if galope else None, cabriola)
    m = c.get_matrix()
    c.restore()

    def a_pantalla(px, py):
        # a coordenadas del llamador (por si dibujó con una cámara aplicada)
        return np.array(c.device_to_user(*m.transform_point(px, py)))

    return {"montura": a_pantalla(0.02, -0.03), "cabeza": a_pantalla(*punto_cabeza),
            "cola": a_pantalla(-0.5, 0.05), "cruz": a_pantalla(0.28, -0.07)}


def _pata(c, pata: _Pata, fase: float | None, cabriola: float) -> None:
    if fase is None:
        a1, a2, a3 = pata.quieta
        if pata.delantera and cabriola > 0:
            a1 += 75 * cabriola
            a2 += -105 * cabriola
            a3 += -30 * cabriola
    else:
        a1, a2, a3 = _angulos_galope(pata, fase)
    r = math.radians
    p0 = np.array(pata.base)
    g1 = r(a1)
    p1 = p0 + dirv(g1) * pata.largos[0]
    g2 = g1 + r(a2)
    p2 = p1 + dirv(g2) * pata.largos[1]
    g3 = g2 + r(a3)
    p3 = p2 + dirv(g3) * pata.largos[2]
    capsula(c, p0 + dirv(g1) * -0.04, p1, pata.grosor[0], pata.grosor[1])
    capsula(c, p1, p2, pata.grosor[1] * 0.85, pata.grosor[2])
    capsula(c, p2, p3, pata.grosor[2], pata.grosor[2] * 0.85)
    d = dirv(g3)
    nrm = np.array([-d[1], d[0]])
    casco = [p3 - nrm * 0.032, p3 + d * 0.045 - nrm * 0.036, p3 + d * 0.05 + nrm * 0.034, p3 + nrm * 0.03]
    rellenar(c, casco, suave_=False)


# --------------------------------------------------------------------------- arquitectura y paisaje


def empalizada(c, x0: float, x1: float, y_base: float, alto: float, semilla: int = 0,
               ancho_estaca: float | None = None, travesano: bool = True) -> None:
    """Estacas afiladas de un campamento romano (sudes) sobre un terraplén."""
    r = np.random.default_rng(semilla)
    w = ancho_estaca or alto * 0.11
    x = x0
    while x < x1:
        h = alto * r.uniform(0.9, 1.06)
        inc = r.uniform(-0.03, 0.03)
        ww = w * r.uniform(0.85, 1.1)
        top = y_base - h
        pts = [(x, y_base), (x + inc * h, top + ww * 0.9), (x + ww / 2 + inc * h, top),
               (x + ww + inc * h, top + ww * 0.9), (x + ww, y_base)]
        rellenar(c, pts, suave_=False)
        x += ww * r.uniform(0.93, 1.02)
    if travesano:
        for f in (0.32, 0.62):
            c.rectangle(x0, y_base - alto * f, x1 - x0, alto * 0.05)
            c.fill()


def terraplen(c, x0, x1, y_top, y_bot, semilla: int = 0, rugosidad: float = 6.0) -> None:
    pts = [(x0, y_bot), (x0, y_top)]
    r = np.random.default_rng(semilla)
    n = max(6, int((x1 - x0) / 60))
    for k in range(1, n):
        pts.append((x0 + (x1 - x0) * k / n, y_top + r.uniform(-1, 1) * rugosidad))
    pts += [(x1, y_top), (x1, y_bot)]
    rellenar(c, pts, suave_=False)


def torre_madera(c, x: float, y_base: float, ancho: float, alto: float, semilla: int = 0,
                 tejado: bool = False, progreso: float = 1.0, tablas: bool = True) -> dict:
    """Torre de vigilancia de madera: postes, riostras en X, plataforma y parapeto de tablas.

    `progreso` (0..1) la construye de abajo hacia arriba (torres que se levantan).
    Devuelve puntos útiles: tope del parapeto y centro de la plataforma.
    """
    r = np.random.default_rng(semilla)
    g = ancho * 0.07
    alto_vis = alto * progreso
    y_top = y_base - alto
    plataforma = y_base - alto * 0.80
    xl, xr = x - ancho / 2, x + ancho / 2
    c.save()
    c.rectangle(xl - ancho, y_base - alto_vis - ancho * 0.2, ancho * 3, alto_vis + ancho * 0.4)
    c.clip()
    # postes ligeramente inclinados hacia adentro
    capsula(c, (xl, y_base), (xl + ancho * 0.06, y_top + alto * 0.04), g, g * 0.85)
    capsula(c, (xr, y_base), (xr - ancho * 0.06, y_top + alto * 0.04), g, g * 0.85)
    niveles = 4
    for k in range(niveles):
        ya = y_base - (plataforma - y_base) * -k / niveles
        yb = y_base - (plataforma - y_base) * -(k + 1) / niveles
        ia = ancho * 0.06 * (y_base - ya) / alto
        ib = ancho * 0.06 * (y_base - yb) / alto
        capsula(c, (xl + ia, ya), (xr - ia, ya), g * 0.55, g * 0.55)
        capsula(c, (xl + ia, ya), (xr - ib, yb), g * 0.4, g * 0.4)
        capsula(c, (xr - ia, ya), (xl + ib, yb), g * 0.4, g * 0.4)
    ip = ancho * 0.06 * (y_base - plataforma) / alto
    capsula(c, (xl + ip - ancho * 0.1, plataforma), (xr - ip + ancho * 0.1, plataforma), g * 0.8, g * 0.8)
    # parapeto de tablas verticales con rendijas
    px0, px1 = xl + ip - ancho * 0.1, xr - ip + ancho * 0.1
    tope_parapeto = plataforma - alto * 0.13
    if tablas:
        xx = px0
        while xx < px1 - 1:
            wt = ancho * r.uniform(0.09, 0.13)
            ht = r.uniform(-0.01, 0.012) * alto
            c.rectangle(xx, tope_parapeto + ht, min(wt * 0.9, px1 - xx), plataforma - tope_parapeto - ht)
            c.fill()
            xx += wt
    else:
        c.rectangle(px0, tope_parapeto, px1 - px0, plataforma - tope_parapeto)
        c.fill()
    # postes que asoman sobre el parapeto
    capsula(c, (px0 + g, plataforma), (px0 + g, tope_parapeto - alto * 0.05), g * 0.8, g * 0.7)
    capsula(c, (px1 - g, plataforma), (px1 - g, tope_parapeto - alto * 0.05), g * 0.8, g * 0.7)
    if tejado:
        rellenar(c, [(px0 - ancho * 0.12, tope_parapeto - alto * 0.05), (x, y_top - alto * 0.12),
                     (px1 + ancho * 0.12, tope_parapeto - alto * 0.05)], suave_=False)
    c.restore()
    return {"tope": np.array([x, tope_parapeto]), "plataforma": np.array([x, plataforma]),
            "esquina_izq": np.array([px0, tope_parapeto]), "esquina_der": np.array([px1, tope_parapeto])}


def tienda(c, x: float, y_base: float, ancho: float, alto: float, frente: bool = False) -> None:
    """Tienda romana de cuero (papilio): paredes bajas y techo a dos aguas."""
    pared = alto * 0.35
    if frente:
        rellenar(c, [(x - ancho / 2, y_base), (x - ancho / 2, y_base - pared), (x, y_base - alto),
                     (x + ancho / 2, y_base - pared), (x + ancho / 2, y_base)], suave_=False)
    else:
        sesgo = ancho * 0.12
        rellenar(c, [(x - ancho / 2, y_base), (x - ancho / 2, y_base - pared),
                     (x - ancho / 2 + sesgo, y_base - alto), (x + ancho / 2 - sesgo, y_base - alto),
                     (x + ancho / 2, y_base - pared), (x + ancho / 2, y_base)], suave_=False)


def arbol_desnudo(c, x: float, y: float, alto: float, semilla: int = 0, niveles: int = 6,
                  apertura: float = 0.5, inclinacion: float = 0.0) -> None:
    """Árbol sin hojas, ramificación recursiva con grosor decreciente (invierno en las Ardenas)."""
    r = np.random.default_rng(semilla)

    def rama(p, ang, largo, grosor, nivel):
        q = p + np.array([math.sin(ang), -math.cos(ang)]) * largo
        capsula(c, p, q, grosor, grosor * 0.68)
        if nivel <= 0 or grosor < 0.4:
            return
        hijos = 2 if r.random() < 0.75 else 3
        for i in range(hijos):
            desvio = (i - (hijos - 1) / 2) * apertura * r.uniform(0.6, 1.3) + r.uniform(-0.15, 0.15)
            rama(q, ang + desvio, largo * r.uniform(0.62, 0.8), grosor * 0.68, nivel - 1)

    rama(np.array([x, y]), inclinacion, alto * 0.32, alto * 0.025, niveles)


def contorno_colina(x0, x1, y_base, puntos_altura, semilla=0, amp=0.0):
    """Contorno de colina: lista de (x relativo 0..1, altura px) -> polígono cerrado hasta y_base."""
    pts = [(x0 + (x1 - x0) * u, y_base - hgt) for u, hgt in puntos_altura]
    return [(x0, y_base + 4000)] + pts + [(x1, y_base + 4000)]


def llama_contorno(x, y, alto, ancho, t, semilla=0):
    """Contorno de una llama (punta arriba) que se agita con el tiempo."""
    r = np.random.default_rng(semilla)
    fase = r.uniform(0, TAU, 4)
    punta_x = x + math.sin(t * 7.3 + fase[2]) * ancho * 0.35 + math.sin(t * 17 + fase[3]) * ancho * 0.1
    altura = alto * (0.85 + 0.15 * math.sin(t * 11 + fase[0]) + 0.08 * math.sin(t * 23 + fase[1]))
    return [(x - ancho * 0.5, y), (x - ancho * 0.42, y - altura * 0.35),
            (punta_x - ancho * 0.12, y - altura * 0.8), (punta_x, y - altura),
            (punta_x + ancho * 0.14, y - altura * 0.78), (x + ancho * 0.44, y - altura * 0.33),
            (x + ancho * 0.5, y), (x, y + ancho * 0.18)]


def a_pil(s: cairo.ImageSurface):
    """Superficie cairo -> imagen Pillow 'RGBa' sin pasar por flotantes (capas muy grandes)."""
    from PIL import Image

    d = _datos(s)
    rgba = np.ascontiguousarray(d[..., [2, 1, 0, 3]])
    return Image.frombytes("RGBa", (rgba.shape[1], rgba.shape[0]), rgba.tobytes())
