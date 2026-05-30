# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added
- Bring-your-own-key field in the web UI; user keys bypass rate limits.
- Live cost meter: per-run token totals and an estimated USD figure printed at the end of every run and saved to `output/<run_id>/usage.json`.
- `autodock list` command shows recent runs with attempts and outcomes.
- Sample-repo quick buttons in the web UI.
- Project logo (`assets/logo.svg`) used as Streamlit page icon.
- `CONTRIBUTING.md` and this `CHANGELOG.md`.

### Changed
- README adds Visibility / Status badges and links the live preview prominently.

## 0.1.0

### Added
- Five-stage agentic pipeline: ingest, analyze, generate, build (self-healing), validate.
- Runtime-repair loop: feeds container logs back to the LLM when the app fails to respond.
- Docker Compose support when multiple services are detected, with port auto-discovery via `docker compose port`.
- LLM providers: Gemini 2.5 Flash and Groq Llama 3.3 70B, switchable via `LLM_PROVIDER`.
- Profile cache keyed by repo URL plus commit SHA.
- Source-code env-var grep (Python, Node, Go, Java, Ruby, PHP).
- GitHub PR-back command: forks the upstream and opens a PR with the generated artifacts. Skips the fork when the upstream is self-owned.
- Streamlit web UI with live log streaming.
- Public preview deploy at https://auto-dock-it.streamlit.app.
- Pytest suite, ruff lint, Bandit security scan, GitHub Actions CI across Python 3.10 to 3.13.
- Dependabot for pip and GitHub Actions.
- MIT license.
