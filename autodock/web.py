"""Streamlit web UI for Auto-Dock It.

Two entry paths:
    streamlit run autodock/web.py        (local)
    streamlit run streamlit_app.py       (Streamlit Cloud, calls render())
"""
from pathlib import Path
import os
import re
import shlex
import subprocess
import sys

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = PROJECT_ROOT / "output"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mGKHF]")


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def _docker_available(docker_bin: str) -> bool:
    try:
        out = subprocess.run(
            shlex.split(docker_bin) + ["version", "--format", "{{.Server.Version}}"],
            capture_output=True, text=True, timeout=5,
        )
        return out.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _secrets_into_env(env: dict) -> None:
    """Copy Streamlit Cloud secrets into env if present, else no-op."""
    try:
        for key in ("GROQ_API_KEY", "GEMINI_API_KEY", "LLM_PROVIDER"):
            try:
                val = st.secrets[key]
            except (KeyError, FileNotFoundError):
                continue
            if val and key not in env:
                env[key] = str(val)
    except Exception:
        pass


def render() -> None:
    st.set_page_config(page_title="Auto-Dock It", page_icon="🐳", layout="wide")
    st.title("Auto-Dock It")
    st.caption("Agentic Dockerfile generator with self-healing build loop.")

    with st.sidebar:
        st.header("Settings")
        docker_bin = st.text_input(
            "DOCKER_BIN", value=os.environ.get("DOCKER_BIN", "docker"),
            help="On a normal terminal leave as 'docker'. Inside VSCode flatpak set to 'flatpak-spawn --host docker'.",
        )
        st.markdown("---")
        st.markdown(
            "**Tip:** API keys come from your `.env` file locally, "
            "or from Streamlit Cloud Secrets when deployed."
        )

    preview_mode = not _docker_available(docker_bin)
    if preview_mode:
        st.info(
            "**Preview mode**: Docker is not reachable from this environment. "
            "The pipeline will run ingest, analyze, and generate only. "
            "For the full self-healing flow, clone the repo and run `autodock run <url>` locally."
        )

    repo_url = st.text_input("GitHub repository URL", placeholder="https://github.com/user/repo")
    go = st.button("Containerize", type="primary", disabled=not repo_url)

    if not go:
        return

    log_area = st.empty()
    status_container = st.status("Running pipeline...", expanded=True)
    log_lines: list[str] = []

    env = {**os.environ, "DOCKER_BIN": docker_bin}
    _secrets_into_env(env)
    cmd = [sys.executable, "-m", "autodock.cli", "run", repo_url]
    if preview_mode:
        cmd.append("--dry-run")
    proc = subprocess.Popen(
        cmd, cwd=str(PROJECT_ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    last_run_dir: Path | None = None

    assert proc.stdout is not None
    for line in proc.stdout:
        clean = _strip_ansi(line.rstrip())
        log_lines.append(clean)
        log_area.code("\n".join(log_lines[-60:]), language="text")
        match = re.search(r"output/(\d{8}-\d{6})", clean)
        if match:
            last_run_dir = OUTPUT_ROOT / match.group(1)
    rc = proc.wait()

    if rc == 0:
        status_container.update(label="Pipeline finished: success", state="complete")
    else:
        status_container.update(label=f"Pipeline finished: failed (exit {rc})", state="error")

    if last_run_dir and last_run_dir.exists():
        st.markdown("### Artifacts")
        cols = st.columns(2)
        with cols[0]:
            df_path = last_run_dir / "Dockerfile"
            if df_path.exists():
                st.subheader("Dockerfile")
                st.code(df_path.read_text(), language="dockerfile")
                st.download_button("Download Dockerfile", df_path.read_text(),
                                    file_name="Dockerfile")
        with cols[1]:
            yaml_path = last_run_dir / "autodock.yaml"
            if yaml_path.exists():
                st.subheader("autodock.yaml")
                st.code(yaml_path.read_text(), language="yaml")
                st.download_button("Download autodock.yaml", yaml_path.read_text(),
                                    file_name="autodock.yaml")

        compose_path = last_run_dir / "docker-compose.yml"
        if compose_path.exists():
            st.subheader("docker-compose.yml")
            st.code(compose_path.read_text(), language="yaml")
            st.download_button("Download docker-compose.yml", compose_path.read_text(),
                                file_name="docker-compose.yml")

        profile_path = last_run_dir / "profile.json"
        if profile_path.exists():
            with st.expander("Detected project profile"):
                st.json(profile_path.read_text())

        attempts_dir = last_run_dir / "attempts"
        if attempts_dir.exists():
            with st.expander(f"Agentic build attempts ({len(list(attempts_dir.glob('*-Dockerfile')))})"):
                for df in sorted(attempts_dir.glob("*-Dockerfile")):
                    st.markdown(f"**Attempt {df.stem.split('-')[0]}**: `{df.name}`")
                    st.code(df.read_text(), language="dockerfile")
                    log = df.with_name(df.name.replace("Dockerfile", "output.log"))
                    if log.exists():
                        st.text_area(f"Build output {df.stem}", value=log.read_text()[-3000:],
                                     height=150, key=f"log-{df.name}")

        validation_path = last_run_dir / "validation.txt"
        if validation_path.exists():
            with st.expander("Validation result"):
                st.code(validation_path.read_text(), language="text")

        st.caption(f"All artifacts: `{last_run_dir}`")


if __name__ == "__main__":
    render()
else:
    # Allow `streamlit run autodock/web.py` (script context, __name__ == "__main__")
    # AND `from autodock.web import render` from streamlit_app.py.
    # When imported, do nothing at module load; the caller calls render().
    pass
