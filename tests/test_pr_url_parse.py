import pytest

from autodock.pr import _parse_upstream, PrError


@pytest.mark.parametrize("url,expected", [
    ("https://github.com/owner/repo", ("owner", "repo")),
    ("https://github.com/owner/repo.git", ("owner", "repo")),
    ("https://github.com/owner/repo/", ("owner", "repo")),
    ("http://github.com/octocat/Hello-World", ("octocat", "Hello-World")),
])
def test_parse_upstream_ok(url, expected):
    assert _parse_upstream(url) == expected


def test_parse_upstream_rejects_bad_url():
    with pytest.raises(PrError):
        _parse_upstream("https://github.com/onlyowner")
