# IntelOwl Enrichment

## When To Load
IntelOwl, enrichment bots, IOC enrichment, observable analysis, `INTEL_OWL_BOT`, `intelowl_enrichment`, report enrichment, story/report bot actions.

## Expected Behavior
IntelOwl enrichment is opt-in through bot configuration. The bot submits CVEs, emails, IPs, domains, URLs, and hashes to IntelOwl using `pyintelowl`, with email address submission disabled unless `INTEL_OWL_EMAIL_ENRICHMENT` is true. Taranis stores only compact summaries and IntelOwl job links, never raw analyzer JSON.

Direct story runs store a story attribute named `intelowl_enrichment` and also mark the story with `INTEL_OWL_BOT` execution metadata so automatic runs do not resubmit the same story. Report runs update the configured report attribute title only when that attribute already exists on the report; otherwise results remain visible in task history.

Analyzer selection is intentionally hardcoded by observable type in v1.

## Code Paths
- Worker bot: `src/worker/worker/bots/intelowl_bot.py`
- Bot dispatch: `src/worker/worker/bots/bot_tasks.py`
- Worker API story/report reads: `src/core/core/api/worker.py`, `src/worker/worker/core_api.py`
- Manual queue endpoints: `src/core/core/api/assess.py`, `src/core/core/api/analyze.py`
- Frontend triggers: `src/frontend/frontend/views/story_views.py`, `src/frontend/frontend/views/report_views.py`, `src/frontend/frontend/templates/assess/story_edit_content.html`, `src/frontend/frontend/templates/assess/assess_top_bar.html`, `src/frontend/frontend/templates/analyze/report.html`, `src/frontend/frontend/templates/analyze/report_table.html`
- Task result persistence: `src/core/core/service/task.py`
- Seeded bot/type config: `src/core/core/managers/pre_seed_data.py`, `src/models/models/types.py`

## Data Flow
Automatic runs use the existing post-collection bot chain when the disabled-by-default IntelOwl bot is enabled and configured. Manual story/report runs queue `bot_task` with `story_id`, `story_ids`, or `report_ids`. The worker deduplicates normalized observables within one execution, submits each observable once to IntelOwl, and returns summary-only task data. Core task handling persists story/report summaries after successful task submission.

## Testing
- Worker bot tests: `src/worker/worker/tests/bots/test_intelowl_bot.py`
- Core task/API tests: `src/core/tests/application/worker_pipeline/test_intelowl_enrichment.py`
- Frontend trigger tests: `src/frontend/tests/unit/views/test_report_intelowl_view.py`
- Recommended checks after Python changes: relevant `uv run pytest ...`, `uv run ruff check`, `uv run ruff format --check`, and `./dev/check_touched_pyright.sh`.

## Pitfalls
Do not log or persist IntelOwl API tokens. Do not store raw analyzer responses. Do not make analyzer/playbook selection admin-configurable without a product decision. Email address enrichment stays disabled by default because it can expose personal data to an external or shared IntelOwl instance.
