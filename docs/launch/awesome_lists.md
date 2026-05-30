# Awesome-list submissions

Two lists are worth submitting to. Open a PR on each. Use the entry below verbatim, choose the alphabetical section that fits.

## awesome-llm-apps

Repo: https://github.com/Shubhamsaboo/awesome-llm-apps

Suggested entry (place under the "DevOps / Developer Tools" section, alphabetical):

```markdown
- [Auto-Dock It](https://github.com/MelvinJoshua1375/auto-dock-it) - Agentic LLM tool that clones any public GitHub repo, generates a Dockerfile and `docker-compose.yml`, builds with a self-healing loop, and validates the container responds. Switchable between Gemini and Groq. Live preview at https://auto-dock-it.streamlit.app.
```

PR title: `Add Auto-Dock It under DevOps / Developer Tools`

PR body:
```
Adding [Auto-Dock It](https://github.com/MelvinJoshua1375/auto-dock-it), an agentic LLM tool that turns any public GitHub repository into a working, validated Docker setup.

Highlights:
- Self-healing build loop: on `docker build` failure, the LLM is given the error log and the current Dockerfile, returns a patched version, and the build retries.
- Runtime-repair loop: if the container builds but the app fails to respond, container logs are fed back for a second pass.
- Multi-service detection: generates `docker-compose.yml` with Redis / Postgres sidecars when the project needs them.
- Two LLM backends: Gemini 2.5 Flash and Groq Llama 3.3 70B. BYOK in the public preview.
- Six demo runs with full attempt history committed to the repo.
- 57 unit tests, CI on Python 3.10 to 3.13, MIT licensed.

Live: https://auto-dock-it.streamlit.app
```

## awesome-docker

Repo: https://github.com/veggiemonk/awesome-docker

Suggested entry (under "Dockerfile generation" or "Tools / DevOps"):

```markdown
- [Auto-Dock It](https://github.com/MelvinJoshua1375/auto-dock-it) - LLM-driven Dockerfile generator with a self-healing build loop. Validates that the container actually responds before declaring success.
```

PR title: `Add Auto-Dock It (LLM-driven Dockerfile generator with self-healing)`

## Optional: awesome-python

Repo: https://github.com/vinta/awesome-python

Auto-Dock It is a Python project so it qualifies, but only submit if you want broader reach beyond Docker/LLM communities. The maintainers are strict about quality bars; the CI badge plus the tests/lint clean state should clear it.
