from pathlib import Path
from pathlib import Path as _Path
from urllib.parse import urlparse

import typer
from rich.console import Console

from . import docker_runner
from .config import load_settings
from .generate import generate_explanation, generate_improvements
from .llm import LLM
from .pipeline import run_pipeline
from .pr import PrError, open_pr


def _validate_repo_url(value: str) -> str:
    """Accept GitHub HTTPS URLs OR local paths (for testing)."""
    if value.startswith(("http://", "https://")):
        if not value.startswith("https://"):
            raise typer.BadParameter("Only HTTPS GitHub URLs are accepted.")
        p = urlparse(value)
        if p.hostname not in ("github.com", "www.github.com"):
            raise typer.BadParameter("Only github.com URLs are accepted.")
        parts = [s for s in p.path.split("/") if s]
        if len(parts) < 2:
            raise typer.BadParameter("URL must be https://github.com/<owner>/<repo>.")
        return value
    local = _Path(value).expanduser().resolve()
    if local.exists() and local.is_dir():
        return str(local)
    raise typer.BadParameter("Must be an https://github.com/<owner>/<repo> URL or an existing local git directory.")

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
    repo_url = _validate_repo_url(repo_url)
    settings = load_settings()
    result = run_pipeline(repo_url, output_root=output_dir, settings=settings, dry_run=dry_run, console=console)
    console.print(f"\nFinal: ok={result.ok} stage={result.stage_reached}")
    console.print(f"Artifacts in: {result.output_dir}")
    if not result.ok:
        raise typer.Exit(code=1)


@app.command()
def explain(
    dockerfile: Path = typer.Argument(..., help="Path to a Dockerfile"),
) -> None:
    """Annotate an existing Dockerfile line by line, explaining why each line is there."""
    if not dockerfile.exists():
        console.print(f"[red]not found:[/red] {dockerfile}")
        raise typer.Exit(code=1)
    settings = load_settings()
    llm = LLM(settings)
    text = generate_explanation(dockerfile.read_text(), llm)
    console.print(text)


@app.command()
def improve(
    dockerfile: Path = typer.Argument(..., help="Path to a Dockerfile"),
) -> None:
    """Review an existing Dockerfile and suggest concrete improvements."""
    if not dockerfile.exists():
        console.print(f"[red]not found:[/red] {dockerfile}")
        raise typer.Exit(code=1)
    settings = load_settings()
    llm = LLM(settings)
    text = generate_improvements(dockerfile.read_text(), llm)
    console.print(text)


@app.command(name="list")
def list_runs(
    output_dir: Path = typer.Option(Path("output"), "--output-dir", "-o"),
    limit: int = typer.Option(20, "--limit", "-n"),
) -> None:
    """Show recent pipeline runs and their outcomes."""
    import contextlib
    import json as _json
    import re as _re

    from rich.table import Table

    if not output_dir.exists():
        console.print(f"[yellow]No runs found in {output_dir}.[/yellow]")
        return
    run_re = _re.compile(r"^\d{8}-\d{6}(?:-[0-9a-f]+)?$")
    runs = sorted(
        (p for p in output_dir.iterdir() if p.is_dir() and run_re.match(p.name)),
        key=lambda p: p.name, reverse=True,
    )[:limit]
    if not runs:
        console.print(f"[yellow]No runs found in {output_dir}.[/yellow]")
        return

    table = Table(title=f"Recent runs ({len(runs)})", show_lines=False)
    table.add_column("Run ID", style="cyan")
    table.add_column("Repo")
    table.add_column("Attempts", justify="right")
    table.add_column("Stage")
    table.add_column("Result")

    for run in runs:
        meta = {}
        meta_path = run / "metadata.json"
        if meta_path.exists():
            with contextlib.suppress(_json.JSONDecodeError):
                meta = _json.loads(meta_path.read_text())
        repo = meta.get("repo_url", "?")
        attempts = len(list((run / "attempts").glob("*-Dockerfile"))) if (run / "attempts").exists() else 0
        validation_path = run / "validation.txt"
        if validation_path.exists():
            text = validation_path.read_text()
            ok = "ok=True" in text
            result = "[green]ok[/green]" if ok else "[red]fail[/red]"
            stage = "validate"
        elif (run / "Dockerfile").exists():
            result = "[yellow]dry/built[/yellow]"
            stage = "generate" if attempts == 0 else "build"
        else:
            result = "[dim]incomplete[/dim]"
            stage = "ingest/analyze"
        table.add_row(run.name, repo, str(attempts), stage, result)

    console.print(table)


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
        raise typer.Exit(code=1) from exc
    console.print(f"\nDone: {url}")


if __name__ == "__main__":
    app()
