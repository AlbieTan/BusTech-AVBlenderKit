# SightLine / BusTech Blender set bundle — NTU Team 1

This is a reusable, stylized Singapore-inspired asset kit for the team's AV-bus film. It contains the current 16-seat AV bus, generic seated Albie in a powered wheelchair, two **separate** bus stops, and a modular street environment. It contains **no individual shot scenes**. All `.blend` files were saved in Blender 5.2 with metric metres and 24 fps. This bundle is separate from the RailTech repository.

## Files

| Location | Use |
| --- | --- |
| `assets/AV_Bus_Master.blend` | Current 16-seat bus; doors, ramp and rain canopy remain controllable. |
| `assets/Albie_Powered_Wheelchair.blend` | Generic stylized seated rider and power chair. |
| `assets/SightLine_Stop_Before.blend` | Ordinary shelter for the opening problem scene. |
| `assets/SightLine_Stop_After.blend` | Upgraded shelter, display, help panel, side-facing boarding camera and kerb sensor, priority bay. |
| `assets/Singapore_Street_Set_Master.blend` | Road, 15 cm kerb, tactile paving, bus-bay markings, housing façades, tropical greenery and street furniture. |
| `previews/preview_singapore_street_set.png` | Preview of the reusable environment only. |
| `scripts/` | Procedural asset builders and bus animation helpers for reproducible edits. |

## Using the assets in a new scene

In Blender, use **File → Append** and open an asset `.blend`, then select its relevant **Collection**. Append both ALBIE collections together, or both stop collections from the **After** file. Their cross-collection parent relationships are intentional. `AV_BUS_ROOT`, `ALBIE_ROOT`, `STOP_ASSET_ROOT` and `SG_SET_ROOT` are the objects to move. Wheel controls are `ALBIE_WHEEL_L/R`; moving `ALBIE_GAZE_TARGET` guides Albie's head.

The street set is built around the Shot 1/2 coordinates: road runs along X, the bus stops near the origin, and the near kerb is at Y=1.76 m. The stop root in the sample shots is at (-4.45, 3.54, 0.15), Albie at (0.9, 2.64, 0.15), and the street-set root at (0, 0, 0). For other locations, move the entire set root; do not move individual pavement pieces one by one. The street set does **not** contain the bus stop itself, so use either the Before or After stop with it.

The After stop has a working **demo QR pointing to `https://example.com`**. Replace its packed image with the final team URL before any public submission. Housing block numbers and the route display are fictional/demo scenery, not a claim that the scene depicts a specific real bus route or location.

The individual scene files and low-resolution review GIFs are kept separately in [`../shots/`](../shots/). Their review GIFs are not the final-quality output. Open a shot `.blend` to render at its saved 1920×1080, 100% scale settings after the team's final camera review.
