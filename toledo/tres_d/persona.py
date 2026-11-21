"""Personas en 3D con MPFB (generador de la comunidad MakeHuman, recursos CC0).

Solo para figuras a distancia media o de espaldas: de cerca, las caras se ven artificiales. Las
víctimas nunca se hacen como personajes 3D (véase direccion_visual.md).

Requiere la extensión MPFB instalada en Blender y el paquete «MakeHuman system assets» en su carpeta
de datos (recursos_3d/mpfb/ guarda los archivos descargados).
"""

import math

import bpy
from mathutils import Quaternion, Vector


def _mpfb():
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    return HumanService


def crear_persona(nombre="peaton", *, hombre=True, edad=0.6, musculo=0.55, peso=0.55, estatura=0.55,
                  piel="middleage_caucasian_male.mhmat", ropa=("male_casualsuit05.mhclo", "shoes06.mhclo"),
                  pelo="short02.mhclo", cejas="eyebrow001.mhclo", pestanas="eyelashes01.mhclo"):
    """Crea una persona vestida, con esqueleto. Devuelve (cuerpo, esqueleto)."""
    HumanService = _mpfb()
    info = HumanService._create_default_human_info_dict()
    info["name"] = nombre
    info["phenotype"].update({"gender": 1.0 if hombre else 0.0, "age": edad, "muscle": musculo, "weight": peso,
                              "height": estatura})
    info["phenotype"]["race"] = {"caucasian": 0.9, "african": 0.05, "asian": 0.05}
    info["rig"] = "default"
    info["eyes"] = "high-poly.mhclo"
    info["eyebrows"] = cejas
    info["eyelashes"] = pestanas
    info["teeth"] = "teeth_base.mhclo"
    info["tongue"] = "tongue01.mhclo"
    info["hair"] = pelo
    info["clothes"] = list(ropa)
    info["skin_mhmat"] = piel
    info["skin_material_type"] = "ENHANCED_SSS"
    info["eyes_material_type"] = "PROCEDURAL_EYES"
    ajustes = HumanService.get_default_deserialization_settings()
    ajustes["subdiv_levels"] = 1
    ajustes["load_clothes"] = True
    cuerpo = HumanService.deserialize_from_dict(info, ajustes)
    esqueleto = cuerpo.parent if cuerpo.parent and cuerpo.parent.type == "ARMATURE" else None
    return cuerpo, esqueleto


def girar_hueso(esqueleto, hueso: str, eje, grados: float):
    """Rota un hueso alrededor de un eje dado en el espacio del esqueleto (no en el del hueso)."""
    pb = esqueleto.pose.bones.get(hueso)
    if pb is None:
        return False
    reposo = pb.bone.matrix_local.to_3x3()
    q_arm = Quaternion(Vector(eje).normalized(), math.radians(grados))
    q_local = (reposo.inverted() @ q_arm.to_matrix() @ reposo).to_quaternion()
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = q_local @ pb.rotation_quaternion
    return True


def posar_caminando(esqueleto, fase: float = 0.0):
    """Pose de un paso a medio camino (la persona mira hacia −y). fase 0: pie izquierdo adelante."""
    s = 1 if fase < 0.5 else -1
    X, Y = (1, 0, 0), (0, 1, 0)
    # brazos: de la pose en A hacia abajo, junto al cuerpo, y balanceo opuesto a las piernas
    girar_hueso(esqueleto, "upperarm01.L", Y, 38)        # de la pose en A (unos 48° abajo) a junto al cuerpo
    girar_hueso(esqueleto, "upperarm01.R", Y, -38)
    girar_hueso(esqueleto, "upperarm01.L", X, 14 * s)
    girar_hueso(esqueleto, "upperarm01.R", X, -14 * s)
    girar_hueso(esqueleto, "lowerarm01.L", X, -18)
    girar_hueso(esqueleto, "lowerarm01.R", X, -18)
    # piernas: una adelante, otra atrás con la rodilla doblada
    adelante, atras = ("L", "R") if s > 0 else ("R", "L")
    girar_hueso(esqueleto, f"upperleg01.{adelante}", X, -22)
    girar_hueso(esqueleto, f"lowerleg01.{adelante}", X, 6)
    girar_hueso(esqueleto, f"foot.{adelante}", X, -8)
    girar_hueso(esqueleto, f"upperleg01.{atras}", X, 14)
    girar_hueso(esqueleto, f"lowerleg01.{atras}", X, 28)
    girar_hueso(esqueleto, f"foot.{atras}", X, 12)
    girar_hueso(esqueleto, "spine01", X, -3)
    girar_hueso(esqueleto, "neck01", X, 4)
    bpy.context.view_layer.update()


def huesos(esqueleto):
    return [(b.name, tuple(round(v, 2) for v in b.head_local), tuple(round(v, 2) for v in b.tail_local))
            for b in esqueleto.data.bones]
