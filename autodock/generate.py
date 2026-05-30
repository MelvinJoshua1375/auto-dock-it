import re
from pathlib import Path

import yaml

from .llm import LLM
from .models import RepoProfile

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Patterns that almost certainly indicate prompt-injection or supply-chain abuse
# slipping through the LLM. These are scanned against every generated Dockerfile
# and a match raises UnsafeDockerfileError. Belt-and-suspenders on top of the
# safety preambles in prompts/dockerfile.md, prompts/repair.md, etc.
_DANGEROUS_PATTERNS = [
    re.compile(r"curl\s+[^|]*\|\s*(?:sh|bash|zsh|sh\s)", re.IGNORECASE),
    re.compile(r"wget\s+[^|]*\|\s*(?:sh|bash|zsh)", re.IGNORECASE),
    re.compile(r"\bnc\s+-e\b"),
    re.compile(r"/dev/tcp/", re.IGNORECASE),
    re.compile(r"\bENV\s+[A-Z_]*KEY\s*=\s*[^\s\$]"),
    re.compile(r"\bENV\s+[A-Z_]*TOKEN\s*=\s*[^\s\$]"),
    re.compile(r"\bENV\s+[A-Z_]*PASSWORD\s*=\s*[^\s\$]"),
    re.compile(r"--privileged\b", re.IGNORECASE),
]


class UnsafeDockerfileError(RuntimeError):
    def __init__(self, pattern: str, line: str):
        super().__init__(f"refused: Dockerfile contains a disallowed pattern: {pattern!r} in line {line!r}")
        self.pattern = pattern
        self.line = line


def assert_safe_dockerfile(dockerfile: str) -> None:
    """Raise if the LLM-generated Dockerfile contains a known-dangerous pattern."""
    for line in dockerfile.splitlines():
        if line.lstrip().startswith("#"):
            continue
        for pat in _DANGEROUS_PATTERNS:
            m = pat.search(line)
            if m:
                raise UnsafeDockerfileError(pattern=m.group(0), line=line.strip())


def generate_dockerfile(profile: RepoProfile, llm: LLM) -> str:
    template = (PROMPT_DIR / "dockerfile.md").read_text()
    prompt = template.replace("{profile}", profile.model_dump_json(indent=2))
    raw = llm.complete_text(prompt)
    dockerfile = _strip_fences(raw)
    assert_safe_dockerfile(dockerfile)
    return dockerfile


def generate_repair(profile: RepoProfile, dockerfile: str, error_tail: str, llm: LLM, *, strong: bool = False) -> str:
    template = (PROMPT_DIR / "repair.md").read_text()
    prompt = (
        template
        .replace("{profile}", profile.model_dump_json(indent=2))
        .replace("{dockerfile}", dockerfile)
        .replace("{error_tail}", error_tail)
    )
    raw = llm.complete_text(prompt, strong=strong)
    repaired = _strip_fences(raw)
    assert_safe_dockerfile(repaired)
    return repaired


def generate_runtime_repair(profile: RepoProfile, dockerfile: str, detail: str, logs: str, llm: LLM) -> str:
    template = (PROMPT_DIR / "runtime_repair.md").read_text()
    prompt = (
        template
        .replace("{profile}", profile.model_dump_json(indent=2))
        .replace("{dockerfile}", dockerfile)
        .replace("{detail}", detail)
        .replace("{logs}", logs[-4000:])
    )
    raw = llm.complete_text(prompt)
    repaired = _strip_fences(raw)
    assert_safe_dockerfile(repaired)
    return repaired


def generate_compose(profile: RepoProfile, dockerfile: str, llm: LLM) -> str:
    template = (PROMPT_DIR / "compose.md").read_text()
    prompt = (
        template
        .replace("{profile}", profile.model_dump_json(indent=2))
        .replace("{dockerfile}", dockerfile)
    )
    raw = llm.complete_text(prompt)
    return _strip_fences(raw)


def generate_explanation(dockerfile: str, llm: LLM) -> str:
    template = (PROMPT_DIR / "explain.md").read_text()
    prompt = template.replace("{dockerfile}", dockerfile)
    return llm.complete_text(prompt).strip()


def generate_improvements(dockerfile: str, llm: LLM) -> str:
    template = (PROMPT_DIR / "improve.md").read_text()
    prompt = template.replace("{dockerfile}", dockerfile)
    return llm.complete_text(prompt).strip()


def generate_autodock_config(profile: RepoProfile) -> str:
    cfg = {
        "version": 1,
        "language": profile.language,
        "framework": profile.framework,
        "build": {"command": profile.build_command},
        "run": {"command": profile.run_command},
        "ports": [profile.exposed_port] if profile.exposed_port else [],
        "env": profile.env_vars,
        "services": [s.model_dump(exclude_none=True) for s in profile.services],
        "notes": profile.notes,
    }
    return yaml.safe_dump(cfg, sort_keys=False, default_flow_style=False)


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        # drop the first fence line (possibly with language tag)
        lines = lines[1:]
        # drop trailing fence if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t
