"""Parametric 3D model of the titanium frame (CadQuery / OpenCascade).

Tubes are modelled as thin-wall shells with coped (mitred) ends: each branch
tube has the outer volume of the tubes it is welded to removed, then
everything is fused into a single solid.
"""
import math

import cadquery as cq
import numpy as np

import params as P
from geometry import Geometry

V = cq.Vector


def v3(p2, z=0.0):
    return V(float(p2[0]), float(p2[1]), float(z))


def _np(v):
    return np.array([v.x, v.y, v.z])


def cylinder(p0, p1, radius):
    d = p1 - p0
    return cq.Solid.makeCylinder(radius, d.Length, p0, d.normalized())


def tube(p0, p1, od, wall):
    """Straight hollow tube from p0 to p1."""
    d = (p1 - p0).normalized()
    return cylinder(p0, p1, od / 2).cut(cylinder(p0 - d, p1 + d, od / 2 - wall))


def frustum(p0, p1, r0, r1):
    d = p1 - p0
    return cq.Solid.makeCone(r0, r1, d.Length, p0, d.normalized())


def _section(point, tangent, w, h):
    """Elliptical section: w across (mostly Z), h in the side plane."""
    t = tangent.normalized()
    up = V(0, 1, 0)
    side_up = (up - t * up.dot(t)).normalized()  # in-plane "height" direction
    if h >= w:
        return cq.Wire.makeEllipse(h / 2, w / 2, point, t, side_up)
    across = t.cross(side_up).normalized()
    return cq.Wire.makeEllipse(w / 2, h / 2, point, t, across)


def lofted_tube(stations, wall):
    """Hollow tube lofted through stations [(point, tangent, w, h), ...]."""
    outer = [_section(p, t, w, h) for p, t, w, h in stations]
    inner = [_section(p, t, w - 2 * wall, h - 2 * wall) for p, t, w, h in stations]
    return cq.Solid.makeLoft(outer, False).cut(cq.Solid.makeLoft(inner, False))


def _tangents(points):
    out = []
    for i in range(len(points)):
        a = points[max(i - 1, 0)]
        b = points[min(i + 1, len(points) - 1)]
        out.append((b - a).normalized())
    return out


class FrameModel:
    def __init__(self, geo=None):
        self.g = geo or Geometry()
        g = self.g
        self.axle_min = g.rear_axle(P.CHAINSTAY_MIN)
        self.axle_nom = g.rear_axle(P.CHAINSTAY_NOMINAL)
        self.axle_max = g.rear_axle(P.CHAINSTAY_MAX)

    # -- hosts -----------------------------------------------------------------
    def head_tube(self):
        g = self.g
        top, bot = v3(g.ht_top), v3(g.ht_bot)
        outer = frustum(bot, top, P.HEAD_TUBE_OD[1] / 2, P.HEAD_TUBE_OD[0] / 2)
        d = (top - bot).normalized()
        bore = frustum(bot - d, top + d, P.HEAD_TUBE_ID[1] / 2, P.HEAD_TUBE_ID[0] / 2)
        return outer, outer.cut(bore)

    def bb_shell(self):
        od, width = P.BB_SHELL
        a, b = V(0, 0, -width / 2), V(0, 0, width / 2)
        outer = cylinder(a, b, od / 2)
        return outer, outer.cut(cylinder(a - V(0, 0, 1), b + V(0, 0, 1), P.BB_SHELL_ID / 2))

    def seat_tube(self):
        g = self.g
        od, wall = P.SEAT_TUBE
        p0, p1 = V(0, 0, 0), v3(g.st_top)
        outer = cylinder(p0, p1, od / 2)
        shell = tube(p0, p1, od, wall)
        # Reamed 27.2 seatpost sleeve inside the top of the seat tube.
        d = (p1 - p0).normalized()
        s0 = p1 - d * 120
        sleeve = cylinder(s0, p1, od / 2 - wall).cut(cylinder(s0 - d, p1 + d, P.SEATPOST_DIA / 2))
        shell = shell.fuse(sleeve)
        # 16 mm seat-clamp slot through the rear wall, with a 4 mm stress-relief hole.
        slot_len = 16.0
        base = p1 - d * slot_len
        plane = cq.Plane(origin=base, xDir=d, normal=V(0, 0, 1))  # plane Y = rearwards
        slot = cq.Workplane(plane).rect(slot_len + 1, od, centered=False).extrude(1.0, both=True).val()
        back = V(0, 0, 1).cross(d)
        relief = cylinder(base, base + back * od, 2.0)
        shell = shell.cut(slot).cut(relief)
        return outer, shell

    def dropout_plate(self, side):
        g = self.g
        y0 = g.bb_drop
        xf = self.axle_min[0]          # slot front (shortest chainstay)
        xr = self.axle_max[0] - 16     # plate rear end (slot opens rearwards)
        z0 = side * P.STAY_DROPOUT_Z - P.DROPOUT_THICKNESS / 2
        wp = cq.Workplane("XY", origin=(0, 0, z0))
        body = (wp.moveTo(xr, y0 - 14).lineTo(xf + 48, y0 - 14)
                .lineTo(xf + 48, y0 + 4).lineTo(xf + 26, y0 + 28)
                .lineTo(xf + 4, y0 + 30).lineTo(xr, y0 + 14).close()
                .extrude(P.DROPOUT_THICKNESS))
        r = P.AXLE_SLOT_WIDTH / 2
        slot = (cq.Workplane("XY", origin=(0, 0, z0 - 1))
                .moveTo(xr - 2, y0 - r).lineTo(xf, y0 - r)
                .threePointArc((xf + r, y0), (xf, y0 + r))
                .lineTo(xr - 2, y0 + r).close().extrude(P.DROPOUT_THICKNESS + 2))
        return body.cut(slot).val()

    # -- branches ----------------------------------------------------------------
    def top_tube(self):
        g = self.g
        od, wall = P.TOP_TUBE
        shell = tube(v3(g.tt_rear), v3(g.tt_front), od, wall)
        # Internal rear-brake routing ports (6 mm) on the top, non-drive side.
        for x in (g.tt_front[0] - 45, g.tt_rear[0] + 45):
            c = V(x, g.tt_y, 0)
            d = V(0, math.cos(math.radians(35)), -math.sin(math.radians(35)))
            shell = shell.cut(cylinder(c, c + d * (od / 2 + 2), 3.0))
        return shell

    def down_tube(self):
        g = self.g
        od, wall = P.DOWN_TUBE
        p0, p1 = V(0, 0, 0), v3(g.dt_front)
        shell = tube(p0, p1, od, wall)
        # Bottle bosses (M5 rivnut bosses) on the top face.
        d = (p1 - p0).normalized()
        n = V(-d.y, d.x, 0)
        for s in (P.BOTTLE_BOSS_FROM_BB, P.BOTTLE_BOSS_FROM_BB + P.BOTTLE_BOSS_SPACING):
            c = p0 + d * s
            boss = cylinder(c, c + n * (od / 2 + 2.5), 5.0)
            shell = shell.fuse(boss.cut(cylinder(c, c + n * (od / 2 + 3), 2.5)))
        return shell

    def chainstay(self, side):
        g = self.g
        xe = self.axle_min[0] + 34                       # end inside the dropout
        ye = g.bb_drop * xe / self.axle_nom[0]
        def y_at(x):
            return ye * x / xe
        stations_x = [-6, -40, -75, -110, -170, -240, -300, xe]
        def z_at(x):
            if x >= -110:
                return np.interp(-x, [6, 75, 110], [P.CHAINSTAY_BB_Z, 24.3, 24.5])
            f = (x - (-110)) / (xe - (-110))
            return 24.5 + (P.STAY_DROPOUT_Z - 24.5) * (3 * f**2 - 2 * f**3 if f < 1 else 1)
        pts = [V(x, y_at(x), side * z_at(x)) for x in stations_x]
        tans = _tangents(pts)
        od = P.CHAINSTAY[0]
        ow, oh = P.CHAINSTAY_OVAL
        sizes = []
        for x in stations_x:
            if x >= -110:
                sizes.append((ow, oh))
            elif x >= -170:
                sizes.append(((ow + od) / 2, (oh + od) / 2))
            else:
                sizes.append((od, od))
        st = [(p, t, w, h) for p, t, (w, h) in zip(pts, tans, sizes)]
        return lofted_tube(st, P.CHAINSTAY[1])

    def seatstay_points(self, side):
        g = self.g
        p0 = np.array([self.axle_min[0] + 6, g.bb_drop + 22])
        p2 = g.ss_top
        d = (p2 - p0) / np.linalg.norm(p2 - p0)
        L = float(np.linalg.norm(p2 - p0))
        s_vals = [0, 40, P.SEATSTAY_BEND_FROM_DROPOUT, 160, 240, 320, L - 30, L]
        zs = []
        for s in s_vals:
            if s <= P.SEATSTAY_BEND_FROM_DROPOUT:
                z = P.STAY_DROPOUT_Z
            else:
                f = (s - P.SEATSTAY_BEND_FROM_DROPOUT) / (L - P.SEATSTAY_BEND_FROM_DROPOUT)
                f = math.sin(f * math.pi / 2)  # leave the bend gently, arrive straight-ish
                z = P.STAY_DROPOUT_Z + (P.SEATSTAY_ST_OFFSET - P.STAY_DROPOUT_Z) * f
            zs.append(z)
        return [V(*(p0 + d * s), side * z) for s, z in zip(s_vals, zs)]

    def seatstay(self, side):
        pts = self.seatstay_points(side)
        tans = _tangents(pts)
        od, wall = P.SEATSTAY
        return lofted_tube([(p, t, od, od) for p, t in zip(pts, tans)], wall)

    def belt_splitter(self):
        """Bolted splitter sleeve on the drive-side seat stay (belt install)."""
        pts = self.seatstay_points(+1)
        a, b = pts[3], pts[4]
        d = (b - a).normalized()
        c = a + (b - a) * 0.5
        return cylinder(c - d * 16, c + d * 16, 12.0).cut(cylinder(c - d * 17, c + d * 17, 7.0))

    def brake_bridge(self):
        g = self.g
        bp = g.brake_bridge()
        # Z of the seat stays at the bridge position (interpolate along the stay).
        pts = self.seatstay_points(+1)
        xs = [p.x for p in pts]
        zb = float(np.interp(bp[0], xs, [p.z for p in pts]))
        a, b = v3(bp, -zb), v3(bp, zb)
        bridge = cylinder(a, b, 6.35).cut(cylinder(a, b, 6.35 - 1.0))
        # Caliper bolt hole: perpendicular to the stays, through the bridge.
        ss_dir = _np(pts[-1] - pts[0])[:2]
        ss_dir = ss_dir / np.linalg.norm(ss_dir)
        n = V(ss_dir[1], -ss_dir[0], 0)   # points rearwards/up, away from tyre
        c = v3(bp, 0)
        hole = cylinder(c - n * 10, c + n * 10, 3.0)
        return bridge.cut(hole)

    # -- assembly ------------------------------------------------------------------
    def build_frame(self):
        ht_out, ht = self.head_tube()
        bb_out, bb = self.bb_shell()
        st_out, st = self.seat_tube()
        drops = [self.dropout_plate(s) for s in (+1, -1)]

        tt = self.top_tube().cut(ht_out).cut(st_out)
        dt = self.down_tube().cut(ht_out).cut(bb_out).cut(st_out)
        st = st.cut(bb_out)
        stays = []
        for s in (+1, -1):
            cs = self.chainstay(s).cut(bb_out)
            ss = self.seatstay(s).cut(st_out)
            stays += [cs, ss]
        parts = [ht, bb, st, tt, dt, *stays, *drops, self.brake_bridge(), self.belt_splitter()]
        frame = parts[0]
        for p in parts[1:]:
            frame = frame.fuse(p)
        return frame.clean()

    def fork(self):
        """Reference-only straight-blade tapered carbon fork (not for manufacture)."""
        g = self.g
        top, bot = v3(g.ht_top), v3(g.ht_bot)
        d = (top - bot).normalized()
        steerer = frustum(bot - d * 2, top + d * 25, 38.1 / 2, 28.6 / 2)
        crown_c = bot - d * 18
        crown = cq.Solid.makeBox(46, 30, 92).translate(crown_c - V(23, 15, 46))
        crown = crown.rotate(crown_c, crown_c + V(0, 0, 1), -(90 - P.HEAD_ANGLE))
        parts = [steerer, crown]
        hub_half = 50.0
        for s in (+1, -1):
            a = crown_c + V(0, 0, s * 38)
            b = v3(g.front_axle, s * (hub_half + 4))
            t = (b - a).normalized()
            parts.append(cq.Solid.makeLoft([
                _section(a, t, 20, 34), _section(b, t, 10, 16)], False))
        f = parts[0]
        for p in parts[1:]:
            f = f.fuse(p)
        return f

    def wheel(self, centre):
        r_rim = P.RIM_BSD / 2
        tyre_r = P.TYRE_WIDTH_DESIGN / 2
        tyre = cq.Solid.makeTorus(r_rim + tyre_r, tyre_r, centre, V(0, 0, 1))
        rim = cylinder(centre - V(0, 0, 9), centre + V(0, 0, 9), r_rim + 2).cut(
            cylinder(centre - V(0, 0, 10), centre + V(0, 0, 10), r_rim - 28))
        hub = cylinder(centre - V(0, 0, 50), centre + V(0, 0, 50), 18)
        return tyre.fuse(rim).fuse(hub)

    def belt_drive(self):
        g = self.g
        d1 = P.FRONT_TEETH * P.BELT_PITCH / math.pi
        d2 = P.REAR_TEETH_FREEWHEEL * P.BELT_PITCH / math.pi
        z0 = P.CHAINLINE - P.BELT_WIDTH / 2
        ring = cylinder(V(0, 0, z0), V(0, 0, z0 + P.BELT_WIDTH), d1 / 2)
        cog_c = self.axle_nom
        cog = cylinder(v3(cog_c, z0), v3(cog_c, z0 + P.BELT_WIDTH), d2 / 2)
        return ring.fuse(cog)

    def build_assembly(self, frame=None):
        frame = frame or self.build_frame()
        asm = cq.Assembly(name="track_commuter_ti_53")
        asm.add(frame, name="frame_titanium", color=cq.Color(0.72, 0.72, 0.74))
        asm.add(self.fork(), name="fork_reference", color=cq.Color(0.1, 0.1, 0.1))
        asm.add(self.wheel(v3(self.g.front_axle)), name="front_wheel_ref",
                color=cq.Color(0.15, 0.15, 0.15))
        asm.add(self.wheel(v3(self.axle_nom)), name="rear_wheel_ref",
                color=cq.Color(0.15, 0.15, 0.15))
        asm.add(self.belt_drive(), name="belt_sprockets_ref", color=cq.Color(0.3, 0.3, 0.3))
        return asm
