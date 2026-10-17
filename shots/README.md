# Shots 1 and 2 — scene files

These are the current Singapore-inspired set-dressed Blender scenes for the SightLine video. They are **separate from the reusable assets** in [`../set-bundle/`](../set-bundle/). Each `.blend` contains appended copies of the bus, ordinary (before) shelter, generic rider and street set, so it opens without external asset links.

| File | Action |
| --- | --- |
| `s01_bus_arrival_v05.blend` | The rider waits while the driverless bus arrives and stops. |
| `s02_bus_gap_v05.blend` | Doors open; the kerb gap and raised entry prevent boarding; the bus departs. No ramp deploys. |

Both scenes use metric metres, 1920 × 1080 at 100% scale, 24 fps, frames 1–144 (six seconds). Open them in Blender 5.2. The scene files are ready for camera and lighting refinement, not final rendered footage.

[`previews/s01_review_v05.gif`](previews/s01_review_v05.gif) and [`previews/s02_review_v05.gif`](previews/s02_review_v05.gif) are reduced-resolution, sparsely sampled motion checks. [`previews/s01_fullres_f121.png`](previews/s01_fullres_f121.png) shows one actual 1920 × 1080 frame. Render the `.blend` scenes at their saved settings for delivery; do not upscale the GIFs.

## Full-resolution exports and combined edit

| File | Contents |
| --- | --- |
| [`renders/s01_bus_arrival_1080p24.mp4`](renders/s01_bus_arrival_1080p24.mp4) | Shot 1, six seconds / 144 frames. |
| [`renders/s02_bus_gap_1080p24.mp4`](renders/s02_bus_gap_1080p24.mp4) | Shot 2, six seconds / 144 frames. |
| [`renders/1-2.mp4`](renders/1-2.mp4) | Both shots stitched together, 12 seconds / 288 frames. |
| [`renders/1-2.blend`](renders/1-2.blend) | Editable, self-contained Blender project with the two original scenes sequenced at frames 1–144 and 145–288. |

The MP4s are 1920 × 1080, 24 fps H.264 video with **no audio**. The combined `.blend` does not rely on the MP4s: open it in Blender 5.2 and use its Video Sequencer timeline. The full-resolution PNG frame sequences used for encoding remain in the team's local `BusTech-Shots/renders/highres` folder; they are not committed here to avoid duplicating hundreds of frames in Git.
