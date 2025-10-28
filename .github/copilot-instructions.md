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

For setup instructions, see [dev/README.md](../dev/README.md) for complete development environment setup.

**Environment Setup Note:** Only copy environment files if they don't already exist:
```bash
# Only if files don't exist
[ ! -f src/core/.env ] && cp dev/env.dev src/core/.env
[ ! -f src/worker/.env ] && cp dev/env.dev src/worker/.env
```

### Development Workflow

Use `./dev/start_tmux.sh` to start all services in tmux tabs:
- `core` - Flask API server (port 5001)
- `gui` - Vue.js dev server (port 5000)  
- `worker` - Prefect worker serving flows
- `tailwind` - CSS compilation watcher
- `frontend` - HTMX frontend server (port 5002)

Each component has `install_and_run_dev.sh` scripts that handle uv sync and startup.

## Architecture

- **core** (`src/core/`) - Flask REST API backend using SQLAlchemy ORM, integrates with Prefect for workflow orchestration
- **gui** (`src/gui/`) - Vue.js 3 frontend application
- **frontend** (`src/frontend/`) - Flask application with HTMX and DaisyUI, currently serves admin section (will gradually replace gui)
- **worker** (`src/worker/`) - Prefect flows for collectors, bots, presenters and publishers (migrated from Celery)
- **models** (`src/models/`) - Pydantic models for input/output validation, including Prefect task request models

### Workflow Orchestration

The system uses **Prefect 3.x** for distributed task execution:
- Worker processes are organized as Prefect flows in `src/worker/worker/flows/`
- Core API communicates with Prefect deployments to trigger workflows
- Each component type has dedicated flows: `collector_task_flow.py`, `bot_task_flow.py`, `presenter_task_flow.py`, etc.
- Use `models.prefect.*` classes for type-safe task parameters (e.g., `CollectorTaskRequest`, `BotTaskRequest`)

### Data Flow

1. **Collection**: OSINT sources → Collectors (via Prefect flows) → News Items → Core API
2. **Analysis**: News Items → Bot Flows → Enhanced content → Core API
3. **Reporting**: Enhanced items → Presenter Flows → Reports → Core API  
4. **Publishing**: Reports → Publisher Flows → External systems

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

### Project-Specific Patterns

**Prefect Task Organization:**
- All flows are in `src/worker/worker/flows/` with descriptive names (`collector_task_flow.py`, `bot_task_flow.py`)
- Use `models.prefect.*` classes for task parameters - never plain dicts
- Tasks are decorated with `@task`, flows with `@flow`
- Each flow type has a dedicated request model in `models/prefect.py`

**Cross-Component Communication:**
- Worker uses `CoreApi` class to communicate with core backend
- Models package is shared dependency across all components
- Use typed request/response models for API interactions

**Component Structure:**
- Each `src/` component has its own `pyproject.toml` and virtual environment
- Shared models in `src/models/` are included as editable dependency
- Tests are component-specific in each `tests/` directory
