"""Reusable stylized Singapore streetscape for SightLine Set A.

All geometry is procedural and made with built-in Blender features. The scene
origin matches Shots 1/2: road centre near Y=-2.5, near kerb at Y=1.76,
bus stop around X=-4.45/Y=3.54. Move SG_SET_ROOT to reposition the whole set.
"""

import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent
RNG = random.Random(2026)


def mat(name, color, roughness=.8, emission=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    if emission:
        bsdf.inputs['Emission Color'].default_value = (*color, 1)
        bsdf.inputs['Emission Strength'].default_value = emission
    return m


ROAD = mat('SG | warm asphalt', (.105, .121, .122))
ROAD_WORN = mat('SG | faded asphalt', (.145, .159, .158))
PAVEMENT = mat('SG | pale concrete footpath', (.58, .59, .54))
KERB = mat('SG | kerb concrete', (.78, .77, .69))
WHITE = mat('SG | road paint white', (.88, .86, .74))
YELLOW = mat('SG | road paint yellow', (.90, .60, .09))
TACTILE = mat('SG | tactile yellow', (.96, .74, .16))
GRASS = mat('SG | tropical verge', (.21, .35, .20))
LEAF_A = mat('SG | rain tree olive', (.12, .28, .15))
LEAF_B = mat('SG | rain tree deep green', (.08, .22, .13))
LEAF_C = mat('SG | tropical leaf highlight', (.22, .37, .18))
TRUNK = mat('SG | tree bark', (.27, .22, .15))
METAL = mat('SG | street metal', (.38, .44, .43), .45)
COOL = mat('SG | shaded housing cream', (.65, .67, .61))
WARM = mat('SG | housing pale peach', (.74, .69, .61))
BLK_BLUE = mat('SG | housing blue accent', (.19, .36, .42))
BLK_TAN = mat('SG | housing ochre accent', (.67, .45, .25))
GLAZING = mat('SG | window glazing', (.13, .23, .27), .22)
BALCONY = mat('SG | corridor shadow', (.36, .42, .41))
DARK = mat('SG | drain slot dark', (.035, .045, .048))
LAMP = mat('SG | lamp warm glow', (.95, .78, .46), emission=2.0)


def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def empty(name, coll, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    coll.objects.link(o)
    o.empty_display_size = .3
    o.parent = parent
    o.location = loc
    return o


def place(o, name, coll, material, parent=None):
    o.name = name
    for old in tuple(o.users_collection):
        old.objects.unlink(o)
    coll.objects.link(o)
    if material:
        o.data.materials.append(material)
    o.parent = parent
    return o


def box(name, loc, dims, material, coll, parent, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = place(bpy.context.object, name, coll, material, parent)
    o.location = loc
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        b = o.modifiers.new('soft manufactured edges', 'BEVEL')
        b.width = bevel
        b.segments = 2
        o.modifiers.new('WEIGHTED_NORMAL', 'WEIGHTED_NORMAL')
    return o


def cylinder(name, loc, radius, depth, material, coll, parent,
             rotation=(0, 0, 0), vertices=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth)
    o = place(bpy.context.object, name, coll, material, parent)
    o.location = loc
    o.rotation_euler = rotation
    return o


def sphere(name, loc, radius, material, coll, parent, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=radius)
    o = place(bpy.context.object, name, coll, material, parent)
    o.location = loc
    o.scale = scale
    bpy.ops.object.shade_smooth()
    return o


def line(name, a, b, radius, material, coll, parent):
    va, vb = Vector(a), Vector(b)
    o = cylinder(name, (va + vb) / 2, radius, (vb - va).length,
                 material, coll, parent, vertices=10)
    o.rotation_euler = (vb - va).to_track_quat('Z', 'Y').to_euler()
    return o


def text(name, value, loc, size, material, coll, parent, rotation=(0, 0, 0)):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = value
    cu.size = size
    cu.extrude = .001
    o = bpy.data.objects.new(name, cu)
    coll.objects.link(o)
    o.parent = parent
    o.location = loc
    o.rotation_euler = rotation
    cu.materials.append(material)
    return o


def make_ground(coll, root):
    ground = empty('SG_GROUND_ASSEMBLY', coll, parent=root)
    # Footpath extends behind the shot camera, avoiding the old blank edge.
    box('sg_road_surface', (0, -2.6, -.065), (64, 9.0, .13), ROAD, coll, ground)
    box('sg_near_footpath', (0, 7.35, .075), (64, 11.25, .15), PAVEMENT, coll, ground)
    box('sg_near_kerb_face', (0, 1.76, .075), (64, .13, .15), KERB, coll, ground)
    box('sg_far_grass_verge', (0, -8.04, .02), (64, 1.78, .05), GRASS, coll, ground)
    box('sg_far_pedestrian_path', (0, -9.31, .055), (64, .85, .11), PAVEMENT, coll, ground)
    box('sg_distant_base', (0, -18, -.16), (90, 18, .30), GRASS, coll, ground)
    # Pavers and expansion joints are quiet details, not a distracting grid.
    for x in range(-30, 31, 3):
        box(f'sg_near_paver_joint_{x}', (x, 7.32, .152),
            (.014, 11.1, .004), BALCONY, coll, ground)
    for y in (3.6, 6.6, 9.6, 12.3):
        box(f'sg_near_paver_longitudinal_{y}', (0, y, .152),
            (64, .012, .004), BALCONY, coll, ground)
    # 400 mm tactile strip beside the kerb; individual tiles catch low light.
    box('sg_tactile_field', (-1.4, 2.13, .161), (15.0, .42, .016),
        TACTILE, coll, ground)
    for xi in range(-88, 61):
        x = xi * .10
        if not -8.85 <= x <= 6.05:
            continue
        for y in (1.98, 2.08, 2.18, 2.28):
            cylinder(f'sg_tactile_dot_{xi}_{int(y*100)}',
                     (x, y, .176), .017, .010, TACTILE,
                     coll, ground, vertices=8)
    # Continuous curb edge and drain grates make the gap legible in Shot 2.
    box('sg_bus_bay_yellow_edge', (0, 1.61, .004),
        (28, .055, .006), YELLOW, coll, ground)
    for x in range(-14, 15, 3):
        box(f'sg_kerb_drain_{x}', (x, 1.47, .009),
            (.50, .18, .014), BALCONY, coll, ground, .012)
        for dx in (-.15, -.05, .05, .15):
            box(f'sg_drain_slot_{x}_{dx}', (x + dx, 1.47, .018),
                (.016, .13, .004), DARK, coll, ground)
    for x in range(-30, 30, 4):
        box(f'sg_centre_dash_{x}', (x, -2.75, .005),
            (1.8, .07, .008), WHITE, coll, ground)
    for x in range(-30, 30, 7):
        box(f'sg_far_lane_dash_{x}', (x, -5.65, .005),
            (2.0, .055, .008), WHITE, coll, ground)
    # Painted bus bay outline and a small text cue, not an actual stop ID.
    for x in (-9, 7.5):
        box(f'sg_bus_bay_end_{x}', (x, .80, .006),
            (.06, 1.35, .006), YELLOW, coll, ground)
    text('sg_road_bus_word', 'BUS', (-3.65, .20, .008), .85,
         WHITE, coll, ground, rotation=(0, 0, math.pi/2))
    return ground


def make_block(name, x, y, width, depth, height, wall_mat, accent, coll, root):
    b = empty(f'SG_HDB_{name}_ASSEMBLY', coll, parent=root)
    box(f'sg_hdb_{name}_main', (x, y, height/2),
        (width, depth, height), wall_mat, coll, b, .035)
    box(f'sg_hdb_{name}_roof', (x, y, height+.16),
        (width+.18, depth+.16, .30), accent, coll, b, .025)
    box(f'sg_hdb_{name}_vertical_accent',
        (x-width*.38, y+depth/2+.03, height/2),
        (.18, .07, height-.4), accent, coll, b)
    floor_count = int(height / 2.65)
    column_count = max(3, int(width / 1.25))
    for floor in range(1, floor_count):
        z = .65 + floor * 2.65
        box(f'sg_hdb_{name}_corridor_{floor}',
            (x, y+depth/2+.10, z+.40),
            (width-.32, .24, .10), BALCONY, coll, b)
        box(f'sg_hdb_{name}_parapet_{floor}',
            (x, y+depth/2+.24, z+.18),
            (width-.30, .08, .38), wall_mat, coll, b)
        for column in range(column_count):
            xx = x - width/2 + .69 + column * ((width-1.35)/(column_count-1))
            box(f'sg_hdb_{name}_window_{floor}_{column}',
                (xx, y+depth/2+.025, z+1.17),
                (.62, .055, .87), GLAZING, coll, b, .015)
            box(f'sg_hdb_{name}_window_awning_{floor}_{column}',
                (xx, y+depth/2+.15, z+1.63),
                (.72, .30, .045), accent, coll, b)
    # Breezeway on the ground floor: open, shaded void suggested with dark panel.
    box(f'sg_hdb_{name}_void_deck', (x, y+depth/2+.04, 1.17),
        (width-.4, .06, 1.75), BALCONY, coll, b)
    text(f'sg_hdb_{name}_label', f'BLK {name}',
         (x-width/2+.38, y+depth/2+.09, 1.70), .29,
         WHITE, coll, b, rotation=(math.pi/2, 0, math.pi))
    return b


def make_trees(coll, root):
    trees = empty('SG_TROPICAL_GREENERY_ASSEMBLY', coll, parent=root)
    for i, x in enumerate((-23, -15, -8.5, 3.7, 11.5, 19.0, 27)):
        y = -7.9 + (.20 if i % 2 else -.12)
        height = 3.8 + (i % 3) * .45
        cylinder(f'sg_rain_tree_trunk_{i}', (x, y, height/2),
                 .12, height, TRUNK, coll, trees, vertices=10)
        line(f'sg_rain_tree_branch_L_{i}', (x, y, height-.8),
             (x-.85, y+.05, height+.15), .075, TRUNK, coll, trees)
        line(f'sg_rain_tree_branch_R_{i}', (x, y, height-.6),
             (x+.9, y-.10, height+.10), .075, TRUNK, coll, trees)
        for j, (dx, dy, dz, sx, sy) in enumerate((
                (-1.12, 0, .12, 1.25, .72),
                (0, 0, .54, 1.42, .82),
                (1.18, -.12, .15, 1.21, .76),
                (-.25, .32, -.18, 1.05, .66))):
            sphere(f'sg_rain_tree_canopy_{i}_{j}',
                   (x+dx, y+dy, height+dz), 1.18,
                   (LEAF_A, LEAF_B, LEAF_C)[(i+j) % 3], coll, trees,
                   scale=(sx, sy, .60))
    # Layered hedges and planted grasses soften the far verge.
    for i in range(85):
        x = -29 + i*.70
        y = -8.28 + RNG.uniform(-.37, .37)
        radius = RNG.uniform(.16, .33)
        sphere(f'sg_verge_shrub_{i}', (x, y, radius*.7), radius,
               (LEAF_A, LEAF_C)[i % 2], coll, trees,
               scale=(1.1, .82, .75))
    # A near-side tree stays off-camera in shot 2 but gives shot 1 depth.
    # Keep the first tree clear of the covered-linkway roof at X=-15.9..-9.1.
    for i, x in enumerate((-20.5, 15.5)):
        y = 6.25
        cylinder(f'sg_near_tree_trunk_{i}', (x, y, 2.05), .15,
                 4.1, TRUNK, coll, trees)
        for j, dx in enumerate((-1.1, 0, 1.1)):
            sphere(f'sg_near_tree_crown_{i}_{j}', (x+dx, y, 4.5+j*.12),
                   1.20, (LEAF_A, LEAF_B, LEAF_C)[j], coll, trees,
                   scale=(1.12, .82, .65))
    return trees


def make_street_furniture(coll, root):
    street = empty('SG_STREET_FURNITURE_ASSEMBLY', coll, parent=root)
    for i, x in enumerate((-18, 9, 24)):
        y = -7.15
        cylinder(f'sg_street_lamp_pole_{i}', (x, y, 2.55),
                 .08, 5.10, METAL, coll, street)
        line(f'sg_street_lamp_arm_{i}', (x, y, 4.91),
             (x+.85, y+.35, 4.91), .045, METAL, coll, street)
        box(f'sg_street_lamp_head_{i}', (x+.87, y+.36, 4.86),
            (.28, .22, .10), METAL, coll, street, .035)
        box(f'sg_street_lamp_glow_{i}', (x+.87, y+.36, 4.80),
            (.22, .17, .012), LAMP, coll, street)
    # Covered pedestrian connection, displaced left of the hero stop.
    box('sg_covered_walkway_roof', (-12.5, 6.55, 2.73),
        (6.8, 1.9, .13), BLK_BLUE, coll, street, .05)
    box('sg_covered_walkway_fascia', (-12.5, 5.57, 2.68),
        (6.8, .08, .09), YELLOW, coll, street)
    for x in (-15.6, -12.5, -9.4):
        for y in (5.72, 7.37):
            cylinder(f'sg_walkway_post_{x}_{y}', (x, y, 1.36),
                     .042, 2.72, METAL, coll, street)
    for i, x in enumerate((-8.8, -8.2, -7.6)):
        cylinder(f'sg_bollard_{i}', (x, 2.65, .39), .075,
                 .78, METAL, coll, street)
        box(f'sg_bollard_reflector_{i}', (x, 2.65, .53),
            (.16, .16, .05), WHITE, coll, street, .008)
    # Simple directional sign, deliberately fictional rather than place-specific.
    cylinder('sg_wayfinding_post', (11.5, 3.05, 1.52),
             .055, 3.04, METAL, coll, street)
    box('sg_wayfinding_panel', (11.5, 3.05, 2.68),
        (1.36, .11, .42), BLK_BLUE, coll, street, .025)
    text('sg_wayfinding_text', 'TOWN CENTRE  →',
         (10.89, 2.982, 2.65), .115, WHITE, coll, street,
         rotation=(math.pi/2, 0, 0))
    return street


def camera_at(loc, target, lens):
    bpy.ops.object.camera_add(location=loc)
    c = bpy.context.object
    c.name = 'TEMP_preview_camera'
    c.rotation_euler = (Vector(target)-c.location).to_track_quat('-Z', 'Y').to_euler()
    c.data.lens = lens
    bpy.context.scene.camera = c
    return c


def render_preview():
    scene = bpy.context.scene
    camera_at((12, 14, 6.2), (-1.8, 0, 2.7), 28)
    bpy.ops.object.light_add(type='SUN', location=(0, 0, 15))
    sun = bpy.context.object
    sun.name = 'TEMP_preview_sun'
    sun.data.energy = 1.5
    sun.rotation_euler = (math.radians(35), math.radians(-25), math.radians(30))
    scene.render.resolution_percentage = 50
    scene.render.filepath = str(OUT / 'preview_singapore_street_set.png')
    bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    scene.render.fps = 24
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.engine = 'BLENDER_EEVEE'
    scene.world.color = (.45, .50, .52)
    coll = collection('SG_STREET_SET | reusable Singapore-inspired environment')
    root = empty('SG_SET_ROOT | move entire streetscape', coll)
    make_ground(coll, root)
    for args in (
        ('18', -18.5, -13.5, 6.4, 3.1, 17.8, COOL, BLK_BLUE),
        ('19', -10.2, -14.6, 6.7, 3.2, 20.5, WARM, BLK_TAN),
        ('20', -.75, -13.5, 6.8, 3.0, 17.8, COOL, BLK_BLUE),
        ('21', 8.0, -14.4, 7.4, 3.2, 23.0, WARM, BLK_TAN),
        ('22', 18.0, -13.8, 7.2, 3.2, 18.0, COOL, BLK_BLUE),
    ):
        make_block(*args, coll, root)
    make_trees(coll, root)
    make_street_furniture(coll, root)
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Singapore_Street_Set_Master.blend'))
    render_preview()
    print('SINGAPORE_SET_COMPLETE')


if __name__ == '__main__':
    main()
