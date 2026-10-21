"""Specification sheet for the builder: PDF (reportlab) plus CSV/JSON geometry."""
import csv
import datetime
import json

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

import params as P


def geometry_rows(g):
    s = g.summary()
    pub = dict(zip(P.PUBLISHED_COLUMNS, P.PUBLISHED[0]))
    return [
        # (parameter, published Hektor 53, this design, note)
        ("Stack", pub["Stack (J)"], P.STACK, "kept"),
        ("Reach", pub["Reach (I)"], P.REACH, "kept"),
        ("Head tube length", pub["Head tube (C)"], P.HEAD_TUBE_LEN, "kept; ZS44/ZS56 zero-stack cups"),
        ("Head tube angle", pub["Head angle (E)"], P.HEAD_ANGLE, "kept"),
        ("Seat tube angle", pub["Seat angle (F)"], P.SEAT_ANGLE, "kept"),
        ("Seat tube c-t", pub["Seat tube c-t (A)"], P.SEAT_TUBE_CT, "BB centre to top of seat tube"),
        ("Top tube (horizontal)", pub["Top tube horiz. (B)"], s["effective_top_tube_at_stack"],
         "follows from stack/reach/STA; published value is ~9 mm short in every size"),
        ("Chainstay", pub["Chainstay (D)"], f"{P.CHAINSTAY_MIN:g}-{P.CHAINSTAY_MAX:g} (nom. {P.CHAINSTAY_NOMINAL:g})",
         "horizontal slot; 378 only possible with Hektor's shaped aero seat tube"),
        ("Wheelbase", pub["Wheelbase (G)"],
         f"{s['chainstay_positions'][0]['wheelbase']:.0f}-{s['chainstay_positions'][2]['wheelbase']:.0f} "
         f"(nom. {s['chainstay_positions'][1]['wheelbase']:.0f})",
         f"{s['wheelbase_at_published_cs']:.0f} at CS 378 -> geometry matches Hektor exactly"),
        ("Standover", pub["Standover (H)"], round(s["standover_est"]), "estimate, 25 mm tyre, at BB"),
        ("BB drop", "n/p", s["bb_drop"], "derived (not published); confirmed from product photo"),
        ("BB height", "n/p", s["bb_height_25c"], "25 mm tyre"),
        ("Fork axle-to-crown", "n/p", P.FORK_AXLE_TO_CROWN, "design value; incl. lower headset"),
        ("Fork offset", "n/p", P.FORK_OFFSET, "design value"),
        ("Trail", "n/p", s["trail_25c"], "25 mm tyre"),
        ("Front centre", "n/p", s["front_center"], f"toe overlap ~{s['toe_overlap_est']:.0f} mm w/ 170 cranks"),
        ("Headset", pub["Headset"], "ZS44 / ZS56 tapered", "Hektor uses integrated tapered 1 1/8-1.5"),
        ("Seatpost", pub["Seatpost"], P.SEATPOST_DIA, "reamed Ti sleeve in 31.8 seat tube"),
    ]


TUBES = [
    ("Top tube", "3Al-2.5V CWSR", f"{P.TOP_TUBE[0]} x {P.TOP_TUBE[1]}", "straight gauge; builder may butt 0.9/0.6/0.9"),
    ("Down tube", "3Al-2.5V CWSR", f"{P.DOWN_TUBE[0]} x {P.DOWN_TUBE[1]}", "oversize for BB/belt stiffness"),
    ("Seat tube", "3Al-2.5V CWSR", f"{P.SEAT_TUBE[0]} x {P.SEAT_TUBE[1]}",
     "120 mm internal sleeve reamed to 27.2; rear clamp slot + relief hole"),
    ("Head tube", "6Al-4V machined", f"OD {P.HEAD_TUBE_OD[0]:g}/{P.HEAD_TUBE_OD[1]:g} tapered",
     "ZS44 top / ZS56 bottom bearing bores (SHIS)"),
    ("BB shell", "6Al-4V", f"OD {P.BB_SHELL[0]:g} x {P.BB_SHELL[1]:g} wide", "BSA 1.37\" x 24 TPI, face & chase"),
    ("Chainstays", "3Al-2.5V CWSR", f"{P.CHAINSTAY[0]} x {P.CHAINSTAY[1]}",
     f"crimped to {P.CHAINSTAY_OVAL[0]:g} x {P.CHAINSTAY_OVAL[1]:g} oval for first 110 mm, then flared"),
    ("Seat stays", "3Al-2.5V CWSR", f"{P.SEATSTAY[0]} x {P.SEATSTAY[1]}",
     "bent: straight 85 mm at dropout (belt clearance), then to seat tube"),
    ("Dropouts", "6Al-4V plate", f"{P.DROPOUT_THICKNESS:g} mm", "horizontal rear-facing track ends, 10.2 slot"),
    ("Brake bridge", "3Al-2.5V", "12.7 x 1.0", "6 mm hole for recessed-nut caliper"),
    ("Belt splitter", "Ti / builder std.", "-", "bolted split in drive-side seat stay"),
]

INTERFACES = [
    ("Wheels / tyres", "700c (622). Designed and checked for 25 mm (stock Ultrasport III 25-622)."),
    ("Rear hub", f"{P.REAR_SPACING:g} mm OLD track hub, 3/8\" or 10 mm solid axle, horizontal dropouts."),
    ("Drivetrain", f"Gates Carbon Drive CDX, {P.FRONT_TEETH}T front, {P.REAR_TEETH_FREEWHEEL}T (9-spline freewheel) "
                   f"or {P.REAR_TEETH_FIXED}T (track thread fixed), {P.BELT_TEETH}T belt, chainline {P.CHAINLINE} mm."),
    ("Frame split", "Required for belt: bolted splitter in drive-side seat stay (or split dropout)."),
    ("Bottom bracket", "BSA / English threaded 68 mm, external cups (stock: Hollow-Axle 170 mm cranks)."),
    ("Headset / fork", "ZS44/ZS56 tapered head tube; any 1 1/8\"-1.5\" tapered carbon fork, "
                       f"{P.FORK_AXLE_TO_CROWN:g} mm A-C, {P.FORK_OFFSET:g} mm offset, drilled for a rim brake."),
    ("Seatpost / clamp", "27.2 mm post; 31.8 mm external seat collar."),
    ("Brakes", "Rear rim-brake bridge for long-reach (47-57 mm) caliper; front through fork crown. "
               "Fixed-gear build can omit both (bridge is harmless)."),
    ("Cable routing", "Rear brake internal through top tube: 6 mm ports 45 mm from each end, non-drive side."),
    ("Mounts", f"2 bottle bosses on down tube, {P.BOTTLE_BOSS_SPACING:g} mm spacing, "
               f"lower at {P.BOTTLE_BOSS_FROM_BB:g} mm from BB centre."),
]

BUILD_NOTES = [
    "TIG weld with full back-purge (argon); no discoloured welds.",
    "Post-weld: face & chase BB, face/ream head tube bores to ZS44/ZS56, ream seat tube to 27.2.",
    "Rear dropouts must be parallel and coplanar (belt drive is intolerant of misalignment): "
    "check rear triangle alignment to +/-0.5 mm and dropout faces parallel within 0.2 mm.",
    "Belt line: rear cog and front ring must align within 0.5 mm at 42.5 mm chainline - "
    "confirm with the actual hub/crank before welding the chainstays.",
    "Finish: brushed or bead-blasted raw titanium (no paint). No branding of Schindelhauer.",
]

OPEN_ITEMS = [
    "Builder to confirm tube gauges/butting and the chainstay crimp (or substitute a machined yoke).",
    "28 mm tyres would need a wider chainline or a yoke; the current layout is checked for 25 mm.",
    "Confirm hub (flip-flop or freewheel), crank and Gates sprocket part numbers so the chainline is exact.",
    "Pick the splitter style the builder prefers (seat-stay coupler vs. split dropout).",
    "Optional for a commuter: mudguard eyelets, rack mounts, dynamo routing - not included yet.",
]


def write_csv_json(g, stem):
    rows = geometry_rows(g)
    with open(f"{stem}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["parameter", "hektor_published_53", "ti_design_53", "note"])
        w.writerows(rows)
    data = {
        "size": P.SIZE,
        "units": "mm / degrees",
        "geometry": [dict(zip(["parameter", "hektor_published", "design", "note"], r)) for r in rows],
        "derived": g.summary(),
        "tubes": [dict(zip(["tube", "material", "size", "note"], t)) for t in TUBES],
        "interfaces": dict(INTERFACES),
        "published_all_sizes": [dict(zip(P.PUBLISHED_COLUMNS, r)) for r in P.PUBLISHED],
    }
    with open(f"{stem}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)


def _table(rows, widths, header=True):
    st = getSampleStyleSheet()["BodyText"]
    st.fontSize, st.leading = 8, 10
    cells = [[Paragraph(str(c), st) for c in r] for r in rows]
    t = Table(cells, colWidths=widths, repeatRows=1 if header else 0)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8") if header else colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def write_pdf(g, path, render_png=None, drawing_pngs=()):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm,
                            title=f"Titanium track commuter - size {P.SIZE} - spec sheet")
    s = []
    s.append(Paragraph(f"Titanium Track Commuter - Size {P.SIZE} - Frame Specification", styles["Title"]))
    s.append(Paragraph(
        "Belt-drive track/commuter frame with the fit and handling geometry of the Schindelhauer Hektor "
        f"(size 53), re-engineered in titanium. Rev A, {datetime.date.today().isoformat()}. "
        "All dimensions in mm and degrees; files: STEP (3D), DXF 1:1 and PDF (2D).", styles["BodyText"]))
    if render_png:
        s.append(Spacer(1, 4 * mm))
        s.append(Image(render_png, width=170 * mm, height=106 * mm))
    s.append(Paragraph("1. Geometry", styles["Heading2"]))
    rows = [("Parameter", "Hektor 53 (published)", "This frame", "Note")] + geometry_rows(g)
    s.append(_table(rows, [38 * mm, 28 * mm, 34 * mm, 80 * mm]))

    sm = g.summary()
    s.append(Paragraph("2. Rear axle position (horizontal track ends)", styles["Heading2"]))
    rows = [("Chainstay", "Wheelbase", "Seat-tube / tyre gap (25 mm)", "Rear brake reach")]
    for r in sm["chainstay_positions"]:
        rows.append((r["chainstay"], r["wheelbase"], r["seat_tube_tyre_gap"], r["rear_brake_reach"]))
    s.append(_table(rows, [40 * mm, 40 * mm, 50 * mm, 50 * mm]))
    s.append(Paragraph(
        f"Belt centre distance with a {P.BELT_TEETH}T belt: {sm['belt_cs_60_22']} mm (60/22 freewheel), "
        f"{sm['belt_cs_60_21']} mm (60/21 fixed). Both sit inside the slot.", styles["BodyText"]))

    s.append(PageBreak())
    s.append(Paragraph("3. Tube set (proposal - builder to confirm)", styles["Heading2"]))
    s.append(_table([("Member", "Material", "Size (OD x wall)", "Note")] + TUBES,
                    [28 * mm, 32 * mm, 36 * mm, 84 * mm]))
    s.append(Paragraph("4. Interfaces and standards", styles["Heading2"]))
    s.append(_table([("Item", "Specification")] + INTERFACES, [38 * mm, 142 * mm]))
    s.append(Paragraph("5. Manufacturing notes", styles["Heading2"]))
    for n in BUILD_NOTES:
        s.append(Paragraph("- " + n, styles["BodyText"]))
    s.append(Paragraph("6. Open items to agree with the builder", styles["Heading2"]))
    for n in OPEN_ITEMS:
        s.append(Paragraph("- " + n, styles["BodyText"]))
    s.append(Paragraph("7. Published Hektor geometry, all sizes (reference)", styles["Heading2"]))
    s.append(_table([P.PUBLISHED_COLUMNS[:11]] + [r[:11] for r in P.PUBLISHED],
                    [15 * mm] + [16.5 * mm] * 10))
    for png in drawing_pngs:
        s.append(PageBreak())
        s.append(Image(png, width=180 * mm, height=127 * mm))
    doc.build(s)
