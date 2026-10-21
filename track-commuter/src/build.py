"""Regenerate every output: python src/build.py (from the track-commuter folder)."""
import json
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import drawings  # noqa: E402
import params as P  # noqa: E402
import spec  # noqa: E402
from model3d import FrameModel, v3  # noqa: E402
from render import render  # noqa: E402

TI = (0.75, 0.76, 0.78)
DARK = (0.18, 0.18, 0.18)


def out(*parts):
    path = os.path.join(ROOT, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def main():
    model = FrameModel()
    g = model.g
    print(json.dumps(g.summary(), indent=2))

    print("building 3D frame ...")
    frame = model.build_frame()
    assert frame.isValid(), "frame solid is invalid"
    tag = "ti_track_commuter_53"
    cq.exporters.export(frame, out("cad", f"{tag}_frame.step"))
    cq.exporters.export(frame, out("cad", f"{tag}_frame.stl"), tolerance=0.1, angularTolerance=0.2)
    model.build_assembly(frame).export(out("cad", f"{tag}_assembly_reference.step"))
    mass = frame.Volume() / 1000 * 4.48
    print(f"frame volume {frame.Volume() / 1000:.1f} cm3, approx. mass {mass:.0f} g (Ti)")

    print("rendering previews ...")
    asm = [(frame, TI), (model.fork(), DARK), (model.wheel(v3(model.axle_nom)), DARK),
           (model.wheel(v3(g.front_axle)), DARK), (model.belt_drive(), (0.35, 0.35, 0.35))]
    render([(frame, TI)], out("renders", "frame_three_quarter.png"), "three_quarter")
    render([(frame, TI)], out("renders", "frame_side.png"), "side_drive")
    render([(frame, TI)], out("renders", "frame_rear.png"), "rear")
    render(asm, out("renders", "bike_side_reference.png"), "side_drive", zoom=1.2)

    print("drawings ...")
    d1 = out("drawings", f"{tag}_sheet1_side_elevation")
    d2 = out("drawings", f"{tag}_sheet2_rear_end")
    drawings.side_elevation(model, d1)
    drawings.rear_end(model, d2)

    print("spec sheet ...")
    spec.write_csv_json(g, out("spec", f"{tag}_geometry"))
    spec.write_pdf(g, out("spec", f"{tag}_spec_sheet.pdf"),
                   render_png=out("renders", "frame_three_quarter.png"),
                   drawing_pngs=(d1 + ".png", d2 + ".png"))
    with open(out("cad", "mass_estimate.txt"), "w") as f:
        f.write(f"Frame volume {frame.Volume() / 1000:.1f} cm3; Ti density 4.48 g/cm3 -> "
                f"{mass:.0f} g bare frame (no welds, paint-free). Size {P.SIZE}.\n")
    print("done")


if __name__ == "__main__":
    main()
