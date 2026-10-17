# AV bus Blender kit — NTU Team 1

Keep these **four files together in one folder** when sharing them:

1. `build_av_bus.py` — creates the reusable bus and its rig.
2. `animate_stop_ramp.py` — bus approaches, stops, opens its doors, slides and lowers the ramp, then departs. The canopy stays closed.
3. `animate_stop_ramp_canopy.py` — the same stop, with the rain canopy extending during boarding.
4. `README_AV_BUS.md` — this guide.

The two animation scripts both use `build_av_bus.py`; the canopy version also
uses `animate_stop_ramp.py`. Do not separate the files.

## Fastest workflow in Blender

1. Start a **new, empty scene**. In Blender's default scene, delete the startup
   cube, camera and light (they are not part of the bus).
2. Open `build_av_bus.py` in the Scripting workspace and click **Run Script**.
   Save as `AV_Bus_Master.blend`. The bus starts drive-ready: doors closed,
   canopy retracted, ramp beneath the floor.
3. For a ramp-only animation, reopen a **fresh copy** of that master, run
   `animate_stop_ramp.py`, and Save As `AV_Bus_Stop_Ramp.blend`.
4. For a ramp-and-canopy animation, reopen the **original unanimated master**,
   run `animate_stop_ramp_canopy.py`, and Save As
   `AV_Bus_Stop_Ramp_Canopy.blend`.
5. Press **Space** to play. Each scene is 192 frames at 24 fps (8 seconds).
   The animation scripts add a studio camera and lights if the master has none.

Do not run both animation scripts on one already-keyframed bus. They deliberately
stop with an error rather than overwrite a teammate's animation.

## Command-line workflow (optional)

Run these from the folder containing the four files, with `blender` on `PATH`.
The first command clears only Blender's new startup scene, then builds the bus:

```powershell
blender --background --python-expr "import bpy; [bpy.data.objects.remove(o,do_unlink=True) for o in list(bpy.data.objects)]" --python build_av_bus.py -- --save AV_Bus_Master.blend
blender --background AV_Bus_Master.blend --python animate_stop_ramp.py -- --save AV_Bus_Stop_Ramp.blend
blender --background AV_Bus_Master.blend --python animate_stop_ramp_canopy.py -- --save AV_Bus_Stop_Ramp_Canopy.blend
```

If `blender` is not on `PATH`, use the full path to your Blender executable.

## Motion and rig

The bus points in **+X**, and its curb-side entrance is **+Y**. Animate
`AV_BUS_ROOT` for vehicle travel. The scene scripts keep that root stationary
through the boarding dwell; they do **not** detect a real vehicle stop.

| Frames | What happens |
| --- | --- |
| 1–36 | Bus approaches and stops; equipment remains stowed. |
| 36–84 | Doors open; ramp slides straight out, then tilts down. The canopy variant also extends the shelter. |
| 84–112 | Boarding configuration stays deployed. |
| 112–156 | Ramp lifts and retracts, doors close, and canopy retracts if present. |
| 156–192 | Bus departs with all equipment stowed. |

The ramp never turns horizontally. Its 0–1 control has two stages: **0–0.70
slides outward**; **0.70–1.0 tilts down**. The canopy slides laterally from a
roof cassette. Door leaves slide apart. All are separate, named assemblies.

For custom shots, load the functions without rebuilding the model:

```python
import runpy
bus = runpy.run_path(r"C:\path\to\build_av_bus.py", run_name="av_bus_api")
root = bpy.data.objects["AV_BUS_ROOT"]
bus["set_doors"](root, 1.0, frame=24)
bus["set_ramp"](root, 0.70, frame=40)  # fully slid out, not tilted
bus["set_ramp"](root, 1.0, frame=52)   # tilted to the curb
bus["set_canopy"](root, 1.0, frame=40)
bus["set_side_display"](root, route_number="400", passenger_seats=16)
bus["set_cutaway"](root, True)
bus["set_exploded"](root, 1.0, frame=80)
```

Save **separate `.blend` files** for custom shots rather than changing the
master. The clean master can also be appended into another scene via
**File → Append → AV_Bus_Master.blend → Collection → AVBUS_MASTER**.

## What the model represents

The asset is an original visual approximation based on the provided AV-bus
photos, not manufacturer CAD. It is approximately 6.65 m × 2.34 m and has a
passenger cabin, 16 passenger seats (nine on the lower floor and seven on the
raised rear platform), one separate safety-operator seat, grab rails, an
entrance-side wheelchair bay with a blue floor pictogram,
fare validator, roof sensors, sliding doors, side route display, canopy and
ramp. The side sign reads `400` and `16 SEATS` by default: this is the **modelled
installed-seat count**, not live vacant-seat availability. Edit `CFG` at the top
of `build_av_bus.py` before building, or use `set_side_display` per scene.

The ramp lands at an illustrative 0.14 m curb height. Its length and slope are
for storytelling only; do not treat them as accessibility-code compliance or
fabrication measurements. Hidden interior and sensor details are plausible
visual approximations. Generic lettering avoids reproducing an operator's
trademark exactly.

## Validation and preview

The kit was tested in Blender 5.2.2 LTS. Both animation scripts generated
playable `.blend` scenes. Frame checks confirmed that the bus holds position
during boarding, the ramp has **zero horizontal rotation**, and the canopy
deploys only in the canopy variant before retracting for departure.

The current motion demo is `demo.gif`. Your own
currently open Blender scene is not modified by the generated master or GIF;
open or append the new master to use this revision.
