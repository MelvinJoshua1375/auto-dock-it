# Auto-Dock It / tools

Dev-only build scripts. None of these run as part of the pipeline or are shipped with the package; they exist to regenerate the visual assets committed under [`assets/`](../assets/) so the SVGs and Lottie files do not have to be hand-edited.

| Script | Produces | Notes |
|---|---|---|
| `make_logos.py` | `assets/logo.svg`, `assets/logo-dark.svg`, `assets/favicon.svg` | Builds the monochrome gear + container-stack mark from a small set of geometric primitives. Dark variant uses an SVG `<mask>` so the hub is truly transparent. |
| `deploy_logos.py` | Side-by-side copies under `assets/logos/` and overrides for the VS Code extension scaffold | Convenience wrapper; runs `make_logos.py` then copies into the legacy paths older docs still reference. |
| `make_lotties.py` | `assets/anim/*.json` (most of them) | Generates the monochrome Lottie animations used as headers and result decorations in the Streamlit UI. |
| `make_improve_lottie.py` | `assets/anim/improve-spark.json` | A separate generator for the "Improve" tab header animation; kept apart because it uses a different keyframe template than the rest of the set. |

## Running

```bash
python tools/make_logos.py
python tools/deploy_logos.py
python tools/make_lotties.py
python tools/make_improve_lottie.py
```

The scripts have no runtime dependencies beyond the Python standard library. They are idempotent: re-running them produces byte-identical output unless you change the source parameters at the top of each file.
