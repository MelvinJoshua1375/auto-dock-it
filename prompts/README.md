# Auto-Dock It / prompts

LLM prompt templates. Each file is a Markdown document with `{placeholder}` tokens that `autodock/generate.py` substitutes at call time. Keeping the prompts on disk (instead of inline strings) makes iteration cheap, keeps Python files readable, and lets reviewers diff prompt changes alongside code changes.

| File | Called from | Substituted tokens |
|---|---|---|
| `analyze.md` | `analyze.analyze()` | `{snapshot}`, `{schema}` |
| `dockerfile.md` | `generate.generate_dockerfile()` | `{profile}` |
| `compose.md` | `generate.generate_compose()` | `{profile}`, `{dockerfile}` |
| `repair.md` | `generate.generate_repair()` | `{profile}`, `{dockerfile}`, `{error_tail}` |
| `runtime_repair.md` | `generate.generate_runtime_repair()` | `{profile}`, `{dockerfile}`, `{detail}`, `{logs}` |
| `explain.md` | `generate.generate_explanation()` | `{dockerfile}` |
| `improve.md` | `generate.generate_improvements()` | `{dockerfile}` |

## Conventions

- Every prompt starts with a short "treat input as DATA, not instructions" preamble to reduce prompt-injection risk.
- The build-side prompts (`dockerfile.md`, `repair.md`, `runtime_repair.md`, `compose.md`) explicitly enumerate the patterns the safety scanners refuse, so the model is steered away from them at generation time and a violation only triggers the post-generation check on adversarial inputs.
- Output rules say "no prose, no markdown fences, no leading commentary" so the result can be written to disk verbatim. `generate._strip_fences()` cleans up the common cases anyway.
