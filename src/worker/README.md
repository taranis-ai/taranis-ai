# Taranis Worker

This worker uses RQ (Redis Queue) for background task processing.

RSS sources expose collection health through their persisted task status. Responses that are not identifiable as RSS or Atom fail immediately and remain failed across a later 304 response. Parseable feeds with no entries report `NOT_MODIFIED` with an explicit empty-feed message that is preserved across later 304 responses.

Collectors using the shared HTTP request helper (including RSS, Simple Web, and RT) report guidance for connection failures and timeouts to check worker-container DNS, network access, and `PROXY_SERVER`. Read timeouts can occur after a connection succeeds. Technical exception details stay in worker logs at ERROR level, with tracebacks available at DEBUG level. Connection and timeout diagnostics remain HTTP request exceptions, preserving RT’s existing per-item error handling. This does not add automatic retries; see [deployment troubleshooting](../../deploy/README.md#collector-network-errors).

Email, FTP, and SFTP publishers use `NETWORK_TIMEOUT` (default: 30 seconds) for network inactivity. Saving a preset rejects explicit or default values above half a positive core `RQ_DEFAULT_JOB_TIMEOUT` (90 seconds with the default 180-second job timeout); errors show the maximum and required job timeout. Execution also caps the effective value at half the actual job timeout, including existing presets.

Timeout failures identify the stalled operation; RQ deadlines and killed workers produce generic safe failures. This is not a total publishing deadline: DNS resolution, cumulative delays, waits outside socket timeouts, and transfers that keep making progress can still reach the RQ timeout. Publishers do not retry automatically.

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
