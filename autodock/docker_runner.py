"""Thin wrapper around the docker CLI.

DOCKER_BIN can be a single binary ("docker") or a multi-token prefix
("flatpak-spawn --host docker"), so we always split it and prepend to argv.
"""
import shlex
import subprocess
from dataclasses import dataclass

from .config import Settings


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


def docker_prefix(settings: Settings) -> list[str]:
    return shlex.split(settings.docker_bin)


def run(settings: Settings, args: list[str], *, cwd: str | None = None,
        timeout: int | None = None, capture: bool = True) -> CommandResult:
    cmd = docker_prefix(settings) + args
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return CommandResult(
            exit_code=127,
            stdout="",
            stderr=f"docker binary not found ({cmd[0]!r}): {exc}",
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout.decode(errors="replace") if exc.stdout else "")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr.decode(errors="replace") if exc.stderr else "")
        return CommandResult(
            exit_code=124,
            stdout=stdout,
            stderr=(stderr + f"\ntimeout after {timeout}s running: {' '.join(cmd)}").strip(),
        )
    except OSError as exc:
        return CommandResult(
            exit_code=1,
            stdout="",
            stderr=f"OS error running docker: {exc}",
        )
    return CommandResult(
        exit_code=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )
