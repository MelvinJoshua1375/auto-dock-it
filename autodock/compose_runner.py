"""Compose-aware validation: bring services up, poll the app, tear down."""
import socket
import time

import requests
from rich.console import Console

from . import docker_runner
from .config import Settings
from .models import RepoProfile, RunResult


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def validate_compose(
    *,
    repo_dir: str,
    profile: RepoProfile,
    settings: Settings,
    console: Console | None = None,
    startup_seconds: int = 60,
) -> RunResult:
    console = console or Console()
    project = "autodock"
    console.print(f"[cyan]docker compose -p {project} up -d --build[/cyan]")
    up = docker_runner.run(
        settings, ["compose", "-p", project, "up", "-d", "--build"], cwd=repo_dir,
        timeout=settings.build_timeout_seconds, capture=True,
    )
    if up.exit_code != 0:
        logs = up.stdout + up.stderr
        return RunResult(ok=False, detail=f"compose up failed: {logs[-500:]}", container_logs_tail=logs[-2000:])

    host_port = _discover_app_port(settings, repo_dir, profile.exposed_port) if profile.exposed_port else None

    try:
        if host_port:
            url = f"http://127.0.0.1:{host_port}/"
            console.print(f"[cyan]app published on host port {host_port}[/cyan]")
            console.print(f"[cyan]Polling {url} for up to {startup_seconds}s[/cyan]")
            deadline = time.monotonic() + startup_seconds
            last_err = ""
            while time.monotonic() < deadline:
                try:
                    r = requests.get(url, timeout=2)
                    if r.status_code < 500:
                        logs = _compose_logs(settings, repo_dir)
                        return RunResult(ok=True, detail=f"HTTP {r.status_code} from {url}",
                                         container_logs_tail=logs)
                    last_err = f"HTTP {r.status_code}"
                except requests.RequestException as exc:
                    last_err = str(exc)
                time.sleep(2)
            logs = _compose_logs(settings, repo_dir)
            return RunResult(ok=False, detail=f"app did not respond: {last_err}", container_logs_tail=logs)
        else:
            time.sleep(15)
            ps = docker_runner.run(settings, ["compose", "-p", "autodock", "ps", "-q"], cwd=repo_dir, timeout=10)
            if ps.stdout.strip():
                return RunResult(ok=True, detail="compose stack still up after 15s",
                                 container_logs_tail=_compose_logs(settings, repo_dir))
            return RunResult(ok=False, detail="compose stack went down",
                             container_logs_tail=_compose_logs(settings, repo_dir))
    finally:
        docker_runner.run(settings, ["compose", "-p", "autodock", "down", "-v"], cwd=repo_dir, timeout=60, capture=True)


def _discover_app_port(settings: Settings, repo_dir: str, container_port: int) -> int | None:
    res = docker_runner.run(
        settings, ["compose", "-p", "autodock", "port", "app", str(container_port)],
        cwd=repo_dir, timeout=10, capture=True,
    )
    if res.exit_code != 0:
        return None
    line = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else ""
    if ":" in line:
        try:
            return int(line.rsplit(":", 1)[1])
        except ValueError:
            return None
    return None


def _compose_logs(settings: Settings, repo_dir: str, n: int = 80) -> str:
    res = docker_runner.run(
        settings, ["compose", "-p", "autodock", "logs", "--tail", str(n)],
        cwd=repo_dir, timeout=15, capture=True,
    )
    return (res.stdout + res.stderr).strip()[-4000:]
