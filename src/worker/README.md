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

Set `OTEL_EXPORTER_OTLP_ENDPOINT` to an OTLP/HTTP base URL to export an RQ consumer span, completed-job count, and duration histogram for every job. Trace context received through RQ metadata is propagated to worker calls back into core. Leave the endpoint unset to disable telemetry.

Check or configure IntelOwl from a worker install/container:

```bash
uv run --no-sync --frozen taranis-intelowl-setup --url http://127.0.0.1:18080
```

## Architecture

see [docs](https://github.com/taranis-ai/taranis-ai/tree/master/doc)
