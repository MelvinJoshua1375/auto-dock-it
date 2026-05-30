from pydantic import BaseModel, Field


class ServiceDep(BaseModel):
    name: str
    image: str | None = None
    purpose: str | None = None


class RepoProfile(BaseModel):
    language: str = Field(description="Primary programming language")
    framework: str | None = Field(default=None, description="Web or app framework if detected")
    package_manager: str | None = None
    install_command: str | None = Field(default=None, description="Command to install dependencies inside the container")
    build_command: str | None = None
    run_command: str = Field(description="Command the container should run on start")
    exposed_port: int | None = Field(default=None, description="TCP port the app listens on, if any")
    env_vars: list[str] = Field(default_factory=list, description="Names only, never values")
    services: list[ServiceDep] = Field(default_factory=list, description="External services such as databases")
    base_image_hint: str | None = Field(default=None, description="Suggested base image, eg python:3.12-slim")
    notes: str | None = Field(default=None, description="Anything the LLM thinks the next stage should know")


class BuildAttempt(BaseModel):
    index: int
    dockerfile: str
    exit_code: int
    error_tail: str = ""
    duration_seconds: float = 0.0


class RunResult(BaseModel):
    ok: bool
    detail: str
    container_logs_tail: str = ""
