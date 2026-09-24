# Story Clustering

## When To Load

Story bot inputs, clustering execution, or LLM provider configuration.

## Contract

`src/worker/worker/bots/story_bot.py` calls `llm_bot.tasks.cluster.cluster_stories` from the pinned `taranis-llm-bot` dependency inside the synchronous RQ job using `asyncio.run`. Clustering and summarization/title generation use the library; NER, sentiment, and classification still call the bot HTTP service.

The dependency uses the published `taranis-llm-bot==0.1.2` release, which fixes Pydantic `schema` field-shadowing warnings without worker-side warning suppression.

Each `ClusterRequest` story contains only its original non-empty `id`, name-keyed `tags` dictionary, and nullable `summary`. Missing tags default to `{}`. Each tag requires `tag_type`. News-item content and other story fields are discarded before entering the library. The library constructs the prompt, truncates summaries, validates cluster membership, and maps its temporary numeric IDs back to original story IDs. Only clusters with multiple stories reach Core's grouping endpoint; singleton-only results report no clusters. Empty input skips the LLM call.

Provider configuration comes from **Admin Settings > LLM Endpoints** via the authenticated, non-cacheable worker API on every run. Explicit feature assignment takes precedence over the shared default; missing configuration fails with a setup message. `REQUESTS_TIMEOUT` overrides the endpoint timeout. Persisted `BOT_ENDPOINT` and `BOT_API_KEY` remain accepted for compatibility but are unused. No worker environment fallback or restart is needed. See [LLM Endpoints](llm-endpoints.md).


Provider transport/HTTP errors become the existing retryable `bot_service_unavailable` failure. Invalid input/output and other library errors fail the job with a static message. Details stay in server logs and underlying exception chains are suppressed. The library can attempt one repair of invalid model output. Queue identity, filters, scheduling, and dependency execution retain the existing bot UUID workflow.

Coverage: `src/worker/tests/bots/test_bots.py::test_story_bot_clusters_via_library` runs the real library request/prompt/parser path with only the provider response mocked, verifies reduced input, provider settings, original-ID grouping, singleton-only results, and empty input. `src/worker/tests/bots/test_bot_tasks.py::TestBotTask::test_story_clustering_failure_is_safe` checks real task failure persistence for provider errors and invalid output. These tests do not assess live model quality.
