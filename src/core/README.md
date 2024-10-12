# Taranis AI Core

Core could be called the "backend" of Taranis AI.

It offers API Endpoints to the Frontend, is the sole persistence layer (via SQLAlchemy) and schedules tasks via Celery.

Furthermore it acts as celery scheduler backend.

## Requirements

* Python version 3.12 or greater.
* SQLite or PostgreSQL
* [Optional] RabbitMQ

## Setup

```bash
uv venv
uv pip install -Ue .[dev]
```

## Run

`flask run`

or

`./start-granian.py`
