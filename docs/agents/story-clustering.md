# Story Clustering

## When To Load

Story bot inputs, clustering execution, or grouping results.

## Contract

`src/worker/worker/bots/story_bot.py` runs `llm_bot.tasks.cluster.cluster_stories` from the locked `taranis-llm-bot` dependency inside the synchronous RQ job via `asyncio.run`. Provider resolution and failure handling follow [LLM Endpoints](llm-endpoints.md).

Each `ClusterRequest` story contains its original non-empty `id`, name-keyed `tags` dictionary, and nullable `summary`. Missing tags default to `{}`; each tag requires `tag_type`. News-item content and other fields are discarded. The library builds the prompt, truncates summaries, validates membership, and maps temporary numeric IDs back to original story IDs.

Only clusters with multiple stories reach Core's grouping endpoint. Singleton-only results report no clusters; empty input skips inference. Invalid input/output fails with a static message. The library can attempt one output repair. Queue identity, filters, scheduling, and dependencies use the existing bot UUID workflow.

## Coverage

`src/worker/tests/bots/test_bots.py::test_story_bot_clusters_via_library` exercises real library prompts/parsing with mocked provider responses: reduced input, populated/empty tags and summaries, timeout selection, original-ID grouping, singleton results, and empty input. `test_llm_bot_failure_is_safe` in `tests/bots/test_bot_tasks.py` covers persisted provider/output failures. These tests do not assess live model quality.
