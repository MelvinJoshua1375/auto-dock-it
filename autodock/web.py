"""Streamlit web UI for Auto-Dock It.

Two entry paths:
    streamlit run autodock/web.py        (local)
    streamlit run streamlit_app.py       (Streamlit Cloud, calls render())
"""
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

from .rate_limit import check_and_record

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = PROJECT_ROOT / "output"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mGKHF]")


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


@st.cache_data(ttl=60, show_spinner=False)
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


def _valid_github_url(url: str) -> bool:
    try:
        p = urlparse(url)
    except ValueError:
        return False
    if p.scheme not in ("http", "https"):
        return False
    if p.hostname not in ("github.com", "www.github.com"):
        return False
    parts = [s for s in p.path.split("/") if s]
    if len(parts) < 2:
        return False
    owner, repo = parts[0], parts[1].removesuffix(".git")
    if not owner.replace("-", "").replace("_", "").isalnum():
        return False
    return repo.replace("-", "").replace("_", "").replace(".", "").isalnum()


def render() -> None:
    logo_path = PROJECT_ROOT / "assets" / "logo.svg"
    favicon_path = PROJECT_ROOT / "assets" / "favicon.svg"
    page_icon = str(favicon_path) if favicon_path.exists() else (str(logo_path) if logo_path.exists() else "🐳")
    st.set_page_config(
        page_title="Auto-Dock It | Agentic Dockerfile Generator",
        page_icon=page_icon,
        layout="wide",
        menu_items={
            "Get Help": "https://github.com/MelvinJoshua1375/auto-dock-it",
            "Report a bug": "https://github.com/MelvinJoshua1375/auto-dock-it/issues",
            "About": "Auto-Dock It: LLM-driven Dockerfile generator with a self-healing build loop.",
        },
    )

    col_logo, col_title = st.columns([1, 9])
    with col_logo:
        if logo_path.exists():
            st.image(str(logo_path), width=64)
    with col_title:
        st.title("Auto-Dock It")
        st.caption("Agentic Dockerfile generator with self-healing build loop.")

    with st.sidebar:
        st.header("Settings")
        provider_choice = st.selectbox(
            "LLM provider", ["groq", "gemini"],
            index=0 if os.environ.get("LLM_PROVIDER", "groq") == "groq" else 1,
        )
        user_key = st.text_input(
            f"Your {provider_choice} API key (optional)",
            type="password",
            placeholder="paste to use your own key",
            help=(
                "If you provide a key, rate limits are removed for your session. "
                "If empty, the deployment falls back to a shared key with strict caps."
            ),
        )
        docker_bin = st.text_input(
            "DOCKER_BIN", value=os.environ.get("DOCKER_BIN", "docker"),
            help="On a normal terminal leave as 'docker'. Inside VSCode flatpak set to 'flatpak-spawn --host docker'.",
        )
        st.markdown("---")
        st.markdown(
            "**Get a free API key:**\n"
            "- [Groq](https://console.groq.com/keys) (recommended, higher daily limit)\n"
            "- [Gemini](https://aistudio.google.com/apikey)"
        )

    preview_mode = not _docker_available(docker_bin)
    if preview_mode:
        st.info(
            "**Preview mode**: Docker is not reachable from this environment. "
            "The pipeline will run ingest, analyze, and generate only. "
            "For the full self-healing flow, clone the repo and run `autodock run <url>` locally."
        )

    tab_containerize, tab_explain, tab_improve = st.tabs(["Containerize", "Explain", "Improve"])

    with tab_explain:
        _render_explain(provider_choice, user_key)
    with tab_improve:
        _render_improve(provider_choice, user_key)

    with tab_containerize:
        _render_containerize(provider_choice, user_key, docker_bin, preview_mode)


def _build_llm(provider: str, user_key: str):
    """Construct an LLM scoped to this request. Never mutates os.environ.

    Multi-user safe: each Streamlit run constructs its own Settings instead
    of writing the visitor's key into the process-wide environment, which
    could otherwise leak across concurrent sessions.
    """
    from .config import load_settings
    from .llm import LLM
    overrides: dict = {"LLM_PROVIDER": provider}
    if user_key.strip():
        overrides[f"{provider.upper()}_API_KEY"] = user_key.strip()
    settings = load_settings(overrides=overrides)
    return LLM(settings)


def _render_explain(provider: str, user_key: str) -> None:
    from .generate import generate_explanation
    st.markdown("Paste a Dockerfile, get a line-by-line walkthrough.")
    text = st.text_area("Dockerfile", height=260, key="explain_input",
                        placeholder="FROM python:3.12-slim\n...")
    if st.button("Explain", type="primary", key="explain_btn", disabled=not text.strip()):
        try:
            llm = _build_llm(provider, user_key)
            with st.spinner("Reading the Dockerfile..."):
                result = generate_explanation(text, llm)
            st.markdown(result)
        except Exception as exc:
            st.error(f"Failed: {exc}")


def _render_improve(provider: str, user_key: str) -> None:
    from .generate import generate_improvements
    st.markdown("Paste a Dockerfile, get prioritized improvement suggestions with diff snippets.")
    text = st.text_area("Dockerfile", height=260, key="improve_input",
                        placeholder="FROM python:3.12-slim\n...")
    if st.button("Suggest improvements", type="primary", key="improve_btn",
                 disabled=not text.strip()):
        try:
            llm = _build_llm(provider, user_key)
            with st.spinner("Reviewing..."):
                result = generate_improvements(text, llm)
            st.markdown(result)
        except Exception as exc:
            st.error(f"Failed: {exc}")


def _render_containerize(provider_choice: str, user_key: str, docker_bin: str, preview_mode: bool) -> None:
    SAMPLE_REPOS = [
        ("Flask sample", "https://github.com/digitalocean/sample-flask"),
        ("Node Express", "https://github.com/heroku/node-js-getting-started"),
        ("Go hello", "https://github.com/heroku/go-getting-started"),
    ]

    if "repo_url_value" not in st.session_state:
        st.session_state.repo_url_value = ""

    st.markdown("**Try a sample:**")
    sample_cols = st.columns(len(SAMPLE_REPOS))
    for col, (label, url) in zip(sample_cols, SAMPLE_REPOS, strict=True):
        if col.button(label, key=f"sample-{label}"):
            st.session_state.repo_url_value = url

    repo_url = st.text_input(
        "GitHub repository URL",
        value=st.session_state.repo_url_value,
        placeholder="https://github.com/user/repo",
        key="repo_url_input",
    )
    go = st.button("Containerize", type="primary", disabled=not repo_url)

    if not go:
        return

    if not _valid_github_url(repo_url):
        st.error("Please paste a valid `https://github.com/<owner>/<repo>` URL.")
        return

    using_own_key = bool(user_key.strip())

    if not using_own_key:
        if "session_runs" not in st.session_state:
            st.session_state.session_runs = 0
            st.session_state.last_run_at = None

        decision = check_and_record(
            session_runs=st.session_state.session_runs,
            session_last_run_at=st.session_state.last_run_at,
        )
        if not decision.allowed:
            st.warning(decision.reason + "  Tip: paste your own API key in the sidebar to skip these limits.")
            return

        st.session_state.session_runs += 1
        st.session_state.last_run_at = time.monotonic()

    log_area = st.empty()
    status_container = st.status("Running pipeline...", expanded=True)
    log_lines: list[str] = []

    env = {**os.environ, "DOCKER_BIN": docker_bin, "LLM_PROVIDER": provider_choice}
    _secrets_into_env(env)
    if using_own_key:
        env[f"{provider_choice.upper()}_API_KEY"] = user_key.strip()
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
        match = re.search(r"output/(\d{8}-\d{6}(?:-[0-9a-f]+)?)", clean)
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
