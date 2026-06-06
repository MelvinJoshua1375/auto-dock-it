# Contributing to Auto-Dock It

Thank you for considering a contribution. The project is MIT-licensed and welcomes bug fixes, new features, new LLM backends, demo repos, documentation improvements, and UI polish.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Before You Open a PR](#before-you-open-a-pr)
- [Areas Open for Contribution](#areas-open-for-contribution)
- [Style Guidelines](#style-guidelines)
- [Reporting Issues](#reporting-issues)
- [Security Vulnerabilities](#security-vulnerabilities)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold it. Report unacceptable behaviour to [sanand03072005@gmail.com](mailto:sanand03072005@gmail.com).

---

## How to Contribute

1. **Discuss first** — for anything non-trivial, open an [issue](https://github.com/MelvinJoshua1375/auto-dock-it/issues) before writing code. This avoids duplicate work and ensures the change fits the project direction.
2. **Fork** the [repository](https://github.com/MelvinJoshua1375/auto-dock-it/fork).
3. **Create a branch**: `git checkout -b feature/your-feature` or `fix/your-fix`.
4. **Make your changes** — see style guidelines below.
5. **Run the checks** — both must pass before opening a PR.
6. **Commit** with a clear, present-tense message (`Add Ollama backend`, not `Added Ollama backend`).
7. **Open a pull request** — describe what you changed and link any related issue.

---

## Development Setup

```bash
git clone https://github.com/MelvinJoshua1375/auto-dock-it.git
cd auto-dock-it
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev,ui]"
cp .env.example .env            # paste your Gemini or Groq API key
autodock doctor                 # verify the setup
```

### Running the web UI locally

```bash
streamlit run autodock/web.py
```

### Running tests

```bash
pytest -q                       # ~101 tests, ~5 s
pytest -q --cov=autodock        # with coverage
pytest -m integration -q        # integration tests (requires Docker + API key)
```

---

## Before You Open a PR

Both checks must pass — CI re-runs them on every push:

```bash
ruff check autodock tests       # lint
pytest -q                       # unit tests
```

Optionally also run:

```bash
bandit -r autodock -ll          # security scan
ruff format autodock tests      # auto-format
```

---

## Areas Open for Contribution

| Area | Details |
|---|---|
| **New LLM backends** | Anthropic Claude, Ollama (local), vLLM, OpenAI |
| **Language coverage** | Better port/env-var detection for Rust, Elixir, C#, .NET, PHP |
| **Demo repos** | Add new repos to `demos/` that stress-test interesting edge cases |
| **Sandboxed build** | Run `docker build` safely on the public Streamlit demo |
| **GitHub Actions template** | Generate a `.github/workflows/docker.yml` alongside the Dockerfile |
| **VS Code extension** | Run `autodock` from the command palette |
| **Documentation** | Clarifications, examples, tutorials |
| **UI improvements** | Streamlit web UI polish (within the B&W design system) |

---

## Style Guidelines

- **Type-hint** all new functions and methods.
- **One blank line** between top-level functions; **two** between classes.
- **No em dashes** in code, comments, prompts, or docs — use commas, colons, parentheses, or en dashes.
- **No new dependencies** for a one-line problem — use the stdlib first.
- **Tests for new logic** — unit tests in `tests/`; integration tests behind `@pytest.mark.integration`.
- **Keep the cleanup safe** — the Dockerfile safety scan (`assert_safe_dockerfile`) must never be weakened. Add tests when extending it.
- **No `shell=True`** in any `subprocess.run()` call — always use argv-style lists.
- **No `os.environ` mutation** in multi-user Streamlit context — pass keys through `load_settings(overrides=...)`.

### Pipeline architecture

The code is organised around the five pipeline stages:

```
autodock/
├── ingest.py       Stage 1 — clone + validate
├── analyze.py      Stage 2 — LLM repo profiling
├── generate.py     Stage 3 — Dockerfile + compose generation
├── build.py        Stage 4 — docker build + LLM repair loop
├── validate.py     Stage 5 — docker run + HTTP poll + runtime repair
├── pipeline.py     Orchestrates all five stages
├── llm.py          LLM provider abstraction (add new backends here)
├── config.py       Settings (env vars → Pydantic model)
├── docker_runner.py  Thin subprocess wrapper for Docker CLI
└── web.py          Streamlit UI
```

---

## Reporting Issues

Open a GitHub issue and include:

- The **command you ran** (or the URL you pasted in the UI).
- The **GitHub repo URL** or local path.
- The relevant files from `output/<run_id>/attempts/` — specifically the failing Dockerfile and build error — or paste the error tail.
- The **LLM provider** you were using (`gemini` or `groq`).
- Your **Python version** (`python --version`) and **Docker version** (`docker version`).

[Open an issue →](https://github.com/MelvinJoshua1375/auto-dock-it/issues/new/choose)

---

## Security Vulnerabilities

Please **do not** open a public issue for security vulnerabilities. Email [sanand03072005@gmail.com](mailto:sanand03072005@gmail.com) with the details. See [SECURITY.md](SECURITY.md) for the full policy.
