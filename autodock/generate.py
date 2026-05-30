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


# Compose-level dangers: things that grant a container access to the host or
# the Docker daemon itself. Scanned against every generated docker-compose.yml
# before `docker compose up` is invoked.
_DANGEROUS_HOST_MOUNTS = (
    "/var/run/docker.sock",
    "/proc",
    "/sys",
    "/etc",
    "/root",
    "/home",
    "/var/lib/docker",
)
_DANGEROUS_CAPS = {"sys_admin", "all", "net_admin", "sys_ptrace", "sys_module"}
_ALLOWED_NETWORK_MODES = {"bridge", "none", "default"}


class UnsafeComposeError(RuntimeError):
    def __init__(self, reason: str, service: str | None = None):
        msg = f"refused: docker-compose.yml unsafe: {reason}"
        if service:
            msg += f" (service: {service})"
        super().__init__(msg)
        self.reason = reason
        self.service = service


def assert_safe_compose(compose_yaml: str) -> None:
    """Raise if the LLM-generated compose file grants a service host or daemon access.

    Checks each service in `services:` for: privileged true, host bind mounts to
    sensitive paths (docker.sock, /proc, /sys, /etc, /root, /home, /var/lib/docker),
    cap_add of dangerous capabilities, network_mode: host, pid: host, ipc: host,
    userns_mode: host, security_opt with apparmor/selinux disable, and devices that
    expose /dev/* directly.
    """
    try:
        data = yaml.safe_load(compose_yaml)
    except yaml.YAMLError as exc:
        raise UnsafeComposeError(f"compose YAML did not parse: {exc}") from exc
    if not isinstance(data, dict):
        raise UnsafeComposeError("compose YAML did not produce a mapping")
    if "services" not in data:
        raise UnsafeComposeError("services block is missing")
    services = data["services"]
    if not isinstance(services, dict) or not services:
        raise UnsafeComposeError("services block is empty or not a mapping")

    def _is_truthy(v) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in {"true", "yes", "on", "1"}
        if isinstance(v, (int, float)):
            return bool(v)
        return False

    def _as_list(v):
        """Compose accepts list OR a single scalar for list-typed fields. Normalize."""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [v]

    for name, svc in services.items():
        if not isinstance(svc, dict):
            raise UnsafeComposeError("service definition is not a mapping", service=name)
        if _is_truthy(svc.get("privileged")):
            raise UnsafeComposeError(f"privileged: {svc['privileged']!r} is not allowed", service=name)
        if svc.get("network_mode") and str(svc["network_mode"]).lower() not in _ALLOWED_NETWORK_MODES:
            raise UnsafeComposeError(f"network_mode {svc['network_mode']!r} is not allowed", service=name)
        if str(svc.get("pid", "")).lower() == "host":
            raise UnsafeComposeError("pid: host is not allowed", service=name)
        if str(svc.get("ipc", "")).lower() == "host":
            raise UnsafeComposeError("ipc: host is not allowed", service=name)
        if str(svc.get("userns_mode", "")).lower() == "host":
            raise UnsafeComposeError("userns_mode: host is not allowed", service=name)
        for cap in _as_list(svc.get("cap_add")):
            low = str(cap).lower()
            if low.startswith("cap_"):
                low = low[4:]
            if low in _DANGEROUS_CAPS:
                raise UnsafeComposeError(f"cap_add {cap!r} is not allowed", service=name)
        for opt in _as_list(svc.get("security_opt")):
            low = str(opt).lower().replace(" ", "")
            if "apparmor:unconfined" in low or "seccomp:unconfined" in low or "label=disable" in low:
                raise UnsafeComposeError(f"security_opt {opt!r} is not allowed", service=name)
        for vol in _as_list(svc.get("volumes")):
            if isinstance(vol, dict):
                spec = vol.get("source") or ""
            else:
                spec = vol
            host_path = str(spec).split(":", 1)[0].strip()
            if not host_path or not host_path.startswith("/"):
                continue
            for bad in _DANGEROUS_HOST_MOUNTS:
                if host_path == bad or host_path.startswith(bad.rstrip("/") + "/"):
                    raise UnsafeComposeError(f"host bind mount {host_path!r} is not allowed", service=name)
        for dev in _as_list(svc.get("devices")):
            if isinstance(dev, dict):
                spec = dev.get("source") or ""
            else:
                spec = dev
            host_dev = str(spec).split(":", 1)[0].strip()
            if host_dev.startswith("/dev/"):
                raise UnsafeComposeError(f"device passthrough {host_dev!r} is not allowed", service=name)


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
    compose = _strip_fences(raw)
    assert_safe_compose(compose)
    return compose


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
