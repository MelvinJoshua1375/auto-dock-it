import time

import pytest

from autodock.llm import LLMRateLimitError, LLMTimeout, _retry_seconds_from_str, _with_retries


@pytest.mark.parametrize("msg,expected", [
    ("Please retry in 15s.", 15),
    ('{"retryDelay": "30s"}', 30),
    ("RateLimit: retry-after: 45", 45),
    ("in 7 seconds", 7),
    ("no hint here", None),
])
def test_retry_seconds_parsing(msg, expected):
    assert _retry_seconds_from_str(msg) == expected


def test_with_retries_succeeds_after_one_429(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _: None)
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise LLMRateLimitError("rate-limit", retry_after=1)
        return "ok"

    assert _with_retries(fn) == "ok"
    assert calls["n"] == 2


def test_with_retries_eventually_raises(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _: None)

    def fn() -> str:
        raise LLMTimeout("slow")

    with pytest.raises(LLMTimeout):
        _with_retries(fn)
