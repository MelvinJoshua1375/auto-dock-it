from collections import Counter
from pathlib import Path

from .llm import LLM
from .models import RepoProfile


MANIFEST_FILES = {
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "requirements.txt", "requirements-dev.txt", "pyproject.toml", "Pipfile", "Pipfile.lock", "setup.py",
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
    "go.mod", "go.sum",
    "Cargo.toml", "Cargo.lock",
    "composer.json", "Gemfile", "Gemfile.lock", "mix.exs",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", ".env.sample", "Procfile",
    "gunicorn_config.py", "gunicorn.conf.py", "uvicorn.conf.py",
    "wsgi.py", "asgi.py", "manage.py",
    "next.config.js", "vite.config.js", "vite.config.ts",
    "server.js", "index.js", "main.go",
}

MAX_MANIFEST_BYTES = 8000
MAX_README_BYTES = 4096
MAX_TREE_ENTRIES = 200
PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "prompts" / "analyze.md"


def build_snapshot(repo_dir: Path) -> str:
    lines: list[str] = []
    lines.append("## Top-level entries")
    for entry in sorted(repo_dir.iterdir()):
        kind = "dir" if entry.is_dir() else "file"
        lines.append(f"- {entry.name} ({kind})")

    lines.append("\n## File extension counts")
    ext_counts: Counter[str] = Counter()
    for p in repo_dir.rglob("*"):
        if p.is_file() and ".git" not in p.parts:
            ext_counts[p.suffix or "(no-ext)"] += 1
    for ext, count in ext_counts.most_common(15):
        lines.append(f"- {ext}: {count}")

    lines.append("\n## Tree (first 200 paths)")
    paths: list[str] = []
    for p in repo_dir.rglob("*"):
        if ".git" in p.parts:
            continue
        rel = p.relative_to(repo_dir).as_posix()
        paths.append(rel + ("/" if p.is_dir() else ""))
        if len(paths) >= MAX_TREE_ENTRIES:
            break
    lines.extend(f"- {p}" for p in paths)

    lines.append("\n## README excerpt")
    readme = _find_first(repo_dir, ["README.md", "README.rst", "README.txt", "README"])
    if readme:
        lines.append(_read_capped(readme, MAX_README_BYTES))
    else:
        lines.append("(no README found)")

    lines.append("\n## Manifest files (verbatim, capped)")
    for p in sorted(repo_dir.rglob("*")):
        if ".git" in p.parts or not p.is_file():
            continue
        if p.name in MANIFEST_FILES:
            rel = p.relative_to(repo_dir).as_posix()
            lines.append(f"\n### {rel}")
            lines.append("```")
            lines.append(_read_capped(p, MAX_MANIFEST_BYTES))
            lines.append("```")

    return "\n".join(lines)


def analyze(repo_dir: Path, llm: LLM) -> RepoProfile:
    snapshot = build_snapshot(repo_dir)
    template = PROMPT_TEMPLATE_PATH.read_text()
    prompt = template.replace("{snapshot}", snapshot)
    return llm.complete_json(prompt, RepoProfile)


def _find_first(repo_dir: Path, names: list[str]) -> Path | None:
    for name in names:
        candidate = repo_dir / name
        if candidate.is_file():
            return candidate
    return None


def _read_capped(path: Path, limit: int) -> str:
    try:
        data = path.read_bytes()[:limit]
        return data.decode("utf-8", errors="replace")
    except OSError as exc:
        return f"(could not read: {exc})"
