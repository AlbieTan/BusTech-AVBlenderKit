"""Animate the shared AV bus with both ramp and rain canopy deployment.

Open a fresh AV_Bus_Master.blend, then Run Script in Blender's Text Editor.
The companion animate_stop_ramp.py supplies the common stop choreography.
"""

import argparse
from pathlib import Path
import runpy
import sys


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", help="Optional output .blend path")
    args = parser.parse_args(argv)
    shared = runpy.run_path(str(Path(__file__).with_name("animate_stop_ramp.py")),
                            run_name="av_stop_module")
    shared["animate_scene"](with_canopy=True, save_path=args.save)


if __name__ == "__main__":
    main()
