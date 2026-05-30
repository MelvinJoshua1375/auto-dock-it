# jenkins-demo run

End-to-end Auto-Dock It run on a fresh user repo, [`MelvinJoshua1375/jenkins-demo`](https://github.com/MelvinJoshua1375/jenkins-demo) (Flask web app), executed inside a GitHub Codespace with Groq (llama-3.3-70b) as the LLM provider. Run id `20260530-225709-38a18f`.

![Run transcript](run.png)

## What happened, in order

1. **Ingest** cloned the upstream repo into the run folder.
2. **Analyze** detected `python/flask` on port `8000` (the value from the repo's existing `EXPOSE` line).
3. **Generate** wrote a fresh Dockerfile and `autodock.yaml` from the analyzed profile. See [`attempts/00-Dockerfile`](attempts/00-Dockerfile).
4. **Build** succeeded on the first try in 24.7 seconds.
5. **Validate** mapped the host port to container port 8000, polled the app, and got connection refused. The app's `app.py` actually binds to `8501` inside the container, which `EXPOSE 8000` could not fix.
6. **Runtime repair cycle 1** kicked in. Container logs were fed back to the LLM along with the current Dockerfile.
   - The LLM proposed `RUN sed -i 's/8501/8000/g' app.py` plus `ENV APP_COLOR=blue`. See [`runtime_attempts/cycle-00/00-Dockerfile`](runtime_attempts/cycle-00/00-Dockerfile).
   - That build **failed** with `sed: couldn't open temporary file ./sednFrMOb: Permission denied` because the `RUN sed` was placed after `USER app` and the working directory was owned by root. See [`runtime_attempts/cycle-00/00-output.log`](runtime_attempts/cycle-00/00-output.log).
   - The build error went back to the LLM. It produced a corrected Dockerfile that adds `RUN chown -R app:app /app` before `USER app` and keeps the `sed` patch. See [`runtime_attempts/cycle-00/01-Dockerfile`](runtime_attempts/cycle-00/01-Dockerfile). Build succeeded in 9.7 seconds.
7. **Validate** re-polled the freshly built container and got **HTTP 200**. See [`validation.txt`](validation.txt) for the response log.

## Why this run matters

Two self-healing loops fired and both completed without human intervention:

- **Outer loop** (validate failure): the agent recovered from a container that built cleanly but did not actually serve the app on the expected port. It patched the source code at build time via `sed` to align the Flask bind port with the exposed port.
- **Inner loop** (build failure inside the repair): the agent recovered from its own first repair attempt by reading the new error log and adjusting Dockerfile ordering (chown before USER) on the next try.

That is the agentic differentiator the project is built around: not a one-shot prompt, but an LLM that watches its own builds and runs fail, reads the logs, edits the Dockerfile, and retries until the container actually serves traffic.

## Cost

4 LLM calls (Groq, `llama-3.3-70b-versatile`), 5,621 input + 536 output tokens. Estimated `$0.0037` at paid-tier rates. **Free** on Groq's free tier.

## Files in this folder

| Path | What it is |
|---|---|
| `Dockerfile` | The final, working Dockerfile that produced an HTTP 200 |
| `autodock.yaml` | Unified run config (ports, env, run command) |
| `profile.json` | The structured `RepoProfile` the analyze stage produced |
| `validation.txt` | The HTTP 200 response and last 60 lines of container logs |
| `usage.json` | LLM call count, token totals, estimated cost |
| `metadata.json` | Run id and upstream repo URL |
| `attempts/00-Dockerfile` | The first generated Dockerfile (built clean, but bind mismatch) |
| `attempts/00-output.log` | The successful build log for attempt 0 |
| `runtime_attempts/cycle-00/00-Dockerfile` | Repair attempt that failed on `sed` permission |
| `runtime_attempts/cycle-00/00-output.log` | The failing build log that the LLM read next |
| `runtime_attempts/cycle-00/01-Dockerfile` | The winning repair |
| `runtime_attempts/cycle-00/01-output.log` | The successful build log for the winning repair |
| `run.png` | Rendered transcript of the run shown at the top of this README |
