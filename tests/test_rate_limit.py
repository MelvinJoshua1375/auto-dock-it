import time

from autodock.rate_limit import check_and_record, reset_instance_counters


def setup_function(_):
    reset_instance_counters()


def test_first_call_allowed():
    d = check_and_record(session_runs=0, session_last_run_at=None,
                         cooldown_seconds=0, session_run_cap=3, instance_run_cap=10)
    assert d.allowed


def test_cooldown_blocks():
    now = time.monotonic()
    d = check_and_record(session_runs=1, session_last_run_at=now,
                         cooldown_seconds=10, session_run_cap=3, instance_run_cap=10)
    assert not d.allowed
    assert "Cooldown" in d.reason
    assert d.retry_after_seconds > 0


def test_session_cap_blocks():
    d = check_and_record(session_runs=3, session_last_run_at=None,
                         cooldown_seconds=0, session_run_cap=3, instance_run_cap=10)
    assert not d.allowed
    assert "Session cap" in d.reason


def test_instance_cap_blocks():
    for _ in range(2):
        check_and_record(session_runs=0, session_last_run_at=None,
                         cooldown_seconds=0, session_run_cap=10, instance_run_cap=2)
    d = check_and_record(session_runs=0, session_last_run_at=None,
                         cooldown_seconds=0, session_run_cap=10, instance_run_cap=2)
    assert not d.allowed
    assert "Instance" in d.reason
