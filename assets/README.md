# Auto-Dock It / assets

Static art for the project. Theme-aware where relevant.

| File | Used by | Notes |
|---|---|---|
| `logo.svg` | Light-mode Streamlit sidebar, README header | Three equal horizontal lines on transparent background, stroke `#111111`. Minimalist mark representing stacked container layers. |
| `logo-dark.svg` | Dark-mode Streamlit sidebar | Same three-line mark with white strokes for the dark surface. |
| `logos/logo.svg`, `logos/logo-dark.svg` | Pinned legacy copies referenced by older docs | Kept identical to the root pair for back-compat. |
| `favicon.svg` | Streamlit page icon, browser tab | Same mark with slightly thicker strokes so the lines stay crisp at 16x16 and 32x32. |
| `anim/*.json` | Streamlit `streamlit-lottie` panels (`hero-ai`, `hero-containers`, `pipeline-loader`, `loader-scan`, `success-notify`, `check-done`, `explain-geo`, `improve-spark`) | Lottie JSON, monochrome-by-design; the `web.py` CSS applies a `grayscale(1) invert(0.88)` filter so any residual hue collapses to the black-and-white palette. |

## Regenerating

The logo SVGs and Lottie files are generated, not hand-edited. The generators live in [`tools/`](../tools/) - run them after a design tweak instead of editing the output by hand.
