"""Utilidades de Blender para los planos 3D del video: nodos de material, geometría con bmesh,
luces, cámara y ajustes de render. Solo corre dentro de Blender (bpy).

Los nombres de ajustes cambian entre versiones de Blender; `poner` asigna solo si existe.
"""

import bmesh
import bpy
from mathutils import Matrix, Vector

COLECCION = None


def escena_nueva():
    """Vacía Blender y deja lista la escena; todo lo que se cree se enlaza a ella."""
    global COLECCION
    bpy.ops.wm.read_factory_settings(use_empty=True)
    escena = bpy.context.scene
    COLECCION = escena.collection
    return escena


def enlazar(ob):
    COLECCION.objects.link(ob)
    return ob


def poner(obj, attr, valor) -> bool:
    """Asigna si la versión de Blender tiene ese ajuste (los nombres cambian entre versiones)."""
    try:
        setattr(obj, attr, valor)
        return True
    except (AttributeError, TypeError, ValueError):
        return False


def entrada(nodo, *nombres):
    for n in nombres:
        if n in nodo.inputs:
            return nodo.inputs[n]
    raise KeyError(f"{nodo.name}: ninguna entrada {nombres}")


def es_socket(v) -> bool:
    return isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], bpy.types.Node)


class Arbol:
    """Atajos para armar árboles de nodos de material sin repetir links.new por todos lados."""

    def __init__(self, mat):
        poner(mat, "use_nodes", True)
        self.nt = mat.node_tree
        self.salida = next(n for n in self.nt.nodes if n.type == "OUTPUT_MATERIAL")
        for n in list(self.nt.nodes):
            if n.type == "BSDF_PRINCIPLED":
                self.nt.nodes.remove(n)

    def nodo(self, tipo, **props):
        n = self.nt.nodes.new(tipo)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def unir(self, origen, destino_nodo, destino):
        self.nt.links.new(origen[0].outputs[origen[1]], destino_nodo.inputs[destino])

    def dar(self, nodo, destino, v):
        if es_socket(v):
            self.unir(v, nodo, destino)
        elif v is not None:
            nodo.inputs[destino].default_value = v

    def m(self, op, a, b=None):
        n = self.nodo("ShaderNodeMath", operation=op)
        self.dar(n, 0, a)
        self.dar(n, 1, b)
        return (n, 0)

    def v(self, op, a, b=None, escala=None):
        n = self.nodo("ShaderNodeVectorMath", operation=op)
        self.dar(n, 0, a)
        self.dar(n, 1, b)
        if escala is not None:
            self.dar(n, "Scale", escala)
        return (n, 0)

    def mezcla(self, a, b, f):
        """a·(1−f) + b·f para colores o vectores."""
        return self.v("ADD", a, self.v("SCALE", self.v("SUBTRACT", b, a), escala=f))

    def rango(self, x, de0, de1, a0=0.0, a1=1.0):
        n = self.nodo("ShaderNodeMapRange")
        self.dar(n, 0, x)
        for i, val in enumerate((de0, de1, a0, a1), start=1):
            n.inputs[i].default_value = val
        return (n, 0)

    def separar(self, vec):
        n = self.nodo("ShaderNodeSeparateXYZ")
        self.unir(vec, n, 0)
        return (n, 0), (n, 1), (n, 2)

    def ruido(self, vec, escala, detalle=4.0, rugosidad=0.5):
        n = self.nodo("ShaderNodeTexNoise")
        if vec is not None:
            self.unir(vec, n, "Vector")
        entrada(n, "Scale").default_value = escala
        entrada(n, "Detail").default_value = detalle
        entrada(n, "Roughness").default_value = rugosidad
        return (n, "Fac"), (n, "Color")

    def bsdf(self, color, rug, metal=0.0, coat=0.0, emision=None, fuerza=0.0, normal=None, especular=None):
        b = self.nodo("ShaderNodeBsdfPrincipled")
        self.dar(b, "Base Color", color if es_socket(color) else (*color, 1.0))
        self.dar(b, "Roughness", rug)
        self.dar(b, "Metallic", metal)
        if coat:
            self.dar(b, entrada(b, "Coat Weight", "Clearcoat").name, coat)
        if emision is not None:
            sock = entrada(b, "Emission Color", "Emission").name
            self.dar(b, sock, emision if es_socket(emision) else (*emision, 1.0))
            self.dar(b, "Emission Strength", fuerza)
        if especular is not None:
            self.dar(b, entrada(b, "Specular IOR Level", "Specular").name, especular)
        if normal is not None:
            self.unir(normal, b, "Normal")
        return (b, 0)

    def mezclar_shader(self, a, b, f):
        n = self.nodo("ShaderNodeMixShader")
        self.dar(n, 0, f)
        self.unir(a, n, 1)
        self.unir(b, n, 2)
        return (n, 0)

    def bump(self, altura, fuerza, distancia):
        n = self.nodo("ShaderNodeBump")
        self.unir(altura, n, "Height")
        self.dar(n, "Strength", fuerza)
        self.dar(n, "Distance", distancia)
        return (n, "Normal")

    def final(self, shader, donde="Surface"):
        self.unir(shader, self.salida, donde)


def pos_mundo(a: Arbol):
    return (a.nodo("ShaderNodeNewGeometry"), "Position")


def coord_objeto(a: Arbol):
    return (a.nodo("ShaderNodeTexCoord"), "Object")


def material(nombre, construir):
    mat = bpy.data.materials.new(nombre)
    a = Arbol(mat)
    a.final(construir(a))
    return mat


def simple(nombre, color, rug=0.5, metal=0.0, coat=0.0, emision=None, fuerza=0.0):
    return material(nombre, lambda a: a.bsdf(color, rug, metal, coat, emision, fuerza))


def caja(bm, centro, tam, mat=0):
    M = Matrix.Translation(Vector(centro)) @ Matrix.Diagonal((tam[0], tam[1], tam[2], 1.0))
    r = bmesh.ops.create_cube(bm, size=1.0, matrix=M)
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mat
    return r["verts"]


def barra(bm, p1, p2, radio, mat=0, lados=8):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    M = Matrix.Translation((p1 + p2) / 2) @ rot
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=lados, radius1=radio, radius2=radio,
                              depth=d.length, matrix=M)
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mat


def objeto(nombre, bm, mats, color=None, padre=None, suave=False):
    me = bpy.data.meshes.new(nombre)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    if suave:
        for pol in me.polygons:
            pol.use_smooth = True
    ob = bpy.data.objects.new(nombre, me)
    enlazar(ob)
    if color is not None:
        ob.color = (*color, 1.0)
    if padre is not None:
        ob.parent = padre
    return ob


def vacio(nombre, pos=(0, 0, 0), padre=None):
    ob = bpy.data.objects.new(nombre, None)
    enlazar(ob)
    ob.location = pos
    if padre is not None:
        ob.parent = padre
    return ob


def luz(nombre, tipo, pos, energia, color, radio=0.1, padre=None, rot=None, cono=None):
    ld = bpy.data.lights.new(nombre, tipo)
    ld.energy = energia
    ld.color = color
    poner(ld, "shadow_soft_size", radio)
    if cono is not None:
        ld.spot_size = cono
        ld.spot_blend = 0.6
    ob = bpy.data.objects.new(nombre, ld)
    enlazar(ob)
    ob.location = pos
    if rot is not None:
        ob.rotation_euler = rot
    if padre is not None:
        ob.parent = padre
    return ob


# --------------------------------------------------------------------------- cielo, neblina, cámara, render

CIELOS = {
    # (horizonte, 12 %, 35 %, cenit, resplandor cálido hacia +y, fuerza)
    "hora_azul": ((0.12, 0.13, 0.27), (0.04, 0.07, 0.22), (0.02, 0.04, 0.15), (0.010, 0.020, 0.065), 0.22, 0.30),
    # madrugada en la ciudad: casi negro, con el resplandor anaranjado de las luces urbanas abajo
    "madrugada": ((0.075, 0.06, 0.065), (0.03, 0.032, 0.05), (0.012, 0.016, 0.032), (0.004, 0.006, 0.014), 0.04, 0.45),
    # amanecer nublado: gris parejo, un poco más claro en el horizonte
    "amanecer_gris": ((0.60, 0.62, 0.66), (0.50, 0.53, 0.59), (0.42, 0.45, 0.52), (0.33, 0.36, 0.44), 0.0, 0.75),
}


def mundo_nuevo(escena, nombre: str):
    """Un mundo vacío (solo su salida) asignado a la escena. Devuelve (mundo, árbol, salida)."""
    mundo = bpy.data.worlds.new(nombre)
    escena.world = mundo
    poner(mundo, "use_nodes", True)
    nt = mundo.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_WORLD":
            nt.nodes.remove(n)
    return mundo, nt, next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")


def cielo(escena, nombre: str):
    mundo, nt, salida = mundo_nuevo(escena, nombre)
    nt.links.new(nodos_cielo(nt, nombre).outputs[0], salida.inputs["Surface"])
    return mundo


def nodos_cielo(nt, nombre: str):
    """El degradado de cielo `nombre` (CIELOS) dentro del árbol `nt`. Devuelve su nodo Background."""
    horizonte, bajo, medio, cenit, calido, fuerza = CIELOS[nombre]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(sep.outputs[2], rampa.inputs[0])
    els = rampa.color_ramp.elements
    els[0].position, els[0].color = 0.0, (*horizonte, 1)
    els[1].position, els[1].color = 1.0, (*cenit, 1)
    els.new(0.12).color = (*bajo, 1)
    els.new(0.35).color = (*medio, 1)
    punto = nt.nodes.new("ShaderNodeVectorMath")
    punto.operation = "DOT_PRODUCT"
    nt.links.new(coord.outputs["Generated"], punto.inputs[0])
    punto.inputs[1].default_value = (0.0, 1.0, 0.0)
    brillo = nt.nodes.new("ShaderNodeMapRange")
    nt.links.new(punto.outputs["Value"], brillo.inputs[0])
    brillo.inputs[1].default_value, brillo.inputs[2].default_value = 0.6, 1.0
    brillo.inputs[3].default_value, brillo.inputs[4].default_value = 0.0, calido
    tibio = nt.nodes.new("ShaderNodeVectorMath")
    tibio.operation = "SCALE"
    tibio.inputs[0].default_value = (0.9, 0.45, 0.25)
    nt.links.new(brillo.outputs[0], tibio.inputs["Scale"])
    suma = nt.nodes.new("ShaderNodeVectorMath")
    suma.operation = "ADD"
    nt.links.new(rampa.outputs["Color"], suma.inputs[0])
    nt.links.new(tibio.outputs[0], suma.inputs[1])
    fondo = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(suma.outputs[0], fondo.inputs["Color"])
    fondo.inputs["Strength"].default_value = fuerza
    return fondo


def neblina(centro, tam, densidad, color=(0.75, 0.78, 0.86), anisotropia=0.5, z_espesa=None, nombre="neblina"):
    """Caja de neblina (volumen de objeto: recibe la luz de las lámparas en Eevee). Con `z_espesa`
    = (z_abajo, z_arriba) la neblina es densa abajo y se adelgaza hacia arriba (bruma sobre el agua)."""
    def hacer(a):
        n = a.nodo("ShaderNodeVolumePrincipled")
        entrada(n, "Color").default_value = (*color, 1)
        entrada(n, "Anisotropy").default_value = anisotropia
        if z_espesa is None:
            entrada(n, "Density").default_value = densidad
        else:
            _, _, z = a.separar(pos_mundo(a))
            ruido_f, _ = a.ruido(pos_mundo(a), 0.08, 3.0, 0.6)
            perfil = a.rango(z, z_espesa[0], z_espesa[1], 1.0, 0.08)
            a.unir(a.m("MULTIPLY", a.m("MULTIPLY", perfil, densidad), a.rango(ruido_f, 0.3, 0.7, 0.5, 1.5)), n, "Density")
        return (n, 0)
    mat = bpy.data.materials.new(nombre)
    a = Arbol(mat)
    a.final(hacer(a), "Volume")
    bm = bmesh.new()
    caja(bm, centro, tam)
    return objeto(nombre, bm, [mat])


def camara(posicion, lente=35.0, fstop=2.8, foco=None, distancia_foco=None):
    """Cámara que apunta siempre a un vacío «mira» (se anima la mira, no la rotación)."""
    cd = bpy.data.cameras.new("camara")
    cd.lens = lente
    cd.sensor_width = 36.0
    cd.clip_start, cd.clip_end = 0.05, 600
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    if foco is not None:
        cd.dof.focus_object = foco
    elif distancia_foco is not None:
        cd.dof.focus_distance = distancia_foco
    cam = enlazar(bpy.data.objects.new("camara", cd))
    bpy.context.scene.camera = cam
    cam.location = posicion
    mira = vacio("mira")
    seg = cam.constraints.new("TRACK_TO")
    seg.target = mira
    seg.track_axis = "TRACK_NEGATIVE_Z"
    seg.up_axis = "UP_Y"
    return cam, mira


def clave(ob, ruta: str, valor, cuadro: int):
    """Un cuadro clave (se pone uno por fotograma: la curva la manda el código, no Blender)."""
    setattr(ob, ruta, valor)
    ob.keyframe_insert(ruta, frame=cuadro)


def preparar_render(escena, cuadros: int, fps: int = 30, muestras: int = 32, exposicion: float = 0.0,
                    volumen_fin: float = 180.0, desenfoque_movimiento: bool = True, motor: str = "eevee",
                    muestras_cycles: int = 96, exposicion_eevee: float | None = None):
    """`exposicion` está calibrada para Cycles; Eevee dispersa menos luz en la neblina y pide la suya."""
    r = escena.render
    if motor != "cycles" and exposicion_eevee is not None:
        exposicion = exposicion_eevee
    if motor == "cycles":
        _usar_cycles(escena, muestras_cycles)
    else:
        for nombre in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            if poner(r, "engine", nombre):
                break
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1920, 1080, 100
    r.fps = fps
    escena.frame_start, escena.frame_end = 1, cuadros
    r.image_settings.file_format = "PNG"
    r.image_settings.color_depth = "8"
    poner(r, "film_transparent", False)
    ev = escena.eevee
    poner(ev, "taa_render_samples", muestras)
    poner(ev, "use_raytracing", True)
    poner(ev, "ray_tracing_method", "SCREEN")
    if hasattr(ev, "ray_tracing_options"):
        poner(ev.ray_tracing_options, "resolution_scale", "1")
        poner(ev.ray_tracing_options, "use_denoise", True)
    poner(ev, "use_fast_gi", True)
    poner(ev, "fast_gi_method", "GLOBAL_ILLUMINATION")
    poner(ev, "use_shadows", True)
    poner(ev, "shadow_ray_count", 2)
    poner(ev, "shadow_step_count", 8)
    poner(ev, "volumetric_start", 0.3)
    poner(ev, "volumetric_end", volumen_fin)
    poner(ev, "volumetric_tile_size", "4")
    poner(ev, "volumetric_samples", 96)
    poner(ev, "use_volumetric_shadows", True)
    if not poner(r, "use_motion_blur", desenfoque_movimiento):
        poner(ev, "use_motion_blur", desenfoque_movimiento)
    poner(r, "motion_blur_shutter", 0.5)
    vs = escena.view_settings
    poner(vs, "view_transform", "AgX")
    for look in ("AgX - Medium High Contrast", "Medium High Contrast"):
        if poner(vs, "look", look):
            break
    vs.exposure = exposicion


def _usar_cycles(escena, muestras: int):
    """Cycles en la GPU (OptiX si está, si no CUDA), con eliminación de ruido: la luz se calcula
    rebote por rebote, como en una foto."""
    escena.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for tipo in ("OPTIX", "CUDA"):
        if poner(prefs, "compute_device_type", tipo):
            prefs.get_devices()
            if any(d.type == tipo for d in prefs.devices):
                break
    for d in prefs.devices:
        d.use = d.type != "CPU"
    cy = escena.cycles
    cy.device = "GPU"
    cy.samples = muestras
    poner(cy, "use_adaptive_sampling", True)
    poner(cy, "adaptive_threshold", 0.02)
    cy.use_denoising = True
    poner(cy, "denoiser", "OPTIX")
    poner(cy, "use_light_tree", True)
    poner(cy, "volume_step_rate", 4.0)
    poner(cy, "max_bounces", 6)
    poner(cy, "diffuse_bounces", 3)
    poner(cy, "glossy_bounces", 4)
    poner(cy, "transmission_bounces", 8)              # vidrios del tranvía: se ve a través de dos
    poner(cy, "volume_bounces", 0)
    poner(cy, "caustics_reflective", False)
    poner(cy, "caustics_refractive", False)
    poner(cy, "sample_clamp_indirect", 8.0)           # sin puntos blancos sueltos en los rebotes
    poner(cy, "use_animated_seed", True)              # el ruido residual cambia en cada cuadro, como grano,
    #                                                   en vez de quedarse pegado a la pantalla
    poner(escena.render, "use_persistent_data", True)  # texturas y geometría se cargan una vez por plano
