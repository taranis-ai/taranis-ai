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

## Architecture

- **core** (`src/core/`) - Flask REST API backend using SQLAlchemy ORM
- **gui** (`src/gui/`) - Vue.js 3 frontend application 
- **frontend** (`src/frontend/`) - Flask application with HTMX and DaisyUI, currently serves admin section (will gradually replace gui)
- **worker** (`src/worker/`) - Celery workers for collectors, bots, presenters and publishers
- **models** (`src/models/`) - Pydantic models for input/output validation

## Testing

See .github/workflows for how tests are configured in CI.
To run tests locally or in CI:
1. In each src directory (`src/core`, `src/frontend`, `src/models`, `src/worker`), run:
	- `uv sync --all-extras --dev` to install all dependencies and dev extras.
2. Then run:
	- `uv run pytest` to execute the tests for that component.
You must run these commands separately in each src directory to ensure all dependencies are installed and tests are run in the correct environment.
Tests are located in each component's `tests/` directory.

## Development Guidelines

- never use `git add -A` or in general do not add "all" files lying around
- use specific git add commands for the files you want to commit
- don't commit how many tests passed (statistics in commit messages are not useful)
- do not use `pip` for any package installations or management, always use `uv`
- do not create comments in code that say what was removed, added, changed and why it was done like this. this should be summarized in commit messages and/or PRs
