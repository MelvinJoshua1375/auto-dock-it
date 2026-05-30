"""Run IDs gained a `-xxxxxx` UUID suffix. Every consumer must recognize both formats."""
import re

from autodock.cleanup import RUN_ID_RE


def test_cleanup_regex_accepts_both_formats():
    assert RUN_ID_RE.match("20260530-225709")
    assert RUN_ID_RE.match("20260530-225709-38a18f")
    # rejects junk
    assert not RUN_ID_RE.match("20260530")
    assert not RUN_ID_RE.match("2026053-225709")
    assert not RUN_ID_RE.match("20260530-225709-NOTHEX")
    assert not RUN_ID_RE.match("20260530-225709-38a18f-extra")


def test_cli_list_regex_matches_both_formats():
    # The CLI `list` command builds its own compiled regex; assert that string
    # matches the same shape.
    from autodock.cli import list_runs as _  # noqa: F401  (force module import)
    import autodock.cli as cli_mod
    # Re-derive the regex used in `list_runs` from its source to keep the test
    # in sync without having to expose the compile site.
    src = open(cli_mod.__file__).read()
    m = re.search(r"_re\.compile\((r?\"[^\"]+\")\)", src)
    assert m, "could not find compiled run-id regex in cli.py"
    pattern = eval(m.group(1))  # noqa: S307  -- pattern is a literal from our own source
    rx = re.compile(pattern)
    assert rx.match("20260530-225709")
    assert rx.match("20260530-225709-38a18f")
    assert not rx.match("20260530-225709-NOTHEX")


def test_web_output_regex_extracts_both_formats():
    """Streamlit watches stdout for 'output/<run_id>' and resolves the dir."""
    import autodock.web as web_mod
    src = open(web_mod.__file__).read()
    m = re.search(r"re\.search\((r?\"[^\"]+\"),", src)
    assert m, "could not find compiled output-path regex in web.py"
    pattern = eval(m.group(1))  # noqa: S307
    rx = re.compile(pattern)
    assert rx.search("Artifacts in: output/20260530-225709").group(1) == "20260530-225709"
    assert rx.search("Artifacts in: output/20260530-225709-38a18f").group(1) == "20260530-225709-38a18f"
    # negative: uppercase hex is not a valid uuid.hex output, should not match the suffix
    assert rx.search("output/20260530-225709-NOTHEX").group(1) == "20260530-225709"
