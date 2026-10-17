"""Render a new preview from Singapore_Street_Set_Master.blend."""

import math
from pathlib import Path

import bpy
from mathutils import Vector

out = Path(__file__).resolve().parent / 'preview_singapore_street_set.png'
scene = bpy.context.scene
bpy.ops.object.camera_add(location=(12, 14, 6.2))
camera = bpy.context.object
camera.rotation_euler = (Vector((-1.8, 0, 2.7)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.lens = 28
scene.camera = camera
bpy.ops.object.light_add(type='SUN', location=(0, 0, 15))
sun = bpy.context.object
sun.data.energy = 1.5
sun.rotation_euler = (math.radians(35), math.radians(-25), math.radians(30))
scene.render.resolution_percentage = 50
scene.render.filepath = str(out)
bpy.ops.render.render(write_still=True)
print('STREET_PREVIEW_RENDERED', out)
