# Taranis Worker

This worker uses RQ (Redis Queue) for background task processing.

## Install

```bash
uv venv
source .venv/bin/activate
uv pip install -Ue .[dev]
```

## Usage

Start the RQ worker:

```bash
python -m worker
```

Or use the development script with auto-reload:

```bash
./start_dev_worker.py
```

## Architecture

see [docs](https://github.com/taranis-ai/taranis-ai/tree/master/doc)
