import pytest
from pydantic import ValidationError

from autodock.models import BuildAttempt, RepoProfile, RunResult, ServiceDep


def test_minimal_profile_round_trip():
    p = RepoProfile(language="python", run_command="python app.py")
    raw = p.model_dump_json()
    p2 = RepoProfile.model_validate_json(raw)
    assert p2.language == "python"
    assert p2.run_command == "python app.py"
    assert p2.env_vars == []
    assert p2.services == []


def test_profile_with_services():
    p = RepoProfile(
        language="python",
        run_command="gunicorn app:app",
        services=[ServiceDep(name="postgres", image="postgres:16")],
    )
    assert p.services[0].name == "postgres"


def test_profile_requires_run_command():
    with pytest.raises(ValidationError):
        RepoProfile(language="python")


def test_build_attempt_defaults():
    a = BuildAttempt(index=0, dockerfile="FROM scratch", exit_code=1)
    assert a.error_tail == ""
    assert a.duration_seconds == 0.0


def test_run_result_truthy():
    assert RunResult(ok=True, detail="x").ok is True
    assert RunResult(ok=False, detail="x").ok is False
