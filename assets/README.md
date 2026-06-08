# Auto-Dock It / assets

Static art for the project. Theme-aware where relevant.

| File | Used by | Notes |
|---|---|---|
| `logo.svg` | Light-mode Streamlit sidebar, README header | Black gear ring + black container stack on transparent background. Pure geometry, no third-party imagery. |
| `logo-dark.svg` | Dark-mode Streamlit sidebar | White gear ring + white containers on transparent background. Uses an SVG `<mask>` to cut a true transparent hole in the hub so the sidebar background shows through. |
| `logos/logo.svg`, `logos/logo-dark.svg` | Pinned legacy copies referenced by older docs and the VS Code extension scaffold | Kept identical to the root pair for back-compat. |
| `favicon.svg` | Streamlit page icon, browser tab | Same gear mark, simplified for 16x16 / 32x32 rendering. |
| `anim/*.json` | Streamlit `streamlit-lottie` panels (`hero-ai`, `hero-containers`, `pipeline-loader`, `loader-scan`, `success-notify`, `check-done`, `explain-geo`, `improve-spark`) | Lottie JSON, monochrome-by-design; the `web.py` CSS applies a `grayscale(1) invert(0.88)` filter so any residual hue collapses to the black-and-white palette. |

## Regenerating

The logo SVGs and Lottie files are generated, not hand-edited. The generators live in [`tools/`](../tools/) - run them after a design tweak instead of editing the output by hand.
