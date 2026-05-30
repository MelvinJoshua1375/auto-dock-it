# Recording the demo GIF for the README

A 10-15 second loop of the agentic build loop in action is the single biggest README upgrade. This is a recipe you can follow on your laptop.

## What we want to show

Two stages, condensed:
1. Build attempt 0 fails with a real error (chown / addgroup mismatch).
2. The LLM repair message, then attempt 1 succeeds and validation prints HTTP 200.

The output of `autodock run https://github.com/digitalocean/sample-flask` is already exactly this. We just need to record it.

## Recommended toolchain

- **terminalizer** (npm) for clean, scriptable terminal GIFs. Or **asciinema + agg** for SVG-to-GIF.
- A 100-column terminal at a readable font size.

Install:

```bash
npm install -g terminalizer
```

## Recording

```bash
cd /path/to/auto-dock-it
source .venv/bin/activate
terminalizer record demo --command "autodock run https://github.com/digitalocean/sample-flask"
# play through, then Ctrl+D when the pipeline finishes
terminalizer render demo -o assets/demo.gif
```

Edit `demo.yml` if needed to set `frameDelay: 50` and trim long pauses.

## Embedding in README

Add at the top, just below the badges:

```markdown
<p align="center">
  <img src="assets/demo.gif" alt="Auto-Dock It in action" width="720" />
</p>
```

## Alternative: a screenshot is fine too

If you don't want to install terminalizer, a single screenshot of the `Validation OK` line plus the surrounding agentic-loop output (the `Build attempt 0/1` lines, the `Repairing Dockerfile...` line) is enough. Save as `assets/demo.png`.
