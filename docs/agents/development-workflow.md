# Development Workflow

## When To Load

Before editing application code, running validation, changing development setup, or suggesting local startup steps.

## Environment

- This project uses [uv](https://docs.astral.sh/uv/) for Python packages. Do not use `pip`.
- In each `src` component, run `uv sync --all-extras --dev` to install development dependencies. Use `uv run` for commands, or activate `.venv` with `source .venv/bin/activate` when needed.
- See `pyproject.toml` for dependency versions. Regenerate lockfiles from manifests/tools; never manually merge `uv.lock` or `deno.lock`.

## Local Startup

Before suggesting local startup, ask which workflow the developer wants:

- `./dev/start_dev.sh` (default when they have no preference; mention the alternatives)
- Manual non-tmux startup: `docker compose -f dev/compose.yml up -d`, then run `./install_and_run_dev.sh` in `src/core`, `src/frontend`, and `src/worker` in separate terminals
- Manual tmux workflow from `dev/README.md`

Do not assume tmux.

## Validation

See `.github/workflows` for CI behavior. Run commands from the relevant component directory.

- Full validation for a branch or CI regression: `cd src/core && uv run pytest`; `cd src/frontend && uv run pytest`; then `cd src/frontend && uv run pytest --e2e-ci`.
- Use narrower pytest targets only after the full pipeline reproduces a failure or while isolating one.
- Run test and lint commands from the relevant component directory. Tests live in each component's `tests/` directory.
- Lint each changed component with `uv run ruff check`; use `uv run ruff check --fix` and `uv run ruff format` where appropriate.
- After touching Python files, run `./dev/check_pyrefly.sh` to check changed files.
- E2E tests start and stop a dedicated Docker/Podman Compose test stack automatically for the session; you mainly need Docker/Podman Compose available locally (see `src/frontend/tests/playwright/README.md`).
- If VS Code supplies `DEBUG=release`, unset it or use a boolean value such as `DEBUG=true` before starting frontend or core tests.
- Models has no unit tests. Worker browser-scraping tests install Playwright browsers.
- E2E admin tests on `master` intentionally keep many functions commented out; do not uncomment them without proving they pass.

## Test Conventions

- Reuse the nearest existing `conftest.py` fixtures. Put broadly useful core fixtures in `src/core/tests/application/conftest.py`; cluster-specific fixtures in their local `conftest.py`; and cross-application payload/setup fixtures in `src/core/tests/conftest.py`.
- Keep large test data in fixtures or `src/core/tests/test_data/`. Put shared builders and helpers in `src/core/tests/application/support/`.
- Do not create inline fake classes or ad-hoc test doubles in test functions. Avoid unit tests that only prove mocked orchestration wiring.
- For cache invalidation, scheduling, seeding, and similar cross-component effects, prefer frontend E2E coverage. Prefer `data-test-id` selectors for E2E tests.
- Do not use pytest autouse fixtures. Request fixtures explicitly or use module/class-level `pytest.mark.usefixtures`.

## Development Conventions

- The best code is no code. Keep designs simple, use mocking only when necessary, and do not force DRY reuse that hurts readability.
- Prefer the simplest correct implementation. Do not add WIP compatibility aliases, migration validators, or compatibility payloads for behavior not released to users.
- Prefer flat settings JSON and direct values. Avoid unnecessary metadata, constants, validators, and helpers.
- Keep changes focused. Use `fix/`, `feature/`, or `chore/` branch prefixes; never use `git add -A`; stage only intended files.
- Run tests and fix lint before committing. Do not include test-pass counts in commit messages.
- Do not add `from __future__ import annotations` unless Python 3.13 compatibility requires postponed annotation evaluation for forward references, circular imports, or `TYPE_CHECKING` annotations.
- Do not add code comments that describe what changed or why; use commits and PRs for that history.
