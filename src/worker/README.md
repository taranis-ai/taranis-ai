# Taranis Worker

This worker uses RQ (Redis Queue) for background task processing.

RSS sources expose collection health through their persisted task status. Responses that are not identifiable as RSS or Atom fail immediately; parseable new feeds remain pending for two empty collections and fail on the third, while feeds that have succeeded before report a later empty collection as not modified.

## Install

```bash
uv venv
source .venv/bin/activate
uv pip install -Ue .[dev]
```

## Usage

Start the RQ worker:

```bash
uv run --no-sync --frozen taranis-worker
```

Module execution remains supported for compatibility:

```bash
python -m worker
```

Or use the development script with auto-reload:

```bash
./start_dev_worker.py
```

Run the worker container healthcheck command:

```bash
uv run --no-sync --frozen taranis-worker-healthcheck --mode worker
```

Check or configure IntelOwl from a worker install/container:

```bash
uv run --no-sync --frozen taranis-intelowl-setup --url http://127.0.0.1:18080
```

## Architecture

see [docs](https://github.com/taranis-ai/taranis-ai/tree/master/doc)
