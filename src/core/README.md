# Taranis AI Core

Core could be called the "backend" of Taranis AI.

It offers API Endpoints to the Frontend, is the sole persistence layer (via SQLAlchemy) and schedules tasks via Celery.

Furthermore it acts as celery scheduler backend.

## Requirements

* Python version 3.12 or greater.
* SQLite or PostgreSQL
* [Optional] RabbitMQ


## Installation

Use the prebuilt container image from https://github.com/orgs/taranis-ai/packages/container/package/taranis-core


Or create a local setup for which it's recommended to use a uv to setup an virtual environment.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
```

Source venv and install dependencies

```bash
source .venv/bin/activate
uv sync --frozen
```

## Usage

```bash
taranis-ai
```

## Development Setup

It is best to follow the [dev setup guide](../../dev/README.md)


### 0. Read the documentation

* [Flask](https://flask.palletsprojects.com)
* [SQLAlchemy](https://www.sqlalchemy.org/)

### 1. Setup Database
Set SQLAlchemy to use a temporary SQLite database.

```bash
export SQLALCHEMY_DATABASE_URI="sqlite:////tmp/taranis.db"
```

### 2. Start Flask

Run the Flask development server:

```bash
./install_and_run_dev.sh
```

This will start the Flask server and run the frontend service at `http://localhost:5000`.


### 3. Test

To run the unit tests just call:

```bash
pytest
```

There are [e2e tests](./tests/playwright/README.md) using Playwright
