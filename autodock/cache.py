"""Tiny on-disk cache for RepoProfile keyed by repo URL + commit SHA."""
import hashlib
import os
from pathlib import Path

from git import Repo

from .models import RepoProfile

CACHE_ROOT = Path(os.environ.get("AUTODOCK_CACHE_DIR", str(Path.home() / ".cache" / "autodock")))


def head_sha(repo_dir: Path) -> str | None:
    try:
        return Repo(repo_dir).head.commit.hexsha
    except Exception:
        return None


def _key(repo_url: str, sha: str) -> str:
    digest = hashlib.sha256(f"{repo_url}@{sha}".encode()).hexdigest()
    return digest[:16]


def _path(repo_url: str, sha: str) -> Path:
    return CACHE_ROOT / "profiles" / f"{_key(repo_url, sha)}.json"


def get(repo_url: str, sha: str) -> RepoProfile | None:
    p = _path(repo_url, sha)
    if not p.exists():
        return None
    try:
        return RepoProfile.model_validate_json(p.read_text())
    except Exception:
        return None


def put(repo_url: str, sha: str, profile: RepoProfile) -> None:
    p = _path(repo_url, sha)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(profile.model_dump_json(indent=2))
