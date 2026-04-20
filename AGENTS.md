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
- **frontend** (`src/frontend/`) - Flask application with HTMX and DaisyUI, and Tailwind CSS for styling.
- **worker** (`src/worker/`) - RQ workers for collectors, bots, presenters and publishers
- **models** (`src/models/`) - Pydantic models for input/output validation

### Task Queue System

The application uses **RQ (Redis Queue)** with **Redis** as the message broker for background task processing:

- **Queue Manager** (`src/core/core/managers/queue_manager.py`) - Manages job scheduling and enqueueing using RQ
- **Task Functions** (`src/worker/worker/*/`) - Background jobs for data collection, analysis, and publishing
- **Redis** - Message broker (port 6379) and job persistence
- **Scheduling** - Uses RQ's built-in scheduler with cron expressions via `croniter>=6.0.0`

Task modules:

- `collector_tasks.py` - OSINT source data collection
- `bot_tasks.py` - Automated analysis and processing
- `presenter_tasks.py` - Report and product generation
- `publisher_tasks.py` - Publishing to external systems
- `connector_tasks.py` - Story sharing with MISP and other systems
- `misc_tasks.py` - Maintenance tasks (token cleanup, wordlist updates)

## Frontend/API Boundaries

- user-facing frontend views must not import admin-domain models from `models.admin`
- admin/config endpoints under `src/core/core/api/config.py` are for admin workflows; do not use them from user-facing views
- when a user workflow needs product or publish-related reference data, expose it through a user-scoped endpoint in `src/core/core/api/publish.py`
- declare matching user-facing model classes in `src/models/models/product.py` and import those from frontend publish views

## Testing

See .github/workflows for how tests are configured in CI.

### Running Tests Locally

**Setup:** In each src directory (`src/core`, `src/frontend`, `src/models`, `src/worker`), run:

- `uv sync --all-extras --dev` to install all dependencies and dev extras.

**Full Test Pipeline:** run this first when validating a branch or chasing a CI regression:

- `cd src/core && uv run pytest`
- `cd src/frontend && uv run pytest`
- `cd src/frontend && uv run pytest --e2e-ci`

Use narrower `pytest` targets only after the full pipeline reproduces or if you are isolating one failing area.

**Linting:** In each component directory:

- `uv run ruff check` - check for linting issues
- `uv run ruff check --fix` - fix auto-fixable linting issues
- `uv run ruff format` - format code

**Important Notes:**

- You must run commands separately in each src directory to ensure all dependencies are installed
- For `src/core` migration work, first launch core once so it bootstraps the current database state; only after that should you apply migrations
- If the latest core migration was only marked as applied, undo or unmark that last migration first and then reapply it
- Always execute test and lint commands from within the corresponding component directory (`cd src/<component>`), then run `uv run ...`
- E2E tests require the application to be running (they start their own test server)
- Tests are located in each component's `tests/` directory
- If you run tests from VS Code / VSC and inherit `DEBUG=release` from the editor environment, override it to a boolean first (for example `DEBUG=true`) or unset it; frontend and core settings parse `DEBUG` as a boolean and `release` breaks test startup
- E2E admin tests in master branch have many functions commented out to avoid flakiness - do not uncomment without ensuring they pass
- Models package does not have unit tests
- Worker package includes Playwright browser installation for web scraping tests
- when adding tests in `src/core`, prefer reusing existing fixtures from the nearest `conftest.py`
- if a fixture is broadly useful across the application suite, add it to `src/core/tests/application/conftest.py`
- if a fixture is specific to one cluster such as admin configuration, keep it in that folder's local `conftest.py`
- if a new payload/setup fixture is needed outside `tests/application/` as well, add it to `src/core/tests/conftest.py`
- keep test data in fixtures or `src/core/tests/test_data/`; do not duplicate large inline payloads across test files
- keep helper functions and builders in dedicated support modules under `src/core/tests/application/support/`, not inside the test files themselves
- avoid inline fake classes or ad-hoc test doubles inside test functions; put shared fakes in the nearest `conftest.py` or a dedicated support module instead
- avoid unit tests for orchestration methods whose collaborators are almost entirely monkeypatched or stubbed out; those tests tend to prove call wiring rather than behavior
- for admin/frontend workflows that depend on cache invalidation, scheduling, seeding, or similar cross-component side effects, prefer frontend e2e coverage over heavily mocked unit tests

## Development Guidelines

- The best code is no code.
- Complexity is bad. Keep designs as simple as possible.
- Mocking is also bad. Use it only when it is absolutely necessary.
- DRY matters, but do not force reuse if it hurts readability.
- When creating branches, use only `fix/`, `feature/`, or `chore/` prefixes.
- never use `git add -A` or in general do not add "all" files lying around
- use specific git add commands for the files you want to commit
- don't commit how many tests passed (statistics in commit messages are not useful)
- do not use `pip` for any package installations or management, always use `uv`
- do not manually merge generated lockfiles such as `uv.lock` or `deno.lock`; regenerate them locally from the manifests/tools and commit the regenerated result
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
- do not leave trailing whitespace anywhere (especially on otherwise empty lines)
