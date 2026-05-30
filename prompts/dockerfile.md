You generate a single, runnable Dockerfile from a structured project profile.

Project profile (JSON):
```
{profile}
```

Rules:
- Output the raw Dockerfile content only. No prose, no markdown fences, no leading commentary.
- The first non-comment line must be a `FROM` instruction with a pinned tag (no `latest`).
- Use the `base_image_hint` when present, else pick the smallest reasonable image for the language.
- Use a non-root user when reasonable.
- `WORKDIR /app`.
- `COPY` dependency manifests first, install, then `COPY .` for source. This is the cache-friendly layer order.
- `EXPOSE` the port if one is set.
- Set `CMD` from `run_command`. Prefer the JSON array form: `CMD ["a","b","c"]`.
- Add a `HEALTHCHECK` that uses `curl -f http://localhost:<port>/ || exit 1` only when a port is exposed and the image is likely to have curl, otherwise skip the healthcheck.
- Do not assume any host paths. Everything lives in the repo.
- Do NOT use `pip install --user`; install to the system site-packages so the resulting binaries are on the standard PATH for any USER.
- If you create a non-root user, install dependencies BEFORE switching to that user.
- If you reference a user with `USER`, make sure that user actually exists in the base image (eg `node:20-slim` already has `node`; `python:*-slim` does not, you must create one).

Return only the Dockerfile.
