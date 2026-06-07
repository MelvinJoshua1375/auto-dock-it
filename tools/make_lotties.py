"""Generate the 2 new Lottie animation JSON files for Auto-Dock It."""
import json
import pathlib

ANIM = pathlib.Path(__file__).resolve().parent.parent / "assets" / "anim"
ANIM.mkdir(parents=True, exist_ok=True)


# ── NEW LOTTIE 1: pipeline-loader.json ── 3 staggered pulsing dots ──────────
def dot_layer(nm: str, ind: int, px: int, t_start: int) -> dict:
    kfs = []
    if t_start > 0:
        kfs.append({"t": 0, "s": [100, 100]})
    kfs += [
        {
            "t": t_start,
            "s": [100, 100],
            "e": [155, 155],
            "i": {"x": [0.5, 0.5], "y": [1, 1]},
            "o": {"x": [0.42, 0.42], "y": [0, 0]},
        },
        {
            "t": t_start + 12,
            "s": [155, 155],
            "e": [100, 100],
            "i": {"x": [0.5, 0.5], "y": [1, 1]},
            "o": {"x": [0.58, 0.58], "y": [1, 1]},
        },
        {"t": t_start + 24, "s": [100, 100]},
    ]
    return {
        "nm": nm,
        "ty": 4,
        "ip": 0,
        "op": 60,
        "sr": 1,
        "st": 0,
        "ind": ind,
        "shapes": [
            {
                "ty": "gr",
                "nm": "g",
                "it": [
                    {
                        "ty": "el",
                        "nm": "el",
                        "p": {"a": 0, "k": [0, 0]},
                        "s": {"a": 0, "k": [12, 12]},
                    },
                    {
                        "ty": "fl",
                        "nm": "fl",
                        "c": {"a": 0, "k": [0.92, 0.92, 0.92, 1]},
                        "o": {"a": 0, "k": 100},
                        "r": 1,
                    },
                    {
                        "ty": "tr",
                        "p": {"a": 0, "k": [0, 0]},
                        "a": {"a": 0, "k": [0, 0]},
                        "s": {"a": 0, "k": [100, 100]},
                        "r": {"a": 0, "k": 0},
                        "o": {"a": 0, "k": 100},
                        "sk": {"a": 0, "k": 0},
                        "sa": {"a": 0, "k": 0},
                    },
                ],
            }
        ],
        "ks": {
            "p": {"a": 0, "k": [px, 20]},
            "a": {"a": 0, "k": [0, 0, 0]},
            "s": {"a": 1, "k": kfs},
            "r": {"a": 0, "k": 0},
            "o": {"a": 0, "k": 100},
        },
    }


loader = {
    "v": "5.7.4",
    "nm": "pipeline-loader",
    "fr": 30,
    "ip": 0,
    "op": 60,
    "w": 80,
    "h": 40,
    "assets": [],
    "layers": [
        dot_layer("dot1", 1, 15, 0),
        dot_layer("dot2", 2, 40, 12),
        dot_layer("dot3", 3, 65, 24),
    ],
}
out = ANIM / "pipeline-loader.json"
out.write_text(json.dumps(loader, separators=(",", ":")), encoding="utf-8")
print(f"Wrote pipeline-loader.json ({out.stat().st_size} bytes)")


# ── NEW LOTTIE 2: check-done.json ── circle draws, then checkmark draws ──────
def stroke(color=(0.92, 0.92, 0.92, 1), width=5):
    return {
        "ty": "st",
        "nm": "stroke",
        "lc": 2,
        "lj": 2,
        "ml": 4,
        "c": {"a": 0, "k": list(color)},
        "o": {"a": 0, "k": 100},
        "w": {"a": 0, "k": width},
    }


def group_tr():
    return {
        "ty": "tr",
        "p": {"a": 0, "k": [0, 0]},
        "a": {"a": 0, "k": [0, 0]},
        "s": {"a": 0, "k": [100, 100]},
        "r": {"a": 0, "k": 0},
        "o": {"a": 0, "k": 100},
        "sk": {"a": 0, "k": 0},
        "sa": {"a": 0, "k": 0},
    }


check = {
    "v": "5.7.4",
    "nm": "check-done",
    "fr": 30,
    "ip": 0,
    "op": 90,
    "w": 100,
    "h": 100,
    "assets": [],
    "layers": [
        {
            "nm": "check",
            "ty": 4,
            "ip": 0,
            "op": 90,
            "sr": 1,
            "st": 0,
            "ind": 1,
            "shapes": [
                # Circle group with trim path
                {
                    "ty": "gr",
                    "nm": "circle-gr",
                    "it": [
                        {
                            "ty": "el",
                            "nm": "circle",
                            "p": {"a": 0, "k": [0, 0]},
                            "s": {"a": 0, "k": [70, 70]},
                        },
                        stroke(),
                        {
                            "ty": "tm",
                            "nm": "trim",
                            "s": {"a": 0, "k": 0},
                            "e": {
                                "a": 1,
                                "k": [
                                    {
                                        "t": 5,
                                        "s": [0],
                                        "e": [100],
                                        "i": {"x": [0.5], "y": [1]},
                                        "o": {"x": [0.5], "y": [0]},
                                    },
                                    {"t": 38, "s": [100]},
                                ],
                            },
                            "o": {"a": 0, "k": -90},
                            "m": 1,
                        },
                        group_tr(),
                    ],
                },
                # Checkmark path group with trim path
                {
                    "ty": "gr",
                    "nm": "check-gr",
                    "it": [
                        {
                            "ty": "sh",
                            "nm": "check-path",
                            "ks": {
                                "a": 0,
                                "k": {
                                    "c": False,
                                    "v": [[-18, 5], [-3, 19], [22, -16]],
                                    "i": [[0, 0], [0, 0], [0, 0]],
                                    "o": [[0, 0], [0, 0], [0, 0]],
                                },
                            },
                        },
                        stroke(),
                        {
                            "ty": "tm",
                            "nm": "trim",
                            "s": {"a": 0, "k": 0},
                            "e": {
                                "a": 1,
                                "k": [
                                    {
                                        "t": 40,
                                        "s": [0],
                                        "e": [100],
                                        "i": {"x": [0.5], "y": [1]},
                                        "o": {"x": [0.5], "y": [0]},
                                    },
                                    {"t": 68, "s": [100]},
                                ],
                            },
                            "o": {"a": 0, "k": 0},
                            "m": 1,
                        },
                        group_tr(),
                    ],
                },
            ],
            "ks": {
                "p": {"a": 0, "k": [50, 50]},
                "a": {"a": 0, "k": [0, 0, 0]},
                "s": {"a": 0, "k": [100, 100]},
                "r": {"a": 0, "k": 0},
                "o": {"a": 0, "k": 100},
            },
        }
    ],
}
out2 = ANIM / "check-done.json"
out2.write_text(json.dumps(check, separators=(",", ":")), encoding="utf-8")
print(f"Wrote check-done.json ({out2.stat().st_size} bytes)")

# List all anim files
print("\nassets/anim/ contents:")
for f in sorted(ANIM.iterdir()):
    print(f"  {f.name}  ({f.stat().st_size:,} bytes)")
