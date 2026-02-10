# GitHub Copilot Instructions

This file contains project-specific instructions for GitHub Copilot to provide better context-aware assistance when working on the taranis.ai codebase.

**For Contributors:** These instructions are automatically loaded by GitHub Copilot in VS Code and other supported IDEs. You don't need to manually reference this file - Copilot will use these hints to provide more accurate suggestions and explanations about the project structure and conventions.

## Project Overview

taranis.ai - an OSINT application

See [README.md](../README.md) for more information.

## Development Environment

- this project uses [uv](https://docs.astral.sh/uv/) for managing python and packages (a fast Python package installer and resolver)
- to set up the development environment, install uv and run `uv sync` to create the virtual environment
- the python virtual environment needs to be activated with `source .venv/bin/activate` (or use `uv run` to run commands directly)
- see pyproject.toml for the python packages used (and their versions)
- uv.lock contains information about used libraries and their versions

### Starting the Development Environment

The recommended way to start the development environment is to run `./dev/start_dev.sh` from the repository root. This script:
1. Sources environment variables from `dev/env.dev`
2. Installs system dependencies (Ubuntu only)
3. Creates `.env` files for core, worker, and frontend components by copying `dev/env.dev`
4. Starts Docker Compose services (PostgreSQL database + Redis) via `dev/compose.yml`
5. Launches a tmux session via `start_tmux.sh` with 4 windows:
   - **core**: Flask REST API (port 5001)
   - **tailwind**: CSS watcher for frontend development
   - **frontend**: Flask frontend (port 5002)
   - **worker**: RQ workers for background tasks

Each component automatically runs `uv sync` and starts its service when the tmux window is created.

## Architecture

- **core** (`src/core/`) - Flask REST API backend using SQLAlchemy ORM
- **ingress** (`src/ingress/`) - Nginx entrypoint for routing requests to frontend and backend
- **frontend** (`src/frontend/`) - Flask application with HTMX and DaisyUI, currently serves admin section (will gradually replace gui)
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

## Testing

See .github/workflows for how tests are configured in CI.

### Running Tests Locally

**Setup:** In each src directory (`src/core`, `src/frontend`, `src/models`, `src/worker`), run:
- `uv sync --all-extras --dev` to install all dependencies and dev extras.

**Unit Tests:** In each component directory, run (after changing into that directory, e.g. `cd src/frontend`):
- `uv run pytest` - run all tests for that component
- `uv run pytest tests/unit/` - run only unit tests
- `uv run pytest tests/functional/` - run only functional tests
- `uv run pytest -v` - verbose output
- `uv run pytest -x` - stop on first failure
- `uv run pytest tests/test_specific.py::test_function_name` - run specific test

**End-to-End (E2E) Tests:** Located in `src/core/tests/playwright/` and `src/frontend/tests/playwright/`
- `uv run pytest tests/playwright/ --e2e-ci` - run e2e tests in CI mode
- `uv run pytest tests/playwright/test_e2e_admin.py --e2e-ci` - run specific e2e test file
- `uv run pytest tests/playwright/test_e2e_admin.py::TestEndToEndAdmin::test_login --e2e-ci` - run specific test
- `--e2e-ci` flag is required for e2e tests to run properly
- Add `--record-video` to record test execution videos
- Add `--highlight-delay=2` to slow down test execution for debugging

**Linting:** In each component directory:
- `uv run ruff check` - check for linting issues
- `uv run ruff check --fix` - fix auto-fixable linting issues
- `uv run ruff format` - format code

**Important Notes:**
- You must run commands separately in each src directory to ensure all dependencies are installed
- Always execute test and lint commands from within the corresponding component directory (`cd src/<component>`), then run `uv run ...`
- E2E tests require the application to be running (they start their own test server)
- Tests are located in each component's `tests/` directory
- E2E admin tests in master branch have many functions commented out to avoid flakiness - do not uncomment without ensuring they pass
- Models package does not have unit tests
- Worker package includes Playwright browser installation for web scraping tests

## Development Guidelines

- never use `git add -A` or in general do not add "all" files lying around
- use specific git add commands for the files you want to commit
- don't commit how many tests passed (statistics in commit messages are not useful)
- do not use `pip` for any package installations or management, always use `uv`
- do not create comments in code that say what was removed, added, changed and why it was done like this. this should be summarized in commit messages and/or PRs
- run tests before comitting code
- write tests for new features and bug fixes
- fix linting issues before committing code
- don't write commit messages like "x tests are passing" or "resolves linting failures"
- don't add comments like "Restore template files ..." directly in the code, when you add new codelines
- do not leave trailing whitespace anywhere (especially on otherwise empty lines)
