FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

# The upstream image ships a stale Yarn apt source whose GPG key has expired.
# The Docker-in-Docker feature runs `apt-get update` and aborts on the bad
# signature, which breaks Codespace creation. Drop the yarn source list and
# any cached yarn signing-key bits so apt-get update succeeds again.
RUN rm -f /etc/apt/sources.list.d/yarn.list /etc/apt/trusted.gpg.d/yarn.gpg \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*
