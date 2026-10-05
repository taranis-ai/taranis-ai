# Taranis Worker

This worker uses RQ (Redis Queue) for background task processing.

RSS sources expose collection health through their persisted task status. Responses that are not identifiable as RSS or Atom fail immediately and remain failed across a later 304 response. Parseable feeds with no entries report `NOT_MODIFIED` with an explicit empty-feed message that is preserved across later 304 responses.

Collectors using the shared HTTP request helper (including RSS, Simple Web, and RT) report guidance for connection failures and timeouts to check worker-container DNS, network access, and `PROXY_SERVER`. Read timeouts can occur after a connection succeeds. Technical exception details stay in worker logs at ERROR level, with tracebacks available at DEBUG level. Connection and timeout diagnostics remain HTTP request exceptions, preserving RT’s existing per-item error handling. This does not add automatic retries; see [deployment troubleshooting](../../deploy/README.md#collector-network-errors).

Email, FTP, and SFTP publisher presets use `NETWORK_TIMEOUT` (30 seconds by default) for network inactivity. A running RQ job caps the effective value at half a finite positive job timeout. Publishers log network operations and raise curated timeout failures identifying the operation that stalled. No publisher phase state is saved in Redis; RQ deadlines and killed workers produce generic safe failures. This setting is not a total publishing deadline: DNS resolution, cumulative delays, library waits outside socket timeouts, and transfers that continue making progress may still reach the RQ timeout. No automatic retries are added.

## Install

```bash
uv sync --all-extras --dev
```

## Usage

Start the RQ worker:

```bash
uv run --no-sync --frozen taranis-worker
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

NER, sentiment, cybersecurity classification, clustering, and summarization/titles use the installed `taranis-llm-bot` library. Configure providers in **Admin Settings > LLM Endpoints**. Core includes the resolved provider in each job's bot configuration: bot selection, then feature assignment, then shared default. Changes apply on the next run; `REQUESTS_TIMEOUT` overrides the endpoint timeout.

Workers must reach the selected providers. Missing configuration fails the job with a setup message. Clustering sends only story IDs, summaries, and tags; classification uses the bot's `CLASSIFICATION_THRESHOLD`.

## Architecture

See [Architecture and Boundaries](../../docs/agents/architecture-and-boundaries.md).
