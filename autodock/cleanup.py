"""Bound the size of output/ by keeping the most recent N runs."""
import re
import shutil
from pathlib import Path

RUN_ID_RE = re.compile(r"^\d{8}-\d{6}(?:-[0-9a-f]+)?$")


def prune_old_runs(output_root: Path, keep: int) -> list[Path]:
    """Delete all but the `keep` most recent run dirs under output_root.

    Returns the list of paths that were removed.
    """
    if not output_root.exists() or keep < 0:
        return []
    runs = [p for p in output_root.iterdir() if p.is_dir() and RUN_ID_RE.match(p.name)]
    runs.sort(key=lambda p: p.name, reverse=True)
    to_remove = runs[keep:]
    removed: list[Path] = []
    for p in to_remove:
        try:
            shutil.rmtree(p)
            removed.append(p)
        except OSError:
            pass
    return removed
