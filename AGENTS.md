# AGENTS Instructions

This file contains project-specific instructions for coding agents working on the taranis.ai codebase.

## Agent Persona
Name: jipitiii

## Project Overview

taranis.ai - an OSINT application

See [README.md](README.md) for more information.

## Development Environment

- this project uses [uv](https://docs.astral.sh/uv/) for managing python and packages (a fast Python package installer and resolver)
- to set up the development environment, install uv and run `uv sync` to create the virtual environment
- the python virtual environment needs to be activated with `source .venv/bin/activate` (or use `uv run` to run commands directly)
- see pyproject.toml for the python packages used (and their versions)
- uv.lock contains information about used libraries and their versions

## Ask Developer Before Local Run Instructions

- do not assume every developer uses tmux
- before suggesting local startup steps, ask which workflow they want:
	- `./dev/start_dev.sh` (automated)
	- manual service startup without tmux (start support services with `docker compose -f dev/compose.yml up -d`, then run `./install_and_run_dev.sh` in `src/core`, `src/frontend`, and `src/worker` in separate terminals)
	- manual tmux workflow from `dev/README.md`
- if the developer does not specify a preference, propose `./dev/start_dev.sh` as default and mention alternatives briefly

## Architecture

- **core** (`src/core/`) - Flask REST API backend using SQLAlchemy ORM
- **ingress** (`src/ingress/`) - Nginx entrypoint for routing requests to frontend and backend
- **frontend** (`src/frontend/`) - Flask application with HTMX and DaisyUI, currently serves admin section (will gradually replace gui)
- **worker** (`src/worker/`) - Celery workers for collectors, bots, presenters and publishers
- **models** (`src/models/`) - Pydantic models for input/output validation

## Testing

See .github/workflows for how tests are configured in CI.

### Running Tests Locally

**Setup:** In each src directory (`src/core`, `src/frontend`, `src/models`, `src/worker`), run:
- `uv sync --all-extras --dev` to install all dependencies and dev extras.

**Unit Tests:** In each component directory, run:
- `uv run pytest` - run all tests for that component
- `uv run pytest tests/unit/` - run only unit tests
- `uv run pytest tests/functional/` - run only functional tests
- `uv run pytest -v` - verbose output
- `uv run pytest -x` - stop on first failure
- `uv run pytest -v` - verbose output
- `uv run pytest -x` - stop on first failure
- `uv run pytest -k test_function_name` - run specific test

**End-to-End (E2E) Tests:** Located in `src/core/tests/playwright/` and `src/frontend/tests/playwright/`
- `uv run pytest tests/playwright/ --e2e-ci` - run e2e tests in CI mode
- `uv run pytest tests/playwright/test_e2e_admin.py --e2e-ci` - run specific e2e test file
- `uv run pytest --e2e-ci` - run e2e tests in CI mode
- `uv run pytest -k TestEndToEndAdmin` - run specific test
- `--e2e-ci` flag is required for e2e tests to run properly
- Add `--record-video` to record test execution videos
- Add `--highlight-delay=2` to slow down test execution for debugging

**Linting:** In each component directory:
- `uv run ruff check` - check for linting issues
- `uv run ruff check --fix` - fix auto-fixable linting issues
- `uv run ruff format` - format code

**Important Notes:**
- You must run commands separately in each src directory to ensure all dependencies are installed
- For `src/core` migration work, first launch core once so it bootstraps the current database state; only after that should you apply migrations
- If the latest core migration was only marked as applied, undo or unmark that last migration first and then reapply it
- E2E tests require the application to be running (they start their own test server)
- Tests are located in each component's `tests/` directory
- If you run tests from VS Code / VSC and inherit `DEBUG=release` from the editor environment, override it to a boolean first (for example `DEBUG=true`) or unset it; frontend and core settings parse `DEBUG` as a boolean and `release` breaks test startup
- E2E admin tests in master branch have many functions commented out to avoid flakiness - do not uncomment without ensuring they pass
- Models package does not have unit tests
- Worker package includes Playwright browser installation for web scraping tests
- when adding tests in `src/core`, prefer reusing existing fixtures from `src/core/tests/functional/conftest.py`
- if a new payload/setup fixture is needed for non-functional tests too, add it to `src/core/tests/conftest.py` instead of creating large inline payloads directly inside tests

## Development Guidelines

- never use `git add -A` or in general do not add "all" files lying around
- use specific git add commands for the files you want to commit
- don't commit how many tests passed (statistics in commit messages are not useful)
- do not use `pip` for any package installations or management, always use `uv`
- do not create comments in code that say what was removed, added, changed and why it was done like this. this should be summarized in commit messages and/or PRs
- run tests before committing code
- write tests for new features and bug fixes
- fix linting issues before committing code
- don't write commit messages like "x tests are passing" or "resolves linting failures"
- don't add comments like "Restore template files ..." directly in the code, when you add new codelines

## Datetime Handling

- in `src/core`, treat persisted naive datetimes as **UTC**, not local time
- for incoming assess/story/news item payload timestamps, prefer normalization through `src/models/models/assess.py`
- when storing timestamps in naive SQLAlchemy `DateTime` columns, store **UTC clock values** consistently
- do not introduce new persistence code that uses local naive `datetime.now()` for values that are stored in the database; prefer UTC-based values
- when serializing naive datetimes from `src/core`, preserve the convention that they represent UTC
