#!/usr/bin/env python3
"""
Deploy the new B&W gear+containers logo to all asset locations.

Reads  assets/logos/logo.svg  (master, 512×512, white background)
Writes:
  assets/logo.svg       — transparent bg, black shapes  (light mode / favicon)
  assets/logo-dark.svg  — transparent bg, white shapes, evenodd hub hole (dark mode)
  assets/favicon.svg    — identical to logo.svg
"""
import pathlib, re

ROOT   = pathlib.Path(__file__).resolve().parent.parent
MASTER = ROOT / "assets" / "logos" / "logo.svg"
ASSETS = ROOT / "assets"

src = MASTER.read_text(encoding="utf-8")

# 1. Remove the white background rectangle
no_bg = re.sub(r'\s*<rect[^>]*fill=["\']white["\'][^/]*/>\s*', "\n", src)
no_bg = no_bg.replace("\n\n\n", "\n\n")

# 2. Light version — black shapes on transparent
light = no_bg

# 3. Dark version — white shapes, hub punched out via fill-rule="evenodd".
#    A hub-circle subpath is appended to the gear path; evenodd makes the
#    overlapping area transparent — no <mask>/<defs> that GitHub strips.
gear_match = re.search(r'<path d="([^"]+)"', no_bg)
gear_d = gear_match.group(1) if gear_match else ""

# Hub circle path: centre (256,256), radius 128
hub_path = "M 384,256 A 128,128 0 1 0 128,256 A 128,128 0 1 0 384,256 Z"

containers_raw = re.findall(r'<(?:rect|line)[^/]*/>', no_bg)

def dark_elem(elem):
    elem = elem.replace('fill="#111111"', 'fill="white"')
    elem = elem.replace('stroke="white"',  'stroke="#111111"')
    return elem

containers_dark = "\n  ".join(dark_elem(e) for e in containers_raw)

dark = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <!-- Gear ring: evenodd punches hub hole — no mask, works on GitHub -->
  <path fill-rule="evenodd" fill="white" d="{gear_d} {hub_path}"/>
  <!-- Container stack -->
  {containers_dark}
</svg>
"""

# 4. Write
(ASSETS / "logo.svg").write_text(light, encoding="utf-8")
(ASSETS / "logo-dark.svg").write_text(dark, encoding="utf-8")
(ASSETS / "favicon.svg").write_text(light, encoding="utf-8")

for name in ("logo.svg", "logo-dark.svg", "favicon.svg"):
    print(f"  assets/{name}  ({(ASSETS / name).stat().st_size:,} bytes)")

print("\nDone.")
