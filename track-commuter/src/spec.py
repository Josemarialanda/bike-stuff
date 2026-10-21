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
        ("Head tube length", pub["Head tube (C)"], P.HEAD_TUBE_LEN,
         "shortened for the taller 35 mm-clearance fork; stack/reach/BB drop unchanged"),
        ("Head tube angle", pub["Head angle (E)"], P.HEAD_ANGLE, "kept"),
        ("Seat tube angle", pub["Seat angle (F)"], P.SEAT_ANGLE, "kept"),
        ("Seat tube c-t", pub["Seat tube c-t (A)"], P.SEAT_TUBE_CT, "BB centre to top of seat tube"),
        ("Top tube (horizontal)", pub["Top tube horiz. (B)"], s["effective_top_tube_at_stack"],
         "follows from stack/reach/STA; published value is ~9 mm short in every size"),
        ("Chainstay", pub["Chainstay (D)"], f"{P.CHAINSTAY_MIN:g}-{P.CHAINSTAY_MAX:g} (nom. {P.CHAINSTAY_NOMINAL:g})",
         f"horizontal slot; minimum set by {P.TYRE_WIDTH_DESIGN:g} mm tyre to round seat tube"),
        ("Wheelbase", pub["Wheelbase (G)"],
         f"{s['chainstay_positions'][0]['wheelbase']:.0f}-{s['chainstay_positions'][2]['wheelbase']:.0f} "
         f"(nom. {s['chainstay_positions'][1]['wheelbase']:.0f})",
         "longer than Hektor because of the longer chainstay; front centre unchanged"),
        ("Standover", pub["Standover (H)"], round(s["standover_est"]), f"{P.TYRE_WIDTH_DESIGN:g} mm tyre, at BB"),
        ("BB drop", "n/p", s["bb_drop"], "derived (not published); confirmed from product photo"),
        ("BB height", "n/p", s["bb_height"], f"{P.TYRE_WIDTH_DESIGN:g} mm tyre"),
        ("Fork axle-to-crown", "n/p", P.FORK_AXLE_TO_CROWN,
         f"design value incl. lower headset; must clear {P.TYRE_WIDTH_DESIGN:g} mm tyres"),
        ("Fork offset", "n/p", P.FORK_OFFSET, "design value"),
        ("Trail", "n/p", s["trail"], f"{P.TYRE_WIDTH_DESIGN:g} mm tyre"),
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
    ("Dropouts", "6Al-4V plate", f"{P.DROPOUT_THICKNESS:g} mm",
     "receivers for sliding dropouts: window + 2 x M6 slots; sliders bought in"),
    ("Hose guides", "Ti bosses", "M4", f"{P.HOSE_GUIDES_ON_SEATSTAY} on non-drive seat stay"),
    ("Belt splitter", "Ti / builder std.", "-", "bolted split in drive-side seat stay"),
]

INTERFACES = [
    ("Wheels / tyres", f"700c (622). Clearance for {P.TYRE_WIDTH_DESIGN:g}-622 tyres with at least "
                       f"{P.TYRE_CLEARANCE_MIN:g} mm all round (checked in 3D). Stock Hektor: 25-622."),
    ("Rear hub", f"{P.REAR_SPACING:g} mm OLD disc hub (6-bolt), fixed/flip-flop or singlespeed freewheel, "
                 "10 mm bolt-on or QR axle in sliding dropouts. Rear sprocket must sit at the chainline below."),
    ("Sliding dropouts", "Bolt-on sliders (e.g. Paragon Machine Works-style) in 6Al-4V receiver plates; "
                         f"{P.CHAINSTAY_MAX - P.CHAINSTAY_MIN:g} mm travel tensions the belt. Builder sets the "
                         "receiver to the chosen slider system's drawing."),
    ("Drivetrain", f"Gates Carbon Drive CDX, {P.FRONT_TEETH}T front, {P.REAR_TEETH_FREEWHEEL}T (9-spline freewheel) "
                   f"or {P.REAR_TEETH_FIXED}T (track thread fixed), {P.BELT_TEETH}T belt, chainline {P.CHAINLINE} mm."),
    ("Frame split", "Required for belt: bolted splitter in drive-side seat stay (or split dropout)."),
    ("Bottom bracket", "BSA / English threaded 68 mm, external cups (stock: Hollow-Axle 170 mm cranks)."),
    ("Headset / fork", "ZS44/ZS56 tapered head tube; any 1 1/8\"-1.5\" tapered carbon fork, "
                       f"{P.FORK_AXLE_TO_CROWN:g} mm A-C, {P.FORK_OFFSET:g} mm offset, {P.FRONT_AXLE}, "
                       f"{P.FRONT_BRAKE_MOUNT}, clearance for {P.TYRE_WIDTH_DESIGN:g} mm tyres."),
    ("Seatpost / clamp", "27.2 mm post; 31.8 mm external seat collar."),
    ("Brakes", f"Hydraulic disc. Rear: {P.REAR_BRAKE_MOUNT}, {P.ROTOR_REAR:g} mm rotor; caliper sits "
               "behind/above the axle and moves with the slider, so belt tensioning never needs a brake "
               f"re-adjustment. Front: {P.FRONT_BRAKE_MOUNT} on the fork."),
    ("Hose routing", "Rear hose internal through top tube (6 mm ports 45 mm from each end, non-drive side), "
                     f"then along the non-drive seat stay on {P.HOSE_GUIDES_ON_SEATSTAY} x M4 guide bosses."),
    ("Mounts", f"2 bottle bosses on down tube, {P.BOTTLE_BOSS_SPACING:g} mm spacing, "
               f"lower at {P.BOTTLE_BOSS_FROM_BB:g} mm from BB centre."),
]

BUILD_NOTES = [
    "TIG weld with full back-purge (argon); no discoloured welds.",
    "Post-weld: face & chase BB, face/ream head tube bores to ZS44/ZS56, ream seat tube to 27.2.",
    "Rear receiver plates must be parallel and coplanar (belt drive and disc brake are both intolerant "
    "of misalignment): check rear triangle alignment to +/-0.5 mm and plate faces parallel within 0.2 mm; "
    "fit the actual sliders in the fixture when welding.",
    f"Belt line: rear cog and front ring must align within 0.5 mm at {P.CHAINLINE:g} mm chainline - "
    "confirm with the actual hub/crank before welding the chainstays.",
    "Finish: brushed or bead-blasted raw titanium (no paint). No branding of Schindelhauer.",
]

OPEN_ITEMS = [
    "Builder to confirm tube gauges/butting and the chainstay crimp (or substitute a machined yoke).",
    f"Confirm a {P.REAR_SPACING:g} mm hub, crank and Gates sprockets that give the {P.CHAINLINE:g} mm "
    "chainline; the chainstay/belt gaps are designed around it.",
    "Choose the slider system (and whether its post mount suits a 160 mm rotor directly); the receiver "
    "plates are drawn generically and follow that system's dimensions.",
    f"Fork: tapered, {P.FORK_AXLE_TO_CROWN:g} A-C, {P.FORK_OFFSET:g} offset, {P.FRONT_AXLE}, "
    f"{P.FRONT_BRAKE_MOUNT}, 35 mm tyre clearance.",
    "Pick the splitter style the builder prefers (seat-stay coupler vs. split dropout).",
    "Optional for a commuter: mudguard eyelets, rack mounts, dynamo routing - not included yet.",
]


def write_csv_json(g, stem, clearances):
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
        "clearances_mm": clearances,
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


def write_pdf(g, path, clearances, render_png=None, drawing_pngs=()):
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
    s.append(Paragraph("2. Rear axle position (sliding dropouts)", styles["Heading2"]))
    rows = [("Chainstay", "Wheelbase", f"Seat-tube / tyre gap ({P.TYRE_WIDTH_DESIGN:g} mm)")]
    for r in sm["chainstay_positions"]:
        rows.append((r["chainstay"], r["wheelbase"], r["seat_tube_tyre_gap"]))
    s.append(_table(rows, [50 * mm, 50 * mm, 60 * mm]))
    s.append(Paragraph(
        f"Belt centre distance with a {P.BELT_TEETH}T belt: {sm['belt_cs_60_22']} mm (60/22 freewheel), "
        f"{sm['belt_cs_60_21']} mm (60/21 fixed). Both sit inside the slot.", styles["BodyText"]))

    s.append(Paragraph("Clearance checks (3D model, mm)", styles["Heading3"]))
    s.append(Paragraph(
        f"Design tyre {P.TYRE_WIDTH_DESIGN:g}-622 (torus, {P.TYRE_HEIGHT_DESIGN:g} mm tall). Targets: tyre "
        f"{P.TYRE_CLEARANCE_MIN:g} mm, belt/sprockets {P.BELT_CLEARANCE_MIN:g} mm, disc rotor/caliper "
        f"{P.DISC_CLEARANCE_MIN:g} mm. 'min'/'max' = axle at "
        "front/rear of the slot.", styles["BodyText"]))
    rows = [("Check", "Gap")] + [(k.replace("_", " "), v) for k, v in clearances.items()]
    s.append(_table(rows, [90 * mm, 40 * mm]))

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
