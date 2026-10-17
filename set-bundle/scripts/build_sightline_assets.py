"""Build reusable SightLine stop and stylized powered-wheelchair rider.

Run: blender --background --factory-startup --python build_sightline_assets.py
The output .blend contains assets only. Preview cameras/lights are temporary.
Coordinates are metres; the road-facing side of the stop is -Y.
"""

import math
from pathlib import Path

import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent


def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def material(name, rgb, metallic=0, roughness=0.55, emission=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*rgb, 1)
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = roughness
    if emission:
        p.inputs['Emission Color'].default_value = (*rgb, 1)
        p.inputs['Emission Strength'].default_value = emission
    return m


NAVY = material('SL | midnight navy', (0.025, 0.072, 0.126), roughness=.38)
TEAL = material('SL | teal', (.015, .49, .48), roughness=.38)
CYAN = material('SL | luminous cyan', (.04, .78, .86), emission=1.5)
WHITE = material('SL | ivory white', (.88, .92, .91))
SILVER = material('SL | brushed aluminium', (.44, .52, .55), metallic=.65, roughness=.34)
GLASS = material('SL | smoky glass', (.11, .20, .25), metallic=.1, roughness=.14)
YELLOW = material('SL | tactile yellow', (.95, .65, .11))
DARK = material('SL | charcoal', (.027, .037, .05))
GREEN = material('SL | access green', (.07, .65, .35), emission=.7)
SKIN = material('Albie | warm skin', (.59, .34, .23))
HAIR = material('Albie | dark hair', (.042, .032, .036))
JACKET = material('Albie | rust jacket', (.77, .29, .13))
PANTS = material('Albie | slate trousers', (.15, .21, .28))
TYRE = material('Chair | rubber', (.022, .027, .032))


def link(obj, name, coll, mat=None, parent=None):
    obj.name = name
    for old in tuple(obj.users_collection):
        old.objects.unlink(obj)
    coll.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    if parent:
        obj.parent = parent
    return obj


def empty(name, coll, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    coll.objects.link(o)
    o.empty_display_size = .16
    o.empty_display_type = 'ARROWS'
    o.parent = parent
    o.location = loc
    return o


def box(name, loc, dims, mat, coll, parent=None, bevel=.015):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = link(bpy.context.object, name, coll, mat, parent)
    o.location = loc
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        b = o.modifiers.new('subtle machined radius', 'BEVEL')
        b.width = bevel
        b.segments = 3
        o.modifiers.new('weighted corner normals', 'WEIGHTED_NORMAL')
    return o


def cylinder(name, loc, radius, depth, mat, coll, parent=None,
             rotation=(0, 0, 0), vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth)
    o = link(bpy.context.object, name, coll, mat, parent)
    o.location = loc
    o.rotation_euler = rotation
    return o


def sphere(name, loc, radius, mat, coll, parent=None, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=radius)
    o = link(bpy.context.object, name, coll, mat, parent)
    o.location = loc
    o.scale = scale
    bpy.ops.object.shade_smooth()
    return o


def text(name, content, loc, size, mat, coll, parent=None, align='LEFT'):
    curve = bpy.data.curves.new(name, 'FONT')
    curve.body = content
    curve.size = size
    curve.extrude = .001
    curve.align_x = align
    o = bpy.data.objects.new(name, curve)
    coll.objects.link(o)
    o.parent = parent
    o.location = loc
    o.rotation_euler.x = math.pi / 2  # text faces road, -Y
    o.data.materials.append(mat)
    return o


def qr_surface(name, loc, size, coll, parent=None):
    image = bpy.data.images.load(str(OUT / 'demo_qr_example_com.png'), check_existing=True)
    image.pack()
    mat = bpy.data.materials.new('SL | demo QR image - replace before submission')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = image
    emit = nodes.new('ShaderNodeEmission')
    emit.inputs['Strength'].default_value = 1
    output = nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(tex.outputs['Color'], emit.inputs['Color'])
    mat.node_tree.links.new(emit.outputs[0], output.inputs['Surface'])
    bpy.ops.mesh.primitive_plane_add(size=size)
    o = link(bpy.context.object, name, coll, mat, parent)
    o.location = loc
    o.rotation_euler.x = math.pi / 2
    return o


def beam(name, a, b, radius, mat, coll, parent=None, vertices=12):
    direction = Vector(b) - Vector(a)
    o = cylinder(name, (Vector(a)+Vector(b))/2, radius, direction.length,
                 mat, coll, parent, vertices=vertices)
    o.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
    return o


def build_stop():
    base = collection('STOP_BASE | shelter and street furniture')
    add = collection('SIGHTLINE | toggle off for before shots')
    root = empty('STOP_ASSET_ROOT | move this object', base)
    shelter = empty('STOP_SHELTER_ASSEMBLY', base, parent=root)
    roof = box('stop_roof', (0, .70, 2.74), (5.25, 1.75, .14), NAVY, base, shelter, .09)
    box('stop_roof_teal_fascia', (0, -.19, 2.70), (5.14, .08, .10), TEAL, base, shelter)
    for x in (-2.43, 2.43):
        for y in (.01, 1.35):
            cylinder(f'stop_post_{x}_{y}', (x, y, 1.34), .046, 2.68,
                     SILVER, base, shelter)
            box(f'stop_post_foot_{x}_{y}', (x, y, .025), (.17, .17, .05), NAVY, base, shelter)
    # Open road-facing side; rear glazing shields rain without hiding the rider.
    for x in (-1.22, 1.22):
        box(f'stop_rear_glass_{x}', (x, 1.36, 1.47), (2.30, .025, 2.26),
            GLASS, base, shelter, .008)
        box(f'stop_rear_glass_rail_{x}', (x, 1.34, 1.12), (2.32, .035, .035),
            SILVER, base, shelter)
    bench = empty('STOP_BENCH_ASSEMBLY', base, parent=root)
    box('stop_bench_seat', (-1.14, .96, .52), (1.95, .44, .075), TEAL, base, bench, .035)
    box('stop_bench_back', (-1.14, 1.17, .79), (1.95, .075, .53), NAVY, base, bench, .025)
    for x in (-1.92, -.36):
        box(f'stop_bench_leg_{x}', (x, .96, .25), (.06, .35, .50), SILVER, base, bench)
    sign = empty('STOP_SIGN_ASSEMBLY', base, parent=root)
    cylinder('stop_sign_pole', (-2.91, -.30, 1.48), .052, 2.96, SILVER, base, sign)
    box('stop_sign_panel', (-2.91, -.30, 2.66), (.80, .11, .54), NAVY, base, sign, .035)
    text('stop_sign_label', 'BUS STOP', (-3.27, -.367, 2.70), .12, WHITE, base, sign)
    text('stop_sign_number', '400', (-3.10, -.367, 2.50), .15, CYAN, base, sign)
    # Upgrade is a separate toggleable collection. Each assembly has a stable origin.
    upgrade = empty('SIGHTLINE_ASSET_ROOT | follows STOP_ASSET_ROOT', add, parent=root)
    display = empty('SL_ARRIVAL_DISPLAY_ASSEMBLY', add, parent=upgrade)
    box('stop_display', (.15, -.19, 2.36), (1.55, .095, .51), DARK, add, display, .025)
    box('stop_display_glass', (.15, -.248, 2.36), (1.46, .009, .43), GLASS, add, display)
    text('stop_display_route', '400', (-.50, -.259, 2.37), .22, CYAN, add, display)
    text('stop_display_arrival', 'ARRIVING  2 MIN', (-.06, -.259, 2.43), .087, WHITE, add, display)
    text('stop_display_access', 'WHEELCHAIR SPACE AVAILABLE', (-.06, -.259, 2.27), .052, GREEN, add, display)
    panel = empty('SL_HELP_PANEL_ASSEMBLY', add, parent=upgrade)
    box('stop_help_panel', (1.95, -.10, 1.38), (.64, .12, 1.46), NAVY, add, panel, .05)
    box('stop_help_panel_screen', (1.95, -.173, 1.73), (.52, .008, .39), GLASS, add, panel)
    text('stop_help_panel_heading', 'SIGHTLINE', (1.73, -.183, 1.78), .085, CYAN, add, panel)
    text('stop_help_panel_prompt', 'BOARDING HELP', (1.73, -.183, 1.64), .055, WHITE, add, panel)
    qr_surface('stop_demo_qr_example_com', (1.78, -.181, 1.32), .22, add, panel)
    text('stop_demo_qr_label', 'DEMO QR', (1.68, -.184, 1.16), .041, WHITE, add, panel)
    cylinder('stop_nfc_pad', (2.10, -.183, 1.34), .09, .012,
             CYAN, add, panel, rotation=(math.pi/2, 0, 0))
    text('stop_nfc_label', 'NFC', (2.04, -.196, 1.31), .045, NAVY, add, panel)
    cylinder('stop_intercom_button', (1.95, -.185, .92), .10, .012,
             GREEN, add, panel, rotation=(math.pi/2, 0, 0))
    text('stop_intercom_label', 'HELP', (1.85, -.199, .77), .065, WHITE, add, panel)
    controller = empty('SL_CONTROLLER_ASSEMBLY', add, parent=upgrade)
    box('stop_controller_enclosure', (2.36, .30, 1.31), (.34, .25, .42),
        SILVER, add, controller, .025)
    box('stop_controller_status_led', (2.36, .163, 1.43), (.035, .009, .035),
        GREEN, add, controller, .004)
    # Both side-mounted assemblies look inward toward their actual target.
    # The housings and lenses use local coordinates so their parent empties can
    # also be animated as one unit in the exploded-view shot.
    kerb_position = Vector((2.42, -.15, .64))
    kerb = empty('SL_KERB_SENSOR_ASSEMBLY', add, kerb_position, upgrade)
    kerb.rotation_euler = (Vector((1.02, -1.35, .15)) - kerb_position).to_track_quat('-Y', 'Z').to_euler()
    box('stop_side_kerb_sensor', (0, 0, 0), (.28, .16, .19), NAVY, add, kerb, .025)
    for x in (-.06, .06):
        cylinder(f'stop_side_sensor_lens_{x}', (x, -.09, 0), .032, .013,
                 CYAN, add, kerb, rotation=(math.pi/2, 0, 0))
    camera_position = Vector((2.42, -.17, 2.39))
    camera = empty('SL_BOARDING_CAMERA_ASSEMBLY', add, camera_position, upgrade)
    camera.rotation_euler = (Vector((1.02, -.69, .12)) - camera_position).to_track_quat('-Y', 'Z').to_euler()
    box('stop_side_boarding_camera', (0, 0, 0), (.25, .16, .13),
        NAVY, add, camera, .025)
    cylinder('stop_side_boarding_camera_lens', (0, -.09, 0), .040,
             .019, GLASS, add, camera, rotation=(math.pi/2, 0, 0))
    zone = empty('SL_BOARDING_ZONE_ASSEMBLY', add, parent=upgrade)
    # At z=.017 this lays on top of the 15 cm-high footpath when root z=.15.
    box('stop_boarding_zone_fill', (1.02, -.69, .013), (1.30, 1.10, .012),
        TEAL, add, zone, .01)
    for x in (.39, 1.65):
        box(f'stop_boarding_zone_edge_x{x}', (x, -.69, .022), (.045, 1.15, .008),
            WHITE, add, zone, 0)
    text('stop_boarding_zone_label', 'PRIORITY BOARDING', (.47, -.68, .026),
         .105, WHITE, add, zone).rotation_euler = (0, 0, 0)
    return base, add


def build_albie():
    chair = collection('ALBIE_CHAIR | powered wheelchair')
    person = collection('ALBIE_RIDER | generic stylized character')
    root = empty('ALBIE_ROOT | animate path on this object', chair)
    chassis = empty('ALBIE_CHAIR_ASSEMBLY', chair, parent=root)
    box('albie_chair_battery_chassis', (0, .04, .34), (.56, .73, .24), NAVY, chair, chassis, .055)
    box('albie_chair_seat', (0, .08, .61), (.57, .54, .11), DARK, chair, chassis, .055)
    box('albie_chair_backrest', (0, .33, .90), (.58, .12, .60), NAVY, chair, chassis, .055)
    box('albie_chair_headrest', (0, .36, 1.25), (.39, .12, .17), DARK, chair, chassis, .04)
    for side, tag in ((-1, 'L'), (1, 'R')):
        wx = side * .39
        wheel = empty(f'ALBIE_WHEEL_{tag} | rotate local X', chair,
                      (wx, .13, .33), chassis)
        cylinder(f'albie_drive_tyre_{tag}', (0, 0, 0), .295, .072,
                 TYRE, chair, wheel, rotation=(0, math.pi/2, 0))
        cylinder(f'albie_drive_hub_{tag}', (side*.042, 0, 0), .135, .078,
                 SILVER, chair, wheel, rotation=(0, math.pi/2, 0))
        cylinder(f'albie_caster_tyre_{tag}', (side*.265, -.36, .105), .095,
                 .055, TYRE, chair, chassis, rotation=(0, math.pi/2, 0))
        box(f'albie_armrest_{tag}', (side*.31, -.015, .80),
            (.09, .48, .07), NAVY, chair, chassis, .025)
    box('albie_footplate', (0, -.52, .17), (.48, .36, .035), SILVER, chair, chassis, .015)
    beam('albie_footplate_support', (0, -.25, .40), (0, -.48, .18),
         .021, SILVER, chair, chassis)
    box('albie_joystick_base', (.33, -.18, .87), (.13, .13, .05), DARK, chair, chassis)
    cylinder('albie_joystick_stem', (.33, -.18, .94), .018, .12, SILVER, chair, chassis)
    sphere('albie_joystick_grip', (.33, -.18, 1.01), .038, DARK, chair, chassis)
    figure = empty('ALBIE_BODY_ASSEMBLY', person, parent=root)
    sphere('albie_torso_jacket', (0, .07, 1.02), .30, JACKET, person,
           figure, scale=(.90, .64, 1.12))
    box('albie_jacket_zip', (0, -.125, 1.05), (.018, .012, .36), SILVER, person, figure, .004)
    sphere('albie_hips', (0, .04, .71), .24, PANTS, person,
           figure, scale=(1.13, .75, .55))
    for side, tag in ((-1, 'L'), (1, 'R')):
        beam(f'albie_upper_arm_{tag}', (side*.22, .03, 1.14),
             (side*.27, -.14, .91), .075, JACKET, person, figure)
        beam(f'albie_forearm_{tag}', (side*.27, -.14, .91),
             ((.32 if side > 0 else -.22), -.19, .84), .063,
             JACKET, person, figure)
        sphere(f'albie_hand_{tag}', ((.32 if side > 0 else -.22), -.19, .84),
               .07, SKIN, person, figure)
        beam(f'albie_thigh_{tag}', (side*.13, -.13, .67),
             (side*.14, -.38, .54), .10, PANTS, person, figure)
        beam(f'albie_shin_{tag}', (side*.14, -.38, .54),
             (side*.14, -.50, .27), .075, PANTS, person, figure)
        box(f'albie_shoe_{tag}', (side*.14, -.56, .205),
            (.16, .25, .095), DARK, person, figure, .025)
    head = empty('ALBIE_HEAD_LOOK | rotate for glances', person,
                 (0, -.02, 1.28), figure)
    cylinder('albie_neck', (0, 0, .025), .082, .13, SKIN, person, head)
    sphere('albie_head', (0, -.025, .20), .177, SKIN, person, head,
           scale=(.86, .91, 1.07))
    sphere('albie_hair_cap', (0, -.005, .326), .158, HAIR, person, head,
           scale=(.88, .95, .44))
    for side, tag in ((-1, 'L'), (1, 'R')):
        sphere(f'albie_eye_{tag}', (side*.061, -.177, .22), .012,
               DARK, person, head)
        sphere(f'albie_ear_{tag}', (side*.155, -.016, .19), .035,
               SKIN, person, head)
    box('albie_mouth', (0, -.189, .135), (.055, .004, .008),
        DARK, person, head, .002)
    gaze = empty('ALBIE_GAZE_TARGET | move to guide head turns', person,
                 (0, -2, 1.25), root)
    look = head.constraints.new('DAMPED_TRACK')
    look.name = 'Look toward ALBIE_GAZE_TARGET'
    look.target = gaze
    look.track_axis = 'TRACK_NEGATIVE_Y'
    return chair, person


def camera_at(name, loc, target, lens):
    bpy.ops.object.camera_add(location=loc)
    c = bpy.context.object
    c.name = name
    c.rotation_euler = (Vector(target)-c.location).to_track_quat('-Z', 'Y').to_euler()
    c.data.lens = lens
    bpy.context.scene.camera = c
    return c


def preview(name, camera_loc, target, hide=None):
    stage = collection('TEMP_PREVIEW_STAGE')
    backdrop = material('TEMP | pale blue-grey', (.67, .72, .72))
    box('TEMP_floor', (0, 0, -.06), (11, 9, .10), backdrop, stage)
    camera_at('TEMP_camera', camera_loc, target, 45)
    for loc, power, size in (((-3, -4, 7), 1250, 5), ((4, 2, 5), 850, 4)):
        bpy.ops.object.light_add(type='AREA', location=loc)
        l = bpy.context.object
        l.data.energy = power
        l.data.shape = 'DISK'
        l.data.size = size
        l.rotation_euler = (Vector(target)-l.location).to_track_quat('-Z', 'Y').to_euler()
    hidden = []
    for coll in hide or ():
        for obj in coll.all_objects:
            hidden.append((obj, obj.hide_render))
            obj.hide_render = True
    scene = bpy.context.scene
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(OUT / name)
    bpy.ops.render.render(write_still=True)
    for obj, was_hidden in hidden:
        obj.hide_render = was_hidden
    for obj in tuple(stage.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(stage)
    for obj in tuple(bpy.context.scene.objects):
        if obj.name.startswith('TEMP_'):
            bpy.data.objects.remove(obj, do_unlink=True)


def main():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    scene.render.fps = 24
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.engine = 'BLENDER_EEVEE'
    scene.world.color = (.28, .32, .34)
    base, add = build_stop()
    chair, person = build_albie()
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'SightLine_Stop_Albie_Master.blend'))
    preview('preview_stop_upgrade.png', (7, -8, 5), (0, .2, 1.4), (chair, person))
    preview('preview_stop_before.png', (7, -8, 5), (0, .2, 1.4), (chair, person, add))
    preview('preview_albie.png', (2.7, -3.2, 2.0), (0, 0, .8), (base, add))
    print('ASSET_BUILD_COMPLETE')


if __name__ == '__main__':
    main()
