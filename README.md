<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)"  srcset="assets/logo-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/logo.svg">
    <img src="assets/logo.svg" alt="Auto-Dock It" width="110" />
  </picture>
</p>

<h1 align="center">Auto-Dock It</h1>

<p align="center">
  <strong>Point it at any public GitHub repository — it figures out the stack, writes a production-grade Dockerfile, builds it, and self-heals through failures. All driven by an LLM.</strong>
</p>

<p align="center">
  <a href="https://auto-dock-it.streamlit.app"><img src="https://img.shields.io/badge/Live%20Demo-auto--dock--it.streamlit.app-111111?style=flat-square&logo=streamlit&logoColor=white" alt="Live Demo"></a>
  <a href="https://codespaces.new/MelvinJoshua1375/auto-dock-it"><img src="https://img.shields.io/badge/Open%20in-GitHub%20Codespaces-111111?style=flat-square&logo=github&logoColor=white" alt="Open in Codespaces"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-111111?style=flat-square" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%2B-111111?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=flat-square" alt="Ruff"></a>
  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-welcome-111111?style=flat-square" alt="PRs Welcome"></a>
</p>

---

## Table of Contents

- [About](#about)
- [What Makes It Different](#what-makes-it-different)
- [Pipeline](#pipeline)
- [Features](#features)
- [Live Demo](#live-demo)
- [Demo Runs](#demo-runs)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Web UI](#web-ui)
- [CLI Reference](#cli-reference)
- [Configuration](#configuration)
- [Deploy Your Own Instance](#deploy-your-own-instance)
- [Security Notes](#security-notes)
- [Build From Source](#build-from-source)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)
- [Contact](#contact)
- [Acknowledgements](#acknowledgements)

---

## About

Containerizing a repository is still a manual process for most teams. You look at the stack, write a Dockerfile, fight with build errors, tweak the CMD, realise the app needs an env var you forgot — and repeat. Tools like Nixpacks and Buildpacks automate the *happy path* only; the moment a repo is non-standard, you are on your own.

**Auto-Dock It** treats Dockerfile generation as an **agentic loop**:

1. It clones the repository and builds a structured profile of the stack using an LLM.
2. It generates a Dockerfile (and `docker-compose.yml` for multi-service repos).
3. It runs `docker build`. On failure, the truncated error is sent back to the LLM with the current Dockerfile; the model returns a patch; the build is retried.
4. The container is started and the exposed port is polled for HTTP 2xx/3xx. On failure, container logs go back to the LLM for a second round of repair.

Every attempt is saved under `output/<run_id>/attempts/`, making the entire loop auditable.

---

## What Makes It Different

| Capability | Nixpacks | Buildpacks | repo2docker | One-shot LLM | **Auto-Dock It** |
|---|:---:|:---:|:---:|:---:|:---:|
| Handles unusual / non-standard repos | ⚠️ | ⚠️ | ❌ | ⚠️ | ✅ |
| Self-heals build errors | ❌ | ❌ | ❌ | ❌ | ✅ |
| Self-heals runtime errors | ❌ | ❌ | ❌ | ❌ | ✅ |
| Multi-service (Docker Compose) | ❌ | ❌ | ❌ | ⚠️ | ✅ |
| Full audit trail of every attempt | ❌ | ❌ | ❌ | ❌ | ✅ |
| Bring-your-own LLM key (BYOK) | — | — | — | — | ✅ |
| Open source | ✅ | ✅ | ✅ | Varies | ✅ |

---

## Pipeline

```
                ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌──────────────┐   ┌──────────┐
 GitHub URL ──► │  Ingest │──►│ Analyze │──►│ Generate │──►│ Build (loop) │──►│ Validate │
                └─────────┘   └─────────┘   └──────────┘   └──────────────┘   └──────────┘
                     │              │              │                │                 │
               shallow clone   LLM builds    Dockerfile +    docker build       docker run
               200 MB cap      RepoProfile   compose.yml     ↺ LLM repair       + HTTP poll
                               from files    if multi-svc    on build error      ↺ LLM repair
                               + manifests                   (max 4 retries)     on bad logs

                every artifact → output/<run_id>/   (attempts/, usage.json, validation.txt)
```

Five stages, each writes to disk — the full run is reproducible and auditable:

| Stage | What it does |
|---|---|
| **Ingest** | Shallow-clones the repo (depth 1, 200 MB cap). Validates the URL against `github.com` before any network call. |
| **Analyze** | Reads manifests, tree summary, README excerpt, entrypoint configs. Sends to LLM; returns a structured `RepoProfile`. Cached per commit SHA — re-runs skip the LLM call. |
| **Generate** | Writes `Dockerfile` from the profile. If `services` is non-empty, also writes `docker-compose.yml`. |
| **Build** | Runs `docker build`. On failure, the error is sent back with the current Dockerfile; the LLM returns a patch; retry. Up to `MAX_BUILD_RETRIES` (default 4). |
| **Validate** | Starts the container (or compose stack), polls the app's exposed port for HTTP 2xx/3xx. On failure, container logs go back to the LLM for up to 2 runtime-repair cycles. |

---

## Features

- **Self-healing build loop** — failed `docker build` outputs are fed back to the LLM for automated repair and retry.
- **Runtime-repair loop** — if the container starts but the app doesn't respond, container logs drive a second LLM repair cycle.
- **Docker Compose** — auto-generates `docker-compose.yml` when multiple services are detected, with `docker compose port` for port discovery.
- **BYOK (Bring Your Own Key)** — paste your Gemini or Groq API key in the UI to bypass rate limits and use your own quota.
- **Full audit trail** — every attempt, the error that triggered repair, and the patch are saved under `output/<run_id>/attempts/`.
- **Explain & Improve** — CLI/UI commands to get a line-by-line walkthrough of any Dockerfile and prioritized improvement suggestions with diffs.
- **PR back to upstream** — after a successful run, `autodock pr` forks the repo and opens a pull request with the generated artifacts.
- **Web UI** — a Streamlit dashboard with live log streaming, sample-repo buttons, and a BYOK field.
- **Free-tier friendly** — works with Gemini 2.5 Flash (20 req/day free) and Groq Llama 3.3 70B (~14,000 req/day free).
- **Security-hardened** — symlink path-traversal protection, LLM-output Dockerfile safety scan, prompt-injection guards, multi-user env isolation.

---

## Live Demo

The public demo at **[auto-dock-it.streamlit.app](https://auto-dock-it.streamlit.app)** runs in **preview mode** (ingest + analyze + generate) because Streamlit Cloud has no Docker daemon. Stages 4 and 5 — the self-healing build and runtime-repair — require a real Docker daemon.

**To see the full loop:**

**Option A — GitHub Codespaces (free, ~60 seconds):**

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/MelvinJoshua1375/auto-dock-it)

The `.devcontainer/` config pre-installs Python, Docker-in-Docker, and the package. Once the IDE loads:

```bash
export GEMINI_API_KEY=your_key_here   # free at aistudio.google.com
autodock run https://github.com/MelvinJoshua1375/githubactions-demo
```

Watch attempts land under `output/<run_id>/attempts/`, then a final HTTP 200 validation.

**Option B — Read captured runs** in [`demos/`](demos/). Each folder has every attempted Dockerfile, the build error, the repair, and `validation.txt`.

---

## Demo Runs

Nine real pipeline runs captured in [`demos/`](demos/):

| Demo | Stack | Self-healing | Outcome |
|---|---|---|---|
| [`jenkins-demo`](demos/jenkins-demo/) | Flask; bind port mismatch (8501 vs EXPOSE 8000) | 1 build + 2 repairs (1 nested) | HTTP 200; `sed` patched port, inner loop fixed `USER` ordering |
| [`flask`](demos/flask/) | Python + Flask + gunicorn | 1 build repair | HTTP 200 |
| [`nodejs`](demos/nodejs/) | Node + Express | 1 build repair | HTTP 200 |
| [`broken-flask`](demos/broken-flask/) | Flask with `flsk` typo in `requirements.txt` | 3 build repairs | HTTP 200; LLM `sed`-patched the typo at build time |
| [`flask-redis`](demos/flask-redis/) | Flask + Redis multi-service | None needed | HTTP 200; auto-generated `docker-compose.yml` |
| [`flask-postgres`](demos/flask-postgres/) | Flask + Postgres with `psycopg` | None needed | HTTP 200; compose with `postgres:16` sidecar |
| [`env-required-flask`](demos/env-required-flask/) | Flask requiring undeclared env var | 1 build repair | HTTP 200; source-code grep detected `REQUIRED_SECRET`, LLM added `ENV` |
| [`crashing-route-flask`](demos/crashing-route-flask/) | Flask route reads hardcoded `/etc/…` path | None needed | HTTP 200; LLM read `app.py`, spotted the path, added `RUN mkdir` |
| [`runtime-loop-fired`](demos/runtime-loop-fired/) | Flask shelling out to `pandoc` via subprocess | 1 build + 1 runtime repair | HTTP 200; build OK, validation 500 → LLM read `FileNotFoundError`, added `RUN apt-get install -y pandoc` |

---

## Installation

### Prerequisites

- Python 3.10+
- Docker Engine 20+ (for build + validate stages)
- Docker Compose v2 (for multi-service repos)
- A free API key from [Google AI Studio](https://aistudio.google.com) (Gemini) or [Groq](https://console.groq.com) (both free-tier)

### Install

```bash
git clone https://github.com/MelvinJoshua1375/auto-dock-it.git
cd auto-dock-it
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev,ui]"
cp .env.example .env
```

Open `.env` and paste at least one API key:

```env
LLM_PROVIDER=gemini                # or groq
GEMINI_API_KEY=your_key_here
# GROQ_API_KEY=your_key_here
```

Verify everything is wired up:

```bash
autodock doctor
```

---

## Quick Start

```bash
autodock run https://github.com/your-org/your-repo
```

The pipeline runs end-to-end. Artifacts land in `output/<run_id>/`:

```
output/
└── 20260601-143022-abc123/
    ├── attempts/
    │   ├── 0-Dockerfile          # first attempt
    │   ├── 0-build-error.txt     # why it failed
    │   ├── 1-Dockerfile          # LLM repair
    │   └── 1-build-success.txt
    ├── Dockerfile                # winner
    ├── docker-compose.yml        # if multi-service
    ├── autodock.yaml             # structured profile
    ├── usage.json                # token counts + cost estimate
    └── validation.txt            # HTTP response from the running container
```

---

## Web UI

```bash
streamlit run autodock/web.py
```

Opens at `http://localhost:8501`. Paste a GitHub URL, click **Containerize**, watch the agentic loop run with live log streaming.

The UI includes:
- **Containerize** — full pipeline with live output
- **Explain** — line-by-line walkthrough of any Dockerfile
- **Improve** — prioritized improvement suggestions with diffs
- **BYOK field** — paste your own Groq or Gemini key to bypass the public demo rate limit
- **Sample repos** — quick buttons to try Flask, Node, and Go hello-world repos
- **Light/Dark toggle** — full B&W theme system

---

## CLI Reference

```
autodock doctor                                  Verify settings, LLM connection, Docker
autodock run <url-or-path>                       Full pipeline (ingest → validate)
autodock run <url> --dry-run                     Stop after Dockerfile generation (no Docker needed)
autodock list                                    Show recent runs with attempt counts and outcomes
autodock explain <Dockerfile>                    Line-by-line walkthrough of a Dockerfile
autodock improve <Dockerfile>                    Improvement suggestions with diffs
autodock pr output/<run_id>                      Fork upstream + open a PR with generated artifacts
autodock pr output/<run_id> --dry-run            Preview what the PR would look like
```

URL validation: only `https://github.com/owner/repo` URLs and existing local paths are accepted.

---

## Configuration

All settings are environment variables (read from `.env` at startup):

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `gemini` or `groq` |
| `GEMINI_API_KEY` | — | Google AI Studio key (free tier available) |
| `GROQ_API_KEY` | — | Groq Console key (generous free tier) |
| `GEMINI_MODEL_FAST` | `gemini-2.5-flash` | Model for analysis and repair |
| `GEMINI_MODEL_STRONG` | `gemini-2.5-pro` | Model for complex generation |
| `GROQ_MODEL_FAST` | `llama-3.3-70b-versatile` | Groq model override |
| `GROQ_MODEL_STRONG` | `llama-3.3-70b-versatile` | Groq model override |
| `MAX_BUILD_RETRIES` | `4` | Self-healing loop budget (build stage) |
| `BUILD_TIMEOUT_SECONDS` | `600` | Per `docker build` timeout |
| `DOCKER_BIN` | `docker` | Docker binary path or prefix (e.g. `flatpak-spawn --host docker`) |
| `BUILD_NO_NETWORK` | `0` | Set to `1` to add `--network=none` to every build (for untrusted repos) |
| `KEEP_RECENT_RUNS` | `20` | Prune old runs in `output/` on each invocation |
| `AUTODOCK_CACHE_DIR` | `~/.cache/autodock` | Profile cache location |

---

## Deploy Your Own Instance

1. Fork or push this repo to GitHub (public).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → select the repo → branch `main` → file `streamlit_app.py`.
3. **Settings → Secrets** — paste the contents of `.streamlit/secrets.toml.example` with your keys filled in.

> The deployed instance runs in **preview mode** (no Docker daemon on Streamlit Cloud). For the full self-healing loop, run locally or in a Codespace.

---

## Security Notes

- **API keys** live in `.env` (gitignored, chmod 600). On Streamlit Cloud they go in the platform Secrets manager — never committed.
- **Arbitrary code execution**: `docker build` runs `RUN` commands from the generated Dockerfile in an isolated build environment. You are still effectively running code from a public repo. Only point this at trusted sources, or run it in a throwaway VM / Codespace.
- **Symlink traversal protection**: the analyze stage refuses to read any file that is a symlink or whose resolved path lies outside the cloned repo directory.
- **Dockerfile safety scan**: every Dockerfile returned by the LLM is scanned by `assert_safe_dockerfile()` before being written to disk. Rejected patterns: `curl | sh`, `wget | bash`, `nc -e`, `/dev/tcp/`, hardcoded `ENV *_KEY=` / `ENV *_TOKEN=` / `ENV *_PASSWORD=`, `--privileged`.
- **Multi-user isolation**: the web UI never writes visitor API keys into `os.environ`. Keys are passed per-request through `load_settings(overrides=...)`.
- All `subprocess.run()` calls use argv-style (never `shell=True`).

---

## Build From Source

```bash
git clone https://github.com/MelvinJoshua1375/auto-dock-it.git
cd auto-dock-it
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,ui]"

# Run tests
pytest -q

# Lint
ruff check autodock tests

# Security scan
bandit -r autodock -ll

# Web UI
streamlit run autodock/web.py
```

CI runs ruff, pytest (Python 3.10–3.13), and Bandit on every push.

---

## Contributing

Contributions are welcome — bug fixes, new LLM backends, demo repos, documentation, and UI improvements.

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full guide.

**Quick steps:**

1. [Fork the repo](https://github.com/MelvinJoshua1375/auto-dock-it/fork)
2. Create a branch: `git checkout -b feature/your-feature`
3. Make changes and run `ruff check autodock tests && pytest -q`
4. Commit with a clear message
5. Open a pull request

[View open issues](https://github.com/MelvinJoshua1375/auto-dock-it/issues) · [Start a discussion](https://github.com/MelvinJoshua1375/auto-dock-it/discussions)

---

## Roadmap

- [x] Self-healing build loop (LLM-driven repair on `docker build` errors)
- [x] Runtime-repair loop (feeds container logs back on validation failure)
- [x] Docker Compose support for multi-service repos
- [x] BYOK (bring-your-own-key) in the Web UI
- [x] GitHub PR-back command
- [x] Explain and Improve CLI/UI commands
- [x] Live cost meter (tokens + estimated USD per run)
- [x] Streamlit Web UI with B&W theme and live log streaming
- [ ] Ollama / local LLM backend (fully offline, no API key required)
- [ ] Sandboxed build preview on the public Streamlit demo
- [ ] Mermaid diagram in generated `autodock.yaml`
- [ ] GitHub Actions workflow template output
- [ ] More demo repos and language coverage (Rust, Elixir, C#, .NET)
- [ ] VS Code extension (run `autodock` from the command palette)

---

## License

Released under the **MIT License**. See [LICENSE](LICENSE) for the full text.

---

## Contact

**Melvin Joshua**
- Email: [melvinjoshua1001@gmail.com](mailto:melvinjoshua1001@gmail.com?subject=Auto-Dock%20It)
- GitHub: [@MelvinJoshua1375](https://github.com/MelvinJoshua1375)
- LinkedIn: [melvin-joshua](https://www.linkedin.com/in/melvin-joshua/)

**Anand Sundaramoorthy SA**
- Email: [sanand03072005@gmail.com](mailto:sanand03072005@gmail.com?subject=Auto-Dock%20It)
- GitHub: [@anandsundaramoorthysa](https://github.com/anandsundaramoorthysa)
- LinkedIn: [anand-sundaramoorthy-sa](https://www.linkedin.com/in/anand-sundaramoorthy-sa-90002a306)

---

## Acknowledgements

Built with these excellent open-source projects:

| Library | Purpose |
|---|---|
| [Streamlit](https://github.com/streamlit/streamlit) | Web UI framework |
| [google-genai](https://github.com/googleapis/python-genai) | Gemini API client |
| [groq](https://github.com/groq/groq-python) | Groq API client |
| [GitPython](https://github.com/gitpython-developers/GitPython) | Repository cloning |
| [Pydantic](https://github.com/pydantic/pydantic) | Structured LLM output validation |
| [Typer](https://github.com/tiangolo/typer) | CLI framework |
| [Rich](https://github.com/Textualize/rich) | Terminal output formatting |
| [Ruff](https://github.com/astral-sh/ruff) | Linting and formatting |
| [Bandit](https://github.com/PyCQA/bandit) | Security scanning |
| [pytest](https://github.com/pytest-dev/pytest) | Test framework |

Thanks to the open-source community and everyone who has tested, starred, or contributed to this project.
