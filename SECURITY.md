# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| `main` branch | Yes |
| Older releases | Best-effort |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Email the maintainers directly with the details:

- **Melvin Joshua** — [melvinjoshua1001@gmail.com](mailto:melvinjoshua1001@gmail.com)
- **Anand Sundaramoorthy SA** — [sanand03072005@gmail.com](mailto:sanand03072005@gmail.com)

Include in your report:

1. A description of the vulnerability and its potential impact.
2. Steps to reproduce the issue.
3. Any proof-of-concept code or output.
4. Which version / branch is affected.

We will acknowledge your report within **48 hours** and aim to release a fix within **14 days** for confirmed vulnerabilities. We will credit you in the changelog unless you prefer to remain anonymous.

## Known Security Considerations

These are known design decisions and mitigations, not vulnerabilities:

### Arbitrary code execution via `docker build`

`docker build` executes `RUN` instructions from the generated Dockerfile in an isolated build environment. However, the Dockerfile is generated from a public repository you pointed the tool at. Treat this like running `npm install` from an untrusted source — it is sandboxed by Docker, but you are still executing code from a stranger's repo.

**Mitigation:** Only run against trusted repositories. Set `BUILD_NO_NETWORK=1` to add `--network=none` to every build, limiting outbound network access during the build phase.

### Dockerfile safety scan

Every Dockerfile returned by the LLM is scanned by `assert_safe_dockerfile()` before being written to disk. The following patterns are rejected:

- `curl | sh`, `wget | bash`, `curl | bash` — pipe-to-shell patterns
- `nc -e`, `/dev/tcp/` — reverse-shell patterns
- Hardcoded `ENV *_KEY=`, `ENV *_TOKEN=`, `ENV *_PASSWORD=` — credential leaks
- `--privileged` — container privilege escalation

### Symlink traversal protection

The analyze stage refuses to read any file that is a symlink or whose resolved absolute path lies outside the cloned repository directory. This prevents a malicious repository from shipping a symlink named like a manifest (`requirements.txt -> /home/user/.ssh/id_rsa`) and having its contents sent to an LLM provider.

### API key isolation

The Streamlit web UI never writes visitor API keys into `os.environ`. Keys are passed per-request through `load_settings(overrides={...})` so concurrent sessions cannot read each other's credentials.

### URL validation

Only `https://github.com/owner/repo` URLs and existing local paths are accepted. The URL is validated against the `github.com` host before any network call is made.

### All subprocess calls use argv-style

No `subprocess.run()` call in the codebase uses `shell=True`. All external commands are passed as argument lists, preventing shell-injection vulnerabilities.
