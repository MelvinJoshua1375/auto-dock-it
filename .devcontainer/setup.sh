#!/usr/bin/env bash
# Codespaces / devcontainer one-shot setup for Auto-Dock It.
# Idempotent: safe to re-run. Verbose: every step prints status.
set -euo pipefail

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
ok()  { printf '\033[1;32m[OK]\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33m[WARN]\033[0m %s\n' "$*"; }
fail(){ printf '\033[1;31m[FAIL]\033[0m %s\n' "$*"; exit 1; }

log "Python interpreter"
python3 --version || fail "python3 not on PATH"
ok "$(python3 --version)"

log "Bootstrap pip"
if ! python3 -m pip --version >/dev/null 2>&1; then
  python3 -m ensurepip --upgrade || fail "ensurepip failed"
fi
python3 -m pip install --upgrade pip >/dev/null
ok "pip $(python3 -m pip --version | awk '{print $2}')"

log "Install Auto-Dock It (editable, dev + ui extras)"
python3 -m pip install -e '.[dev,ui]'
ok "package installed"

log "Ensure user-local bin is on PATH for every shell"
USER_BIN="$(python3 -c 'import site, os; print(os.path.join(site.getuserbase(), "bin"))')"
for rc in "$HOME/.bashrc" "$HOME/.profile" "$HOME/.zshrc"; do
  [ -f "$rc" ] || continue
  if ! grep -q "PATH=$USER_BIN" "$rc"; then
    printf '\nexport PATH="%s:$PATH"\n' "$USER_BIN" >> "$rc"
  fi
done
export PATH="$USER_BIN:$PATH"
ok "PATH updated ($USER_BIN)"

log "Verify autodock entrypoint"
if ! command -v autodock >/dev/null 2>&1; then
  warn "autodock not on PATH; trying user-local install location"
  export PATH="$HOME/.local/bin:$PATH"
fi
command -v autodock >/dev/null || fail "autodock command not found after install"
autodock --help >/dev/null 2>&1 || fail "autodock --help failed"
ok "$(command -v autodock)"

log "Docker daemon"
if docker info >/dev/null 2>&1; then
  ok "docker reachable: $(docker --version)"
else
  warn "docker daemon not reachable yet (DinD feature may still be starting). Re-run 'docker info' in a minute."
fi

log "Setup complete"
ok "Run \`autodock --help\` to see commands."
