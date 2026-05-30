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
- File must be valid YAML.
