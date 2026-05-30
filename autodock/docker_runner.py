"""Thin wrapper around the docker CLI.

DOCKER_BIN can be a single binary ("docker") or a multi-token prefix
("flatpak-spawn --host docker"), so we always split it and prepend to argv.
"""
from dataclasses import dataclass
import shlex
import subprocess

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
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=capture,
        text=True,
        timeout=timeout,
    )
    return CommandResult(
        exit_code=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
    )
