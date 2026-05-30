"""Verify analyze.py refuses to read symlinks and out-of-repo paths.

Regression for the path-traversal-via-symlink vulnerability where a malicious
repo could symlink a manifest name (eg `requirements.txt`) to a sensitive
host file like `~/.ssh/id_rsa`, causing analyze to read it and include the
contents in the prompt sent to the LLM provider.
"""
import contextlib
import os
from pathlib import Path

from autodock.analyze import _safe_inside, build_snapshot, detect_env_vars


def test_safe_inside_accepts_real_file(tmp_path: Path):
    f = tmp_path / "requirements.txt"
    f.write_text("flask\n")
    assert _safe_inside(tmp_path, f) is True


def test_safe_inside_rejects_symlink_to_outside(tmp_path: Path):
    secret = tmp_path.parent / "outside.txt"
    secret.write_text("SECRET=top\n")
    sym = tmp_path / "requirements.txt"
    sym.symlink_to(secret)
    assert _safe_inside(tmp_path, sym) is False
    with contextlib.suppress(OSError):
        secret.unlink()


def test_safe_inside_rejects_symlink_to_inside(tmp_path: Path):
    real = tmp_path / "real.txt"
    real.write_text("x\n")
    sym = tmp_path / "requirements.txt"
    sym.symlink_to(real)
    # Even a symlink that resolves inside the repo is rejected: the policy
    # treats all symlinks as untrusted to avoid TOCTOU swaps.
    assert _safe_inside(tmp_path, sym) is False


def test_safe_inside_rejects_dangling_symlink(tmp_path: Path):
    sym = tmp_path / "Pipfile"
    sym.symlink_to(tmp_path / "does-not-exist")
    assert _safe_inside(tmp_path, sym) is False


def test_build_snapshot_skips_symlinked_manifest(tmp_path: Path):
    secret = tmp_path.parent / "host_secret.txt"
    secret.write_text("SUPER_SECRET_VALUE_42\n")
    try:
        (tmp_path / "requirements.txt").symlink_to(secret)
        (tmp_path / "README.md").write_text("# normal readme\n")
        snap = build_snapshot(tmp_path)
        assert "SUPER_SECRET_VALUE_42" not in snap
    finally:
        with contextlib.suppress(OSError):
            secret.unlink()


def test_detect_env_vars_skips_symlinked_source(tmp_path: Path):
    secret = tmp_path.parent / "host_app.py"
    secret.write_text('os.environ.get("LEAKED_VAR")\n')
    try:
        (tmp_path / "app.py").symlink_to(secret)
        assert "LEAKED_VAR" not in detect_env_vars(tmp_path)
    finally:
        with contextlib.suppress(OSError):
            secret.unlink()


def test_build_snapshot_reads_real_manifest(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("flask==3.0.0\n")
    snap = build_snapshot(tmp_path)
    assert "flask==3.0.0" in snap


def test_find_first_skips_symlinked_readme(tmp_path: Path):
    secret = tmp_path.parent / "host_readme.md"
    secret.write_text("LEAKED_READ_ME\n")
    try:
        (tmp_path / "README.md").symlink_to(secret)
        snap = build_snapshot(tmp_path)
        assert "LEAKED_READ_ME" not in snap
        assert "(no README found)" in snap
    finally:
        with contextlib.suppress(OSError):
            secret.unlink()


def test_macro_owner_not_changed(tmp_path: Path):
    """Sanity: a normal repo with no symlinks behaves as before."""
    (tmp_path / "app.py").write_text('os.environ.get("REAL_VAR")\n')
    (tmp_path / "requirements.txt").write_text("flask\n")
    assert "REAL_VAR" in detect_env_vars(tmp_path)
    assert os.geteuid() != 0  # documents that tests do not run as root
