from pathlib import Path
import shutil
import tempfile

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
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total / (1024 * 1024)
