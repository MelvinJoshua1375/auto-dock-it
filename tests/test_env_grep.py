from pathlib import Path

from autodock.analyze import detect_env_vars


def test_python_os_environ_get(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        'import os\n'
        'db = os.environ.get("DATABASE_URL")\n'
        'k = os.environ["SECRET_KEY"]\n'
        'h = os.getenv("REDIS_HOST", "redis")\n'
    )
    assert detect_env_vars(tmp_path) == ["DATABASE_URL", "REDIS_HOST", "SECRET_KEY"]


def test_node_process_env(tmp_path: Path):
    (tmp_path / "server.js").write_text(
        'const port = process.env.PORT;\n'
        'const url = process.env["DATABASE_URL"];\n'
    )
    assert detect_env_vars(tmp_path) == ["DATABASE_URL", "PORT"]


def test_go_getenv(tmp_path: Path):
    (tmp_path / "main.go").write_text('addr := os.Getenv("HTTP_ADDR")\n')
    assert detect_env_vars(tmp_path) == ["HTTP_ADDR"]


def test_skips_node_modules_and_venv(tmp_path: Path):
    (tmp_path / "node_modules" / "lib").mkdir(parents=True)
    (tmp_path / "node_modules" / "lib" / "x.js").write_text('process.env.NOISE\n')
    (tmp_path / ".venv" / "site-packages").mkdir(parents=True)
    (tmp_path / ".venv" / "site-packages" / "x.py").write_text('os.environ.get("NOISE")\n')
    (tmp_path / "app.py").write_text('os.environ.get("WANTED")\n')
    assert detect_env_vars(tmp_path) == ["WANTED"]


def test_no_source_returns_empty(tmp_path: Path):
    (tmp_path / "README.md").write_text("# nothing")
    assert detect_env_vars(tmp_path) == []
