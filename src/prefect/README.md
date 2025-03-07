# Taranis Worker

This worker is a celery worker

## Install

```bash
uv venv
source .venv/bin/activate
uv pip install -Ue .[dev]
```

## Usage

As a worker

```bash
celery -A worker worker
```

## Architecture

see [docs](https://github.com/taranis-ai/taranis-ai/tree/master/doc)
