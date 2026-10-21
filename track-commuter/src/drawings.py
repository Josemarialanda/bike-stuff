"""2D manufacturing drawings: DXF (1:1, mm) plus PDF/SVG plots at a fixed scale on A3.

Frame outlines are true hidden-line projections of the 3D model, so copes,
crimps and dropouts match the STEP file exactly.
"""
import math

import ezdxf
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.config import BackgroundPolicy, ColorPolicy, Configuration
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
import cadquery as cq

import params as P

A3 = (420.0, 297.0)
LAYERS = {
    "FRAME": (7, "CONTINUOUS", 50),
    "HIDDEN": (8, "DASHED", 18),
    "CENTER": (1, "CENTER", 18),
    "REFERENCE": (5, "PHANTOM", 18),
    "DIM": (3, "CONTINUOUS", 18),
    "TEXT": (7, "CONTINUOUS", 25),
    "SHEET": (7, "CONTINUOUS", 50),
}


def hlr_edges(shape, view_dir, x_dir, hidden=False):
    """Project a shape; returns lists of 2D polylines (visible, hidden)."""
    algo = HLRBRep_Algo()
    algo.Add(shape.wrapped)
    ax2 = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*view_dir), gp_Dir(*x_dir))
    algo.Projector(HLRAlgo_Projector(ax2))
    algo.Update()
    algo.Hide()
    hs = HLRBRep_HLRToShape(algo)

    def collect(compounds):
        out = []
        for c in compounds:
            if c is None or c.IsNull():
                continue
            for e in cq.Shape.cast(c).Edges():
                n = 2 if e.geomType() == "LINE" else max(8, int(e.Length() / 2))
                pts = [e.positionAt(t) for t in np.linspace(0, 1, n)]
                out.append([(p.x, p.y) for p in pts])
        return out

    vis = collect([hs.VCompound(), hs.OutLineVCompound(), hs.Rg1LineVCompound()])
    hid = collect([hs.HCompound(), hs.OutLineHCompound()]) if hidden else []
    return vis, hid


class Sheet:
    def __init__(self, scale, title, sheet_no, origin=(0.0, 0.0)):
        self.scale = scale
        self.doc = ezdxf.new("R2010", setup=True, units=ezdxf.units.MM)
        self.doc.header["$LTSCALE"] = scale * 2.0
        for name, (color, lt, lw) in LAYERS.items():
            self.doc.layers.add(name, color=color, linetype=lt, lineweight=lw)
        self.msp = self.doc.modelspace()
        self.title = title
        self.sheet_no = sheet_no
        self.origin = np.array(origin)
        self.txt = 2.5 * scale
        ds = self.doc.dimstyles.get("EZDXF")
        ds.dxf.dimtxt = 2.5 * scale
        ds.dxf.dimasz = 2.5 * scale
        ds.dxf.dimexo = 1.0 * scale
        ds.dxf.dimexe = 1.5 * scale
        ds.dxf.dimgap = 0.8 * scale
        ds.dxf.dimlfac = 1.0   # the EZDXF style defaults to m -> cm scaling
        ds.dxf.dimpost = ""
        ds.dxf.dimdec = 1
        ds.dxf.dimadec = 1
        ds.dxf.dimtad = 1
        ds.dxf.dimclrd = 3
        ds.dxf.dimclre = 3

    # -- primitives ---------------------------------------------------------------
    def polylines(self, lines, layer, offset=(0, 0)):
        ox, oy = offset
        for pts in lines:
            self.msp.add_lwpolyline([(x + ox, y + oy) for x, y in pts], dxfattribs={"layer": layer})

    def line(self, a, b, layer="CENTER"):
        self.msp.add_line(tuple(a), tuple(b), dxfattribs={"layer": layer})

    def circle(self, c, r, layer="REFERENCE"):
        self.msp.add_circle(tuple(c), r, dxfattribs={"layer": layer})

    def text(self, s, at, h=None, layer="TEXT", align="LEFT"):
        h = h or self.txt
        t = self.msp.add_mtext(s, dxfattribs={"layer": layer, "char_height": h})
        t.set_location(tuple(at), attachment_point={"LEFT": 1, "CENTER": 2, "RIGHT": 3,
                                                    "BOTTOM_LEFT": 7}[align])
        return t

    def dim_linear(self, p1, p2, base, angle=0, text="<>"):
        self.msp.add_linear_dim(base=tuple(base), p1=tuple(p1), p2=tuple(p2), angle=angle,
                                text=text, dxfattribs={"layer": "DIM"}).render()

    def dim_aligned(self, p1, p2, distance, text="<>"):
        self.msp.add_aligned_dim(p1=tuple(p1), p2=tuple(p2), distance=distance, text=text,
                                 dxfattribs={"layer": "DIM"}).render()

    def dim_angle(self, center, p1, p2, radius, label=None):
        """Angle between rays center->p1 and center->p2 (< 180 deg): arc, arrows-free ticks, label."""
        c = np.array(center, float)
        a1 = math.degrees(math.atan2(*(np.array(p1, float) - c)[::-1]))
        a2 = math.degrees(math.atan2(*(np.array(p2, float) - c)[::-1]))
        lo, hi = sorted((a1 % 360, a2 % 360))
        if hi - lo > 180:
            lo, hi = hi, lo + 360
        self.msp.add_arc(tuple(c), radius, lo, hi, dxfattribs={"layer": "DIM"})
        for a in (lo, hi):
            u = np.array([math.cos(math.radians(a)), math.sin(math.radians(a))])
            self.line(c + u * (radius - 2 * self.scale), c + u * (radius + 2 * self.scale), "DIM")
        mid = math.radians((lo + hi) / 2)
        at = c + np.array([math.cos(mid), math.sin(mid)]) * (radius + 3 * self.scale)
        self.text(label or f"{(hi - lo):.1f}\u00b0", at, layer="DIM",
                  align="RIGHT" if math.cos(mid) < 0 else "LEFT")

    # -- sheet frame / title block --------------------------------------------------
    def frame_and_title(self, notes):
        s = self.scale
        w, h = A3[0] * s, A3[1] * s
        x0, y0 = self.origin
        m = 10 * s
        self.msp.add_lwpolyline([(x0 + m, y0 + m), (x0 + w - m, y0 + m), (x0 + w - m, y0 + h - m),
                                 (x0 + m, y0 + h - m)], close=True, dxfattribs={"layer": "SHEET"})
        tw, th = 150 * s, 38 * s
        tx, ty = x0 + w - m - tw, y0 + m
        self.msp.add_lwpolyline([(tx, ty), (tx + tw, ty), (tx + tw, ty + th), (tx, ty + th)],
                                close=True, dxfattribs={"layer": "SHEET"})
        for k in (1, 2, 3):
            self.line((tx, ty + th * k / 4), (tx + tw, ty + th * k / 4), "SHEET")
        rows = [
            f"SHEET {self.sheet_no}   SCALE 1:{s:g} ON A3   UNITS mm / deg   REV A",
            "Ti 3Al-2.5V / 6Al-4V   PROJECTION: 1st angle",
            self.title,
            f"TITANIUM TRACK COMMUTER  -  SIZE {P.SIZE}",
        ]
        for k, r in enumerate(rows):
            self.text(r, (tx + 3 * s, ty + th * (k + 0.75) / 4), h=(3.2 if k == 3 else 2.4) * s)
        notes_text = self.text(notes, (x0 + m + 4 * s, y0 + m + 4 * s), h=2.2 * s, align="BOTTOM_LEFT")
        notes_text.dxf.width = 230 * s

    # -- output ------------------------------------------------------------------------
    def save(self, stem):
        self.doc.saveas(f"{stem}.dxf")
        cfg = Configuration(background_policy=BackgroundPolicy.WHITE,
                            color_policy=ColorPolicy.BLACK, lineweight_scaling=1.0)
        fig = plt.figure(figsize=(A3[0] / 25.4, A3[1] / 25.4))
        ax = fig.add_axes([0, 0, 1, 1])
        Frontend(RenderContext(self.doc), MatplotlibBackend(ax), config=cfg).draw_layout(
            self.msp, finalize=True)
        x0, y0 = self.origin
        ax.set_xlim(x0, x0 + A3[0] * self.scale)
        ax.set_ylim(y0, y0 + A3[1] * self.scale)
        ax.set_aspect("equal", adjustable="box")
        fig.savefig(f"{stem}.pdf")
        fig.savefig(f"{stem}.svg")
        fig.savefig(f"{stem}.png", dpi=110)
        plt.close(fig)


def side_elevation(model, stem):
    g = model.g
    sc = 5.0
    ground = g.bb_drop - g.tyre_radius
    sh = Sheet(sc, "SIDE ELEVATION - FRAME GEOMETRY", "1/2",
               origin=(-950.0, ground - 420.0))
    frame = model.build_frame()
    vis, _ = hlr_edges(frame, (0, 0, 1), (1, 0, 0))
    sh.polylines(vis, "FRAME")
    fvis, _ = hlr_edges(model.fork(), (0, 0, 1), (1, 0, 0))
    sh.polylines(fvis, "REFERENCE")

    ax_nom, ax_min, ax_max = model.axle_nom, model.axle_min, model.axle_max
    fa = g.front_axle
    # Centre lines.
    sh.line((0, 0), g.st_top)
    sh.line(g.tt_rear, g.tt_front)
    sh.line((0, 0), g.dt_front)
    up = -g.u_ht
    sh.line(g.ht_top + up * 40, g.ht_bot + g.u_ht * ((g.ht_bot[1] - ground) / -g.u_ht[1]))
    sh.line((0, 0), ax_nom)
    sh.line(ax_nom, g.ss_top)
    sh.line((ax_max[0] - 60, g.bb_drop), (fa[0] + 60, g.bb_drop))
    sh.line((ax_max[0] - 380, ground), (fa[0] + 380, ground), "REFERENCE")
    # Wheels (design tyre) and axle positions.
    for c in (ax_nom, fa):
        sh.circle(c, g.tyre_radius)
        sh.circle(c, P.RIM_BSD / 2)
    for a in (ax_min, ax_max):
        sh.circle(a, 3, "CENTER")

    # Dimensions.
    sh.dim_linear((0, 0), g.ht_top, (g.ht_top[0] + 150, 0), angle=90)                 # stack
    sh.dim_linear((0, 0), g.ht_top, (0, g.ht_top[1] + 90))                             # reach
    sh.dim_aligned(g.ht_top, g.ht_bot, -70)                                            # head tube
    hc = g.ht_bot + g.u_ht * ((g.ht_bot[1] - g.bb_drop) / -g.u_ht[1])
    sh.dim_angle(hc, hc + np.array([-1, 0]), hc + up, 110, f"HTA {P.HEAD_ANGLE}\u00b0")
    sh.dim_angle((0, 0), (-1, 0), g.u_st, 230, f"STA {P.SEAT_ANGLE}\u00b0")
    sh.dim_aligned((0, 0), g.st_top, 90)                                               # ST c-t
    sh.dim_linear(g.tt_rear, g.tt_front, (0, g.tt_y + 45),
                  text=f"<> (TT axis; pub. {P.PUBLISHED[0][2]})")
    sh.dim_aligned(ax_nom, (0, 0), 60,
                   text=f"<> nom. (slot {P.CHAINSTAY_MIN:g}-{P.CHAINSTAY_MAX:g})")     # CS
    sh.dim_linear(ax_nom, fa, (0, ground - 35))                                        # WB
    sh.dim_linear((0, 0), (fa[0], g.bb_drop), (230, 0), angle=90)                      # BB drop
    sh.dim_linear((0, ground), (0, 0), (-250, 0), angle=90)                            # BB height
    crown = g.ht_bot
    foot = crown + g.u_ht * float(np.dot(fa - crown, g.u_ht))
    sh.dim_aligned(crown, fa, -130, text="<> A-C (fork, ref.)")
    sh.dim_aligned(foot, fa, 0, text="<> offset")
    # Rear disc (reference): 160 rotor and caliper envelope ride on the slider.
    sh.circle(ax_nom, P.ROTOR_REAR / 2)
    cvis, _ = hlr_edges(model.caliper_envelope(P.CHAINSTAY_NOMINAL), (0, 0, 1), (1, 0, 0))
    sh.polylines(cvis, "REFERENCE")
    for side in (+1,):
        svis, _ = hlr_edges(model.slider(side, P.CHAINSTAY_NOMINAL), (0, 0, 1), (1, 0, 0))
        sh.polylines(svis, "REFERENCE")
    # Bottle bosses.
    d = g.dt_front / np.linalg.norm(g.dt_front)
    b1 = d * P.BOTTLE_BOSS_FROM_BB
    b2 = d * (P.BOTTLE_BOSS_FROM_BB + P.BOTTLE_BOSS_SPACING)
    sh.dim_aligned((0, 0), b1, 80)
    sh.dim_aligned(b1, b2, 80)

    s = g.summary()
    notes = "\n".join([
        "NOTES",
        f"1. Dimensions to tube centre lines; 700c (622) wheels, clearance for {P.TYRE_WIDTH_DESIGN:g} mm tyres "
        f"(min {P.TYRE_CLEARANCE_MIN:g} mm gap all round, checked in 3D).",
        f"2. Fit geometry = published Hektor 53 (stack {P.STACK:g}, reach {P.REACH:g}, HTA {P.HEAD_ANGLE}, "
        f"STA {P.SEAT_ANGLE}). Head tube {P.HEAD_TUBE_LEN:g} (pub. 120) for a {P.FORK_AXLE_TO_CROWN:g}/"
        f"{P.FORK_OFFSET:g} fork; BB drop {s['bb_drop']} as Hektor.",
        f"3. Horizontal TT measures {s['effective_top_tube_at_stack']:.0f} at stack height; published 530 is "
        "inconsistent with published stack/reach/STA (same 9-10 mm in all sizes).",
        f"4. Rear axle slot: chainstay {P.CHAINSTAY_MIN:g}-{P.CHAINSTAY_MAX:g} (min set by tyre/seat tube). "
        f"{P.FRONT_TEETH}T/{P.REAR_TEETH_FREEWHEEL}T + {P.BELT_TEETH}T belt sits at {s['belt_cs_60_22']}.",
        f"5. Trail {s['trail']} mm. Toe overlap approx. {s['toe_overlap_est']:.0f} mm "
        "(170 cranks) - expected with track geometry and large tyres.",
        f"6. Brakes: hydraulic disc. Rear {P.REAR_BRAKE_MOUNT}; front {P.FRONT_BRAKE_MOUNT} on a "
        f"{P.FRONT_AXLE} fork.",
        "7. Fork, wheels, sprockets, sliders, rotor and caliper are reference only (phantom). DXF is 1:1 - "
        "do not scale the PDF.",
    ])
    sh.frame_and_title(notes)
    sh.save(stem)


def rear_end(model, stem):
    g = model.g
    sc = 2.0
    sh = Sheet(sc, "REAR END PLAN VIEW + DROPOUT DETAIL", "2/2", origin=(-620.0, -360.0))
    frame = model.build_frame()
    # Plan view from above: view dir +Y; drawing x = model X, drawing y = -model Z.
    vis, _ = hlr_edges(frame, (0, 1, 0), (1, 0, 0))
    vis = [pts for pts in vis if max(p[0] for p in pts) < 60]
    ty = 40.0   # plan view drawn at y offset
    sh.polylines(vis, "FRAME", offset=(0, ty))

    ax_nom = model.axle_nom
    def zy(z):
        return -z + ty
    # Centre plane, hub, tyre envelope, belt plane.
    sh.line((ax_nom[0] - 40, zy(0)), (60, zy(0)))
    for z in (P.REAR_SPACING / 2, -P.REAR_SPACING / 2):
        sh.line((ax_nom[0], zy(z)), (ax_nom[0], zy(0)), "REFERENCE")
    hw = P.TYRE_WIDTH_DESIGN / 2
    x0, x1 = ax_nom[0] - g.tyre_radius, ax_nom[0] + g.tyre_radius
    sh.msp.add_lwpolyline([(x0, zy(hw)), (x1, zy(hw)), (x1, zy(-hw)), (x0, zy(-hw))], close=True,
                          dxfattribs={"layer": "REFERENCE"})
    bz0, bz1 = P.CHAINLINE - P.BELT_WIDTH / 2, P.CHAINLINE + P.BELT_WIDTH / 2
    r_ring = P.FRONT_TEETH * P.BELT_PITCH / math.pi / 2
    r_cog = P.REAR_TEETH_FREEWHEEL * P.BELT_PITCH / math.pi / 2
    for xa, xb in ((-r_ring, r_ring), (ax_nom[0] - r_cog, ax_nom[0] + r_cog)):
        sh.msp.add_lwpolyline([(xa, zy(bz0)), (xb, zy(bz0)), (xb, zy(bz1)), (xa, zy(bz1))],
                              close=True, dxfattribs={"layer": "REFERENCE"})
    sh.text("BELT LINE (Gates CDX 12 mm)", (r_ring + 10, zy(P.CHAINLINE)))
    sh.text(f"TYRE {P.TYRE_WIDTH_DESIGN:g}-622 ENVELOPE", (ax_nom[0] + 40, zy(-hw) - 6))
    # Dimensions.
    half = P.REAR_SPACING / 2
    sh.dim_linear((ax_nom[0], zy(half)), (ax_nom[0], zy(-half)), (ax_nom[0] - 55, 0), angle=90,
                  text="<> OLD (solid axle hub)")
    sh.dim_linear((30, zy(0)), (30, zy(P.CHAINLINE)), (125, 0), angle=90, text="<> chainline")
    sh.dim_linear((0, zy(34)), (0, zy(-34)), (80, 0), angle=90, text="<> BSA shell")
    zs = P.STAY_DROPOUT_Z
    sh.dim_linear((ax_nom[0] + 20, zy(zs)), (ax_nom[0] + 20, zy(-zs)), (ax_nom[0] - 25, 0), angle=90,
                  text="<> stays c-c at dropout")
    cz = P.CHAINSTAY_BB_Z
    sh.dim_linear((-8, zy(cz)), (-8, zy(-cz)), (-45, 0), angle=90, text="<> CS c-c at BB")
    zt, ow = P.CHAINSTAY_TYRE_ZONE_Z, P.CHAINSTAY_OVAL[0]
    sh.dim_linear((-110, zy(zt - ow / 2)), (-110, zy(-zt + ow / 2)), (-150, 0), angle=90,
                  text=f"<> CS gap ({ow:g} wide crimp)")

    # Sliding dropout detail (side view, drive side), shifted below the plan view.
    dy = -230.0
    dx = 0.0
    plate = model.dropout_plate(+1)
    dvis, _ = hlr_edges(plate, (0, 0, 1), (1, 0, 0))
    sh.polylines(dvis, "FRAME", offset=(dx, dy))
    svis, _ = hlr_edges(model.slider(+1, P.CHAINSTAY_NOMINAL), (0, 0, 1), (1, 0, 0))
    sh.polylines(svis, "REFERENCE", offset=(dx, dy))
    a_min, a_max = model.axle_min, model.axle_max
    for cs, a in ((P.CHAINSTAY_MIN, a_min), (P.CHAINSTAY_NOMINAL, ax_nom), (P.CHAINSTAY_MAX, a_max)):
        c = (a[0] + dx, a[1] + dy)
        sh.circle(c, 4.75, "CENTER")
        sh.line((c[0], c[1] - 8), (c[0], c[1] + 8))
    sh.line((a_max[0] - 40 + dx, g.bb_drop + dy), (a_min[0] + 70 + dx, g.bb_drop + dy))
    sh.dim_linear((a_max[0] + dx, g.bb_drop + dy), (a_min[0] + dx, g.bb_drop + dy),
                  (0, g.bb_drop + dy - 45),
                  text=f"<> slider travel (CS {P.CHAINSTAY_MIN:g} - {P.CHAINSTAY_MAX:g})")
    bx, by = P.SLIDER_BOLT_TOP
    sh.dim_linear((a_min[0] + dx, g.bb_drop + dy), (a_min[0] + bx + dx, g.bb_drop + by + dy),
                  (a_min[0] + 75 + dx, 0), angle=90, text="<> bolt")
    sh.text("SLIDING DROPOUT DETAIL (DRIVE SIDE, OUTSIDE VIEW)\n"
            f"Frame: 6Al-4V receiver plate, {P.DROPOUT_THICKNESS:g} mm, window + 2 x M6 slots "
            f"({P.SLIDER_BOLT_SLOT_WIDTH:g} wide)\n"
            "Slider (phantom, bought-in): axle in vertical slot; non-drive slider carries the post mount\n"
            f"Axle marks: CS {P.CHAINSTAY_MIN:g} / {P.CHAINSTAY_NOMINAL:g} ({P.BELT_TEETH}T belt) / "
            f"{P.CHAINSTAY_MAX:g}", (a_max[0] - 60 + dx, g.bb_drop + dy + 95))
    sh.text("PLAN VIEW FROM ABOVE (front to the right, drive side down)", (-430, zy(-95)))

    notes = "\n".join([
        "NOTES",
        f"1. Chainstays {P.CHAINSTAY[0]} x {P.CHAINSTAY[1]} crimped to {P.CHAINSTAY_OVAL[0]:g} x "
        f"{P.CHAINSTAY_OVAL[1]:g} oval from BB to 110 mm behind BB (clears {P.TYRE_WIDTH_DESIGN:g} mm tyre "
        f"AND {P.FRONT_TEETH}T belt ring at {P.CHAINLINE:g} chainline).",
        f"2. Stays run at {P.STAY_DROPOUT_Z:g} mm from centre plane near the dropout so the belt and rear "
        "cog clear the drive-side stays.",
        "3. Belt drive requires a frame split: bolted splitter in the drive-side seat stay (shown), "
        "or a split dropout per builder's standard.",
        f"4. Sliding dropouts tension the belt and carry the rear {P.REAR_BRAKE_MOUNT}; "
        f"{P.ROTOR_REAR:g} rotor on the non-drive side. Rotor and caliper clear the frame by "
        f">= {P.DISC_CLEARANCE_MIN:g} mm over the full travel. No rim-brake bridge.",
        "5. Rear hose: internal through top tube (6 mm ports, non-drive side), then along the non-drive "
        "seat stay on 2 x M4 guide bosses.",
    ])
    sh.frame_and_title(notes)
    sh.save(stem)
