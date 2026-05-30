import yaml

from autodock.generate import _strip_fences, generate_autodock_config
from autodock.models import RepoProfile, ServiceDep


def test_strip_fences_plain():
    assert _strip_fences("FROM alpine\nRUN ls\n") == "FROM alpine\nRUN ls"


def test_strip_fences_with_lang_tag():
    raw = "```dockerfile\nFROM alpine\nRUN ls\n```"
    assert _strip_fences(raw) == "FROM alpine\nRUN ls"


def test_strip_fences_without_lang_tag():
    raw = "```\nfoo\nbar\n```"
    assert _strip_fences(raw) == "foo\nbar"


def test_strip_fences_no_trailing_fence():
    raw = "```yaml\nkey: value"
    assert _strip_fences(raw) == "key: value"


def test_autodock_config_is_valid_yaml():
    p = RepoProfile(
        language="python", run_command="gunicorn app:app",
        exposed_port=8000, env_vars=["DATABASE_URL"],
        services=[ServiceDep(name="postgres", image="postgres:16")],
    )
    out = generate_autodock_config(p)
    parsed = yaml.safe_load(out)
    assert parsed["language"] == "python"
    assert parsed["ports"] == [8000]
    assert parsed["env"] == ["DATABASE_URL"]
    assert parsed["services"][0]["name"] == "postgres"
