# Taranis Worker

This worker uses RQ (Redis Queue) for background task processing.

RSS sources expose collection health through their persisted task status. Responses that are not identifiable as RSS or Atom fail immediately and remain failed across a later 304 response. Parseable feeds with no entries report `NOT_MODIFIED` with an explicit empty-feed message that is preserved across later 304 responses.

Collectors using the shared HTTP request helper (including RSS, Simple Web, and RT) report guidance for connection failures and timeouts to check worker-container DNS, network access, and `PROXY_SERVER`. Read timeouts can occur after a connection succeeds. Technical exception details stay in worker logs at ERROR level, with tracebacks available at DEBUG level. Connection and timeout diagnostics remain HTTP request exceptions, preserving RT’s existing per-item error handling. This does not add automatic retries; see [deployment troubleshooting](../../deploy/README.md#collector-network-errors).

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

## Story clustering

Story clustering runs through the installed `taranis-llm-bot` Python library and calls the LLM provider directly. Other LLM bot functions continue using the `llm-bot` HTTP service.

Set `LLM_BASE_URL` and, when required by your provider, `LLM_API_KEY` in the worker environment or its private `.env` before startup. Set `LLM_MODEL` if the provider requires a model. `LLM_API_MODE` defaults to `responses`; use `chat_completions` for providers exposing that API. `LLM_TIMEOUT` defaults to 120 seconds, with the bot's `REQUESTS_TIMEOUT` taking precedence. Restart workers after changing these settings.

Clustering uses only story IDs, summaries, and tags. Configure upstream enrichment as needed; full news-item text is not used. Existing clustering `BOT_ENDPOINT`, `BOT_API_KEY`, and `STORY_API_ENDPOINT` settings are ignored. Provider credentials belong in `LLM_API_KEY`, not the legacy bot key. The Compose worker receives the shared `LLM_*` settings automatically; custom worker deployments must supply them explicitly.

## Architecture

see [docs](https://github.com/taranis-ai/taranis-ai/tree/master/doc)
