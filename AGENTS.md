## After completing a task

- **Review acceptance criteria** together. Go through each checkbox.
- **Student runs the verify commands** from the task — not you.
- **Git workflow.** Issue, branch, PR with `Closes #...`, partner review, merge.

## What NOT to do

- Don't create `requirements.txt` or use `pip`. This project uses `uv` and `pyproject.toml` exclusively. Having both leads to dependency drift.
- Don't hardcode URLs or API keys.
- Don't commit secrets.
- Don't implement features from later tasks.
- **(Task 3 specific)** Don't use regex or keyword matching to decide which tool to call. If the LLM isn't calling tools, the fix is in the system prompt or tool descriptions — not in code-based routing. Replacing LLM routing with regex defeats the entire point of this task.
- **(Task 3 specific)** Don't build "reliable fallbacks" that handle common queries without the LLM. A real fallback is for when the LLM service is unreachable. If the LLM picks the wrong tool, improve the tool description — don't route around it.

## Project structure

- `bot/` — the Telegram bot (built across tasks 1–4).
  - `bot/bot.py` — entry point with `--test` mode.
  - `bot/handlers/` — command handlers, intent router.
  - `bot/services/` — API client, LLM client.
  - `bot/PLAN.md` — implementation plan.
- `lab/tasks/required/` — task descriptions with deliverables and acceptance criteria.
- `wiki/` — project documentation.
- `backend/` — the FastAPI backend the bot queries.
- `.env.bot.secret` — bot token + LLM credentials (gitignored).
- `.env.docker.secret` — backend API credentials (gitignored).
