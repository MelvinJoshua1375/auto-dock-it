from pathlib import Path

from autodock import cache
from autodock.models import RepoProfile


def test_cache_miss_returns_none(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_ROOT", tmp_path)
    assert cache.get("https://github.com/x/y", "abc123") is None


def test_cache_round_trip(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_ROOT", tmp_path)
    p = RepoProfile(language="python", run_command="python app.py", exposed_port=8000)
    cache.put("https://github.com/x/y", "abc123", p)
    loaded = cache.get("https://github.com/x/y", "abc123")
    assert loaded is not None
    assert loaded.language == "python"
    assert loaded.exposed_port == 8000


def test_cache_key_differs_per_sha(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_ROOT", tmp_path)
    p1 = RepoProfile(language="python", run_command="a")
    p2 = RepoProfile(language="node", run_command="b")
    cache.put("https://github.com/x/y", "sha1", p1)
    cache.put("https://github.com/x/y", "sha2", p2)
    assert cache.get("https://github.com/x/y", "sha1").language == "python"
    assert cache.get("https://github.com/x/y", "sha2").language == "node"
