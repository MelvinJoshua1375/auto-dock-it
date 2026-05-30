"""In-process rate limiting for the Streamlit preview deployment.

Strategy: three layers.
  1. Cooldown between consecutive runs in one session.
  2. Per-session run cap (st.session_state, reset on browser refresh).
  3. Per-instance global cap (module dict, reset on Streamlit Cloud restart).
This is a circuit breaker, not real auth. Replace with BYOK to remove it.
"""
import threading
import time
from dataclasses import dataclass

DEFAULTS = dict(
    cooldown_seconds=10,
    session_run_cap=3,
    instance_run_cap=50,
)


@dataclass
class LimitDecision:
    allowed: bool
    reason: str = ""
    retry_after_seconds: int = 0


_lock = threading.Lock()
_state = {"instance_runs": 0, "window_started_at": time.monotonic()}
_WINDOW_SECONDS = 60 * 60  # 1 hour rolling window for the instance cap


def reset_instance_counters() -> None:
    with _lock:
        _state["instance_runs"] = 0
        _state["window_started_at"] = time.monotonic()


def check_and_record(
    *,
    session_runs: int,
    session_last_run_at: float | None,
    cooldown_seconds: int = DEFAULTS["cooldown_seconds"],
    session_run_cap: int = DEFAULTS["session_run_cap"],
    instance_run_cap: int = DEFAULTS["instance_run_cap"],
) -> LimitDecision:
    now = time.monotonic()

    if session_last_run_at is not None:
        elapsed = now - session_last_run_at
        if elapsed < cooldown_seconds:
            return LimitDecision(
                allowed=False,
                reason=f"Cooldown: try again in {int(cooldown_seconds - elapsed)} seconds.",
                retry_after_seconds=int(cooldown_seconds - elapsed),
            )

    if session_runs >= session_run_cap:
        return LimitDecision(
            allowed=False,
            reason=f"Session cap reached ({session_run_cap} runs). Refresh the page to start a new session.",
        )

    with _lock:
        if now - _state["window_started_at"] > _WINDOW_SECONDS:
            _state["instance_runs"] = 0
            _state["window_started_at"] = now
        if _state["instance_runs"] >= instance_run_cap:
            return LimitDecision(
                allowed=False,
                reason=f"Instance hourly cap reached ({instance_run_cap} runs/hour). Try again later, or run locally.",
            )
        _state["instance_runs"] += 1

    return LimitDecision(allowed=True)
