import json
import time
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from . import cache, docker_runner
from .analyze import analyze
from .build import build_with_repair
from .cleanup import prune_old_runs
from .compose_runner import validate_compose
from .config import Settings
from .generate import generate_autodock_config, generate_compose, generate_dockerfile, generate_runtime_repair
from .ingest import clone_repo
from .llm import LLM
from .validate import validate_container


@dataclass
class PipelineResult:
    ok: bool
    output_dir: Path
    image_tag: str | None
    stage_reached: str
    detail: str


def run_pipeline(
    repo_url: str,
    *,
    output_root: Path,
    settings: Settings,
    dry_run: bool = False,
    console: Console | None = None,
) -> PipelineResult:
    console = console or Console()
    output_root.mkdir(parents=True, exist_ok=True)
    pruned = prune_old_runs(output_root, keep=settings.keep_recent_runs)
    if pruned:
        console.print(f"[dim]Pruned {len(pruned)} old run(s) from {output_root}[/dim]")
    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "metadata.json").write_text(
        json.dumps({"run_id": run_id, "repo_url": repo_url})
    )
    llm = LLM(settings)

    console.print(Panel.fit(f"Auto-Dock It | run {run_id}\nrepo: {repo_url}", style="bold"))

    console.print("[bold]Stage 1: Ingest[/bold]")
    repo_dir = clone_repo(repo_url, run_dir / "clones")
    console.print(f"  cloned to {repo_dir}")

    console.print("[bold]Stage 2: Analyze[/bold]")
    sha = cache.head_sha(repo_dir)
    profile = cache.get(repo_url, sha) if sha else None
    if profile is not None:
        console.print(f"  cache hit for {sha[:8]}, skipping LLM analyze")
    else:
        profile = analyze(repo_dir, llm)
        if sha:
            cache.put(repo_url, sha, profile)
    (run_dir / "profile.json").write_text(profile.model_dump_json(indent=2))
    console.print(f"  detected {profile.language}/{profile.framework or 'no framework'} on port {profile.exposed_port}")

    console.print("[bold]Stage 3: Generate[/bold]")
    dockerfile = generate_dockerfile(profile, llm)
    (run_dir / "Dockerfile").write_text(dockerfile)
    (run_dir / "autodock.yaml").write_text(generate_autodock_config(profile))
    console.print(f"  wrote Dockerfile ({len(dockerfile)} bytes) and autodock.yaml")

    use_compose = bool(profile.services)
    compose_yaml: str | None = None
    if use_compose:
        compose_yaml = generate_compose(profile, dockerfile, llm)
        (run_dir / "docker-compose.yml").write_text(compose_yaml)
        console.print(f"  detected {len(profile.services)} service(s); wrote docker-compose.yml")

    if dry_run:
        return PipelineResult(True, run_dir, None, "generate", "dry run, stopped before build")

    console.print("[bold]Stage 4: Build (self-healing)[/bold]")
    image_tag = f"autodock-{run_id}"
    outcome = build_with_repair(
        repo_dir=repo_dir,
        profile=profile,
        initial_dockerfile=dockerfile,
        image_tag=image_tag,
        attempts_dir=run_dir / "attempts",
        settings=settings,
        llm=llm,
        console=console,
    )
    (run_dir / "Dockerfile").write_text(outcome.final_dockerfile)
    if not outcome.success:
        return PipelineResult(False, run_dir, None, "build",
                              f"build failed after {len(outcome.attempts)} attempt(s)")

    console.print("[bold]Stage 5: Validate[/bold]")
    if use_compose and compose_yaml:
        (repo_dir / "docker-compose.yml").write_text(compose_yaml)
        result = validate_compose(repo_dir=str(repo_dir), profile=profile,
                                  settings=settings, console=console)
    else:
        result = validate_container(image_tag=image_tag, profile=profile,
                                    settings=settings, console=console)

    current_dockerfile = outcome.final_dockerfile
    max_runtime_repairs = 2
    for cycle in range(max_runtime_repairs):
        if result.ok:
            break
        console.print(f"[yellow]Runtime repair cycle {cycle + 1}: feeding logs back to LLM[/yellow]")
        try:
            repaired = generate_runtime_repair(profile, current_dockerfile, result.detail,
                                                result.container_logs_tail, llm)
        except Exception as exc:
            console.print(f"[red]Runtime repair LLM call failed: {exc}[/red]")
            break
        if not repaired.lstrip().upper().startswith("FROM"):
            console.print("[red]Runtime repair did not start with FROM; stopping.[/red]")
            break
        runtime_dir = run_dir / "runtime_attempts" / f"cycle-{cycle:02d}"
        outcome2 = build_with_repair(
            repo_dir=repo_dir, profile=profile, initial_dockerfile=repaired,
            image_tag=image_tag, attempts_dir=runtime_dir,
            settings=settings, llm=llm, console=console,
        )
        if not outcome2.success:
            console.print("[red]Runtime-repaired Dockerfile did not build; stopping.[/red]")
            break
        current_dockerfile = outcome2.final_dockerfile
        (run_dir / "Dockerfile").write_text(current_dockerfile)
        if use_compose and compose_yaml:
            result = validate_compose(repo_dir=str(repo_dir), profile=profile,
                                      settings=settings, console=console)
        else:
            result = validate_container(image_tag=image_tag, profile=profile,
                                        settings=settings, console=console)

    (run_dir / "validation.txt").write_text(
        f"ok={result.ok}\ndetail={result.detail}\n\nlogs:\n{result.container_logs_tail}\n"
    )
    if result.ok:
        console.print(f"[green]Validation OK: {result.detail}[/green]")
    else:
        console.print(f"[red]Validation failed: {result.detail}[/red]")

    usage = llm.usage
    cost = llm.estimated_cost_usd()
    cost_line = (
        f"LLM usage: {usage['calls']} calls, "
        f"{usage['input_tokens']:,} in + {usage['output_tokens']:,} out tokens"
    )
    if cost > 0:
        cost_line += f", ~${cost:.4f} at paid-tier rates"
    console.print(f"[dim]{cost_line}[/dim]")
    (run_dir / "usage.json").write_text(json.dumps({
        "provider": llm.provider,
        "calls": usage["calls"],
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "estimated_cost_usd": round(cost, 6),
    }, indent=2))

    # cleanup: remove the image to keep host clean (best effort)
    docker_runner.run(settings, ["rmi", image_tag], timeout=15, capture=True)

    return PipelineResult(
        ok=result.ok, output_dir=run_dir, image_tag=image_tag,
        stage_reached="validate", detail=result.detail,
    )
