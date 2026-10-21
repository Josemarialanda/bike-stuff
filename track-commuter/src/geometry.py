"""Frame geometry solver: turns params.py into key points and derived numbers.

All 2D points are (x, y) in the frame's side plane (z = 0), mm, origin at the
BB centre, x forward, y up.
"""
import math

import numpy as np

import params as P


def unit(deg):
    r = math.radians(deg)
    return np.array([math.cos(r), math.sin(r)])


def belt_center_distance(teeth_front, teeth_rear, belt_teeth, pitch=P.BELT_PITCH):
    """Centre distance for a two-pulley belt drive (open belt, exact solve)."""
    d1 = teeth_front * pitch / math.pi
    d2 = teeth_rear * pitch / math.pi
    length = belt_teeth * pitch
    lo, hi = 100.0, 1000.0
    for _ in range(100):
        c = (lo + hi) / 2
        phi = math.asin((d1 - d2) / (2 * c))
        span = 2 * c * math.cos(phi) + math.pi * (d1 + d2) / 2 + phi * (d1 - d2)
        lo, hi = (c, hi) if span < length else (lo, c)
    return (lo + hi) / 2


def point_line_distance(p, a, direction):
    d = direction / np.linalg.norm(direction)
    v = p - a
    return abs(v[0] * d[1] - v[1] * d[0])


class Geometry:
    def __init__(self):
        ha, sa = P.HEAD_ANGLE, P.SEAT_ANGLE
        # Steering axis, pointing down/forward, and its forward normal.
        self.u_ht = np.array([math.cos(math.radians(ha)), -math.sin(math.radians(ha))])
        self.n_ht = np.array([math.sin(math.radians(ha)), math.cos(math.radians(ha))])
        self.ht_top = np.array([P.REACH, P.STACK])
        self.ht_bot = self.ht_top + P.HEAD_TUBE_LEN * self.u_ht

        # Fork -> front axle -> BB drop.
        s = math.sqrt(P.FORK_AXLE_TO_CROWN**2 - P.FORK_OFFSET**2)
        self.fork_crown = self.ht_bot
        self.front_axle = self.ht_bot + s * self.u_ht + P.FORK_OFFSET * self.n_ht
        self.bb_drop = float(self.front_axle[1])

        # Seat tube.
        self.u_st = np.array([-math.cos(math.radians(sa)), math.sin(math.radians(sa))])
        self.st_top = P.SEAT_TUBE_CT * self.u_st

        # Top tube: horizontal, top surface just below the head tube top.
        self.tt_y = P.STACK - P.TOP_TUBE_DROP_BELOW_HT_TOP - P.TOP_TUBE[0] / 2
        self.tt_rear = self.u_st * (self.tt_y / self.u_st[1])
        self.tt_front = self.ht_top + self.u_ht * ((P.STACK - self.tt_y) / -self.u_ht[1])

        # Down tube: BB centre to the head tube axis.
        self.dt_front = self.ht_bot - P.DOWN_TUBE_HT_JUNCTION * self.u_ht

        # Seat stay junction on the seat tube.
        t_tt = np.linalg.norm(self.tt_rear)
        self.ss_top = self.u_st * (t_tt - P.SEATSTAY_BELOW_TT)

        self.belt_cd_freewheel = belt_center_distance(
            P.FRONT_TEETH, P.REAR_TEETH_FREEWHEEL, P.BELT_TEETH)
        self.belt_cd_fixed = belt_center_distance(
            P.FRONT_TEETH, P.REAR_TEETH_FIXED, P.BELT_TEETH)

        self.tyre_radius = P.RIM_BSD / 2 + P.TYRE_HEIGHT_DESIGN

    # Rear axle position for a given chainstay length.
    def rear_axle(self, cs=None):
        cs = P.CHAINSTAY_NOMINAL if cs is None else cs
        return np.array([-math.sqrt(cs**2 - self.bb_drop**2), self.bb_drop])

    def wheelbase(self, cs=None):
        return float(self.front_axle[0] - self.rear_axle(cs)[0])

    def trail(self):
        a = math.radians(P.HEAD_ANGLE)
        return (self.tyre_radius * math.cos(a) - P.FORK_OFFSET) / math.sin(a)

    def front_center(self):
        return float(np.linalg.norm(self.front_axle))

    def seat_tube_tyre_gap(self, cs):
        d = point_line_distance(self.rear_axle(cs), np.zeros(2), self.u_st)
        return d - P.SEAT_TUBE[0] / 2 - self.tyre_radius

    def min_chainstay_for_clearance(self):
        lo, hi = 300.0, 500.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if self.seat_tube_tyre_gap(mid) < P.TYRE_CLEARANCE_MIN:
                lo = mid
            else:
                hi = mid
        return hi

    def chainstay_for_belt(self, cd):
        # The belt centre distance is BB-to-axle, i.e. the chainstay length.
        return cd

    def brake_bridge(self):
        """Point on the seat-stay centreline where the 12.7 mm bridge clears the
        tyre by BRAKE_BRIDGE_TYRE_GAP with the axle at the front of the slot."""
        axle = self.rear_axle(P.CHAINSTAY_MIN)
        a, b = self.rear_axle(P.CHAINSTAY_NOMINAL), self.ss_top
        target = self.tyre_radius + P.BRAKE_BRIDGE_TYRE_GAP + 12.7 / 2
        lo, hi = 0.0, 1.0
        for _ in range(60):
            m = (lo + hi) / 2
            if np.linalg.norm(a + m * (b - a) - axle) < target:
                lo = m
            else:
                hi = m
        return a + hi * (b - a)

    def brake_reach(self, cs):
        return float(np.linalg.norm(self.brake_bridge() - self.rear_axle(cs))
                     - P.RIM_BRAKE_TRACK_RADIUS)

    def effective_top_tube(self):
        """Horizontal seat-axis to steering-axis distance at stack height."""
        x_seat = self.u_st[0] * (P.STACK / self.u_st[1])
        return float(P.REACH - x_seat)

    def standover(self):
        bb_height = self.tyre_radius - self.bb_drop
        return bb_height + self.tt_y + P.TOP_TUBE[0] / 2

    def toe_overlap(self, foot=100.0):
        """Positive = overlap (mm) between toe (crank + ball-to-toe) and front tyre."""
        fx = self.front_axle[0]
        gap = math.hypot(fx, self.front_axle[1]) - self.tyre_radius
        return P.CRANK_LENGTH + foot - gap

    def summary(self):
        cs_rows = []
        for cs in (P.CHAINSTAY_MIN, P.CHAINSTAY_NOMINAL, P.CHAINSTAY_MAX):
            cs_rows.append({
                "chainstay": cs,
                "wheelbase": round(self.wheelbase(cs), 1),
                "seat_tube_tyre_gap": round(self.seat_tube_tyre_gap(cs), 1),
                "rear_brake_reach": round(self.brake_reach(cs), 1),
            })
        return {
            "bb_drop": round(self.bb_drop, 1),
            "bb_height": round(self.tyre_radius - self.bb_drop, 1),
            "trail": round(self.trail(), 1),
            "front_center": round(self.front_center(), 1),
            "wheelbase_at_published_cs": round(self.wheelbase(P.CHAINSTAY_PUBLISHED), 1),
            "effective_top_tube_at_stack": round(self.effective_top_tube(), 1),
            "top_tube_axis_height": round(self.tt_y, 1),
            "seat_tube_above_tt": round(P.SEAT_TUBE_CT - np.linalg.norm(self.tt_rear), 1),
            "standover_est": round(self.standover(), 1),
            "toe_overlap_est": round(self.toe_overlap(), 1),
            "belt_cs_60_22": round(self.belt_cd_freewheel, 1),
            "belt_cs_60_21": round(self.belt_cd_fixed, 1),
            "min_cs_for_tyre": round(self.min_chainstay_for_clearance(), 1),
            "chainstay_positions": cs_rows,
        }


if __name__ == "__main__":
    import json
    print(json.dumps(Geometry().summary(), indent=2))
