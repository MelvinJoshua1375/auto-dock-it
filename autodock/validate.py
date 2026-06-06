import socket
import time
from dataclasses import dataclass

import requests
from rich.console import Console

from . import docker_runner
from .config import Settings
from .models import RepoProfile, RunResult


@dataclass
class RunHandle:
    container_name: str
    host_port: int | None


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def validate_container(
    *,
    image_tag: str,
    profile: RepoProfile,
    settings: Settings,
    console: Console | None = None,
    startup_seconds: int = 30,
    run_id: str | None = None,
) -> RunResult:
    console = console or Console()
    suffix = run_id or f"{int(time.time())}"
    container_name = f"autodock-test-{suffix}"
    # Deliberately NOT using --rm. A fast-crashing container would be auto-removed
    # the instant it exits, so `docker logs` would return "No such container" and the
    # runtime-repair loop would repair blind. We keep the container around and let the
    # finally block force-remove it, so its crash logs are always available.
    args = ["run", "-d", "--name", container_name]
    host_port = None
    if profile.exposed_port:
        host_port = _free_port()
        args += ["-p", f"{host_port}:{profile.exposed_port}"]
    args.append(image_tag)

    run_res = docker_runner.run(settings, args, timeout=30, capture=True)
    if run_res.exit_code != 0:
        return RunResult(ok=False, detail=f"docker run failed: {run_res.stderr.strip()}")

    try:
        if host_port:
            url = f"http://127.0.0.1:{host_port}/"
            console.print(f"[cyan]Polling {url} for up to {startup_seconds}s[/cyan]")
            deadline = time.monotonic() + startup_seconds
            last_err = ""
            while time.monotonic() < deadline:
                try:
                    r = requests.get(url, timeout=2)
                    if 200 <= r.status_code < 400:
                        logs = _logs_tail(settings, container_name)
                        return RunResult(
                            ok=True,
                            detail=f"HTTP {r.status_code} from {url}",
                            container_logs_tail=logs,
                        )
                    last_err = f"HTTP {r.status_code}"
                except requests.RequestException as exc:
                    last_err = str(exc)
                # Fail fast if the container already exited: polling a dead port for the
                # full timeout wastes time, and we want the crash traceback while the
                # stopped container still exists so the LLM can actually diagnose it.
                if not _container_running(settings, container_name):
                    logs = _logs_tail(settings, container_name)
                    return RunResult(
                        ok=False,
                        detail=f"container exited during startup (last probe: {last_err or 'no response yet'})",
                        container_logs_tail=logs,
                    )
                time.sleep(1)
            logs = _logs_tail(settings, container_name)
            return RunResult(ok=False, detail=f"app did not respond: {last_err}", container_logs_tail=logs)
        else:
            time.sleep(15)
            if _container_running(settings, container_name):
                logs = _logs_tail(settings, container_name)
                return RunResult(ok=True, detail="container still running after 15s", container_logs_tail=logs)
            logs = _logs_tail(settings, container_name)
            return RunResult(ok=False, detail="container exited within 15s", container_logs_tail=logs)
    finally:
        docker_runner.run(settings, ["rm", "-f", container_name], timeout=10, capture=True)


def _container_running(settings: Settings, name: str) -> bool:
    res = docker_runner.run(settings, ["ps", "-q", "-f", f"name={name}"], timeout=10, capture=True)
    return bool(res.stdout.strip())


def _logs_tail(settings: Settings, name: str, n: int = 60) -> str:
    res = docker_runner.run(settings, ["logs", "--tail", str(n), name], timeout=10, capture=True)
    return (res.stdout + res.stderr).strip()
