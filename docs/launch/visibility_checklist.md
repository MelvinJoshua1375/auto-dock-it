# Visibility checklist

A one-evening sequence to take the repo from "shipped" to "visible". Do these in order.

## 30-minute essentials

- [ ] **Pin the repo on your GitHub profile.** Profile page → Customize your pins → check `auto-dock-it`. First impression for anyone who opens your profile.
- [ ] **Add `auto-dock-it` to your GitHub bio link.** Use https://github.com/MelvinJoshua1375/auto-dock-it.
- [ ] **Enable Codecov.** Sign in at https://codecov.io with GitHub, add the `auto-dock-it` repo, no further config needed. The Codecov badge in the README starts working automatically on the next push.
- [ ] **Add repo topics on GitHub.** Open the repo settings, click the gear next to "About", add: `docker`, `llm`, `agentic-ai`, `gemini`, `groq`, `dockerfile`, `devops`, `streamlit`, `python`. Topics are the main GitHub search signal.
- [ ] **Set the repo description.** "Agentic LLM tool that turns any public GitHub repo into a working, validated Docker setup. Live at auto-dock-it.streamlit.app."
- [ ] **Set the website field** on the repo to https://auto-dock-it.streamlit.app.

## Same-day shareables

- [ ] **Record the demo GIF.** Recipe at [`docs/recording_demo.md`](../recording_demo.md). Save as `assets/demo.gif`. The README is pre-wired to display it.
- [ ] **Post the LinkedIn launch.** Draft at [`docs/launch/linkedin_post.md`](linkedin_post.md). Attach a screenshot of the agentic loop or the demo GIF.
- [ ] **Submit awesome-list PRs.** Bodies at [`docs/launch/awesome_lists.md`](awesome_lists.md).

## Within a week

- [ ] **Tweet/X thread.** Repurpose the LinkedIn post as a 4-tweet thread. Hook + problem + result + link.
- [ ] **Submit to Show HN.** URL: https://news.ycombinator.com/submit. Title: "Show HN: Auto-Dock It, agentic Dockerfile generator with self-healing build loop". Post Tuesday or Wednesday 8 to 10 am Pacific time for max visibility.
- [ ] **Reddit r/programming and r/devops.** Title: "I rebuilt my failed hackathon project as an agentic Dockerfile generator". Link to the live preview, not the repo.

## Within a month

- [ ] **Blog post.** Title suggestion: "Why one-shot LLM prompts fail at DevOps, and what fixed it for me". Walk through the broken-flask demo. Embed the agentic-loop diff. Link to the repo at the end, not the top.
- [ ] **Add to your resume** under Projects. Use the Live URL + repo URL as the two anchor links.
- [ ] **Submit to Product Hunt.** Lower priority because the audience is less technical, but adds backlinks.

## Tracking

After two weeks, check:
- GitHub stars on the repo (target: 25+ for a credible signal).
- Streamlit Cloud analytics (Dashboard → Manage app → Analytics) for unique visitors.
- LinkedIn post impressions.
- Any inbound DMs from recruiters or devs trying the tool.

If you see traction, the next two things to ship are the demo GIF (if not already done) and a write-up of the most interesting real failure someone reported.
