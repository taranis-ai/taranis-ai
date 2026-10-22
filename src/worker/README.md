# Taranis Worker

This worker uses RQ (Redis Queue) for background task processing.

Worker and cron Redis clients use RESP2 to keep maintenance-notification probes disabled when RQ rebuilds scheduler or spawned-worker connections.

RSS sources expose collection health through their persisted task status. Responses that are not identifiable as RSS or Atom fail immediately and remain failed across a later 304 response. Parseable feeds with no entries report `NOT_MODIFIED` with an explicit empty-feed message that is preserved across later 304 responses.

Collectors using the shared HTTP request helper (including RSS, Simple Web, and RT) report guidance for connection failures and timeouts to check worker-container DNS, network access, and `PROXY_SERVER`. Read timeouts can occur after a connection succeeds. Technical exception details stay in worker logs at ERROR level, with tracebacks available at DEBUG level. Connection and timeout diagnostics remain HTTP request exceptions, preserving RT’s existing per-item error handling. This does not add automatic retries; see [deployment troubleshooting](../../deploy/README.md#collector-network-errors).

On initial collection, collectors prefer feed/RT images, then declared website icons (Apple touch icons first), then conventional root icons. Downloads share a five-second budget and four request slots; failures do not fail collection. Core validates accepted images, and existing icons are not automatically refreshed. Icon requests honor source proxies and private hosts, while stripping source credentials across origins. See [HTTP client contracts](../../docs/agents/http-clients.md) for network and discovery limits.

Email, FTP, and SFTP publishers use `NETWORK_TIMEOUT` (default: 30 seconds) for network inactivity. Saving a preset rejects explicit or default values above half a positive core `RQ_DEFAULT_JOB_TIMEOUT` (900 seconds with the default 1800-second job timeout); errors show the maximum and required job timeout. Execution also caps the effective value at half the actual job timeout, including existing presets.

Timeout failures identify the stalled operation; RQ deadlines and killed workers produce generic safe failures. This is not a total publishing deadline: DNS resolution, cumulative delays, waits outside socket timeouts, and transfers that keep making progress can still reach the RQ timeout. Publishers do not retry automatically.

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

NER, sentiment, topic classification, clustering, and summarization/titles use the installed `taranis-llm-bot` library. Configure providers in **Admin Settings > LLM Endpoints**. Core includes the resolved provider in each job's bot configuration: bot selection, then feature assignment, then shared default. Changes apply on the next run; `REQUESTS_TIMEOUT` overrides the endpoint timeout.

Workers must reach the selected providers. Missing configuration fails the job with a setup message. Clustering sends only story IDs, summaries, and tags; topic classification uses the Decisions API in `taranis-llm-bot==0.1.6`. Enable **Decisions** on the assigned endpoint, select **System One (vLLM / llama.cpp)**, **OpenRouter**, or **OpenAI** under **Decisions API format**, and set its model. The same provider can also enable Responses or Chat Completions with another model and shared credentials. Use a full URL override if Decisions lives outside the provider base path. For example, OpenRouter uses `https://openrouter.ai/api/alpha/decisions`; compatible local providers use `/v1/systemone` or `/v1/decisions`. Other LLM features continue to use Responses or Chat Completions. Classification does not support OpenRouter batch processing. It saves the highest-scoring topic and all eight probabilities on each news item, with the most common topic on its story (ties follow library category order). Empty content clears old topic results without an inference. Categories are disinformation, security incident, vulnerability, threat intelligence, security policy, security news, general news, and other. Disinformation is a topic, not a truth verdict. The old binary threshold is unused.

NER, wordlist, IOC, and regex tagging save each nonempty news-item tag result immediately through Core’s tag update API. Saved tags survive a later bot or pipeline failure; empty results need no upload, and failed uploads stop the run with `tag_save_failed`. Each successful upload advances the expected story revision. Other bot changes are staged and submitted to Core with those expected revisions. DAG pipelines share one story snapshot and commit the staged changes together. Story tags are derived from news-item tags; the pipeline refreshes its derived tag snapshot after tagging and grouping so later clustering stages see all merged tags. Post-collection runs select only new or changed story IDs; empty collections enqueue no bots. Within that scope, each bot type skips stories carrying its completion attribute. Core records completion only when results commit, including successful runs with no findings; collection changes clear these attributes. Explicit manual selections can force reruns.

Queued LLM/tagging bots and all DAG pipelines checkpoint their configuration, story context, completed stages, saved tag items, and completed LLM responses in private Redis job metadata. A job execution timeout immediately requeues the same job, resuming from the checkpoint without repeating completed inferences or saved tag uploads. Three consecutive execution timeouts without checkpoint progress stop the run with a failure. Request timeouts and other errors remain failures. Only the final outcome is written to My Tasks; attempts remain visible in RQ results and worker logs. Redis restart loses pending runs and checkpoints.

`REQUESTS_TIMEOUT` controls only network requests. `EXECUTION_TIMEOUT` supplies the bot's per-attempt job budget, falling back to Core's `RQ_DEFAULT_JOB_TIMEOUT` (default: 1800 seconds, 30 minutes). Pipeline deadlines combine those budgets with 20% headroom and share them across stages; four default bots have a 144-minute attempt budget. These remain total execution deadlines rather than inactivity timers. OpenRouter batch stages pause and retry separately while waiting for the provider. See [LLM Endpoints](../../docs/agents/llm-endpoints.md) for provider and batch limitations.

## Architecture

See [Architecture and Boundaries](../../docs/agents/architecture-and-boundaries.md).
