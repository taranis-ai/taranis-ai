# Story Clustering

## When To Load

Story bot request payloads or external clustering integration.

## Contract

`src/worker/worker/bots/story_bot.py` serializes each story through `StoryBotPayload` before posting to the clustering service. The `stories` list contains only `tags` and `summary`; all other fields, including IDs and news-item content, are discarded. Tags retain the worker API's name-keyed dictionary structure. Missing tags default to `{}` and missing or null summaries serialize as `null`.

The response handling still expects `cluster_ids.event_clusters` containing story IDs for core's grouping endpoint. The external clustering service is maintained separately; compatibility with the reduced request must be verified there.

Coverage: `src/worker/tests/bots/test_bots.py::test_story_bot_sends_only_tags_and_summary` checks the outgoing HTTP JSON using a full story fixture.
