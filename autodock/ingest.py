import contextlib
import shutil
import tempfile
from pathlib import Path

from git import Repo

MAX_REPO_SIZE_MB = 200


class IngestError(Exception):
    pass


def clone_repo(repo_url: str, target_parent: Path) -> Path:
    """Shallow-clone repo_url into a new subdir of target_parent. Returns the clone path."""
    target_parent.mkdir(parents=True, exist_ok=True)
    clone_dir = Path(tempfile.mkdtemp(prefix="repo-", dir=target_parent))
    try:
        Repo.clone_from(repo_url, clone_dir, depth=1)
    except Exception as exc:
        shutil.rmtree(clone_dir, ignore_errors=True)
        # GitPython surfaces auth/404 failures from `git clone` as a GitCommandError
        # with exit code 128 and a stderr line like:
        #   "fatal: could not read Username for 'https://github.com': No such device or address"
        #   "fatal: Authentication failed for 'https://github.com/...'"
        #   "fatal: repository 'https://github.com/owner/repo/' not found"
        # From the user's side these all mean: the repo is private, gated, or
        # does not exist. Translate to a one-line message so the Streamlit UI
        # does not dump a Git traceback.
        err = str(exc).lower()
        if (
            "could not read username" in err
            or "authentication failed" in err
            or ("repository" in err and "not found" in err)
        ):
            raise IngestError(
                f"{repo_url} is private, gated, or does not exist. "
                "Auto-Dock It only supports PUBLIC GitHub repositories. "
                "Try a public repo (for example one of the sample buttons above)."
            ) from exc
        raise IngestError(f"clone failed for {repo_url}: {exc}") from exc

    size_mb = _dir_size_mb(clone_dir)
    if size_mb > MAX_REPO_SIZE_MB:
        shutil.rmtree(clone_dir, ignore_errors=True)
        raise IngestError(f"repo too large: {size_mb:.0f} MB > {MAX_REPO_SIZE_MB} MB")
    return clone_dir


def _dir_size_mb(path: Path) -> float:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            with contextlib.suppress(OSError):
                total += p.stat().st_size
    return total / (1024 * 1024)
