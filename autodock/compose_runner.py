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
    project: str = "autodock",
) -> RunResult:
    console = console or Console()
    console.print(f"[cyan]docker compose -p {project} up -d --build[/cyan]")
    up = docker_runner.run(
        settings, ["compose", "-p", project, "up", "-d", "--build"], cwd=repo_dir,
        timeout=settings.build_timeout_seconds, capture=True,
    )
    if up.exit_code != 0:
        logs = up.stdout + up.stderr
        return RunResult(ok=False, detail=f"compose up failed: {logs[-500:]}", container_logs_tail=logs[-2000:])

    host_port = _discover_app_port(settings, repo_dir, profile.exposed_port, project) if profile.exposed_port else None

    try:
        # If the profile declared an exposed port but we cannot find it on the host,
        # the compose file or app isn't actually publishing it. That's a failure, not
        # a "stack still up" success: the whole point of validation is to confirm the
        # app responds on its expected port.
        if profile.exposed_port and not host_port:
            logs = _compose_logs(settings, repo_dir, project)
            return RunResult(
                ok=False,
                detail=(f"profile declared port {profile.exposed_port} on service 'app' "
                        "but `docker compose port app` did not return a host mapping"),
                container_logs_tail=logs,
            )

        if host_port:
            url = f"http://127.0.0.1:{host_port}/"
            console.print(f"[cyan]app published on host port {host_port}[/cyan]")
            console.print(f"[cyan]Polling {url} for up to {startup_seconds}s[/cyan]")
            deadline = time.monotonic() + startup_seconds
            last_err = ""
            while time.monotonic() < deadline:
                try:
                    r = requests.get(url, timeout=2)
                    if 200 <= r.status_code < 400:
                        logs = _compose_logs(settings, repo_dir, project)
                        return RunResult(ok=True, detail=f"HTTP {r.status_code} from {url}",
                                         container_logs_tail=logs)
                    last_err = f"HTTP {r.status_code}"
                except requests.RequestException as exc:
                    last_err = str(exc)
                time.sleep(2)
            logs = _compose_logs(settings, repo_dir, project)
            return RunResult(ok=False, detail=f"app did not respond: {last_err}", container_logs_tail=logs)
        else:
            # No port expected (worker / cron / consumer style). Liveness only.
            time.sleep(15)
            ps = docker_runner.run(settings, ["compose", "-p", project, "ps", "-q"], cwd=repo_dir, timeout=10)
            if ps.stdout.strip():
                return RunResult(ok=True, detail="no port expected; compose stack still up after 15s",
                                 container_logs_tail=_compose_logs(settings, repo_dir, project))
            return RunResult(ok=False, detail="compose stack went down",
                             container_logs_tail=_compose_logs(settings, repo_dir, project))
    finally:
        docker_runner.run(settings, ["compose", "-p", project, "down", "-v"], cwd=repo_dir, timeout=60, capture=True)


def _discover_app_port(settings: Settings, repo_dir: str, container_port: int, project: str = "autodock") -> int | None:
    res = docker_runner.run(
        settings, ["compose", "-p", project, "port", "app", str(container_port)],
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


def _compose_logs(settings: Settings, repo_dir: str, project: str = "autodock", n: int = 80) -> str:
    res = docker_runner.run(
        settings, ["compose", "-p", project, "logs", "--tail", str(n)],
        cwd=repo_dir, timeout=15, capture=True,
    )
    return (res.stdout + res.stderr).strip()[-4000:]
