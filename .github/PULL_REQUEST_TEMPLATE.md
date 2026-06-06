## Summary

<!-- What does this PR do? One paragraph or bullet list is fine. -->

## Related Issue

<!-- Link the issue this PR closes, if any: "Closes #123" -->

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] LLM backend (new provider)
- [ ] Documentation update
- [ ] Demo repo addition
- [ ] Refactor / cleanup
- [ ] Other (describe below)

## Checklist

- [ ] `ruff check autodock tests` passes with no errors
- [ ] `pytest -q` passes (all existing tests green)
- [ ] New logic has tests (or I've explained why tests aren't needed)
- [ ] No new `shell=True` in any `subprocess.run()` call
- [ ] No `os.environ` mutation in multi-user Streamlit context
- [ ] `assert_safe_dockerfile()` is not weakened (if Dockerfile scanning was touched)
- [ ] Documentation updated if behaviour changed

## How to Test

<!-- Steps to verify the change manually, if applicable. -->

## Screenshots / Output

<!-- Paste terminal output or screenshots if this is a UI or CLI change. -->
