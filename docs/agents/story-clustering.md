# Story Clustering

## When To Load

Story bot request payloads or external clustering integration.

## Contract

`src/worker/worker/bots/story_bot.py` serializes each story through `StoryBotPayload` before posting to the clustering service. The `stories` list contains only `id`, `tags`, and `summary`; all other fields, including news-item content, are discarded. Each story must retain its non-empty original `id` so the service can return cluster membership. Tags retain the worker API's name-keyed dictionary structure. Missing tags default to `{}` and missing or null summaries serialize as `null`.

The response must contain `cluster_ids.event_clusters` as lists of those original story IDs for core's grouping endpoint. The external clustering service must support the reduced request: `taranis-ai/llm-bot` at `616dd73fb550639a2f241c3cc2eb95a1f69697f7` still requires `news_items`, so that version is incompatible even with IDs preserved.

Coverage: `src/worker/tests/bots/test_bots.py::test_story_bot_preserves_ids_in_reduced_payload` checks the outgoing HTTP JSON using full story fixtures, returns cluster membership from the transmitted IDs, verifies the grouping request, and preserves the no-cluster behavior. It does not run the external clustering service.
