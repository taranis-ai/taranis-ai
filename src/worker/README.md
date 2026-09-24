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

## Shared LLM settings

Chat, story clustering, and summarization share **Admin Settings > LLM Endpoints**. Add a named provider/model with a base URL, API format (`responses` or `chat_completions`), optional API key, and timeout. Select a default endpoint and optional feature overrides. Summarization and title generation share one assignment.

Clustering and summarization run the installed `taranis-llm-bot` library directly. Workers fetch the effective endpoint from Core once per bot run; settings changes apply to the next run without restarting. The bot's optional `REQUESTS_TIMEOUT` takes precedence over the endpoint timeout. Worker `LLM_*` environment values and legacy clustering/summary service endpoints no longer select these providers.

NER, sentiment analysis, and cybersecurity classification still use the standalone `llm-bot` service and its configuration. Workers must be able to reach the configured providers. Missing shared configuration fails the affected job with a setup message; there is no implicit environment fallback.

Clustering sends only story IDs, summaries, and tags; full news-item text is not used. Configure upstream enrichment as needed.

## Architecture

see [docs](https://github.com/taranis-ai/taranis-ai/tree/master/doc)
