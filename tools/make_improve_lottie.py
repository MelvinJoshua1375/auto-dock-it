"""Generate improve-spark.json — a sparkle-burst Lottie for the Improve tab.

Design: a central glowing core that pulses, with 4 small spark particles radiating
outward at 45-degree angles (NE/SE/SW/NW). Each spark travels ~22 px from centre,
scales 0 → 1 → 0, and is staggered 10 frames apart so they feel natural rather
than mechanical.  Colour: near-white (0.95, 0.95, 0.95) on transparent background.
Loop: 60 frames @ 30 fps (2-second cycle).
"""

import json
import math
import pathlib

ANIM = pathlib.Path(__file__).resolve().parent.parent / "assets" / "anim"
ANIM.mkdir(parents=True, exist_ok=True)

W, H = 100, 100
CX, CY = 50, 50
FPS = 30
FRAMES = 60

# ── helpers ─────────────────────────────────────────────────────────────────

def ease_io():
    return {"i": {"x": [0.42], "y": [1]}, "o": {"x": [0.58], "y": [0]}}

def ease_io_2d():
    return {"i": {"x": [0.42, 0.42], "y": [1, 1]},
            "o": {"x": [0.58, 0.58], "y": [0, 0]}}

def kf(t, s, e=None, two_d=False):
    """Build a keyframe dict.  If e is given, add easing."""
    d = {"t": t, "s": s if isinstance(s, list) else [s]}
    if e is not None:
        d["e"] = e if isinstance(e, list) else [e]
        d.update(ease_io_2d() if two_d else ease_io())
    return d

def tr():
    """Default transform for a group."""
    return {
        "ty": "tr",
        "p":  {"a": 0, "k": [0, 0]},
        "a":  {"a": 0, "k": [0, 0]},
        "s":  {"a": 0, "k": [100, 100]},
        "r":  {"a": 0, "k": 0},
        "o":  {"a": 0, "k": 100},
        "sk": {"a": 0, "k": 0},
        "sa": {"a": 0, "k": 0},
    }

FILL_WHITE = {
    "ty": "fl", "nm": "fill",
    "c":  {"a": 0, "k": [0.95, 0.95, 0.95, 1]},
    "o":  {"a": 0, "k": 100},
    "r":  1,
}

# ── central core ────────────────────────────────────────────────────────────
# A small circle (r=5) that scales 0→1 in the first 8 frames, holds until
# frame 45, then scales back to 0 by frame 58, giving a heartbeat rhythm.

core_layer = {
    "nm": "core",
    "ty": 4,
    "ip": 0, "op": FRAMES, "sr": 1, "st": 0, "ind": 10,
    "shapes": [{
        "ty": "gr", "nm": "g",
        "it": [
            {
                "ty": "el", "nm": "el",
                "p": {"a": 0, "k": [0, 0]},
                "s": {"a": 0, "k": [10, 10]},
            },
            FILL_WHITE, tr(),
        ],
    }],
    "ks": {
        "p": {"a": 0, "k": [CX, CY]},
        "a": {"a": 0, "k": [0, 0, 0]},
        "s": {
            "a": 1,
            "k": [
                kf(0,  [0,   0],   [100, 100], two_d=True),
                kf(8,  [100, 100], [110, 110], two_d=True),
                kf(22, [110, 110], [100, 100], two_d=True),
                kf(36, [100, 100], [0,   0],   two_d=True),
                kf(50, [0,   0]),
            ],
        },
        "r": {"a": 0, "k": 0},
        "o": {"a": 0, "k": 100},
    },
}

# ── sparkle cross arms ───────────────────────────────────────────────────────
# A thin elongated diamond (4-point star made from two overlapping ellipses
# rotated 90°) that also scales in and out with the core.

def cross_arm(rot_deg, ind):
    """One arm of the central + cross: a thin horizontal bar, rotated."""
    return {
        "nm": f"arm{ind}",
        "ty": 4,
        "ip": 0, "op": FRAMES, "sr": 1, "st": 0, "ind": ind,
        "shapes": [{
            "ty": "gr", "nm": "g",
            "it": [
                {
                    "ty": "el", "nm": "el",
                    "p": {"a": 0, "k": [0, 0]},
                    "s": {"a": 0, "k": [28, 4]},  # wide flat ellipse = arm
                },
                FILL_WHITE, tr(),
            ],
        }],
        "ks": {
            "p": {"a": 0, "k": [CX, CY]},
            "a": {"a": 0, "k": [0, 0, 0]},
            "s": {
                "a": 1,
                "k": [
                    kf(0,  [0,   0],   [100, 100], two_d=True),
                    kf(8,  [100, 100], [100, 100], two_d=True),
                    kf(36, [100, 100], [0,   0],   two_d=True),
                    kf(50, [0,   0]),
                ],
            },
            "r": {"a": 0, "k": rot_deg},
            "o": {"a": 0, "k": 80},
        },
    }

h_arm = cross_arm(0,  9)   # horizontal arm
v_arm = cross_arm(90, 8)   # vertical arm

# ── spark particles ──────────────────────────────────────────────────────────
# 4 small circles at 45° diagonals that travel outward then vanish.

TRAVEL  = 24   # px from centre
PSIZE   = 6    # particle diameter (px)
OFFSETS = [0, 10, 20, 30]  # stagger starts (frames)
ANGLES  = [45, 135, 225, 315]  # NE SE SW NW (degrees)


def spark_layer(angle_deg, start, ind):
    rad = math.radians(angle_deg)
    ex  = CX + TRAVEL * math.cos(rad)
    ey  = CY + TRAVEL * math.sin(rad)

    t0, t1, t2 = start, start + 14, start + 26
    # Wrap frames so nothing exceeds FRAMES
    t0 = t0 % FRAMES
    t1 = t1 % FRAMES
    t2 = min(t2, FRAMES - 1)

    return {
        "nm": f"spark{ind}",
        "ty": 4,
        "ip": 0, "op": FRAMES, "sr": 1, "st": 0, "ind": ind,
        "shapes": [{
            "ty": "gr", "nm": "g",
            "it": [
                {
                    "ty": "el", "nm": "el",
                    "p": {"a": 0, "k": [0, 0]},
                    "s": {"a": 0, "k": [PSIZE, PSIZE]},
                },
                FILL_WHITE, tr(),
            ],
        }],
        "ks": {
            "p": {
                "a": 1,
                "k": [
                    kf(t0, [CX, CY], [ex, ey], two_d=True),
                    kf(t2, [ex, ey]),
                ],
            },
            "a": {"a": 0, "k": [0, 0, 0]},
            "s": {
                "a": 1,
                "k": [
                    kf(t0, [0,   0],   [110, 110], two_d=True),
                    kf(t1, [110, 110], [0,   0],   two_d=True),
                    kf(t2, [0,   0]),
                ],
            },
            "r": {"a": 0, "k": 0},
            "o": {"a": 0, "k": 100},
        },
    }


spark_layers = [
    spark_layer(angle, start, idx + 1)
    for idx, (angle, start) in enumerate(zip(ANGLES, OFFSETS))
]

# ── assemble ─────────────────────────────────────────────────────────────────

improve_spark = {
    "v": "5.7.4",
    "nm": "improve-spark",
    "fr": FPS,
    "ip": 0,
    "op": FRAMES,
    "w": W,
    "h": H,
    "assets": [],
    "layers": [core_layer, h_arm, v_arm] + spark_layers,
}

out = ANIM / "improve-spark.json"
out.write_text(json.dumps(improve_spark, separators=(",", ":")), encoding="utf-8")
print(f"Wrote {out}  ({out.stat().st_size:,} bytes)")

print("\nassets/anim/ contents:")
for f in sorted(ANIM.iterdir()):
    print(f"  {f.name}  ({f.stat().st_size:,} bytes)")
