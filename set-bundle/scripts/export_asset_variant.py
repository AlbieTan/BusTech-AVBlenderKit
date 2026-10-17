"""Load the combined master and save a self-contained scene asset.

blender --background SightLine_Stop_Albie_Master.blend --python export_asset_variant.py -- --variant before
Variants: before, after, albie.
"""

import argparse
import sys
from pathlib import Path
import bpy

parser = argparse.ArgumentParser()
parser.add_argument('--variant', choices=('before', 'after', 'albie'), required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])

names = {
    'before': 'SightLine_Stop_Before.blend',
    'after': 'SightLine_Stop_After.blend',
    'albie': 'Albie_Powered_Wheelchair.blend',
}
remove = {
    'before': ('SIGHTLINE | toggle off for before shots',
               'ALBIE_CHAIR | powered wheelchair',
               'ALBIE_RIDER | generic stylized character'),
    'after': ('ALBIE_CHAIR | powered wheelchair',
              'ALBIE_RIDER | generic stylized character'),
    'albie': ('SIGHTLINE | toggle off for before shots',
              'STOP_BASE | shelter and street furniture'),
}

for name in remove[args.variant]:
    c = bpy.data.collections[name]
    for obj in tuple(c.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(c)

target = Path(__file__).resolve().parent / names[args.variant]
bpy.ops.wm.save_as_mainfile(filepath=str(target))
print('ASSET_VARIANT_SAVED', args.variant, target)
