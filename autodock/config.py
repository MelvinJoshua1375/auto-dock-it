import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    provider: str  # "gemini" or "groq"
    gemini_api_key: str
    gemini_model_fast: str
    gemini_model_strong: str
    groq_api_key: str
    groq_model_fast: str
    groq_model_strong: str
    max_build_retries: int
    build_timeout_seconds: int
    docker_bin: str
    keep_recent_runs: int
    build_no_network: bool


def load_settings(env_file: Path | None = None, *, overrides: dict | None = None) -> Settings:
    if env_file is not None:
        load_dotenv(env_file)
    else:
        load_dotenv()
    overrides = overrides or {}

    def get(name: str, default: str = "") -> str:
        if name in overrides and overrides[name] is not None:
            return str(overrides[name])
        return os.environ.get(name, default)

    provider = get("LLM_PROVIDER", "gemini").strip().lower()
    if provider not in {"gemini", "groq"}:
        raise RuntimeError(f"LLM_PROVIDER must be 'gemini' or 'groq', got {provider!r}")

    gemini_key = get("GEMINI_API_KEY").strip()
    groq_key = get("GROQ_API_KEY").strip()
    if provider == "gemini" and not gemini_key:
        raise RuntimeError("LLM_PROVIDER=gemini but GEMINI_API_KEY is empty.")
    if provider == "groq" and not groq_key:
        raise RuntimeError("LLM_PROVIDER=groq but GROQ_API_KEY is empty.")

    return Settings(
        provider=provider,
        gemini_api_key=gemini_key,
        gemini_model_fast=get("GEMINI_MODEL_FAST", "gemini-2.5-flash"),
        gemini_model_strong=get("GEMINI_MODEL_STRONG", "gemini-2.5-pro"),
        groq_api_key=groq_key,
        groq_model_fast=get("GROQ_MODEL_FAST", "llama-3.3-70b-versatile"),
        groq_model_strong=get("GROQ_MODEL_STRONG", "llama-3.3-70b-versatile"),
        max_build_retries=int(get("MAX_BUILD_RETRIES", "4")),
        build_timeout_seconds=int(get("BUILD_TIMEOUT_SECONDS", "600")),
        docker_bin=get("DOCKER_BIN", "docker"),
        keep_recent_runs=int(get("KEEP_RECENT_RUNS", "20")),
        build_no_network=get("BUILD_NO_NETWORK", "0").lower() in {"1", "true", "yes"},
    )
