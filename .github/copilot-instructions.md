# Taranis AI Copilot Instructions

- Use the repository `AGENTS.md` guidance together with these repository instructions.
- Prefer `uv` for Python dependency management. Run commands from the owning component directory under `src/core`, `src/frontend`, `src/models`, or `src/worker`.
- Use Deno for frontend asset tasks in `src/frontend`.
- Prefer the default local workflow in `./dev/start_dev.sh`. If you need manual setup, follow `dev/README.md`.
- Run tests and linters from the component directory that owns the code you changed.
- Respect the frontend and API boundary rules in `AGENTS.md`.
- Do not introduce `pip`-based setup or ad hoc dependency installation.
- Keep changes small, reversible, and documented when behavior or setup changes.
- During PR reviews, add a reviewer briefing comment with the most important pointers and hints (such as risky areas, key files, and useful verification steps) and, most importantly, a clear estimate of how long a human review should take (for example, `Estimated human review time: 20–30 minutes`).
