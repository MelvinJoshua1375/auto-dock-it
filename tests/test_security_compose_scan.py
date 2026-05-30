"""Compose-level safety: refuse host-access / privileged config from the LLM."""
import pytest

from autodock.generate import UnsafeComposeError, assert_safe_compose

SAFE = """\
services:
  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql://app:app@postgres:5432/app
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
"""


def test_safe_compose_passes():
    assert_safe_compose(SAFE)


@pytest.mark.parametrize("snippet", [
    "services:\n  app:\n    build: .\n    privileged: true\n",
    "services:\n  app:\n    build: .\n    network_mode: host\n",
    "services:\n  app:\n    build: .\n    pid: host\n",
    "services:\n  app:\n    build: .\n    ipc: host\n",
    "services:\n  app:\n    build: .\n    userns_mode: host\n",
    "services:\n  app:\n    build: .\n    volumes:\n      - /var/run/docker.sock:/var/run/docker.sock\n",
    "services:\n  app:\n    build: .\n    volumes:\n      - /etc/passwd:/etc/passwd:ro\n",
    "services:\n  app:\n    build: .\n    volumes:\n      - /root:/host-root\n",
    "services:\n  app:\n    build: .\n    volumes:\n      - /proc:/host-proc\n",
    "services:\n  app:\n    build: .\n    cap_add:\n      - SYS_ADMIN\n",
    "services:\n  app:\n    build: .\n    cap_add:\n      - ALL\n",
    "services:\n  app:\n    build: .\n    security_opt:\n      - apparmor:unconfined\n",
    "services:\n  app:\n    build: .\n    security_opt:\n      - seccomp:unconfined\n",
    "services:\n  app:\n    build: .\n    devices:\n      - /dev/kvm:/dev/kvm\n",
])
def test_dangerous_compose_refused(snippet):
    with pytest.raises(UnsafeComposeError):
        assert_safe_compose(snippet)


@pytest.mark.parametrize("snippet", [
    # privileged as string instead of bool
    "services:\n  app:\n    build: .\n    privileged: 'true'\n",
    "services:\n  app:\n    build: .\n    privileged: yes\n",
    # scalar cap_add (compose allows scalar where list expected; safety must too)
    "services:\n  app:\n    build: .\n    cap_add: SYS_ADMIN\n",
    "services:\n  app:\n    build: .\n    cap_add: CAP_SYS_ADMIN\n",
    # scalar devices
    "services:\n  app:\n    build: .\n    devices: /dev/kvm:/dev/kvm\n",
    # scalar volumes
    "services:\n  app:\n    build: .\n    volumes: /etc:/host-etc\n",
    "services:\n  app:\n    build: .\n    volumes: /var/run/docker.sock:/var/run/docker.sock\n",
    # service value not a mapping
    "services:\n  app: not-a-mapping\n",
])
def test_dangerous_scalar_forms_refused(snippet):
    with pytest.raises(UnsafeComposeError):
        assert_safe_compose(snippet)


def test_invalid_yaml_refused():
    with pytest.raises(UnsafeComposeError):
        assert_safe_compose("services:\n  app:\n    build: .\n    cap_add: [SYS_ADMIN\n")


def test_no_services_block_refused():
    with pytest.raises(UnsafeComposeError):
        assert_safe_compose("version: '3'\n")
