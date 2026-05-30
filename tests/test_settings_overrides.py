"""Verify load_settings(overrides=...) does not touch os.environ.

Regression for the multi-user concurrency issue: the Streamlit UI used to
mutate process-wide env vars when a visitor pasted a BYOK key, which would
leak across concurrent sessions.
"""
import os

from autodock.config import load_settings


def test_overrides_do_not_mutate_environ(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "from_env")
    monkeypatch.setenv("GROQ_API_KEY", "")
    settings = load_settings(overrides={"LLM_PROVIDER": "groq", "GROQ_API_KEY": "from_override"})
    assert settings.provider == "groq"
    assert settings.groq_api_key == "from_override"
    # Critical: the override values must not have been written to os.environ.
    # (load_dotenv may add other unrelated keys; that is not what we are testing.)
    assert os.environ.get("LLM_PROVIDER") == "gemini"
    assert os.environ.get("GROQ_API_KEY") == ""


def test_overrides_take_precedence_over_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "from_env")
    settings = load_settings(overrides={"GEMINI_API_KEY": "from_override"})
    assert settings.gemini_api_key == "from_override"


def test_overrides_none_ignored(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "from_env")
    settings = load_settings(overrides={"GEMINI_API_KEY": None})
    assert settings.gemini_api_key == "from_env"


def test_build_no_network_default_false(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.delenv("BUILD_NO_NETWORK", raising=False)
    assert load_settings().build_no_network is False


def test_build_no_network_can_be_enabled(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setenv("BUILD_NO_NETWORK", "true")
    assert load_settings().build_no_network is True
