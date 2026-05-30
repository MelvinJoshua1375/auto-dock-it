from pathlib import Path

from autodock.cleanup import prune_old_runs


def _seed(root: Path, names: list[str]) -> None:
    for name in names:
        (root / name).mkdir(parents=True)
        (root / name / "Dockerfile").write_text("FROM scratch\n")


def test_keep_only_recent(tmp_path: Path):
    _seed(tmp_path, [
        "20260101-000000", "20260102-000000", "20260103-000000",
        "20260104-000000", "20260105-000000",
    ])
    removed = prune_old_runs(tmp_path, keep=2)
    assert {p.name for p in removed} == {
        "20260101-000000", "20260102-000000", "20260103-000000",
    }
    remaining = sorted(p.name for p in tmp_path.iterdir())
    assert remaining == ["20260104-000000", "20260105-000000"]


def test_keep_zero_removes_all(tmp_path: Path):
    _seed(tmp_path, ["20260101-000000"])
    removed = prune_old_runs(tmp_path, keep=0)
    assert len(removed) == 1


def test_ignores_non_run_dirs(tmp_path: Path):
    _seed(tmp_path, ["20260101-000000"])
    (tmp_path / "smoke").mkdir()
    (tmp_path / "notes.txt").write_text("hi")
    removed = prune_old_runs(tmp_path, keep=0)
    assert {p.name for p in removed} == {"20260101-000000"}
    assert (tmp_path / "smoke").exists()
    assert (tmp_path / "notes.txt").exists()


def test_missing_root_is_noop(tmp_path: Path):
    assert prune_old_runs(tmp_path / "missing", keep=5) == []
