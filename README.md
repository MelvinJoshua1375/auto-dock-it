# Auto-Dock It

Live preview: **https://auto-dock-it.streamlit.app**

Agentic LLM tool that clones a public GitHub repository, figures out its stack, generates a Dockerfile (and `docker-compose.yml` when external services are needed), builds it with a self-healing loop, and validates that the container actually runs.

## What's different vs Nixpacks / Buildpacks / one-shot LLM demos

When `docker build` fails, the tool feeds the truncated error log + current Dockerfile back to the LLM, asks for a patched Dockerfile, and retries. If the container builds but the app fails to respond on its port, it feeds the container logs back for a runtime repair. Every attempted Dockerfile and its build log is saved under `output/<run_id>/attempts/` so the agentic loop is auditable end-to-end.

## Demos

Four runs captured in [`demos/`](demos/). Each folder has the final Dockerfile, the structured profile, the agentic attempts, and the validation result.

| Demo | Repo | Stack | Attempts | Outcome |
|---|---|---|---|---|
| [`demos/flask`](demos/flask/) | `digitalocean/sample-flask` | Python + Flask + gunicorn | 2 (1 repair) | HTTP 200 |
| [`demos/nodejs`](demos/nodejs/) | `heroku/node-js-getting-started` | Node + Express | 2 (1 repair) | HTTP 200 |
| [`demos/broken-flask`](demos/broken-flask/) | Local Flask repo with `flsk` typo in requirements.txt | Python + Flask + intentional bug | 4 (3 repairs) | HTTP 200 — LLM patched the typo with `sed` in the Dockerfile |
| [`demos/flask-redis`](demos/flask-redis/) | Local Flask + Redis multi-service | Python + Flask + Redis | 1 | HTTP 200 — auto-generated `docker-compose.yml` with Redis sidecar |

### What the agentic loop actually fixed

In [`demos/flask/attempts/`](demos/flask/attempts/), attempt 0 fails on:

```
chown: invalid group: 'appuser:appuser'
```

because `adduser --system --no-create-home appuser` on debian-slim doesn't create the group reliably. Attempt 1 (after the LLM saw the error tail) replaces those two lines with:

```dockerfile
RUN addgroup --system appuser \
    && adduser --system --no-create-home --ingroup appuser appuser \
    && chown -R appuser:appuser /app
```

and builds clean.

In [`demos/broken-flask/attempts/`](demos/broken-flask/attempts/), the final winning Dockerfile contains:

```dockerfile
RUN sed -i 's/flsk/flask/g' requirements.txt
RUN pip install -r requirements.txt
```

The LLM diagnosed the typo from `pip install` output and patched the user's requirements at build time rather than asking a human to fix the repo.

## Setup

```
python -m venv .venv
source .venv/bin/activate
pip install -e .              # core CLI
pip install -e ".[ui]"        # add Streamlit UI
cp .env.example .env          # paste your Gemini or Groq key
```

## Supported LLM providers

Set `LLM_PROVIDER` in `.env` to `gemini` (free tier: 20 requests/day on Flash) or `groq` (free tier: much higher daily ceiling, llama-3.3-70b).

## CLI usage

```
autodock doctor                                  # verify API key + Docker
autodock run https://github.com/user/repo        # full pipeline
autodock run https://github.com/user/repo --dry-run   # stop after Dockerfile generation
```

Inside the VSCode flatpak terminal, prefix `DOCKER_BIN="flatpak-spawn --host docker"` so the tool talks to the host's Docker daemon.

## Open a PR back to the upstream repo

After a successful `autodock run`, the tool can fork the upstream repo and open a pull request with the generated Dockerfile (plus `autodock.yaml` and `docker-compose.yml` if present).

One-time setup: `gh auth login` (in a host terminal).

```
autodock pr output/<run_id>                       # opens a real PR
autodock pr output/<run_id> --dry-run             # prints what it would do, no API calls
```

If the upstream is owned by you, the tool skips the fork and pushes the branch directly. Otherwise it forks first.

Reference PR opened against the maintainer's test repo: https://github.com/MelvinJoshua1375/autodock-pr-test/pull/1.

## Web UI

```
streamlit run autodock/web.py
```

Opens at http://localhost:8501. Paste a repo URL, click Containerize, watch the agentic loop run.

### Deploying to Streamlit Community Cloud

The web UI runs on https://share.streamlit.io for free with one caveat: Streamlit Cloud containers do not have Docker, so the deployed app falls back to **preview mode** (ingest + analyze + generate Dockerfile only). Build / validate / PR need a local Docker daemon.

To deploy:

1. Push this repo to your GitHub (public). The entry point `streamlit_app.py` is already at the root.
2. Visit https://share.streamlit.io, sign in with GitHub, click **New app**, select this repo, branch `main`, file `streamlit_app.py`.
3. Open the app's **Settings → Secrets** and paste the contents of [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example) filled with your real keys.
4. Deploy. The first build takes 2-3 minutes while pip resolves dependencies.

## Pipeline stages

1. **Ingest** — shallow clone (depth 1, 200 MB cap).
2. **Analyze** — file tree + manifests + entrypoint configs (`gunicorn_config.py`, `wsgi.py`, etc.) fed to the LLM, which returns a structured `RepoProfile`.
3. **Generate** — Dockerfile from the profile. If `services` is non-empty, also generates `docker-compose.yml`.
4. **Build (self-healing)** — runs `docker build`; on failure, sends error tail to LLM for repair; retries up to `MAX_BUILD_RETRIES`.
5. **Validate** — runs the container (or compose stack); polls the app port for HTTP 2xx/3xx. On failure, runs up to 2 runtime-repair cycles feeding container logs back to the LLM.

Artifacts per run: `output/<timestamp>/Dockerfile`, `autodock.yaml`, `profile.json`, `attempts/`, optional `docker-compose.yml`, `validation.txt`.

## Requirements

- Python 3.10+.
- Docker Engine 20+.
- For multi-service repos: Docker Compose v2 (`sudo apt install docker-compose-v2`).
