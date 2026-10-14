"""Reusable, procedural Singapore-style autonomous minibus for Blender 4.x.

Run in Blender's Scripting workspace, or:
    blender --background --python scripts/blender/build_av_bus.py -- --save bus.blend

Coordinate convention: +X = front, +Y = Singapore curb/entrance side, +Z = up.
All dimensions are metres. This is an original visual approximation of the supplied
reference vehicle, not a manufacturer's dimensionally certified CAD model.

After running, use the functions at the end of this file in Blender's Python console:
    root = bpy.data.objects["AV_BUS_ROOT"]
    set_doors(root, 1.0, frame=48)       # 0 closed, 1 open
    set_canopy(root, 1.0, frame=48)      # 0 retracted, 1 rain shelter extended
    set_ramp(root, 1.0, frame=48)        # 0 under floor, 1 unfolded
    set_side_display(root, "400", 16)   # route and passenger-seat count
    animate_boarding_stop(root, 72, 120)  # hardware sequence for a dwell
    set_exploded(root, 1.0, frame=96)    # 0 assembled, 1 exploded
    set_cutaway(root, True)              # hide the near-side glass/roof skin

The root object can be linked/duplicated into other scenes. Every movable assembly
is parented below it, so transform the root for a bus-driving animation.
"""

import bpy
import math
import sys
from mathutils import Matrix


PREFIX = "AVBUS_"
ROOT_NAME = "AV_BUS_ROOT"

CFG = {
    "length": 6.65,
    "width": 2.34,
    "body_bottom": 0.53,
    "roof_top": 2.99,
    "wheel_radius": 0.46,
    "wheel_x": (2.12, -2.20),
    "door_x": (0.26, 1.46),
    "door_side": 1,  # +Y: entrance/curb side in this asset convention
    "destination": "400  SHENTON WAY",
    "route_number": "400",
    "passenger_seats": 16,  # modelled passenger seats; excludes safety-operator seat
    "canopy_length": 5.55,
    "canopy_extension": 0.86,
    "ramp_length": 2.35,
}


def material(name, color, metallic=0.0, roughness=0.4, transmission=0.0,
             emission=None, emission_strength=0.0, opacity=1.0):
    mat = bpy.data.materials.get(PREFIX + name) or bpy.data.materials.new(PREFIX + name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Transmission Weight"].default_value = transmission
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if opacity < 1.0:
        # A controlled transparent mix reveals the cabin in both Eevee and
        # Cycles. Purely dark Principled transmission looked opaque in Eevee.
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        output = nodes.get("Material Output")
        clear = nodes.new('ShaderNodeBsdfTransparent')
        mix = nodes.new('ShaderNodeMixShader')
        mix.inputs[0].default_value = opacity
        links.new(clear.outputs[0], mix.inputs[1])
        links.new(bsdf.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], output.inputs['Surface'])
        mat.surface_render_method = 'DITHERED'
    return mat


M = {}


def init_materials():
    M.update({
        "lime": material("Lime body", (0.46, 0.82, 0.015), 0.16, 0.24),
        "lime_light": material("Roof lime", (0.61, 0.91, 0.07), 0.08, 0.29),
        "black": material("Black trim", (0.014, 0.020, 0.022), 0.10, 0.38),
        "rubber": material("Tyre rubber", (0.022, 0.025, 0.027), 0.0, 0.83),
        "glass": material("Smoked glass", (0.075, 0.14, 0.16), 0.0, 0.12,
                          0.12, opacity=0.36),
        "door_glass": material("Door glass", (0.13, 0.23, 0.24), 0.0, 0.10,
                               0.15, opacity=0.30),
        "steel": material("Brushed metal", (0.54, 0.59, 0.57), 0.72, 0.28),
        "aluminium": material("Bright aluminium", (0.74, 0.77, 0.74), 0.78, 0.23),
        "floor": material("Dark floor", (0.105, 0.13, 0.14), 0.0, 0.82),
        "interior": material("Interior ivory", (0.64, 0.68, 0.64), 0.0, 0.69),
        "seat_blue": material("Teal seats", (0.02, 0.23, 0.30), 0.0, 0.68),
        "seat_red": material("Priority red seats", (0.53, 0.065, 0.09), 0.0, 0.65),
        "yellow": material("Safety yellow", (0.95, 0.64, 0.015), 0.02, 0.43),
        "access_blue": material("Accessibility blue", (0.025, 0.28, 0.61),
                                0.0, 0.55),
        "access_white": material("Accessibility white", (0.94, 0.97, 0.98),
                                 0.0, 0.60),
        "white": material("White lamps", (0.86, 0.95, 1.0), 0.04, 0.16,
                          emission=(0.8, 0.95, 1.0), emission_strength=1.4),
        "red": material("Brake red", (0.66, 0.012, 0.015), 0.0, 0.19,
                        emission=(1.0, 0.005, 0.01), emission_strength=0.6),
        "amber": material("Amber LEDs", (1.0, 0.40, 0.015), 0.0, 0.31,
                          emission=(1.0, 0.32, 0.005), emission_strength=1.5),
        "sensor": material("Sensor housing", (0.19, 0.25, 0.21), 0.18, 0.32),
        "lens": material("Camera lens", (0.012, 0.025, 0.055), 0.32, 0.07),
    })


def collection(name, parent=None):
    coll = bpy.data.collections.new(PREFIX + name)
    (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def move_to_collection(obj, coll):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    coll.objects.link(obj)


def parent_to(obj, parent):
    if parent is not None:
        obj.parent = parent
    return obj


def empty(name, coll, parent=None, location=(0, 0, 0)):
    obj = bpy.data.objects.new(PREFIX + name, None)
    coll.objects.link(obj)
    obj.location = location
    obj.empty_display_type = 'PLAIN_AXES'
    obj.empty_display_size = 0.19
    return parent_to(obj, parent)


def cube(name, loc, scale, mat, coll, parent=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = PREFIX + name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    move_to_collection(obj, coll)
    if bevel:
        mod = obj.modifiers.new("Soft manufactured edges", 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        mod.affect = 'EDGES'
        obj.modifiers.new("Weighted normals", 'WEIGHTED_NORMAL')
    return parent_to(obj, parent)


def cylinder(name, loc, radius, depth, mat, coll, parent=None, vertices=32,
             rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius,
                                        depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = PREFIX + name
    obj.data.materials.append(mat)
    move_to_collection(obj, coll)
    obj.modifiers.new("Weighted normals", 'WEIGHTED_NORMAL')
    return parent_to(obj, parent)


def torus(name, loc, major, minor, mat, coll, parent=None,
          rotation=(math.pi / 2, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_segments=36, minor_segments=10,
                                     location=loc, rotation=rotation,
                                     major_radius=major, minor_radius=minor)
    obj = bpy.context.object
    obj.name = PREFIX + name
    obj.data.materials.append(mat)
    move_to_collection(obj, coll)
    return parent_to(obj, parent)


def rod(name, a, b, radius, mat, coll, parent=None, vertices=12):
    from mathutils import Vector
    av, bv = Vector(a), Vector(b)
    direction = bv - av
    obj = cylinder(name, (av + bv) * 0.5, radius, direction.length,
                   mat, coll, parent, vertices=vertices)
    obj.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
    return obj


def text_obj(name, body, loc, size, mat, coll, parent=None, side=None,
             align='CENTER'):
    curve = bpy.data.curves.new(PREFIX + name, 'FONT')
    curve.body = body
    curve.size = size
    curve.align_x = align
    curve.align_y = 'CENTER'
    curve.extrude = 0.0008
    curve.materials.append(mat)
    obj = bpy.data.objects.new(PREFIX + name, curve)
    coll.objects.link(obj)
    obj.location = loc
    if side == 1:  # local X to -X, local Y to +Z, outward normal +Y
        obj.rotation_euler = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0))).to_euler()
    elif side == -1:  # local X to +X, local Y to +Z, outward normal -Y
        obj.rotation_euler = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0))).to_euler()
    elif side == 2:  # forward-facing +X
        obj.rotation_euler = Matrix(((0, 0, 1), (1, 0, 0), (0, 1, 0))).to_euler()
    return parent_to(obj, parent)


def arch_trim(name, x, y, z, radius, mat, coll, parent):
    """Visible semicircular arch over a wheel, on a side-facing plane."""
    points = []
    for i in range(17):
        angle = math.pi - i * math.pi / 16
        points.append((x + radius * math.cos(angle), y,
                       z + radius * math.sin(angle)))
    for i in range(len(points) - 1):
        rod(f"{name}_{i:02}", points[i], points[i + 1], 0.024, mat, coll, parent)


def build_shell(groups, c):
    shell, roof, glazing, trim, decals = [groups[k] for k in
                                          ('shell', 'roof', 'glazing', 'trim', 'decals')]
    half_w = c['width'] / 2
    # Separate subassemblies leave a genuine open cabin; no opaque cube sits behind glazing.
    cube("Underframe", (0, 0, 0.57), (6.45, 2.17, 0.17), M['black'], shell,
         bevel=0.05)
    cube("Cabin floor", (0, 0, 0.73), (6.17, 2.15, 0.085), M['floor'], shell,
         bevel=0.014)
    cube("Front fascia lower", (3.295, 0, 1.105), (0.14, 2.25, 1.11),
         M['lime'], shell, bevel=0.075)
    cube("Rear fascia lower", (-3.295, 0, 1.105), (0.14, 2.25, 1.11),
         M['lime'], shell, bevel=0.058)
    cube("Front roof header", (3.25, 0, 2.74), (0.23, 2.25, 0.39),
         M['lime'], roof, bevel=0.055)
    cube("Rear roof header", (-3.25, 0, 2.74), (0.23, 2.25, 0.39),
         M['lime'], roof, bevel=0.055)
    cube("Roof lid / removable", (0, 0, 2.96), (6.48, 2.27, 0.19),
         M['lime_light'], roof, bevel=0.10)
    cube("Roof underside", (0, 0, 2.79), (6.12, 2.11, 0.08),
         M['interior'], roof, bevel=0.02)
    cube("Front windshield", (3.329, 0, 2.015), (0.055, 2.07, 1.29),
         M['glass'], glazing, bevel=0.075)
    cube("Front screen lower gasket", (3.35, 0, 1.38), (0.065, 2.10, 0.048),
         M['black'], trim)
    cube("Rear window", (-3.329, 0, 2.15), (0.055, 1.98, 0.88),
         M['glass'], glazing, bevel=0.045)
    cube("Rear window gasket", (-3.351, 0, 2.15), (0.038, 2.07, 0.98),
         M['black'], trim, bevel=0.025)

    # Segmented side panels create actual door and wheel spaces. Most windows are
    # individual panes, which can be hidden for cutaway and interior shots.
    door_a, door_b = c['door_x']
    for side in (-1, 1):
        y = side * (half_w - 0.04)
        lower = [(-3.12, -2.75), (-1.69, door_a if side == 1 else 1.91),
                 (door_b if side == 1 else 1.91, 1.70), (2.55, 3.13)]
        # Wheel cut-outs: rear -2.2 and front +2.12.
        for i, (a, b) in enumerate(lower):
            if b - a > 0.02:
                cube(f"Lower side {side} segment {i}", ((a+b)/2, y, 1.08),
                     (b-a, 0.105, 0.78), M['lime'], shell, bevel=0.025)
        for wheel_x in c['wheel_x']:
            arch_trim(f"Wheel arch {side} {wheel_x}", wheel_x,
                      side * (half_w + 0.022), 0.50, 0.63,
                      M['lime'], trim, None)
        cube(f"Sill {side}", (0, y, 0.73), (6.1, 0.083, 0.10),
             M['black'], trim, bevel=0.018)
        cube(f"Waist stripe {side}", (0, side*(half_w+0.017), 1.48),
             (6.10, 0.018, 0.064), M['aluminium'], trim)
        # Outline the dark window ribbon without filling it. An opaque full-height
        # band would make the detailed cabin invisible through the glass.
        cube(f"Window band upper rail {side}", (0, y, 2.62),
             (6.20, 0.067, 0.085), M['black'], trim, bevel=0.020)
        cube(f"Window band lower rail {side}", (0, y, 1.54),
             (6.20, 0.067, 0.075), M['black'], trim, bevel=0.018)
        cube(f"Roof gutter {side}", (0, side*(half_w+0.006), 2.70),
             (6.32, 0.11, 0.11), M['lime_light'], roof, bevel=0.032)

        # Each side's black band is only a narrow frame shell. Glazing is offset
        # outward. Interior is visible through the lighter-transmission panes.
        if side == 1:
            panes = [(-2.74, -1.86), (-1.83, -0.82), (-0.79, 0.19),
                     (1.53, 2.78)]
        else:
            panes = [(-2.74, -1.85), (-1.82, -0.88), (-0.85, 0.16),
                     (0.19, 1.17), (1.20, 2.78)]
        for i, (a, b) in enumerate(panes):
            cube(f"Side glass {side} {i}", ((a+b)/2, side*(half_w+0.005), 2.09),
                 (b-a-0.045, 0.028, 0.96), M['glass'], glazing, bevel=0.028)
            cube(f"Window mullion {side} {i}", (b, side*(half_w+0.018), 2.09),
                 (0.033, 0.054, 1.02), M['black'], trim)
        for wheel_x in c['wheel_x']:
            cube(f"Wheel crown body {side} {wheel_x}",
                 (wheel_x, y, 1.29), (1.07, 0.105, 0.32),
                 M['lime'], shell, bevel=0.020)
        for x in (-3.09, 3.09):
            cube(f"End pillar {side} {x}", (x, side*(half_w-0.045), 2.02),
                 (0.12, 0.15, 1.49), M['lime'], shell, bevel=0.029)
        text_obj(f"Side name {side}", "SG  BUS", (-0.85, side*(half_w+0.030), 1.16),
                 0.22, M['black'], decals, side=side)
        text_obj(f"Side AV marking {side}", "AUTONOMOUS", (-2.13, side*(half_w+0.031), 1.18),
                 0.075, M['black'], decals, side=side)

    # Outward lighting, LED board, mirrors and front details.
    cube("Front destination screen", (3.372, 0, 2.75),
         (0.035, 1.85, 0.23), M['black'], trim, bevel=0.025)
    text_obj("Front destination text", c['destination'], (3.400, 0, 2.73),
             0.095, M['amber'], decals, side=2)
    cube("Rear destination screen", (-3.374, 0, 2.71),
         (0.035, 1.82, 0.24), M['black'], trim, bevel=0.018)
    cube("Front bumper", (3.39, 0, 0.66), (0.13, 2.27, 0.16),
         M['lime'], shell, bevel=0.058)
    cube("Rear bumper", (-3.39, 0, 0.66), (0.13, 2.27, 0.16),
         M['lime'], shell, bevel=0.055)
    cube("Front grille slit", (3.371, 0, 1.20), (0.032, 1.24, 0.045),
         M['black'], trim, bevel=0.012)
    for side in (-1, 1):
        y = side * 0.94
        for i, z in enumerate((1.18, 0.99, 0.79)):
            cube(f"Front light bezel {side} {i}", (3.38, y, z),
                 (0.056, 0.30, 0.15), M['black'], trim, bevel=0.055)
            cylinder(f"Front lamp {side} {i}", (3.422, y, z), 0.048, 0.017,
                     M['white'] if i < 2 else M['amber'], trim,
                     rotation=(0, math.pi/2, 0))
        cube(f"Tail light bezel {side}", (-3.379, y, 1.18),
             (0.045, 0.20, 0.60), M['black'], trim, bevel=0.035)
        for z in (1.40, 1.19, 0.98):
            cylinder(f"Tail lamp {side} {z}", (-3.409, y, z), 0.060, 0.013,
                     M['red'] if z != 1.19 else M['white'], trim,
                     rotation=(0, math.pi/2, 0))
        rod(f"Mirror arm {side}", (2.84, side*1.12, 2.16),
            (3.21, side*1.34, 2.17), 0.028, M['black'], trim)
        cube(f"Mirror housing {side}", (3.23, side*1.36, 2.16),
             (0.19, 0.10, 0.25), M['black'], trim, bevel=0.042)
    for y in (-0.69, 0.69):
        rod(f"Wiper {y}", (3.39, y, 1.44), (3.40, y-0.35, 1.78),
            0.014, M['black'], trim)
    return roof


def build_wheels(group, c):
    half_w = c['width'] / 2
    for axle, x in zip(("front", "rear"), c['wheel_x']):
        for side in (-1, 1):
            anchor = empty(f"WHEEL_{axle}_{'curb' if side == 1 else 'road'}",
                           group, location=(x, side*(half_w-0.05), c['wheel_radius']))
            anchor["animation_role"] = "spin_about_local_Y"
            cylinder(f"{axle} tyre {side}", (0, side*0.085, 0),
                     c['wheel_radius'], 0.22, M['rubber'], group, anchor,
                     vertices=48, rotation=(math.pi/2, 0, 0))
            torus(f"{axle} tyre shoulder {side}", (0, side*0.21, 0),
                  0.35, 0.085, M['rubber'], group, anchor)
            cylinder(f"{axle} alloy rim {side}", (0, side*0.202, 0),
                     0.285, 0.040, M['aluminium'], group, anchor,
                     vertices=40, rotation=(math.pi/2, 0, 0))
            cylinder(f"{axle} hub {side}", (0, side*0.234, 0),
                     0.085, 0.045, M['steel'], group, anchor,
                     rotation=(math.pi/2, 0, 0))
            for i in range(8):
                a = 2*math.pi*i/8
                cylinder(f"{axle} rim bolt {side} {i}",
                         (0.173*math.cos(a), side*0.238,
                          0.173*math.sin(a)), 0.016, 0.012,
                         M['black'], group, anchor, vertices=12,
                         rotation=(math.pi/2, 0, 0))


def build_doors(group, c):
    y = c['width']/2 + 0.035
    a, b = c['door_x']
    mid = (a+b)/2
    width = (b-a)/2
    cube("Door header", (mid, y, 2.64), (b-a+0.08, 0.12, 0.12),
         M['black'], group, bevel=0.020)
    cube("Door step", (mid, y-0.18, 0.71), (b-a+0.04, 0.33, 0.10),
         M['yellow'], group, bevel=0.018)
    for i in (0, 1):
        leaf_x = a + width*(i+0.5)
        leaf = empty(f"DOOR_LEAF_{i}", group, location=(leaf_x, y, 1.68))
        leaf["closed_x"] = leaf_x
        leaf["open_delta_x"] = -0.46 if i == 0 else 0.46
        cube(f"Door leaf {i} lower", (0, 0, -0.43),
             (width-0.015, 0.073, 0.79), M['lime'], group, leaf, bevel=0.016)
        cube(f"Door leaf {i} glass", (0, 0, 0.47),
             (width-0.057, 0.038, 0.90), M['door_glass'], group, leaf,
             bevel=0.018)
        cube(f"Door leaf {i} vertical frame", ((-1 if i == 0 else 1)*width*0.48,
             0.016, 0.42), (0.034, 0.060, 1.02), M['black'], group, leaf)
        cube(f"Door leaf {i} handle", ((1 if i == 0 else -1)*0.095,
             0.065, -0.05), (0.035, 0.045, 0.24), M['steel'], group, leaf,
             bevel=0.012)
    for x in (a-0.025, b+0.025):
        cube(f"Door side frame {x}", (x, y, 1.77),
             (0.058, 0.11, 1.76), M['black'], group, bevel=0.015)


def build_side_display(group, c):
    """Curb-facing route/capacity display, legible before passengers board."""
    y = c['width']/2 + 0.095
    x = 2.28  # forward side window, clear of the passenger door
    cube("Side route display housing", (x, y, 2.33),
         (0.83, 0.11, 0.51), M['black'], group, bevel=0.042)
    cube("Side route display inset", (x, y+0.061, 2.33),
         (0.74, 0.012, 0.42), M['lens'], group, bevel=0.014)
    route = text_obj("SIDE_ROUTE_NUMBER", str(c['route_number']),
                     (x, y+0.072, 2.416), 0.265, M['amber'], group, side=1)
    seats = text_obj("SIDE_PASSENGER_SEATS",
                     f"{int(c['passenger_seats']):02d} SEATS",
                     (x, y+0.072, 2.217), 0.106, M['white'], group, side=1)
    route["display_role"] = "route_number"
    seats["display_role"] = "passenger_seats"


def build_canopy(group, c):
    """Roof-integrated slide-out weather shelter along the curb side."""
    # The cassette stays at the roof edge; the slim panel retracts beneath
    # the roof skin and slides over the door/boarding area when deployed.
    cube("Rain canopy cassette", (0.04, c['width']/2-0.055, 2.852),
         (c['canopy_length']+0.20, 0.20, 0.15), M['lime'], group,
         bevel=0.048)
    slide = empty("RAIN_CANOPY_SLIDER", group,
                  location=(0.04, 0.30, 2.818))
    slide["stowed_y"] = 0.30
    slide["deployed_y"] = c['width']/2-0.025
    length = c['canopy_length']
    extension = c['canopy_extension']
    cube("Rain canopy panel", (0, extension/2, 0),
         (length, extension, 0.062), M['lime_light'], group, slide,
         bevel=0.033)
    # Thin edge section and two visible telescopic runners help the shelter
    # read as a manufactured part rather than a floating roof slab.
    cube("Rain canopy outer drip edge", (0, extension+0.012, -0.043),
         (length, 0.055, 0.10), M['lime'], group, slide, bevel=0.023)
    for i, x in enumerate((-length*0.37, length*0.37)):
        cube(f"Rain canopy runner {i}", (x, extension/2, -0.045),
             (0.044, extension-0.08, 0.045), M['steel'], group, slide,
             bevel=0.010)
    cube("Canopy underside light", (0, extension*0.76, -0.049),
         (length-0.45, 0.035, 0.010), M['white'], group, slide,
         bevel=0.005)
    return slide


def build_ramp(group, c):
    """Straight-sliding underfloor ramp with a final downward curb tilt."""
    a, b = c['door_x']
    door_mid = (a+b)/2
    door_width = b-a
    hinge_y = c['width']/2+0.060
    hinge_z = 0.700
    stow_z = 0.575
    length = c['ramp_length']
    pivot = empty("BOARDING_RAMP_PIVOT", group,
                  location=(door_mid, hinge_y-length, stow_z))
    pivot["stowed_y"] = hinge_y-length
    pivot["deployed_y"] = hinge_y
    pivot["stowed_z"] = stow_z
    pivot["deployed_z"] = hinge_z
    pivot["deployed_angle_rad"] = -math.asin((hinge_z-0.14)/length)
    cube("Boarding ramp deck", (0, length/2, 0),
         (door_width-0.09, length, 0.052), M['steel'], group, pivot,
         bevel=0.019)
    cube("Boarding ramp non-slip centre", (0, length/2, 0.030),
         (door_width-0.18, length-0.12, 0.009), M['floor'], group, pivot,
         bevel=0.006)
    for side in (-1, 1):
        cube(f"Ramp raised guide lip {side}",
             (side*(door_width/2-0.076), length/2, 0.055),
             (0.047, length, 0.105), M['yellow'], group, pivot,
             bevel=0.016)
    for i, y in enumerate((0.12, length-0.14)):
        cube(f"Ramp caution stripe {i}", (0, y, 0.040),
             (door_width-0.22, 0.065, 0.010), M['yellow'], group, pivot)
    cube("Ramp hinged knuckle", (0, 0.025, -0.018),
         (door_width-0.06, 0.090, 0.095), M['black'], group, pivot,
         bevel=0.020)
    # Local +Y always points outward. In storage the entire panel sits under
    # the cabin floor; it translates along +Y before tipping toward the curb.
    return pivot


def build_seat(group, name, x, y, facing=1, priority=False, floor_lift=0.0):
    seat_mat = M['seat_red'] if priority else M['seat_blue']
    anchor = empty(f"SEAT_{name}", group, location=(x, y, floor_lift))
    # Local +X is the direction the seated passenger faces.
    if facing == -1:
        anchor.rotation_euler[2] = math.pi
    cube(f"{name} pedestal", (0, 0, 0.96), (0.12, 0.12, 0.47),
         M['steel'], group, anchor, bevel=0.020)
    cube(f"{name} cushion", (0, 0, 1.17), (0.48, 0.47, 0.12),
         seat_mat, group, anchor, bevel=0.072)
    cube(f"{name} back", (-0.23, 0, 1.48), (0.13, 0.47, 0.64),
         seat_mat, group, anchor, bevel=0.061)
    cube(f"{name} back rim", (-0.303, 0, 1.57), (0.035, 0.46, 0.44),
         M['black'], group, anchor, bevel=0.022)
    for sy in (-0.22, 0.22):
        rod(f"{name} arm {sy}", (-0.18, sy, 1.38),
            (0.21, sy, 1.31), 0.019, M['steel'], group, anchor)
    return anchor


def build_interior(group, c):
    cube("Inner wall road side", (0, -1.08, 1.12),
         (6.10, 0.035, 0.70), M['interior'], group)
    cube("Front cabin partition", (2.70, 0, 1.54),
         (0.055, 1.96, 1.56), M['interior'], group, bevel=0.016)
    cube("Rear cabin partition", (-3.10, 0, 1.39),
         (0.045, 2.00, 1.20), M['interior'], group, bevel=0.018)
    cube("Rear raised plinth", (-2.50, 0, 0.88),
         (1.29, 2.03, 0.25), M['floor'], group, bevel=0.035)
    # Looking from the front toward the rear, left is -Y and right is +Y.
    # Lower floor: three rows, two left + one right = nine passenger seats.
    # The +Y door / wheelchair clear zone remains forward of these rows.
    lower_rows = (-0.02, -0.72, -1.42)
    for row, x in enumerate(lower_rows, start=1):
        build_seat(group, f"lower_L{row}_outer", x, -0.81)
        build_seat(group, f"lower_L{row}_inner", x, -0.31)
        build_seat(group, f"lower_R{row}", x, 0.77,
                   priority=(row == 1))

    # Raised rear platform: front row has 2 left + 1 right; back row has
    # 2 left + 2 right, like a full-width rear bench. The seat anchors are
    # lifted by the same 0.23 m step as the platform, not buried in its floor.
    raised_rows = (-2.16, -2.72)
    raised_lift = 0.23
    for row, x in enumerate(raised_rows, start=1):
        build_seat(group, f"raised_L{row}_outer", x, -0.81,
                   floor_lift=raised_lift)
        build_seat(group, f"raised_L{row}_inner", x, -0.31,
                   floor_lift=raised_lift)
    build_seat(group, "raised_R1", raised_rows[0], 0.77,
               floor_lift=raised_lift)
    build_seat(group, "raised_R2_inner", raised_rows[1], 0.31,
               floor_lift=raised_lift)
    build_seat(group, "raised_R2_outer", raised_rows[1], 0.81,
               floor_lift=raised_lift)

    # Ceiling, rails, grab poles, hanging grips and interior lighting.
    for side in (-1, 1):
        rod(f"Ceiling grab rail {side}", (-2.71, side*0.64, 2.58),
            (2.49, side*0.64, 2.58), 0.022, M['steel'], group)
        for i, x in enumerate((-2.18, -1.18, -0.19, 1.68)):
            # The front road-side pole would pass through the safety-operator
            # seat; leave that station unobstructed.
            if side == -1 and i == 3:
                continue
            rod(f"Vertical grab pole {side} {i}", (x, side*0.58, 0.77),
                (x, side*0.58, 2.60), 0.022, M['steel'], group)
        for i, x in enumerate((-1.79, -0.84, 0.10, 1.58)):
            rod(f"Hanging grip stalk {side} {i}", (x, side*0.64, 2.57),
                (x, side*0.64, 2.33), 0.012, M['black'], group)
            torus(f"Hanging grip {side} {i}", (x, side*0.64, 2.28),
                  0.070, 0.012, M['yellow'], group,
                  rotation=(0, math.pi/2, 0))
        cube(f"Ceiling light {side}", (-0.16, side*0.39, 2.724),
             (4.75, 0.085, 0.018), M['white'], group, bevel=0.012)

    # AV safety-operator station remains plausible for a trial vehicle.
    cube("Safety operator console", (2.15, -0.62, 1.12),
         (0.66, 0.77, 0.64), M['black'], group, bevel=0.060)
    cube("Operator display", (2.25, -0.60, 1.51),
         (0.36, 0.45, 0.035), M['lens'], group, bevel=0.015)
    build_seat(group, "safety_operator", 1.54, -0.70)
    cube("Fare validator body", (1.60, 0.50, 1.38),
         (0.24, 0.19, 0.40), M['sensor'], group, bevel=0.040)
    cube("Fare validator display", (1.60, 0.604, 1.45),
         (0.18, 0.014, 0.20), M['lens'], group, bevel=0.011)
    rod("Fare validator post", (1.60, 0.50, 0.76),
        (1.60, 0.50, 1.20), 0.026, M['steel'], group)
    # Floor-mounted accessibility marking in the clear entrance-side bay,
    # behind and across the aisle from the safety-operator station.
    bay_x, bay_y, mark_z = 0.59, 0.53, 0.797
    cube("Wheelchair bay blue plate", (bay_x, bay_y, 0.787),
         (0.53, 0.46, 0.006), M['access_blue'], group, bevel=0.018)
    torus("Wheelchair symbol main wheel", (bay_x-0.055, bay_y-0.055, mark_z),
          0.093, 0.012, M['access_white'], group, rotation=(0, 0, 0))
    cylinder("Wheelchair symbol head", (bay_x-0.085, bay_y+0.138, mark_z),
             0.027, 0.003, M['access_white'], group, vertices=24)
    rod("Wheelchair symbol back", (bay_x-0.086, bay_y+0.098, mark_z),
        (bay_x-0.086, bay_y+0.022, mark_z), 0.011,
        M['access_white'], group)
    rod("Wheelchair symbol seat", (bay_x-0.086, bay_y+0.028, mark_z),
        (bay_x+0.094, bay_y+0.028, mark_z), 0.011,
        M['access_white'], group)
    rod("Wheelchair symbol leg", (bay_x+0.080, bay_y+0.027, mark_z),
        (bay_x+0.143, bay_y-0.082, mark_z), 0.011,
        M['access_white'], group)
    rod("Wheelchair symbol footrest", (bay_x+0.143, bay_y-0.082, mark_z),
        (bay_x+0.190, bay_y-0.082, mark_z), 0.011,
        M['access_white'], group)
    cylinder("Wheelchair symbol front caster", (bay_x+0.173, bay_y-0.114, mark_z),
             0.020, 0.003, M['access_white'], group, vertices=16)


def build_sensors(group, c):
    # Architecture is intentionally separated for clean exploded-view animation.
    lidar = empty("SENSOR_LIDAR_FRONT_ASSEMBLY", group, location=(2.47, 0, 3.02))
    cube("Lidar plinth", (0, 0, 0.085), (0.63, 0.43, 0.16),
         M['lime'], group, lidar, bevel=0.065)
    cylinder("Lidar rotating puck", (0, 0, 0.21), 0.17, 0.14,
             M['sensor'], group, lidar, vertices=40)
    cylinder("Lidar dark band", (0, 0, 0.26), 0.17, 0.055,
             M['lens'], group, lidar, vertices=40)

    front_pod = empty("SENSOR_FORWARD_CAMERA_ASSEMBLY", group,
                      location=(2.78, 0, 3.01))
    cube("Forward camera housing", (0, 0, 0.18),
         (0.44, 0.68, 0.32), M['lime_light'], group, front_pod,
         bevel=0.055)
    for i, y in enumerate((-0.20, 0, 0.20)):
        cylinder(f"Forward camera lens {i}", (0.234, y, 0.17),
                 0.055, 0.012, M['lens'], group, front_pod,
                 rotation=(0, math.pi/2, 0))
    cube("Roof AV GNSS cap", (-0.16, 0, 3.075),
         (0.45, 0.45, 0.14), M['lime_light'], group, bevel=0.07)
    cube("Rear AV perception pod", (-2.61, 0, 3.10),
         (0.37, 0.55, 0.22), M['lime_light'], group, bevel=0.062)
    cylinder("Rear perception camera", (-2.816, 0, 3.13),
             0.058, 0.016, M['lens'], group,
             rotation=(0, math.pi/2, 0))
    for side in (-1, 1):
        cube(f"Side camera housing {side}", (1.41, side*0.98, 3.01),
             (0.24, 0.25, 0.15), M['lime_light'], group, bevel=0.032)
        cylinder(f"Side camera lens {side}", (1.41, side*1.116, 3.02),
                 0.043, 0.012, M['lens'], group,
                 rotation=(math.pi/2, 0, 0))
    cylinder("Amber safety beacon", (2.89, -0.56, 3.08),
             0.068, 0.14, M['amber'], group, vertices=24)


def build_bus(config=None, clear_previous=True):
    """Build a reusable rig and return its root Empty object.

    Existing objects owned by this script are removed only if clear_previous=True;
    unrelated scene objects are always retained.
    """
    c = dict(CFG)
    if config:
        c.update(config)
    if clear_previous:
        old = bpy.data.collections.get(PREFIX + "MASTER")
        if old:
            for obj in list(old.all_objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            for child in list(old.children):
                bpy.data.collections.remove(child)
            bpy.data.collections.remove(old)
    init_materials()
    master = collection("MASTER")
    root = empty("ROOT", master)
    root.name = ROOT_NAME
    root["asset"] = "Singapore-style AV minibus visual prototype"
    root["forward_axis"] = "+X"
    root["curb_door_side"] = "+Y"
    root["door_open"] = 0.0
    root["exploded"] = 0.0
    root["model_length_m"] = c['length']
    root["model_width_m"] = c['width']
    group_names = ('shell', 'roof', 'glazing', 'trim', 'decals',
                   'doors', 'wheels', 'interior', 'sensors',
                   'display', 'canopy', 'ramp')
    groups = {}
    for name in group_names:
        coll = collection(name.upper(), master)
        anchor = empty(name.upper() + "_ASSEMBLY", coll, root)
        groups[name] = coll
        groups[name + '_anchor'] = anchor

    build_shell(groups, c)
    build_wheels(groups['wheels'], c)
    build_doors(groups['doors'], c)
    build_interior(groups['interior'], c)
    build_sensors(groups['sensors'], c)
    build_side_display(groups['display'], c)
    build_canopy(groups['canopy'], c)
    build_ramp(groups['ramp'], c)

    # All loose objects in an assembly are attached to its anchor. Door leaves,
    # wheel pivots and sensor subassemblies already have their own children.
    for name in group_names:
        coll = groups[name]
        anchor = groups[name + '_anchor']
        for obj in list(coll.objects):
            if obj != anchor and obj.parent is None:
                obj.parent = anchor
    root["roof_assembly"] = groups['roof_anchor'].name
    root["interior_assembly"] = groups['interior_anchor'].name
    root["sensor_assembly"] = groups['sensors_anchor'].name
    root["door_assembly"] = groups['doors_anchor'].name
    root["canopy_assembly"] = groups['canopy_anchor'].name
    root["ramp_assembly"] = groups['ramp_anchor'].name
    root["glazing_collection"] = groups['glazing'].name
    root["route_number"] = str(c['route_number'])
    root["passenger_seats"] = int(c['passenger_seats'])
    root["canopy_open"] = 0.0
    root["ramp_open"] = 0.0
    bpy.context.scene["av_bus_rig"] = root.name
    # Both shelter and ramp remain stowed in the default, drive-ready asset.
    set_canopy(root, 0.0)
    set_ramp(root, 0.0)
    return root


def _asset_descendants(root):
    result = []
    stack = list(root.children)
    while stack:
        obj = stack.pop()
        result.append(obj)
        stack.extend(obj.children)
    return result


def set_doors(root, fraction, frame=None):
    """Slide the two passenger-door leaves apart; optionally insert keyframes."""
    fraction = max(0.0, min(1.0, float(fraction)))
    for obj in _asset_descendants(root):
        if "closed_x" in obj and "open_delta_x" in obj:
            obj.location.x = obj["closed_x"] + fraction * obj["open_delta_x"]
            if frame is not None:
                obj.keyframe_insert(data_path="location", frame=frame)
    root["door_open"] = fraction
    if frame is not None:
        root.keyframe_insert(data_path='["door_open"]', frame=frame)


def set_canopy(root, fraction, frame=None):
    """Slide the rain shelter out (1) or beneath the roof (0)."""
    fraction = max(0.0, min(1.0, float(fraction)))
    for obj in _asset_descendants(root):
        if "stowed_y" in obj and "deployed_y" in obj:
            obj.location.y = (obj["stowed_y"] +
                              fraction*(obj["deployed_y"]-obj["stowed_y"]))
            if frame is not None:
                obj.keyframe_insert(data_path="location", frame=frame)
    root["canopy_open"] = fraction
    if frame is not None:
        root.keyframe_insert(data_path='["canopy_open"]', frame=frame)


def set_ramp(root, fraction, frame=None):
    """Slide ramp straight outward, then tilt its free end to the curb.

    The landing height is illustrative, not a certified accessibility slope.
    """
    fraction = max(0.0, min(1.0, float(fraction)))
    slide = min(1.0, fraction / 0.70)
    tilt = max(0.0, (fraction - 0.70) / 0.30)
    for obj in _asset_descendants(root):
        if "deployed_angle_rad" in obj:
            obj.location.y = obj["stowed_y"] + slide*(obj["deployed_y"]-obj["stowed_y"])
            obj.location.z = obj["stowed_z"] + tilt*(obj["deployed_z"]-obj["stowed_z"])
            obj.rotation_euler.x = obj["deployed_angle_rad"] * tilt
            obj.rotation_euler.z = 0.0
            if frame is not None:
                obj.keyframe_insert(data_path="location", frame=frame)
                obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    root["ramp_open"] = fraction
    if frame is not None:
        root.keyframe_insert(data_path='["ramp_open"]', frame=frame)


def set_side_display(root, route_number=None, passenger_seats=None):
    """Update the curb-facing route and modelled seat-count labels."""
    if route_number is not None:
        root["route_number"] = str(route_number)
    if passenger_seats is not None:
        root["passenger_seats"] = max(0, int(passenger_seats))
    for obj in _asset_descendants(root):
        role = obj.get("display_role")
        if role == "route_number":
            obj.data.body = str(root["route_number"])
        elif role == "passenger_seats":
            obj.data.body = f"{int(root['passenger_seats']):02d} SEATS"


def animate_boarding_stop(root, stop_frame, dwell_frames=120):
    """Keyframe stop-only boarding hardware; does not move the bus itself.

    Keep AV_BUS_ROOT stationary between stop_frame and the departure frame.
    Canopy opens first, then doors, then ramp; departure reverses the order.
    """
    stop_frame = int(stop_frame)
    dwell_frames = int(dwell_frames)
    if dwell_frames < 100:
        raise ValueError("dwell_frames must be at least 100")
    departure = stop_frame + dwell_frames
    for fn in (set_doors, set_canopy, set_ramp):
        fn(root, 0.0, frame=stop_frame-1)
    set_canopy(root, 1.0, frame=stop_frame+8)
    set_doors(root, 1.0, frame=stop_frame+18)
    set_ramp(root, 0.0, frame=stop_frame+19)
    set_ramp(root, 0.70, frame=stop_frame+29)
    set_ramp(root, 1.0, frame=stop_frame+38)
    set_ramp(root, 1.0, frame=departure-48)
    set_ramp(root, 0.70, frame=departure-38)
    set_ramp(root, 0.0, frame=departure-26)
    set_doors(root, 1.0, frame=departure-26)
    set_canopy(root, 1.0, frame=departure-16)
    set_doors(root, 0.0, frame=departure-16)
    set_canopy(root, 0.0, frame=departure-1)
    root["boarding_stop_frame"] = stop_frame
    root["departure_frame"] = departure
    return departure


def set_exploded(root, fraction, frame=None):
    """Expose cabin and AV hardware while keeping every piece reversible."""
    fraction = max(0.0, min(1.0, float(fraction)))
    offsets = {
        'roof_assembly': (0, 0, 1.03),
        'sensor_assembly': (0, 0, 1.90),
        'canopy_assembly': (0, 0, 1.03),
        'glazing_collection': None,
        'interior_assembly': (-0.34, 0, 0.10),
        'door_assembly': (0, 0.68, 0.18),
        'ramp_assembly': (0, 0.68, 0.18),
    }
    for key, offset in offsets.items():
        if offset is None:
            continue
        obj = bpy.data.objects.get(root.get(key, ""))
        if obj:
            obj.location = tuple(fraction * v for v in offset)
            if frame is not None:
                obj.keyframe_insert(data_path="location", frame=frame)
    root["exploded"] = fraction
    if frame is not None:
        root.keyframe_insert(data_path='["exploded"]', frame=frame)


def set_cutaway(root, enabled=True):
    """Hide near-side glass and roof skin for a readable cabin camera angle."""
    prefix = PREFIX + "Side glass 1"
    for obj in _asset_descendants(root):
        if (obj.name.startswith(prefix)
                or obj.name.startswith(PREFIX + "Roof lid")
                or obj.name.startswith(PREFIX + "Roof underside")):
            obj.hide_render = bool(enabled)
            obj.hide_viewport = bool(enabled)


def keyframe_wheel_rotation(root, frame, radians):
    """Keyframe wheel rotation about each local axle for drive-by shots."""
    for obj in _asset_descendants(root):
        if obj.get("animation_role") == "spin_about_local_Y":
            obj.rotation_euler.y = radians
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)


def add_preview_stage(root):
    """Optional studio camera and lights; does not alter the asset's rig."""
    stage = collection("PREVIEW_STAGE")
    ground = cube("Preview ground", (0, 0, -0.035), (13, 10, 0.07),
                  material("Preview ground", (0.13, 0.16, 0.18), roughness=0.79),
                  stage, bevel=0.01)
    ground.name = "AVBUS_Preview_ground"
    cam_data = bpy.data.cameras.new("AVBUS_Preview_camera")
    cam = bpy.data.objects.new("AVBUS_Preview_camera", cam_data)
    stage.objects.link(cam)
    cam.location = (8.8, 9.0, 5.0)
    from mathutils import Vector
    direction = Vector((0, 0, 1.48)) - cam.location
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 9.7
    bpy.context.scene.camera = cam
    for i, (loc, power, size) in enumerate((((2, 3, 7), 1700, 5),
                                            ((-4, -2, 5), 1200, 4))):
        light_data = bpy.data.lights.new(f"AVBUS_Studio_{i}", 'AREA')
        light_data.energy = power
        light_data.shape = 'DISK'
        light_data.size = size
        light = bpy.data.objects.new(f"AVBUS_Studio_{i}", light_data)
        stage.objects.link(light)
        light.location = loc
        light.rotation_euler = (Vector((0, 0, 1)) - light.location).to_track_quat('-Z', 'Y').to_euler()
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 48
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.world.color = (0.24, 0.24, 0.24)


if __name__ == "__main__":
    rig = build_bus()
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    if '--access-preview' in argv:
        set_doors(rig, 1.0)
        set_canopy(rig, 1.0)
        set_ramp(rig, 1.0)
    if '--preview' in argv:
        add_preview_stage(rig)
    if '--save' in argv:
        path = argv[argv.index('--save') + 1]
        bpy.ops.wm.save_as_mainfile(filepath=path)
    print("Built", ROOT_NAME, "—", len(_asset_descendants(rig)), "objects")
