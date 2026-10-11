"""Escena 3D de producto para Blender en modo headless.

Uso: blender -b --factory-startup -P escena.py -- '<json>'
  {"modo": "tarjeta_gira" | "tarjeta_mesa" | "logo_flota",
   "textura": "/ruta/tarjeta.png",   diseño plano de la tarjeta (frente)
   "logo": "/ruta/logo.png",          para logo_flota
   "color_canto": [r, g, b],          0-1, cantos y reverso de la tarjeta
   "w": 1080, "h": 1920, "frames": 120, "fps": 30, "muestras": 32,
   "salida": "/dir/frames/"}          PNG RGBA con fondo transparente

La tarjeta es una pieza de 85,6 x 54 x 0,76 mm (escala x10) con esquinas de radio
3,18 mm, así que la proporción es la de una tarjeta real."""
import json
import math
import sys

import bmesh
import bpy
from mathutils import Vector

args = json.loads(sys.argv[sys.argv.index("--") + 1])
MODO = args.get("modo", "tarjeta_gira")
W, H, FRAMES, FPS = args.get("w", 1080), args.get("h", 1920), args.get("frames", 120), args.get("fps", 30)

# ---------------------------------------------------------------- escena base
bpy.ops.wm.read_factory_settings(use_empty=True)
esc = bpy.context.scene
for motor in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        esc.render.engine = motor
        break
    except TypeError:
        continue
esc.render.resolution_x, esc.render.resolution_y = W, H
esc.render.fps = FPS
esc.frame_start, esc.frame_end = 1, FRAMES
esc.render.film_transparent = True
esc.render.image_settings.file_format = "PNG"
esc.render.image_settings.color_mode = "RGBA"
esc.render.filepath = args["salida"].rstrip("/") + "/f"
try:
    esc.eevee.taa_render_samples = args.get("muestras", 32)
except AttributeError:
    pass
esc.view_settings.view_transform = "AgX" if "AgX" in [v.identifier for v in type(esc.view_settings).bl_rna.properties["view_transform"].enum_items] else "Filmic"
esc.view_settings.look = "None"
mundo = bpy.data.worlds.new("Mundo")
esc.world = mundo
mundo.use_nodes = True
mundo.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.02, 0.025, 1)
mundo.node_tree.nodes["Background"].inputs[1].default_value = 0.6


def suavizar(fc_owner):
    """Interpolación suave (bezier) en todas las claves."""
    ad = fc_owner.animation_data
    if not ad or not ad.action:
        return
    try:
        curvas = ad.action.fcurves
    except AttributeError:  # Blender 5: acciones por capas
        curvas = [c for layer in ad.action.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves]
    for fc in curvas:
        for k in fc.keyframe_points:
            k.interpolation = "BEZIER"
            k.easing = "AUTO"


def material_imagen(nombre, ruta, rugosidad=0.55, alfa=False):
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(ruta)
    tex.interpolation = "Cubic"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if alfa:
        nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        try:
            mat.blend_method = "BLEND"
        except AttributeError:
            pass
    bsdf.inputs["Roughness"].default_value = rugosidad
    for nombre_in, v in (("Coat Weight", 0.12), ("Coat Roughness", 0.25)):
        if nombre_in in bsdf.inputs:
            bsdf.inputs[nombre_in].default_value = v
    return mat


def material_color(nombre, rgb, rugosidad=0.5):
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rugosidad
    return mat


def tarjeta(textura, color_canto):
    """Rectángulo redondeado extruido; la cara frontal lleva la textura con UV exacto."""
    ancho, alto, grosor, radio, seg = 8.56, 5.40, 0.076, 0.318, 10
    contorno = []
    for cx, cy, a0 in ((ancho / 2 - radio, alto / 2 - radio, 0), (-ancho / 2 + radio, alto / 2 - radio, 90),
                       (-ancho / 2 + radio, -alto / 2 + radio, 180), (ancho / 2 - radio, -alto / 2 + radio, 270)):
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            contorno.append((cx + radio * math.cos(a), cy + radio * math.sin(a)))
    me = bpy.data.meshes.new("tarjeta")
    bm = bmesh.new()
    frente = bm.faces.new([bm.verts.new((x, y, grosor / 2)) for x, y in contorno])
    atras = bm.faces.new([bm.verts.new((x, y, -grosor / 2)) for x, y in reversed(contorno)])
    n = len(contorno)
    vf, va = list(frente.verts), list(reversed(atras.verts))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([vf[j], vf[i], va[i], va[j]])
    uv = bm.loops.layers.uv.new()
    for cara in bm.faces:
        for lp in cara.loops:
            x, y = lp.vert.co.x, lp.vert.co.y
            lp[uv].uv = ((x + ancho / 2) / ancho, (y + alto / 2) / alto)
        cara.material_index = 0 if cara is frente else 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("Tarjeta", me)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material_imagen("Frente", textura))
    obj.data.materials.append(material_color("Canto", color_canto, 0.55))
    return obj


def luz_area(nombre, pos, energia, tam, color=(1, 1, 1), mirar=(0, 0, 0)):
    ld = bpy.data.lights.new(nombre, "AREA")
    ld.energy, ld.size, ld.color = energia, tam, color
    ob = bpy.data.objects.new(nombre, ld)
    bpy.context.collection.objects.link(ob)
    ob.location = pos
    direccion = Vector(mirar) - Vector(pos)
    ob.rotation_euler = direccion.to_track_quat("-Z", "Y").to_euler()
    return ob


def camara(pos, mirar, lente=70, dof=None):
    cd = bpy.data.cameras.new("Cam")
    cd.lens = lente
    if dof:
        cd.dof.use_dof = True
        cd.dof.focus_distance = dof[0]
        cd.dof.aperture_fstop = dof[1]
    cd.sensor_fit = "HORIZONTAL"  # el encuadre se calcula por ancho en cualquier formato
    ob = bpy.data.objects.new("Cam", cd)
    bpy.context.collection.objects.link(ob)
    ob.location = pos
    ob.rotation_euler = (Vector(mirar) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    esc.camera = ob
    return ob


canto = tuple(args.get("color_canto", [0.08, 0.08, 0.09]))


def distancia(ancho_objeto, fraccion, lente=70):
    """Distancia de cámara para que el objeto ocupe `fraccion` del ancho del cuadro."""
    visible = ancho_objeto / fraccion
    return visible / 2 / math.tan(math.atan(18 / lente))


FRACCION = 0.8 if H > W else (0.62 if H == W else 0.42)

# ---------------------------------------------------------------- modos
if MODO == "tarjeta_gira":
    t = tarjeta(args["textura"], canto)
    t.rotation_euler = (math.radians(90), 0, 0)  # de pie, frente a cámara (-Y)
    cam = camara((0, -distancia(8.56, FRACCION), 0), (0, 0, 0), lente=70)
    luz_area("Clave", (-7, -10, 7), 420, 9)
    luz_area("Relleno", (8, -8, -3), 160, 10, (0.9, 0.95, 1))
    luz_area("Frontal", (2, -22, 5), 500, 12)  # que no se apague al girar
    luz_area("Derecha", (12, -10, 4), 450, 10)
    barrido = luz_area("Barrido", (-10, -6, 3), 650, 3, (1, 0.97, 0.9))
    # giro con flotación suave
    for f, rz, z in ((1, -34, -0.15), (FRAMES // 2, -4, 0.15), (FRAMES, 14, -0.05)):
        t.rotation_euler = (math.radians(90 + 6 * math.sin(f / FRAMES * math.pi)), 0, math.radians(rz))
        t.location = (0, 0, z)
        t.keyframe_insert("rotation_euler", frame=f)
        t.keyframe_insert("location", frame=f)
    for f, x in ((1, -10), (FRAMES, 10)):  # brillo que recorre la tarjeta
        barrido.location.x = x
        barrido.keyframe_insert("location", frame=f)
    for f, y in ((1, cam.location.y), (FRAMES, cam.location.y * 0.9)):  # leve acercamiento
        cam.location.y = y
        cam.keyframe_insert("location", frame=f)
    suavizar(t)
    suavizar(cam)

elif MODO == "tarjeta_mesa":
    t = tarjeta(args["textura"], canto)
    t.rotation_euler = (0, 0, math.radians(-12))
    t.location = (0, 0, 0.04)
    piso = bpy.data.meshes.new("piso")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=40)
    bm.to_mesh(piso)
    bm.free()
    ob_piso = bpy.data.objects.new("Mesa", piso)
    bpy.context.collection.objects.link(ob_piso)
    # madera procedimental (vetas con wave + ruido)
    mat = bpy.data.materials.new("Madera")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    ola = nt.nodes.new("ShaderNodeTexWave")
    ola.inputs["Scale"].default_value = 1.6
    ola.inputs["Distortion"].default_value = 12
    ola.inputs["Detail"].default_value = 6
    ola.inputs["Detail Scale"].default_value = 1.4
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    rampa.color_ramp.elements[0].color = (0.06, 0.028, 0.012, 1)
    rampa.color_ramp.elements[1].color = (0.24, 0.12, 0.055, 1)
    nt.links.new(ola.outputs["Fac"], rampa.inputs["Fac"])
    nt.links.new(rampa.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.38
    ob_piso.data.materials.append(mat)
    esc.render.film_transparent = False
    mundo.node_tree.nodes["Background"].inputs[0].default_value = (0.012, 0.01, 0.01, 1)
    luz_area("Clave", (-5, -4, 7), 1100, 5, (1, 0.9, 0.78))
    luz_area("Borde", (6, 5, 3), 500, 4, (1, 0.85, 0.6))
    d = distancia(8.56, FRACCION * 0.85, 58)
    cam = camara((0, -d * 0.55, d * 0.85), (0, 0.3, 0), lente=58, dof=(d, 2.4))
    for f, k in ((1, 1.0), (FRAMES, 0.9)):
        pos = (0.5 * (1 - k) * 4, -d * 0.55 * k, d * 0.85 * k)
        cam.location = pos
        cam.rotation_euler = (Vector((0, 0.4, 0)) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        cam.data.dof.focus_distance = (Vector(pos) - Vector((0, 0, 0))).length
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
    suavizar(cam)

elif MODO == "logo_flota":
    img = bpy.data.images.load(args["logo"])
    ancho_l = 6.0
    alto_l = ancho_l * img.size[1] / img.size[0]
    bpy.ops.mesh.primitive_plane_add(size=1)
    logo = bpy.context.active_object
    logo.scale = (ancho_l, alto_l, 1)
    logo.rotation_euler = (math.radians(90), 0, 0)
    logo.data.materials.append(material_imagen("Logo", args["logo"], 0.3, alfa=True))
    cam = camara((0, -distancia(ancho_l, FRACCION * 0.85), 0), (0, 0, 0), lente=70)
    luz_area("Clave", (-6, -10, 6), 450, 9)
    barrido = luz_area("Barrido", (-9, -5, 2), 800, 2.5, (1, 0.97, 0.92))
    for f, rz, s in ((1, -20, 0.82), (FRAMES // 2, 0, 1.0), (FRAMES, 10, 1.04)):
        logo.rotation_euler = (math.radians(90), 0, math.radians(rz))
        logo.scale = (ancho_l * s, alto_l * s, 1)
        logo.keyframe_insert("rotation_euler", frame=f)
        logo.keyframe_insert("scale", frame=f)
    for f, x in ((1, -9), (FRAMES, 9)):
        barrido.location.x = x
        barrido.keyframe_insert("location", frame=f)
    suavizar(logo)

bpy.ops.render.render(animation=True)
