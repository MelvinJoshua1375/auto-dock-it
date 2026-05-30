# Sandboxing the build step

Running `docker build` from an arbitrary GitHub URL is a real security concern: every `RUN` line in the LLM-generated Dockerfile executes with root in the build container, and a malicious repo could supply a base image or dependency that exfiltrates whatever lives in the build environment.

For local CLI usage this is no different from `docker build` on any cloned repo: it is the user's machine, the user is in control. For the deployed public preview, it is a liability.

Three layers of mitigation, in increasing order of effort:

## 1. Network isolation (minimum bar)

When invoking `docker build`, add `--network=none` so the build container cannot reach the open internet for exfiltration. This breaks many builds that need `pip install` or `npm install`, so you would need to also drop a private PyPI/npm mirror or accept the failure.

Effort: low. Trade-off: many builds will fail.

## 2. Rootless Docker

Switch the Auto-Dock It server's docker daemon to rootless mode. The build still runs but cannot escape the daemon's user namespace. Combine with `--network=none` where the build allows.

Setup:

```bash
sudo apt install docker-ce-rootless-extras
dockerd-rootless-setuptool.sh install
```

Then run the server process as a non-root user with `DOCKER_HOST=unix:///run/user/$UID/docker.sock`.

Effort: medium. Trade-off: some Dockerfiles that need privileged ops will fail.

## 3. Kaniko (recommended for public deployment)

[Kaniko](https://github.com/GoogleContainerTools/kaniko) builds container images entirely in userspace, without a docker daemon and without privileged mode. It runs each build in an ephemeral container with no host filesystem access.

Switching the build step to Kaniko means replacing `docker build` calls in `autodock/build.py` with:

```bash
/kaniko/executor \
  --dockerfile Dockerfile \
  --context <repo_dir> \
  --no-push \
  --tarPath /tmp/image.tar
```

Then load the tar with `docker load -i /tmp/image.tar` only on the validation step, which can run on a separate sandboxed daemon.

Effort: high. Trade-off: ~30% slower builds, no live cache layer sharing across runs.

## Recommendation

For the public preview deploy, take a phased approach:

1. Ship preview-mode only (current state) until traffic warrants the change.
2. Move to Fly.io with rootless Docker as the next step.
3. Only swap to Kaniko if abuse becomes a real signal.
