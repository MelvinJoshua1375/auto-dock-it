# Contributing

Thanks for considering a contribution. The project is still small enough that drive-by improvements are very welcome.

## Quick setup

```bash
git clone https://github.com/MelvinJoshua1375/auto-dock-it.git
cd auto-dock-it
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,ui]"
cp .env.example .env   # paste your Gemini or Groq key
```

## Before you open a PR

```bash
ruff check autodock tests
pytest -q
```

Both must pass. CI re-runs them on every push.

## Areas open for contribution

- New LLM provider backends (Anthropic, Ollama, vLLM).
- Better detection of env vars and ports for languages the static scan doesn't yet cover (Rust, Elixir, C#).
- More demo repos in `demos/` to stress-test the agentic loop.
- A real GIF or video walk-through for the README.
- Sandbox the `docker build` step so the live preview can run it safely.

## Style

- Type-hint new code.
- One blank line between top-level functions, two between classes.
- Use commas, colons, parentheses, or en dashes for date ranges. Avoid em dashes in code, comments, prompts, and docs.
- Don't introduce dependencies for a one-line problem.
- Tests for new logic; integration tests can live behind `@pytest.mark.integration`.

## Reporting issues

Open a GitHub issue with: the command you ran, the repo URL or local path, the relevant `output/<run_id>/attempts/` artifacts (or paste the error tail), and the LLM provider you were using.
