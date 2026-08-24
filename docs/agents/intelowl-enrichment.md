# IntelOwl Enrichment

## When To Load
IntelOwl, enrichment bots, IOC enrichment, observable analysis, `INTEL_OWL_BOT`, `ioc`, CTI information, story bot actions, report CTI.

## Expected Behavior
IntelOwl enrichment is opt-in through bot configuration. The IOC bot extracts IOC tags for CVEs, emails, IPs, domains, URLs, and hashes. IntelOwl consumes those stored news item tags instead of re-extracting observables from story or report text. Email tags are submitted like other IOC tags; email enrichment succeeds only when IntelOwl has at least one requested email analyzer enabled and configured. Taranis stores only compact final analyzer summaries, errors, status, and timestamps in `ioc`, never IntelOwl job references, raw analyzer JSON, or secrets.

Direct story and report runs remain supported. Report-level UI controls should stay generic rather than IntelOwl-specific. IntelOwl task results use `ioc_type` as their canonical type field and upsert one enrichment row per normalized IOC `value` instead of writing story or report attributes; `ioc_type` is metadata.

Read-only CTI endpoints aggregate IOC tags and asset observables, then join matching enrichment rows:
- news item: tags on that news item
- story: tags across all news items in the story
- report: tags across all news items in all stories attached to the report
- asset: typed `asset_observables` plus tags across readable vulnerability reports linked to the asset
- assets overview: typed `asset_observables` plus tags across readable vulnerability reports linked to all readable assets

Analyzer selection is intentionally hardcoded by observable type in v1. Batch executions submit all missing observables before polling outstanding IntelOwl jobs in shared rounds, so the configured poll timeout bounds the batch rather than applying serially to every observable.

## Code Paths
- Worker bot: `src/worker/worker/bots/intelowl_bot.py`
- IntelOwl operator docs: `docs/intelowl.md`
- IntelOwl config/setup script: `src/worker/worker/intelowl_taranis_setup.py` exposed as `taranis-intelowl-setup`
- IOC bot: `src/worker/worker/bots/ioc_bot.py`
- Bot dispatch: `src/worker/worker/bots/bot_tasks.py`
- Enrichment table: `src/core/core/model/ioc.py`
- Asset observables table: `src/core/core/model/asset.py`
- CTI response models: `src/models/models/cti.py`
- CTI aggregation service: `src/core/core/service/cti.py`
- Worker API story/enrichment reads: `src/core/core/api/worker.py`, `src/worker/worker/core_api.py`
- Manual queue endpoints: `src/core/core/api/assess.py`, `src/core/core/api/analyze.py`
- Read endpoints: `GET /api/assess/news-items/<id>/cti`, `GET /api/assess/stories/<id>/cti`, `GET /api/analyze/report-items/<id>/cti`, `GET /api/assets/<id>/cti`, `GET /api/assets/cti`
- Frontend CTI views: `src/frontend/frontend/views/story_views.py`, `src/frontend/frontend/views/report_views.py`, `src/frontend/frontend/views/asset_views.py`, `src/frontend/frontend/templates/shared/cti_dialog.html`
- Frontend triggers: `src/frontend/frontend/templates/assess/news_item_card.html`, `src/frontend/frontend/templates/assess/story_actions.html`, `src/frontend/frontend/templates/analyze/report.html`, `src/frontend/frontend/templates/assets/asset.html`
- Task result persistence: `src/core/core/service/task.py`
- Seeded bot/type config: `src/core/core/managers/pre_seed_data.py`, `src/models/models/types.py`

## Data Flow
Automatic runs use the bot run-order DAG when the disabled-by-default IntelOwl bot is enabled and configured. The seeded dependency is `IOC_BOT -> INTEL_OWL_BOT`, so enrichment runs only after IOC tags have been created. The DAG scheduler does not treat IntelOwl specially. Manual story and report runs queue `bot_task` with `story_id`, `story_ids`, or `report_ids` after core verifies item-level write access. The worker deduplicates normalized IOC tags within one execution, fetches existing final IOC rows, submits all missing IOCs, polls the outstanding jobs in shared rounds for up to `INTEL_OWL_POLL_TIMEOUT_SECONDS` (default `1800`), and returns compact final enrichment payloads. Core task handling batch-fetches existing rows and retries once if concurrent IOC insertion races with the unique value constraint.

Frontend CTI routes render normal full-page views and CTI entry points should use plain `<a href="...">` links, not modal-targeted HTMX requests. The CTI Back button uses browser history so users return to the page and state from which they opened CTI. The shared template has compact analyzer-specific rendering for NVD CVE, VirusTotal observable, and URLhaus no-result payloads, with raw JSON as the fallback for unknown analyzers.
Analyzer-provided CTI links are rendered only for `http` and `https` URLs.

## Testing
- Worker bot tests: `src/worker/worker/tests/bots/test_intelowl_bot.py`
- Core task/API tests: `src/core/tests/application/worker_pipeline/test_intelowl_enrichment.py`
- Frontend CTI/trigger tests: `src/frontend/tests/unit/views/test_report_intelowl_view.py`
- IntelOwl config/setup smoke test: `cd src/worker && uv run taranis-intelowl-setup --self-test`
- Recommended checks after Python changes: relevant `uv run pytest ...`, `uv run ruff check`, `uv run ruff format --check`, and `./dev/check_touched_pyright.sh`.

## Pitfalls
Do not log or persist IntelOwl API tokens. Do not store raw analyzer responses. Do not add report-level IntelOwl-specific UI controls without an explicit product decision. Do not make analyzer/playbook selection admin-configurable without a product decision. Use `docs/intelowl.md` and `taranis-intelowl-setup` for operator-side IntelOwl setup instead of changing Taranis analyzer selection; the setup helper trims supplied string config values before writing them to IntelOwl and rejects cross-origin pagination URLs before reusing the API token. Do not validate external analyzer links with domain substring checks; keep them scheme-gated or use URL parsing. Enable IntelOwl email analyzers only on instances approved to receive email address IOCs.
