import time
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from . import docker_runner
from .config import Settings
from .generate import generate_repair
from .llm import LLM
from .models import BuildAttempt, RepoProfile

ERROR_TAIL_LINES = 80


@dataclass
class BuildOutcome:
    success: bool
    image_tag: str | None
    attempts: list[BuildAttempt]
    final_dockerfile: str


def build_with_repair(
    *,
    repo_dir: Path,
    profile: RepoProfile,
    initial_dockerfile: str,
    image_tag: str,
    attempts_dir: Path,
    settings: Settings,
    llm: LLM,
    console: Console | None = None,
) -> BuildOutcome:
    console = console or Console()
    attempts_dir.mkdir(parents=True, exist_ok=True)
    dockerfile = initial_dockerfile
    attempts: list[BuildAttempt] = []

    for i in range(settings.max_build_retries + 1):
        (repo_dir / "Dockerfile").write_text(dockerfile)
        (attempts_dir / f"{i:02d}-Dockerfile").write_text(dockerfile)
        console.print(f"[cyan]Build attempt {i}[/cyan] tag={image_tag}")

        start = time.monotonic()
        result = docker_runner.run(
            settings,
            ["build", "-t", image_tag, "."],
            cwd=str(repo_dir),
            timeout=settings.build_timeout_seconds,
            capture=True,
        )
        duration = time.monotonic() - start

        combined = result.stdout + "\n" + result.stderr
        (attempts_dir / f"{i:02d}-output.log").write_text(combined)
        error_tail = _tail(combined, ERROR_TAIL_LINES)

        attempts.append(BuildAttempt(
            index=i, dockerfile=dockerfile, exit_code=result.exit_code,
            error_tail=error_tail, duration_seconds=duration,
        ))

        if result.exit_code == 0:
            console.print(f"[green]Build succeeded in {duration:.1f}s after {i + 1} attempt(s)[/green]")
            return BuildOutcome(True, image_tag, attempts, dockerfile)

        console.print(f"[red]Build failed (exit {result.exit_code}) in {duration:.1f}s[/red]")
        if i == settings.max_build_retries:
            break

        console.print("[yellow]Repairing Dockerfile...[/yellow]")
        try:
            dockerfile = generate_repair(profile, dockerfile, error_tail, llm, strong=False)
        except Exception as exc:
            console.print(f"[red]Repair LLM call failed: {exc}[/red]")
            break
        if not dockerfile.lstrip().upper().startswith("FROM"):
            console.print("[red]LLM repair response did not start with FROM; stopping.[/red]")
            break

    return BuildOutcome(False, None, attempts, dockerfile)


def _tail(text: str, n_lines: int) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-n_lines:])
