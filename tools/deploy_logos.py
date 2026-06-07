#!/usr/bin/env python3
"""
Deploy the new B&W gear+containers logo to all asset locations.

Reads  assets/logos/logo.svg  (master, 512×512, white background)
Writes:
  assets/logo.svg          — transparent bg, black shapes  (light mode / favicon)
  assets/logo-dark.svg     — transparent bg, white shapes  (dark mode sidebar)
  assets/favicon.svg       — identical to logo.svg (SVG favicons scale automatically)
"""
import pathlib, re

ROOT    = pathlib.Path(__file__).resolve().parent.parent
MASTER  = ROOT / "assets" / "logos" / "logo.svg"
ASSETS  = ROOT / "assets"

src = MASTER.read_text(encoding="utf-8")

# 1. Remove the white background rectangle
no_bg = re.sub(
    r'\s*<rect[^>]*fill=["\']white["\'][^/]*/>\s*',
    "\n",
    src,
)
no_bg = no_bg.replace("\n\n\n", "\n\n")

# 2. Light version — black shapes on transparent (straight from master, no bg)
light = no_bg

# 3. Dark version — built from scratch using SVG <mask> so the hub cutout is
#    truly transparent (works on any dark background, not tied to a hex colour).
#
#    Structure:
#      <defs><mask id="hub"> full white rect + black hub circle </mask></defs>
#      Gear path — white fill, masked → shows as ring, hub is transparent
#      Container rects — white fill (visible on any dark bg through the hub hole)
#      Rib lines — #111111 (dark separator on white containers)

# Extract gear path d="..." from the light SVG
gear_match = re.search(r'<path d="([^"]+)"', no_bg)
gear_d = gear_match.group(1) if gear_match else ""

# Extract container rects and lines
containers_raw = re.findall(
    r'<(?:rect|line)[^/]*/>', no_bg
)

# Recolour containers for dark: rects white, rib strokes dark
def dark_elem(elem):
    elem = elem.replace('fill="#111111"', 'fill="white"')
    elem = elem.replace('stroke="white"',  'stroke="#111111"')
    return elem

containers_dark = "\n  ".join(dark_elem(e) for e in containers_raw)

dark = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <!-- Mask cuts the hub hole out of the gear so it is truly transparent -->
    <mask id="hub">
      <rect width="512" height="512" fill="white"/>
      <circle cx="256" cy="256" r="128" fill="black"/>
    </mask>
  </defs>
  <!-- Gear ring — white, hub punched out transparently -->
  <path d="{gear_d}" fill="white" mask="url(#hub)"/>
  <!-- Container stack inside the hub -->
  {containers_dark}
</svg>
"""

# 4. Write files
(ASSETS / "logo.svg").write_text(light, encoding="utf-8")
(ASSETS / "logo-dark.svg").write_text(dark, encoding="utf-8")
(ASSETS / "favicon.svg").write_text(light, encoding="utf-8")

for name in ("logo.svg", "logo-dark.svg", "favicon.svg"):
    size = (ASSETS / name).stat().st_size
    print(f"  assets/{name}  ({size:,} bytes)")

print("\nDone — old coloured logo replaced with B&W gear+containers logo.")
