You are explaining a Dockerfile to a developer who knows Docker but did not write this file.

For each non-empty, non-comment line, write one short sentence that explains WHY the line is there (the intent, the constraint it satisfies, the gotcha it avoids), not WHAT it does literally. Skip blank lines and pure comments.

Format your response as Markdown:

```
## Dockerfile walkthrough

- **`FROM <image>`** - <why this base, what trade-off>
- **`RUN apt-get update && ...`** - <why this exact form: layer caching, no stale lists>
- ...
```

End with a section called `## Notable choices and risks` listing up to 5 bullet points that flag anything subtle: cache friendliness, security posture, image size, missing healthcheck, hard-coded versions, etc.

Be concise. No marketing language. No restating the obvious.

Dockerfile:

```
{dockerfile}
```
