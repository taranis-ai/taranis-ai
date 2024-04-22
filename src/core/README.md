# Taranis AI Core

Core could be called the "backend" of Taranis AI.

It offers API Endpoints to the Frontend, is the sole persistence layer (via SQLAlchemy) and schedules tasks via Celery.

Furthermore it offers SSE to the Frontend and acts as celery scheduler backend.


## Requirements

* Python version 3.12 or greater.
* SQLite or PostgreSQL
* [Optional] RabbitMQ


## Setup

`pip install -e .[dev]`

## Run

`flask run`

or

`./start-granian.py`
