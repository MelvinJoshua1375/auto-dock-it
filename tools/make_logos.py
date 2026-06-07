#!/usr/bin/env python3
"""
Auto-Dock It — single perfect B&W logo.

Concept: precision 8-tooth gear (automation / settings) with a clean
3-layer container stack inside (Docker containerisation).
Purely geometric.  No whale.

Outputs → assets/logos/
  logo.svg           black on white  (light-mode / print)
  logo-dark.svg      white on black  (dark-mode)
"""
import math
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "assets" / "logos"
OUT.mkdir(parents=True, exist_ok=True)

S  = 512
CX = CY = S // 2   # 256, 256


# ── helpers ────────────────────────────────────────────────────────────────────

def P(cx, cy, r, deg):
    """Polar → Cartesian.  0 ° = 12-o'clock."""
    a = math.radians(deg - 90)
    return cx + r * math.cos(a), cy + r * math.sin(a)

def xy(p):
    return f"{p[0]:.3f},{p[1]:.3f}"


# ── gear path ──────────────────────────────────────────────────────────────────

def gear_path(cx, cy, r_root, r_tip, n=8, tooth_frac=0.42, bevel=5.0):
    """
    Returns a closed SVG path string for a gear silhouette.
    tooth_frac : fraction of each sector the tooth-flat spans  (0–1)
    bevel      : chamfer in degrees on tooth shoulders
    """
    step = 360.0 / n
    ht   = step * tooth_frac / 2.0
    seg  = []
    for i in range(n):
        ca  = i * step
        v   = P(cx, cy, r_root, ca - step / 2 + bevel)   # valley floor
        rs  = P(cx, cy, r_root, ca - ht)                  # shoulder start
        ts  = P(cx, cy, r_tip,  ca - ht + bevel)          # tooth tip start
        te  = P(cx, cy, r_tip,  ca + ht - bevel)          # tooth tip end
        re  = P(cx, cy, r_root, ca + ht)                  # shoulder end
        pfx = "M" if i == 0 else "L"
        seg += [f"{pfx} {xy(v)}", f"L {xy(rs)}", f"L {xy(ts)}",
                f"L {xy(te)}", f"L {xy(re)}"]
    return " ".join(seg) + " Z"


# ── dimensions ────────────────────────────────────────────────────────────────

R_ROOT  = 165    # gear valley circle radius
R_TIP   = 210    # gear tooth-tip radius
R_HUB   = 128    # white hub cut-out radius   (gear ring = 165-128 = 37 px thick)
N       = 8      # number of teeth
TF      = 0.42   # tooth fraction
BV      = 5.0    # bevel degrees

# Container stack (lives inside the R_HUB white circle)
N_C   = 3        # number of containers
C_W   = 152      # container width   (px)
C_H   = 32       # container height  (px)
C_GAP = 10       # vertical gap between containers
C_RX  = 5        # corner radius

# Vertical centering of the stack
STACK_TOTAL = N_C * C_H + (N_C - 1) * C_GAP   # 116 px
STACK_TOP   = CY - STACK_TOTAL // 2            # 198

# Horizontal centering
C_X = CX - C_W // 2                            # 180


# ── build elements ────────────────────────────────────────────────────────────

gp = gear_path(CX, CY, R_ROOT, R_TIP, n=N, tooth_frac=TF, bevel=BV)

def container_row(index):
    y = STACK_TOP + index * (C_H + C_GAP)
    # main rectangle
    rect = (
        f'<rect x="{C_X}" y="{y}" width="{C_W}" height="{C_H}"'
        f' rx="{C_RX}" fill="#111111"/>'
    )
    # two thin horizontal ribs (white lines) — give each box a
    # "container panel" look; invisible at favicon scale, nice at large size
    mid_y  = y + C_H // 2
    rib_x1 = C_X + 18
    rib_x2 = C_X + C_W - 18
    rib = (
        f'<line x1="{rib_x1}" y1="{mid_y}" x2="{rib_x2}" y2="{mid_y}"'
        f' stroke="white" stroke-width="2" opacity="0.55"/>'
    )
    return rect + "\n  " + rib

containers = "\n  ".join(container_row(i) for i in range(N_C))

# ── assemble SVG ──────────────────────────────────────────────────────────────

body = f"""
  <!-- white canvas -->
  <rect width="{S}" height="{S}" fill="white"/>

  <!-- gear (automation symbol) -->
  <path d="{gp}" fill="#111111"/>

  <!-- hub cut-out — reveals the interior -->
  <circle cx="{CX}" cy="{CY}" r="{R_HUB}" fill="white"/>

  <!-- 3-layer container stack (Docker containerisation) -->
  {containers}
"""

svg_light = (
    f'<svg xmlns="http://www.w3.org/2000/svg"'
    f' viewBox="0 0 {S} {S}" width="{S}" height="{S}">\n'
    + body + "\n</svg>\n"
)


def make_dark(s):
    """Swap #111111 ↔ white to produce white-on-black variant."""
    return (
        s.replace('fill="white"',    'fill="__SWAP__"')
         .replace('fill="#111111"',  'fill="white"')
         .replace('fill="__SWAP__"', 'fill="#111111"')
         .replace('stroke="white"',  'stroke="#111111"')
    )

svg_dark = make_dark(svg_light)

(OUT / "logo.svg").write_text(svg_light, encoding="utf-8")
(OUT / "logo-dark.svg").write_text(svg_dark, encoding="utf-8")

print(f"Wrote  logo.svg       ({(OUT / 'logo.svg').stat().st_size:,} bytes)")
print(f"Wrote  logo-dark.svg  ({(OUT / 'logo-dark.svg').stat().st_size:,} bytes)")
print(f"Path:  {OUT}")
