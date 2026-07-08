# IntelOwl Enrichment

## When To Load
IntelOwl, enrichment bots, IOC enrichment, observable analysis, `INTEL_OWL_BOT`, `intelowl_enrichment`, CTI information, story bot actions, report CTI.

## Expected Behavior
IntelOwl enrichment is opt-in through bot configuration. The IOC bot extracts IOC tags for CVEs, emails, IPs, domains, URLs, and hashes. IntelOwl consumes those stored news item tags instead of re-extracting observables from story or report text, with email address submission disabled unless `INTEL_OWL_EMAIL_ENRICHMENT` is true. Taranis stores only compact analyzer summaries, errors, status, and IntelOwl job links in `intelowl_enrichment`, never raw analyzer JSON or secrets.

Direct story runs remain supported. Report-level IntelOwl execution is not supported: report IntelOwl controls should not be shown, and core rejects IntelOwl report bot-action requests. IntelOwl task results upsert one enrichment row per normalized IOC `(ioc_type, value)` instead of writing story or report attributes.

Read-only CTI endpoints aggregate IOC tags and join matching enrichment rows:
- news item: tags on that news item
- story: tags across all news items in the story
- report: tags across all news items in all stories attached to the report

Analyzer selection is intentionally hardcoded by observable type in v1.

## Code Paths
- Worker bot: `src/worker/worker/bots/intelowl_bot.py`
- IOC bot: `src/worker/worker/bots/ioc_bot.py`
- Bot dispatch: `src/worker/worker/bots/bot_tasks.py`
- Enrichment table: `src/core/core/model/intelowl_enrichment.py`
- CTI response models: `src/models/models/cti.py`
- CTI aggregation service: `src/core/core/service/cti.py`
- Worker API story/enrichment reads: `src/core/core/api/worker.py`, `src/worker/worker/core_api.py`
- Manual queue endpoints: `src/core/core/api/assess.py`, `src/core/core/api/analyze.py`
- Read endpoints: `GET /api/assess/news-items/<id>/cti`, `GET /api/assess/stories/<id>/cti`, `GET /api/analyze/report-items/<id>/cti`
- Frontend CTI views: `src/frontend/frontend/views/story_views.py`, `src/frontend/frontend/views/report_views.py`, `src/frontend/frontend/templates/shared/cti_dialog.html`
- Frontend triggers: `src/frontend/frontend/templates/assess/news_item_card.html`, `src/frontend/frontend/templates/assess/story_actions.html`, `src/frontend/frontend/templates/analyze/report.html`
- Task result persistence: `src/core/core/service/task.py`
- Seeded bot/type config: `src/core/core/managers/pre_seed_data.py`, `src/models/models/types.py`

## Data Flow
Automatic runs use the bot run-order DAG when the disabled-by-default IntelOwl bot is enabled and configured. The seeded dependency is `IOC_BOT -> INTEL_OWL_BOT`, so enrichment runs only after IOC tags have been created. The DAG scheduler does not treat IntelOwl specially. Manual story runs queue `bot_task` with `story_id` or `story_ids`; report filters are rejected by the IntelOwl workflow itself. The worker deduplicates normalized IOC tags within one execution, fetches existing enrichment rows, submits only missing IOCs, refreshes pending jobs by `job_id`, polls briefly, and returns compact enrichment payloads. Core task handling persists those payloads in `intelowl_enrichment`.

## Testing
- Worker bot tests: `src/worker/worker/tests/bots/test_intelowl_bot.py`
- Core task/API tests: `src/core/tests/application/worker_pipeline/test_intelowl_enrichment.py`
- Frontend CTI/trigger tests: `src/frontend/tests/unit/views/test_report_intelowl_view.py`
- Recommended checks after Python changes: relevant `uv run pytest ...`, `uv run ruff check`, `uv run ruff format --check`, and `./dev/check_touched_pyright.sh`.

## Pitfalls
Do not log or persist IntelOwl API tokens. Do not store raw analyzer responses. Do not reintroduce report-level IntelOwl execution without an explicit product decision. Do not make analyzer/playbook selection admin-configurable without a product decision. Email address enrichment stays disabled by default because it can expose personal data to an external or shared IntelOwl instance.
