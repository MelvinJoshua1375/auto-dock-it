import pytest
import typer

from autodock.cli import _validate_repo_url


@pytest.mark.parametrize("url", [
    "https://github.com/owner/repo",
    "https://github.com/owner/repo.git",
    "http://github.com/octocat/Hello-World",
    "https://www.github.com/owner/repo",
])
def test_accepts_github_https(url):
    assert _validate_repo_url(url) == url


@pytest.mark.parametrize("url", [
    "https://gitlab.com/owner/repo",
    "https://example.com/x/y",
    "https://github.com/onlyowner",
    "ftp://github.com/owner/repo",
])
def test_rejects_non_github_https(url):
    with pytest.raises(typer.BadParameter):
        _validate_repo_url(url)


def test_accepts_existing_local_dir(tmp_path):
    out = _validate_repo_url(str(tmp_path))
    assert out == str(tmp_path)


def test_rejects_missing_local_path():
    with pytest.raises(typer.BadParameter):
        _validate_repo_url("/definitely/does/not/exist/12345")
