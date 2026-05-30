# GitHub App design: AutoPR-on-push

A GitHub App that opens an Auto-Dock It pull request automatically whenever a public repo without a Dockerfile receives a push. This is a separate deployable from the CLI / Streamlit UI and is a substantial project on its own. This doc is a sketch, not a build plan.

## What the user does

1. Visits https://github.com/apps/auto-dock-it.
2. Clicks Install, selects which repos to enable on.
3. The next push (or first commit on an enabled repo) triggers a pipeline run.
4. A PR appears on the repo with the generated Dockerfile, autodock.yaml, and compose file (if applicable).
5. PR comment includes the agentic build-attempt log so the maintainer can audit how the LLM got there.

## Architecture

```
GitHub push webhook ─► [Webhook receiver]  
                          │ verifies signature, queues job
                          ▼
                       [Queue (Redis or SQS)]
                          │
                          ▼
                       [Worker pool] ─► autodock run + autodock pr
                          │
                          ▼
                       [PostgreSQL]
                       runs, results, billing
```

Components:

- **Webhook receiver**: FastAPI service, verifies the X-Hub-Signature, enqueues the job. Cheap to scale.
- **Queue**: Redis or SQS. Bounded concurrency per repo to avoid runaway.
- **Worker**: dequeues, clones, runs the existing `run_pipeline` and `open_pr` code. Needs Docker, ideally in a Kaniko sandbox per the [sandboxing notes](sandboxing.md).
- **Persistence**: Postgres for run history, per-installation rate limits, billing usage.

## Auth model

- The app gets installation tokens scoped to the installed repos via the GitHub App private key.
- No user OAuth needed.
- Optional: collect a Groq or Gemini key per installation for BYOK, otherwise use a shared platform key with strict per-installation rate limits.

## Pricing options (if commercialized)

| Tier | Limit |
|---|---|
| Free | 10 PRs per installation per month, shared LLM key, build inside Kaniko sandbox |
| Pro | $9 per month, 200 PRs per installation, faster workers, optional BYOK |
| Team | $29 per month, no PR cap, audit log export |

## Scoping decisions to make before starting

- Open-source the GitHub App code, or keep it closed and sell the SaaS?
- Self-host friendly (Docker Compose deploy), or SaaS only?
- Skip the queue entirely and run synchronously inside the webhook handler? Doable for small repos and simple stacks, fails over time as load grows.

## Suggested first milestone

A demo deployment that listens for pushes on `MelvinJoshua1375/*` repos only, runs the pipeline locally, and posts a PR. No queue, no billing, no UI. Just enough to validate the loop end-to-end. The path from there to a real public app is mostly operational, not architectural.

## Estimated effort

- Week 1: webhook receiver + private key flow + first end-to-end PR.
- Week 2: Postgres run history + per-installation rate limiting.
- Week 3: Kaniko sandbox + production deploy on Fly or Render.
- Week 4: Marketplace listing, billing if commercializing.

This is the biggest item on the roadmap. Do not start it without committing the time.
