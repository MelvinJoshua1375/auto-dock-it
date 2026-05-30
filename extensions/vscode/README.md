# Auto-Dock It - VS Code extension

Wraps the `autodock` CLI so you can containerize the current workspace, explain a Dockerfile, or get improvement suggestions from inside the editor.

## Prerequisites

- `autodock` installed and on `PATH` (`pip install -e .` from the project root, or `pipx install` once published).
- API key in your shell env (`GROQ_API_KEY` or `GEMINI_API_KEY`).

## Build and run locally

```bash
cd extensions/vscode
npm install
npm run compile
code --extensionDevelopmentPath=$PWD
```

In the launched VS Code window, open a folder with code in it and run any of:

- `Auto-Dock: Containerize this workspace`
- `Auto-Dock: Explain this Dockerfile`
- `Auto-Dock: Suggest improvements for this Dockerfile`

## Publish to the Marketplace

```bash
npm run package
vsce publish     # requires a publisher token from https://marketplace.visualstudio.com/manage
```

## Status

Scaffold only. Smoke-test before publishing. Open to contributions.
