# Story Clustering

Load for: Story bot inputs, clustering execution, or grouping results.

## Contracts

`src/worker/worker/bots/story_bot.py` prepares one `llm_bot.tasks.cluster.prepare_cluster` task for the full selected story list using the locked `taranis-llm-bot` dependency. The shared worker runner either runs that task immediately via `asyncio.run` or submits it to OpenRouter batch processing and resumes the RQ job when its result arrives. Provider resolution and failure handling follow [LLM Endpoints](llm-endpoints.md).

Each `ClusterRequest` story contains its original non-empty `id`, name-keyed `tags` dictionary, and nullable `summary`. Missing tags default to `{}`; each tag requires `tag_type`. News-item content and other fields are discarded. The library builds the prompt, truncates summaries, validates membership, and maps temporary numeric IDs back to original story IDs.

Only clusters with multiple stories are staged for Core's final bot-result submission. The pipeline applies those groups to its shared context so later bots see merged news items before the Core transaction. The pipeline recomputes the survivor’s derived tag map from those items after grouping, preserving source-only tags in subsequent clustering input. Singleton-only results report no clusters; empty input skips inference. Invalid input/output fails with a static message. Immediate execution can attempt one output repair; invalid batch output fails without a repair request. Queue identity, filters, scheduling, and dependencies use the bot UUID workflow.

Core marks the surviving processed stories complete when the staged run commits, including singleton-only results. Later automatic runs skip these stories until collection changes their content or membership; explicit manual selections can force a rerun.

## Coverage

`src/worker/tests/bots/test_bots.py::test_story_bot_clusters_via_library` covers real prompts/parsing with mocked responses, reduced inputs, original IDs, empty/singleton results, and timeouts. `tests/bots/test_bot_tasks.py::test_llm_bot_failure_is_safe` covers persisted failures. Neither establishes live model quality.
