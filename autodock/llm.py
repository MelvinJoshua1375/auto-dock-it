import json
import re
import time
from collections.abc import Callable
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from .config import Settings

T = TypeVar("T", bound=BaseModel)

DEFAULT_TIMEOUT_SECONDS = 60
RETRY_ATTEMPTS = 2
DEFAULT_BACKOFF_SECONDS = 10
MAX_BACKOFF_SECONDS = 60


class LLMError(RuntimeError):
    pass


class LLMRateLimitError(LLMError):
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class LLMTimeout(LLMError):
    pass


class _Backend(Protocol):
    def text(self, prompt: str, *, strong: bool) -> str: ...
    def json(self, prompt: str, *, strong: bool) -> str: ...


def _retry_seconds_from_str(msg: str) -> float | None:
    m = re.search(r"retry[_ \-]after[\"': ]+([0-9.]+)", msg, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"retryDelay['\":\s]+(\d+(?:\.\d+)?)s", msg)
    if m:
        return float(m.group(1))
    m = re.search(r"in\s+(\d+(?:\.\d+)?)\s*s(?:econd)?s?\b", msg, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def _with_retries(fn: Callable[[], str]) -> str:
    last_err: Exception | None = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return fn()
        except LLMRateLimitError as exc:
            wait = exc.retry_after or DEFAULT_BACKOFF_SECONDS
            wait = min(wait, MAX_BACKOFF_SECONDS)
            if attempt == RETRY_ATTEMPTS - 1:
                raise
            time.sleep(wait + 0.5)
            last_err = exc
        except LLMTimeout as exc:
            last_err = exc
            if attempt == RETRY_ATTEMPTS - 1:
                raise
            time.sleep(2)
    raise last_err if last_err else LLMError("retry loop exhausted unexpectedly")


class _GeminiBackend:
    def __init__(self, settings: Settings):
        from google import genai
        from google.genai import types as gtypes
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._fast = settings.gemini_model_fast
        self._strong = settings.gemini_model_strong
        self._http_opts = gtypes.HttpOptions(timeout=DEFAULT_TIMEOUT_SECONDS * 1000)
        self._json_cfg = gtypes.GenerateContentConfig(response_mime_type="application/json")
        self.usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0}

    def _name(self, strong: bool) -> str:
        return self._strong if strong else self._fast

    def _call(self, prompt: str, *, strong: bool, json_mode: bool) -> str:
        from google.genai.errors import APIError
        try:
            kwargs = {"model": self._name(strong), "contents": prompt}
            if json_mode:
                kwargs["config"] = self._json_cfg
            resp = self._client.models.generate_content(**kwargs)
            meta = getattr(resp, "usage_metadata", None)
            if meta is not None:
                self.usage["input_tokens"] += getattr(meta, "prompt_token_count", 0) or 0
                self.usage["output_tokens"] += getattr(meta, "candidates_token_count", 0) or 0
            self.usage["calls"] += 1
            return (resp.text or "").strip()
        except APIError as exc:
            msg = str(exc)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                raise LLMRateLimitError(msg, retry_after=_retry_seconds_from_str(msg)) from exc
            raise LLMError(msg) from exc
        except TimeoutError as exc:
            raise LLMTimeout(str(exc)) from exc

    def text(self, prompt: str, *, strong: bool) -> str:
        return _with_retries(lambda: self._call(prompt, strong=strong, json_mode=False))

    def json(self, prompt: str, *, strong: bool) -> str:
        return _with_retries(lambda: self._call(prompt, strong=strong, json_mode=True))


class _GroqBackend:
    def __init__(self, settings: Settings):
        from groq import Groq
        self._client = Groq(api_key=settings.groq_api_key, timeout=DEFAULT_TIMEOUT_SECONDS)
        self._fast = settings.groq_model_fast
        self._strong = settings.groq_model_strong
        self.usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0}

    def _name(self, strong: bool) -> str:
        return self._strong if strong else self._fast

    def _call(self, prompt: str, *, strong: bool, response_format: dict | None) -> str:
        from groq import APIStatusError, APITimeoutError
        try:
            kwargs = {
                "model": self._name(strong),
                "messages": [{"role": "user", "content": prompt}],
            }
            if response_format:
                kwargs["response_format"] = response_format
            resp = self._client.chat.completions.create(**kwargs)
            usage = getattr(resp, "usage", None)
            if usage is not None:
                self.usage["input_tokens"] += getattr(usage, "prompt_tokens", 0) or 0
                self.usage["output_tokens"] += getattr(usage, "completion_tokens", 0) or 0
            self.usage["calls"] += 1
            return (resp.choices[0].message.content or "").strip()
        except APITimeoutError as exc:
            raise LLMTimeout(str(exc)) from exc
        except APIStatusError as exc:
            if exc.status_code == 429:
                retry_after = None
                try:
                    raw = exc.response.headers.get("retry-after") if exc.response else None
                    retry_after = float(raw) if raw else _retry_seconds_from_str(str(exc))
                except Exception:
                    pass
                raise LLMRateLimitError(str(exc), retry_after=retry_after) from exc
            raise LLMError(str(exc)) from exc

    def text(self, prompt: str, *, strong: bool) -> str:
        return _with_retries(lambda: self._call(prompt, strong=strong, response_format=None))

    def json(self, prompt: str, *, strong: bool) -> str:
        return _with_retries(
            lambda: self._call(prompt, strong=strong, response_format={"type": "json_object"})
        )


# Paid-tier prices in USD per million tokens, used to give the user a rough cost
# estimate even when they are on a free tier. Sources: provider docs as of 2026-05.
PRICING_USD_PER_M = {
    "gemini-2.5-flash": (0.075, 0.30),
    "gemini-2.5-pro":   (1.25, 5.00),
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant":    (0.05, 0.08),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = PRICING_USD_PER_M.get(model)
    if not rates:
        return 0.0
    in_rate, out_rate = rates
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000


class LLM:
    def __init__(self, settings: Settings):
        if settings.provider == "gemini":
            self._backend: _Backend = _GeminiBackend(settings)
            self._model_for_cost = settings.gemini_model_fast
        elif settings.provider == "groq":
            self._backend = _GroqBackend(settings)
            self._model_for_cost = settings.groq_model_fast
        else:
            raise LLMError(f"unknown provider {settings.provider!r}")
        self.provider = settings.provider

    @property
    def usage(self) -> dict:
        return self._backend.usage  # type: ignore[attr-defined]

    def estimated_cost_usd(self) -> float:
        return estimate_cost_usd(self._model_for_cost,
                                  self.usage["input_tokens"], self.usage["output_tokens"])

    def complete_text(self, prompt: str, *, strong: bool = False) -> str:
        return self._backend.text(prompt, strong=strong)

    def complete_json(self, prompt: str, schema: type[T], *, strong: bool = False) -> T:
        current = prompt
        for attempt in range(2):
            raw = self._backend.json(current, strong=strong)
            try:
                data = json.loads(raw)
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                if attempt == 1:
                    raise LLMError(
                        f"LLM returned invalid JSON for {schema.__name__}: {exc}\nRaw: {raw[:500]}"
                    ) from exc
                current = (
                    f"{prompt}\n\nYour previous response could not be parsed. "
                    f"Error: {exc}. Return only valid JSON matching the schema."
                )
        raise LLMError("unreachable")
