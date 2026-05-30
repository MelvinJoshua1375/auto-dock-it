from typing import Protocol, Type, TypeVar
import json

from pydantic import BaseModel, ValidationError

from .config import Settings


T = TypeVar("T", bound=BaseModel)


class _Backend(Protocol):
    def text(self, prompt: str, *, strong: bool) -> str: ...
    def json(self, prompt: str, *, strong: bool) -> str: ...


class _GeminiBackend:
    def __init__(self, settings: Settings):
        from google import genai
        from google.genai import types as gtypes
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._fast = settings.gemini_model_fast
        self._strong = settings.gemini_model_strong
        self._json_cfg = gtypes.GenerateContentConfig(response_mime_type="application/json")

    def _name(self, strong: bool) -> str:
        return self._strong if strong else self._fast

    def text(self, prompt: str, *, strong: bool) -> str:
        resp = self._client.models.generate_content(model=self._name(strong), contents=prompt)
        return (resp.text or "").strip()

    def json(self, prompt: str, *, strong: bool) -> str:
        resp = self._client.models.generate_content(
            model=self._name(strong), contents=prompt, config=self._json_cfg,
        )
        return (resp.text or "").strip()


class _GroqBackend:
    def __init__(self, settings: Settings):
        from groq import Groq
        self._client = Groq(api_key=settings.groq_api_key)
        self._fast = settings.groq_model_fast
        self._strong = settings.groq_model_strong

    def _name(self, strong: bool) -> str:
        return self._strong if strong else self._fast

    def text(self, prompt: str, *, strong: bool) -> str:
        resp = self._client.chat.completions.create(
            model=self._name(strong),
            messages=[{"role": "user", "content": prompt}],
        )
        return (resp.choices[0].message.content or "").strip()

    def json(self, prompt: str, *, strong: bool) -> str:
        resp = self._client.chat.completions.create(
            model=self._name(strong),
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return (resp.choices[0].message.content or "").strip()


class LLM:
    def __init__(self, settings: Settings):
        if settings.provider == "gemini":
            self._backend: _Backend = _GeminiBackend(settings)
        elif settings.provider == "groq":
            self._backend = _GroqBackend(settings)
        else:
            raise RuntimeError(f"unknown provider {settings.provider!r}")
        self.provider = settings.provider

    def complete_text(self, prompt: str, *, strong: bool = False) -> str:
        return self._backend.text(prompt, strong=strong)

    def complete_json(self, prompt: str, schema: Type[T], *, strong: bool = False) -> T:
        current = prompt
        for attempt in range(2):
            raw = self._backend.json(current, strong=strong)
            try:
                data = json.loads(raw)
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                if attempt == 1:
                    raise RuntimeError(
                        f"LLM returned invalid JSON for {schema.__name__}: {exc}\nRaw: {raw[:500]}"
                    )
                current = (
                    f"{prompt}\n\nYour previous response could not be parsed. "
                    f"Error: {exc}. Return only valid JSON matching the schema."
                )
        raise RuntimeError("unreachable")
