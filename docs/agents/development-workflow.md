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

`./dev/start_dev.sh` supports macOS with Homebrew and Podman, Ubuntu, and Debian 13.

Do not assume tmux.

## Validation

See `.github/workflows` for CI behavior. Run commands from the relevant component directory.

- Full validation for a branch or CI regression: `cd src/core && uv run pytest`; `cd src/frontend && uv run pytest`; then `cd src/frontend && uv run pytest tests/playwright --e2e-ci`.
- Use narrower pytest targets only after the full pipeline reproduces a failure or while isolating one.
- Run test and lint commands from the relevant component directory. Tests live in each component's `tests/` directory.
- Lint each changed component with `uv run ruff check`; use `uv run ruff check --fix` and `uv run ruff format` where appropriate.
- After touching Python files, run `./dev/check_pyrefly.sh` to check changed files.
- E2E tests normally start an isolated Docker/Podman Compose stack and stop it afterward. The feature signoff pipeline deliberately retains and reuses its full E2E stack.
- The project-scoped Codex configuration filters inherited `DEBUG` values from shell commands. This prevents the VS Code Codex extension's `DEBUG=release` value from overriding the boolean values in the component `.env` files.
- Models has no unit tests. Worker browser-scraping tests install Playwright browsers.
- Core tests replace Redis connections with an in-process fake so test queues and cache invalidations cannot affect a running local instance.
- E2E admin tests on `master` intentionally keep many functions commented out; do not uncomment them without proving they pass.

### Feature Signoff Loop

After implementing and committing a feature, both humans and agents run the complete push-and-signoff pipeline from the repository root:

```bash
./dev/test_push_signoff.sh
```

The script requires a clean worktree, runs the full local lint, unit, and E2E pipeline, then pushes and signs off only after validation passes. The E2E command inside `dev/testpipeline.sh` always includes `--e2e-keep-stack`. Its first run creates a full Compose project named for the current branch. Later runs on that branch restart Core, worker, and cron to load edited code, then reuse the existing containers, dependency environments, SQLite database, and Redis data. Different branches use different projects, so signoff pipelines may run concurrently from separate worktrees; do not run multiple pipelines for the same branch concurrently.

When validation fails, fix the feature, commit the fix, and run `./dev/test_push_signoff.sh` again. Do not replace this with a focused E2E test, tear down the retained stack between attempts, or run multiple signoff pipelines for the same branch concurrently. Reusing the full stack is the intended acceleration for the complete fix-and-rerun loop.

If retained state appears to cause a failure, copy the project name printed by `dev/testpipeline.sh`, reset that stack, and rerun the same complete script:

```bash
e2e_project="taranis-e2e-..."  # replace with the project name printed by testpipeline.sh
docker compose --profile rq -p "$e2e_project" -f src/frontend/tests/playwright/compose.e2e.yml down -v --remove-orphans --timeout 1
```

CI always uses its own isolated stack, so no separate clean-stack local run is required before signoff.

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
