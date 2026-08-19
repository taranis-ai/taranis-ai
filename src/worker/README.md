# Taranis Worker

This worker uses RQ (Redis Queue) for background task processing.

RSS sources expose collection health through their persisted task status. Responses that are not identifiable as RSS or Atom fail immediately and remain failed across a later 304 response. Parseable feeds with no entries report `NOT_MODIFIED` with an explicit empty-feed message that is preserved across later 304 responses.

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
