Generate a `docker-compose.yml` for a project that needs external services.

Project profile:
```
{profile}
```

App Dockerfile that already builds:
```
{dockerfile}
```

Rules:
- Output the raw `docker-compose.yml` content only. No prose, no markdown fences, no leading commentary.
- Top-level `services:` section.
- The `app` service must use `build: .` and reference the Dockerfile above. Expose the app port.
- Add one service per item in `profile.services`. Use the canonical official image with a pinned major tag (eg `postgres:16`, `redis:7`). Pick reasonable default env vars.
- Add `depends_on:` from app to each service.
- Add `environment:` block on the app service with placeholders for connecting to dependencies. For each dependency, set BOTH the URL form AND the host/port form, because apps differ:
  - postgres: `DATABASE_URL=postgresql://app:app@postgres:5432/app`, `POSTGRES_HOST=postgres`, `POSTGRES_PORT=5432`, `POSTGRES_USER=app`, `POSTGRES_PASSWORD=app`, `POSTGRES_DB=app`
  - redis: `REDIS_URL=redis://redis:6379/0`, `REDIS_HOST=redis`, `REDIS_PORT=6379`
  - similar for any other dependency
- Use `${ENV_VAR:-default}` interpolation where reasonable so the user can override.
- Use named `volumes:` for stateful services (postgres data, etc).
- Do not bind random host ports for dependency services; only the app needs a host port mapping.
- Do NOT mount the host source code over the container's app directory (no `- .:/app`, no `- .:/code` etc). The Dockerfile already copies the source in; mounting the host dir will mask the COPY result and break permissions for non-root users.
- Security rules (the orchestrator refuses to run a compose file that violates any of these):
  - Do not set `privileged: true`.
  - Do not bind-mount sensitive host paths (`/var/run/docker.sock`, `/proc`, `/sys`, `/etc`, `/root`, `/home`, `/var/lib/docker`) into any service.
  - Do not pass host devices (no `devices:` entries pointing at `/dev/*`).
  - Do not set `network_mode: host`, `pid: host`, `ipc: host`, or `userns_mode: host`.
  - Do not `cap_add` any of: `SYS_ADMIN`, `ALL`, `NET_ADMIN`, `SYS_PTRACE`, `SYS_MODULE`.
  - Do not disable confinement via `security_opt` (`apparmor:unconfined`, `seccomp:unconfined`, `label=disable`).
  - Do not hardcode secrets, tokens, API keys, or passwords in plain text; use `${VAR}` interpolation only.
- File must be valid YAML.
