# LinkedIn launch post

Paste the section below into a new LinkedIn post. Attach one screenshot of the agentic loop running, or the demo GIF once it is recorded. Pin the post to your profile for two weeks.

---

A year ago I walked into a hackathon, picked up an agentic-AI problem statement, and walked out without finishing it. I did not understand the brief at the time. Last week I went back and rebuilt it as something I am proud to ship.

**Auto-Dock It** clones any public GitHub repository, figures out its stack, generates a Dockerfile (and `docker-compose.yml` when needed), builds it, and confirms the container actually responds on its port. When something fails, the LLM reads the build or container logs and proposes a fix. The loop is bounded, auditable, and effective.

What that means in practice: I pointed it at a Flask sample, a Node Express sample, a Flask repo with a deliberate `flsk` typo in requirements, and a Flask+Redis multi-service repo. All four returned HTTP 200. The typo demo healed itself by adding a `sed -i 's/flsk/flask/g'` line to the Dockerfile at build time. That is not a one-shot LLM prompt. That is a real agentic loop.

Highlights:
- Live preview at https://auto-dock-it.streamlit.app
- Source, docs, demos, and a 5-page project report at https://github.com/MelvinJoshua1375/auto-dock-it
- 57 unit tests, CI matrix across Python 3.10 through 3.13, ruff lint clean, Bandit security scan clean
- Two LLM backends so far: Groq Llama 3.3 70B (free, high daily ceiling) and Google Gemini 2.5 Flash
- Bring-your-own-key in the deployed UI so anyone can try it without using my quota

Cost of one run on the paid tier: roughly $0.001. On the free tier: zero, well within the daily ceiling for a single user.

If you have ever opened a stranger's GitHub repo and wondered how to run it, this is for you. Please try it on a repo you know and tell me where it fails. Every interesting failure makes the loop smarter.

#AgenticAI #LLM #Docker #DevTools #OpenSource

---

## Posting tips

- Post Monday morning or Tuesday morning India time for highest engagement.
- Reply to your own post in the first hour with: "If you want to peek at the demos and the report PDF, they are in `docs/REPORT.pdf` in the repo." That keeps the comment thread alive.
- Pin the post to your profile for two weeks.
- Comment on three relevant posts from the day to seed reciprocity.
