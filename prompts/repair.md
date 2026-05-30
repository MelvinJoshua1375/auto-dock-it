A `docker build` failed. Repair the Dockerfile so the build succeeds.

Project profile:
```
{profile}
```

Current Dockerfile:
```
{dockerfile}
```

Last 80 lines of build error output:
```
{error_tail}
```

Rules:
- Diagnose the root cause from the error log. Common issues: missing OS packages, wrong base image, missing build tools (gcc, make), wrong manifest path, network-restricted commands, port conflicts, missing files.
- Return the full corrected Dockerfile. Output the raw text only, no prose, no markdown fences.
- First non-comment line must be `FROM`.
- Do not introduce new failure modes. If you change the base image, keep it minimal and pinned.
- If the error is in the run command rather than the build, still return a Dockerfile (you can adjust CMD or add deps), since the build loop runs `docker build` only.
