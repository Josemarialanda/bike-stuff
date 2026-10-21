# Titanium track commuter, size 53 (S)

A belt-drive track/commuter frame with the **fit and handling geometry of the
[Schindelhauer Hektor](https://schindelhauerbikes.com/en/bikes/hektor), size 53**, re-engineered in
titanium. These files are a complete brief for a frame builder: they show what to build, and the
builder still does their own production engineering.

![3D render](renders/frame_three_quarter.png)

## What to send the manufacturer

| File | Format | What it is |
|---|---|---|
| `cad/ti_track_commuter_53_frame.step` | STEP AP214 | 3D frame solid, mm. **Main file.** |
| `cad/ti_track_commuter_53_assembly_reference.step` | STEP | Frame + reference fork, wheels and belt sprockets (for clearance checks) |
| `cad/ti_track_commuter_53_frame.stl` | STL | Mesh, for quick viewing or 3D printing a model |
| `drawings/*_sheet1_side_elevation.{dxf,pdf,svg}` | DXF 1:1 / PDF A3 1:5 | Side elevation: all geometry dimensions |
| `drawings/*_sheet2_rear_end.{dxf,pdf,svg}` | DXF 1:1 / PDF A3 1:2 | Rear plan view (spacing, chainline, tyre/belt clearance) + dropout detail |
| `spec/ti_track_commuter_53_spec_sheet.pdf` | PDF | Geometry vs. Hektor, tube set, interfaces, build notes, open items |
| `spec/ti_track_commuter_53_geometry.{csv,json}` | CSV / JSON | Same data, machine readable |

STEP + DXF + PDF are what nearly every frame builder and Asian OEM works from. The DXF is 1:1 in
mm; don't scale off the PDFs.

## Key numbers (size 53)

| | Hektor 53 (published) | This frame |
|---|---|---|
| Stack / Reach | 498 / 406 | 498 / 406 |
| Head angle / Seat angle | 73.5° / 75° | 73.5° / 75° |
| Head tube | 120 | 120 (ZS44/ZS56 tapered) |
| Seat tube c-t | 530 | 530 |
| Chainstay | 378 | 384–400 slot (390 with stock belt) |
| Wheelbase | 961 | 967–983 (961 at CS 378) |
| BB drop / height | not published | 48.4 / 287.6 (25 mm tyre) |
| Fork | tapered carbon | any tapered fork, 365 A-C, 45 offset |
| Trail | not published | 52.6 |
| Frame mass (est.) | 6061 Al | ~1.65 kg Ti, bare |

## Decisions and deviations from the Hektor (please read)

1. **Geometry source.** The table comes from Schindelhauer's own site data
   (`reference/hektor_source_data.json`). BB drop and fork dimensions aren't published. 48 mm drop
   with a 365 mm / 45 mm fork reproduces the published 961 mm wheelbase exactly and matches a
   measurement of the side-on product photo.
2. **Top tube.** The published horizontal top tube (530) doesn't agree with the published
   stack/reach/seat angle. The same 9–10 mm gap appears in every size. Stack and reach were kept,
   because fit and handling depend on them, which gives 539 mm at stack height.
3. **Chainstay.** 378 mm only works with Hektor's shaped aero seat tube. With a round 31.8 mm
   titanium seat tube, a 25 mm tyre needs at least 384 mm. The stock 60T/22T gearing with a 113T
   belt lands at 390 mm anyway. The horizontal slot covers 384–400.
4. **Titanium construction.** Round 3Al-2.5V tubes replace the hydroformed aluminium. The machined
   head tube, BB shell and dropouts are 6Al-4V. Chainstays are crimped to a 16 mm-wide oval near
   the BB so a 25 mm tyre and the 60T belt ring both fit at a 42.5 mm track chainline. Seat stays
   stay wide for 85 mm above the dropout so the belt clears them.
5. **Belt drive needs a frame split.** Hektor uses a patented "Belt Port" in the dropout. This
   design uses a bolted splitter in the drive-side seat stay instead, a standard titanium
   belt-drive solution. The builder can swap in their preferred splitter.
6. **Headset.** Hektor has an integrated tapered headset. Titanium builders normally machine a
   ZS44/ZS56 tapered head tube, which takes the same 1 1/8"–1.5" tapered forks.
7. **No Schindelhauer branding or patented details** are reproduced.

Open items to agree with the builder are listed at the end of the spec sheet (tube butting,
splitter style, exact hub/crank/sprocket part numbers, 28 mm tyre option, commuter mounts).

## Changing the design

Everything is generated from `src/params.py`. Edit a value (e.g. `HEAD_ANGLE`, `CHAINSTAY_NOMINAL`,
tube sizes), then:

```bash
cd track-commuter
pip install -r requirements.txt
python src/build.py
```

The build regenerates the STEP/STL, drawings, renders and spec sheet (about 2 minutes) and prints
the derived geometry and clearance checks (`python src/geometry.py` prints just those).

| Module | Role |
|---|---|
| `src/params.py` | All inputs (published geometry, design choices, tube set) |
| `src/geometry.py` | Solves key points, BB drop, trail, wheelbase, belt length, tyre and brake checks |
| `src/model3d.py` | CadQuery/OpenCascade solid model with coped tube joints |
| `src/drawings.py` | DXF/PDF/SVG drawings from hidden-line projections of the model |
| `src/spec.py` | Spec sheet PDF + CSV/JSON |
| `src/render.py` | Preview images |

Coordinates: origin at the BB centre, +X forward, +Y up, +Z toward the drive (right) side, mm.
