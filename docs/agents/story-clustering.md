# Story Clustering

## When To Load

Story bot inputs, clustering execution, or LLM provider configuration.

## Contract

`src/worker/worker/bots/story_bot.py` calls `llm_bot.tasks.cluster.cluster_stories` from the pinned `taranis-llm-bot` dependency inside the synchronous RQ job using `asyncio.run`. Only story clustering uses the library; other LLM bot functions still call the bot HTTP service.

Each `ClusterRequest` story contains only its original non-empty `id`, name-keyed `tags` dictionary, and nullable `summary`. Missing tags default to `{}`. Each tag requires `tag_type`. News-item content and other story fields are discarded before entering the library. The library constructs the prompt, truncates summaries, validates cluster membership, and maps its temporary numeric IDs back to original story IDs. Only clusters with multiple stories reach Core's grouping endpoint; singleton-only results report no clusters. Empty input skips the LLM call.

The library reads `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_API_MODE` (default `responses`), and `LLM_TIMEOUT` (default 120 seconds) from the worker environment or `.env` at import time. `REQUESTS_TIMEOUT` overrides the provider timeout for an individual bot. Persisted `BOT_ENDPOINT` and `BOT_API_KEY` remain accepted for configuration compatibility but are unused for clustering; `STORY_API_ENDPOINT` is no longer used. Restart workers after changing provider settings.

Provider transport/HTTP errors become the existing retryable `bot_service_unavailable` failure. Invalid input/output and other library errors fail the job with a static message. Details stay in server logs and underlying exception chains are suppressed. The library can attempt one repair of invalid model output. Queue identity, filters, scheduling, and dependency execution retain the existing bot UUID workflow.

Coverage: `src/worker/tests/bots/test_bots.py::test_story_bot_clusters_via_library` runs the real library request/prompt/parser path with only the provider response mocked, verifies reduced input, provider settings, original-ID grouping, singleton-only results, and empty input. `src/worker/tests/bots/test_bot_tasks.py::TestBotTask::test_story_clustering_failure_is_safe` checks real task failure persistence for provider errors and invalid output. These tests do not assess live model quality.
