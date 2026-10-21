"""Design parameters for the titanium track commuter (Hektor-inspired), size S/53.

Every number used by the 3D model, 2D drawings and spec sheet comes from here.
Change a value, run `python src/build.py`, and all outputs regenerate.

Coordinate system (mm): origin = bottom bracket centre, +X forward,
+Y up, +Z towards the drive (right) side.
"""

# --- Published Schindelhauer Hektor geometry (all sizes), for reference -------
# Columns: A seat tube c-t, B top tube horizontal, C head tube, D chainstay,
# E head angle, F seat angle, G wheelbase, H standover, I reach, J stack,
# headset, seatpost.  Source: schindelhauerbikes.com (Strapi geometryData).
PUBLISHED_COLUMNS = [
    "Size", "Seat tube c-t (A)", "Top tube horiz. (B)", "Head tube (C)",
    "Chainstay (D)", "Head angle (E)", "Seat angle (F)", "Wheelbase (G)",
    "Standover (H)", "Reach (I)", "Stack (J)", "Headset", "Seatpost",
]
PUBLISHED = [
    ["53 S", 530, 530, 120, 378, 73.5, 75.0, 961, 793, 406, 498, '1 1/8"', 27.2],
    ["56 M", 560, 550, 140, 378, 73.0, 74.5, 982, 816, 416, 516, '1 1/8"', 27.2],
    ["59 L", 590, 570, 160, 378, 74.0, 74.0, 988, 841, 426, 537, '1 1/8"', 27.2],
    ["62 XL", 620, 590, 180, 378, 74.0, 74.0, 1008, 865, 440, 557, '1 1/8"', 27.2],
]
SIZE = "53 S"

# --- Fit-critical geometry (kept exactly as published for size 53) -----------
STACK = 498.0            # BB centre to top-centre of head tube, vertical
REACH = 406.0            # BB centre to top-centre of head tube, horizontal
HEAD_TUBE_LEN = 105.0    # published 120; -15 for the taller 35 mm-clearance fork (keeps stack/reach/BB drop)
HEAD_ANGLE = 73.5        # deg from horizontal
SEAT_ANGLE = 75.0        # deg from horizontal
SEAT_TUBE_CT = 530.0     # BB centre to top of seat tube, along the axis
CHAINSTAY_PUBLISHED = 378.0

# --- Chosen fork (not published) -------------------------------------------------
# With stack/reach/head angle fixed, the fork sets the front axle height and so
# the BB drop (geometry.py derives it). Hektor (25 mm tyres): 365 A-C with the
# 120 head tube gives 48.4 drop and the published 961 wheelbase. For 35 mm tyres
# the fork grows to 380 A-C and the head tube shrinks 15 mm, so the drop is unchanged.
FORK_AXLE_TO_CROWN = 380.0   # incl. lower headset stack (zero-stack ZS56 ~0 mm)
FORK_OFFSET = 45.0

# Rear axle travel in the horizontal track-end slot (chainstay length).
# CHAINSTAY_MIN is the shortest position where a 35 mm tyre clears the round
# 31.8 mm seat tube by TYRE_CLEARANCE_MIN (Hektor: 378 with 25 mm tyres).
# NOMINAL is where 60T/22T + 115T Gates belt lands.
CHAINSTAY_MIN = 395.0
CHAINSTAY_NOMINAL = 401.5
CHAINSTAY_MAX = 409.0

# --- Wheels / tyres -----------------------------------------------------------
RIM_BSD = 622.0
TYRE_WIDTH_DESIGN = 35.0     # design clearance target: 35-622 (stock Hektor: 25-622)
TYRE_HEIGHT_DESIGN = 35.0
TYRE_CLEARANCE_MIN = 4.0     # min gap from tyre to any tube, all round (mm)
BELT_CLEARANCE_MIN = 3.0     # min gap from belt / sprockets to any tube (mm)
RIM_BRAKE_TRACK_RADIUS = 308.0  # pad centre radius on a 622 rim

# --- Drivetrain: Gates Carbon Drive CDX -----------------------------------------
REAR_SPACING = 135.0         # 135 mm solid-axle hub (fixed/flip-flop or singlespeed)
CHAINLINE = 50.0             # 42.5 track chainline leaves no room between 35 mm tyre and 60T ring
BELT_PITCH = 11.0
BELT_WIDTH = 12.0
BELT_TEETH = 115             # 113T (stock) is too short for the longer chainstay
FRONT_TEETH = 60
REAR_TEETH_FREEWHEEL = 22
REAR_TEETH_FIXED = 21
CRANK_LENGTH = 170.0

# --- Titanium tube set (3Al-2.5V CWSR unless noted) -----------------------------
# (outer diameter, wall) in mm. Proposals: the builder sets final butting.
TOP_TUBE = (31.8, 0.9)        # = seat tube OD so the TT miters cleanly onto it
DOWN_TUBE = (44.5, 0.9)
SEAT_TUBE = (31.8, 0.9)      # 27.2 post via reamed internal Ti sleeve at top
SEATPOST_DIA = 27.2
CHAINSTAY = (22.2, 0.9)      # ovalised to CHAINSTAY_OVAL near BB for clearance
CHAINSTAY_OVAL = (16.0, 27.0)  # (width Z, height) in the tyre/belt-ring zone
SEATSTAY = (16.0, 0.9)
HEAD_TUBE_OD = (48.0, 62.0)  # top / bottom OD, 6Al-4V machined, ZS44/ZS56
HEAD_TUBE_ID = (44.0, 56.0)
BB_SHELL = (41.0, 68.0)      # OD, width. BSA 1.37" x 24 TPI, 6Al-4V
BB_SHELL_ID = 34.0
DROPOUT_THICKNESS = 6.0      # 6Al-4V track-end plates
AXLE_SLOT_WIDTH = 10.2       # 3/8" (9.5) / 10 mm axles

# --- Layout details -------------------------------------------------------------
TOP_TUBE_DROP_BELOW_HT_TOP = 5.0   # TT top surface below HT top
DOWN_TUBE_HT_JUNCTION = 34.0       # DT axis meets HT axis this far above HT bottom
SEATSTAY_BELOW_TT = 65.0           # SS meet ST this far below TT axis (along ST)
SEATSTAY_ST_OFFSET = 11.0          # SS centre Z offset at the seat-tube junction
SEATSTAY_BEND_FROM_DROPOUT = 85.0  # SS run straight (belt clearance) before bending in
SEATSTAY_CONVERGE_POWER = 1.6      # >1 keeps the stays wide past the tyre, converging late
CHAINSTAY_BB_Z = 25.0              # CS centre Z at BB shell
CHAINSTAY_TYRE_ZONE_Z = 31.5       # CS centre Z where tyre and belt ring overlap (oval section)
STAY_DROPOUT_Z = REAR_SPACING / 2 + DROPOUT_THICKNESS / 2  # stay centre Z at dropout (mid-plate)
BOTTLE_BOSS_SPACING = 64.0
BOTTLE_BOSS_FROM_BB = 160.0        # lower boss, along DT axis from BB centre
BRAKE_BRIDGE_TYRE_GAP = 4.0        # bridge tube to tyre at the shortest axle position

MATERIAL_NOTE = "Titanium 3Al-2.5V CWSR tubes; 6Al-4V head tube, BB shell, dropouts"
