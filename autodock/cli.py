from pathlib import Path

import typer
from rich.console import Console

from . import docker_runner
from .config import load_settings
from .llm import LLM
from .pipeline import run_pipeline
from .pr import open_pr, PrError

app = typer.Typer(help="Auto-Dock It: agentic Dockerfile generator", add_completion=False)
console = Console()


@app.command()
def doctor() -> None:
    """Verify environment: Gemini key reachable, Docker reachable."""
    settings = load_settings()
    model = settings.groq_model_fast if settings.provider == "groq" else settings.gemini_model_fast
    console.print(f"[green]OK[/green] settings loaded (provider={settings.provider}, model={model})")

    try:
        llm = LLM(settings)
        reply = llm.complete_text("Reply with the single word: pong")
        console.print(f"[green]OK[/green] {settings.provider} reply: {reply!r}")
    except Exception as exc:
        console.print(f"[red]FAIL[/red] {settings.provider} call: {exc}")

    res = docker_runner.run(settings, ["version", "--format", "{{.Server.Version}}"], timeout=10)
    if res.exit_code == 0:
        console.print(f"[green]OK[/green] Docker server: {res.stdout.strip()}")
    else:
        console.print(f"[red]FAIL[/red] docker version: {res.stderr.strip() or res.stdout.strip()}")


@app.command()
def run(
    repo_url: str = typer.Argument(..., help="Public GitHub repo URL"),
    output_dir: Path = typer.Option(Path("output"), "--output-dir", "-o"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Stop after generating Dockerfile, do not build"),
) -> None:
    """Clone, analyze, generate a Dockerfile, build it with self-healing, and validate."""
    settings = load_settings()
    result = run_pipeline(repo_url, output_root=output_dir, settings=settings, dry_run=dry_run, console=console)
    console.print(f"\nFinal: ok={result.ok} stage={result.stage_reached}")
    console.print(f"Artifacts in: {result.output_dir}")
    if not result.ok:
        raise typer.Exit(code=1)


@app.command()
def pr(
    run_dir: Path = typer.Argument(..., help="Path to output/<run_id>/ from a successful run"),
    gh_bin: str = typer.Option("gh", "--gh-bin", help="gh CLI binary (eg 'flatpak-spawn --host gh' inside the VSCode sandbox)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would be committed without forking/pushing"),
) -> None:
    """Fork the upstream repo and open a PR with the generated Dockerfile."""
    try:
        url = open_pr(run_dir, gh_bin=gh_bin, console=console, dry_run=dry_run)
    except PrError as exc:
        console.print(f"[red]PR failed:[/red] {exc}")
        raise typer.Exit(code=1)
    console.print(f"\nDone: {url}")


if __name__ == "__main__":
    app()
