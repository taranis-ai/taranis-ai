# Taranis Worker

This worker is a celery worker

## Install

```bash
pip install -e .
```

## Usage

As a worker

```bash
celery -A worker worker
```

as a scheduler

```bash
celery -A worker beat
```

## Architecture

see [docs](https://github.com/taranis-ai/taranis-ai/tree/master/doc)
