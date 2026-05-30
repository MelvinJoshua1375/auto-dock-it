import re
from collections import Counter
from pathlib import Path

from .llm import LLM
from .models import RepoProfile


def _safe_inside(repo_dir: Path, p: Path) -> bool:
    """True iff p is a regular file (not a symlink) and resolves under repo_dir.

    Defends analyze against a malicious repo that supplies a symlink named like
    a manifest (eg `requirements.txt`) pointing at a sensitive host file such as
    `~/.ssh/id_rsa`. Without this guard, the symlink target would be read into
    the LLM prompt and exfiltrated to the model provider.
    """
    try:
        if p.is_symlink():
            return False
        resolved = p.resolve(strict=True)
        repo_resolved = repo_dir.resolve(strict=True)
    except OSError:
        return False
    return resolved == repo_resolved or repo_resolved in resolved.parents


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
SOURCE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rb", ".php", ".rs", ".ex", ".exs"}
MAX_SOURCE_FILES_SCANNED = 60
MAX_ENV_VARS_REPORTED = 25
PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "prompts" / "analyze.md"

ENV_PATTERNS = [
    re.compile(r"""os\.environ\.get\(\s*['"]([A-Z_][A-Z0-9_]*)['"]"""),
    re.compile(r"""os\.environ\[\s*['"]([A-Z_][A-Z0-9_]*)['"]\s*\]"""),
    re.compile(r"""os\.getenv\(\s*['"]([A-Z_][A-Z0-9_]*)['"]"""),
    re.compile(r"""process\.env\.([A-Z_][A-Z0-9_]*)"""),
    re.compile(r"""process\.env\[\s*['"]([A-Z_][A-Z0-9_]*)['"]\s*\]"""),
    re.compile(r"""System\.getenv\(\s*"([A-Z_][A-Z0-9_]*)"\s*\)"""),
    re.compile(r"""ENV\[\s*['"]([A-Z_][A-Z0-9_]*)['"]\s*\]"""),
    re.compile(r"""os\.Getenv\(\s*"([A-Z_][A-Z0-9_]*)"\s*\)"""),
    re.compile(r"""getenv\(\s*"([A-Z_][A-Z0-9_]*)"\s*\)"""),
]


def detect_env_vars(repo_dir: Path) -> list[str]:
    """Scan source files for env-var references; return unique names sorted."""
    found: set[str] = set()
    scanned = 0
    for p in repo_dir.rglob("*"):
        if scanned >= MAX_SOURCE_FILES_SCANNED:
            break
        if not p.is_file() or p.suffix not in SOURCE_EXTS:
            continue
        if ".git" in p.parts or "node_modules" in p.parts or ".venv" in p.parts:
            continue
        if not _safe_inside(repo_dir, p):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")[:50_000]
        except OSError:
            continue
        scanned += 1
        for pattern in ENV_PATTERNS:
            for m in pattern.finditer(text):
                found.add(m.group(1))
                if len(found) >= MAX_ENV_VARS_REPORTED:
                    return sorted(found)
    return sorted(found)


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

    lines.append("\n## Env vars referenced in source code")
    env_refs = detect_env_vars(repo_dir)
    if env_refs:
        for name in env_refs:
            lines.append(f"- {name}")
    else:
        lines.append("(none detected by static scan; rely on manifests/README)")

    lines.append("\n## Manifest files (verbatim, capped)")
    for p in sorted(repo_dir.rglob("*")):
        if ".git" in p.parts or not p.is_file():
            continue
        if p.name not in MANIFEST_FILES:
            continue
        if not _safe_inside(repo_dir, p):
            continue
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
        if candidate.is_file() and _safe_inside(repo_dir, candidate):
            return candidate
    return None


def _read_capped(path: Path, limit: int) -> str:
    try:
        data = path.read_bytes()[:limit]
        return data.decode("utf-8", errors="replace")
    except OSError as exc:
        return f"(could not read: {exc})"
