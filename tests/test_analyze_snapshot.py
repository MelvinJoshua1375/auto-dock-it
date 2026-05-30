from pathlib import Path

import pytest

from autodock.analyze import build_snapshot


@pytest.fixture
def flask_repo(tmp_path: Path) -> Path:
    (tmp_path / "app.py").write_text("from flask import Flask\napp = Flask(__name__)\n")
    (tmp_path / "requirements.txt").write_text("flask==3.0.0\ngunicorn==23.0.0\n")
    (tmp_path / "README.md").write_text("# tiny flask\n\nA toy.\n")
    (tmp_path / "Procfile").write_text("web: gunicorn app:app\n")
    return tmp_path


def test_snapshot_contains_top_level_entries(flask_repo):
    snap = build_snapshot(flask_repo)
    assert "app.py" in snap
    assert "requirements.txt" in snap
    assert "Procfile" in snap


def test_snapshot_includes_manifest_contents(flask_repo):
    snap = build_snapshot(flask_repo)
    assert "flask==3.0.0" in snap
    assert "gunicorn==23.0.0" in snap


def test_snapshot_includes_readme_excerpt(flask_repo):
    snap = build_snapshot(flask_repo)
    assert "tiny flask" in snap.lower()


def test_snapshot_handles_no_readme(tmp_path: Path):
    (tmp_path / "main.go").write_text("package main\n")
    snap = build_snapshot(tmp_path)
    assert "no README" in snap


def test_snapshot_skips_git_dir(tmp_path: Path):
    (tmp_path / "app.py").write_text("x = 1\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]\n")
    snap = build_snapshot(tmp_path)
    assert ".git" not in snap or "config" not in snap.split(".git", 1)[-1][:200]
