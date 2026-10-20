# Taranis AI Copilot Instructions

- Use the repository [AGENTS.md](../AGENTS.md) guidance together with these repository instructions. Read [CONTRIBUTING.md](../CONTRIBUTING.md) before preparing a contribution. Its contributor process and mandatory [PR template](pull_request_template.md) use apply only to outside collaborators. Core members of the [taranis-ai/ait team](https://github.com/orgs/taranis-ai/teams/ait) may omit those sections; do not require prompt disclosure, human confirmations, or review-time estimates from them. Follow AGENTS.md to determine the human contributor's status and preserve shared project rules.
- Prefer `uv` for Python dependency management. Run commands from the owning component directory under `src/core`, `src/frontend`, `src/models`, or `src/worker`.
- Use Deno for frontend asset tasks in `src/frontend`.
- Prefer the default local workflow in `./dev/start_dev.sh`. If you need manual setup, follow `dev/README.md`.
- Run tests and linters from the component directory that owns the code you changed.
- Respect the frontend and API boundary rules in `AGENTS.md`.
- Do not introduce `pip`-based setup or ad hoc dependency installation.
- Keep changes small, reversible, and documented when behavior or setup changes.
