"""Clearance checks of the 3D layout against the design tyre and the belt drive.

The tyre is modelled as a torus (circular section, width = TYRE_WIDTH_DESIGN)
around the rear axle; stays are sampled densely along their lofted stations.
All results are gaps in mm (negative = interference).
"""
import math

import numpy as np

import params as P
from geometry import point_line_distance


def _samples(stations, n=12):
    """Densely interpolate (point, width, height) between loft stations."""
    out = []
    for (p0, _, w0, h0), (p1, _, w1, h1) in zip(stations, stations[1:]):
        a, b = np.array(p0.toTuple()), np.array(p1.toTuple())
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append((a + (b - a) * t, w0 + (w1 - w0) * t, h0 + (h1 - h0) * t))
    p, _, w, h = stations[-1]
    out.append((np.array(p.toTuple()), w, h))
    return out


def tyre_gap(samples, axle):
    r_sec = P.TYRE_WIDTH_DESIGN / 2
    r_c = P.RIM_BSD / 2 + P.TYRE_HEIGHT_DESIGN - r_sec   # torus centre-circle radius
    best = math.inf
    for p, w, h in samples:
        dx, dy, dz = p[0] - axle[0], p[1] - axle[1], p[2]
        rho = math.hypot(dx, dy)
        dr = rho - r_c
        d = math.hypot(dr, dz)
        # Stay half-size in the direction of the tyre (ellipse support distance).
        ur, uz = dr / d, dz / d
        half = math.hypot(h / 2 * ur, w / 2 * uz)
        best = min(best, d - r_sec - half)
    return best


def belt_gaps(samples, axle):
    """Lateral gap from a stay to the belt ring, rear cog and both belt runs."""
    z_in = P.CHAINLINE - P.BELT_WIDTH / 2      # inner face of belt / sprockets
    z_out = P.CHAINLINE + P.BELT_WIDTH / 2
    r1 = P.FRONT_TEETH * P.BELT_PITCH / math.pi / 2 + 3    # incl. belt thickness
    r2 = P.REAR_TEETH_FREEWHEEL * P.BELT_PITCH / math.pi / 2 + 3
    ax, ay = axle

    def run_y(x, sign):
        t = x / ax
        return sign * r1 + t * (ay + sign * r2 - sign * r1)

    worst = math.inf
    for p, w, h in samples:
        x, y, z = p
        zin, zout = z - w / 2, z + w / 2
        overlaps_z = zout > z_in and zin < z_out
        in_ring = math.hypot(x, y) < r1 + h / 2
        in_cog = math.hypot(x - ax, y - ay) < r2 + h / 2
        on_run = ax < x < 0 and any(abs(y - run_y(x, s)) < h / 2 + 2 for s in (1, -1))
        if in_ring or in_cog or on_run:
            gap = (z_in - zout) if z < P.CHAINLINE else (zin - z_out)
            worst = min(worst, gap if not overlaps_z else -min(zout - z_in, z_out - zin))
    return worst


def run_checks(model):
    g = model.g
    cs = _samples(model.chainstay_stations(+1))
    ss = _samples(model.seatstay_stations(+1))
    res = {}
    for label, csl in (("min", P.CHAINSTAY_MIN), ("max", P.CHAINSTAY_MAX)):
        axle = g.rear_axle(csl)
        res[f"tyre_to_chainstay_{label}"] = round(tyre_gap(cs, axle), 1)
        res[f"tyre_to_seatstay_{label}"] = round(tyre_gap(ss, axle), 1)
        res[f"tyre_to_seat_tube_{label}"] = round(g.seat_tube_tyre_gap(csl), 1)
        bp = g.brake_bridge()
        res[f"tyre_to_brake_bridge_{label}"] = round(
            float(np.linalg.norm(bp - axle)) - g.tyre_radius - 12.7 / 2, 1)
        res[f"belt_to_chainstay_{label}"] = round(belt_gaps(cs, axle), 1)
        res[f"belt_to_seatstay_{label}"] = round(belt_gaps(ss, axle), 1)
    # Front: down tube (wheel straight ahead) and space under the fork crown.
    res["front_tyre_to_down_tube"] = round(
        point_line_distance(g.front_axle, np.zeros(2), g.dt_front)
        - P.DOWN_TUBE[0] / 2 - g.tyre_radius, 1)
    res["front_crown_space_above_tyre"] = round(P.FORK_AXLE_TO_CROWN - g.tyre_radius, 1)
    tyre_keys = [k for k in res if k.startswith("tyre") or k == "front_tyre_to_down_tube"]
    belt_keys = [k for k in res if k.startswith("belt")]
    res["tyre_ok"] = all(res[k] >= P.TYRE_CLEARANCE_MIN - 0.05 for k in tyre_keys)
    res["belt_ok"] = all(res[k] >= P.BELT_CLEARANCE_MIN - 0.05 for k in belt_keys)
    return res


if __name__ == "__main__":
    import json

    from model3d import FrameModel
    print(json.dumps(run_checks(FrameModel()), indent=2))
