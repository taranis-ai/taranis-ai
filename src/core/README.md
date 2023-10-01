# TaranisNG Core

The Tarins-NG Core could be called the "backend" of TaranisNG.

It offers API Endpoints to the Frontend, is the sole persistence layer (via SQLAlchemy) and schedules tasks via Celery.

Furthermore it offers SSE to the Frontend and acts as celery scheduler backend.


## Requirements

* Python version 3.11 or greater.
* SQLite or PostgreSQL
* [Optional] RabbitMQ


## Setup

`pip install -e .[dev]`

## Run

`flask run`

or

`gunicorn`
