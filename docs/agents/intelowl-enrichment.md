# IntelOwl Enrichment

## When To Load

IntelOwl, IOC/CTI enrichment, `INTEL_OWL_BOT`, observable analysis, or story/report/asset CTI views.

## Contracts

- IntelOwl is opt-in and consumes stored IOC news-item tags (CVE, email, IP, domain, URL, hash), not re-extracted text. The seeded `IOC_BOT -> INTEL_OWL_BOT` dependency uses the ordinary [bot DAG](bot-run-order-dag.md).
- Store only compact final summaries, errors, status, and timestamps in `ioc`; never raw analyzer responses, job references, or secrets. Upsert by normalized IOC `value`; canonical `ioc_type` is metadata, not identity. Core retries once on concurrent unique-value insertion races.
- Story/report manual runs remain generic bot actions with item-level write checks. Deduplicate observables, reuse final rows, submit all missing jobs, then poll in shared rounds. `INTEL_OWL_POLL_TIMEOUT_SECONDS` (default 1800) bounds the batch, not each observable serially.
- Analyzer selection is fixed by observable type. Email IOCs require requested email analyzers configured on an instance approved to receive those addresses. Use `docs/intelowl.md` and `taranis-intelowl-setup` for setup; its pagination must reject cross-origin URLs before reusing tokens.
- CTI reads aggregate tags for a news item, all items in a story, or all stories in a report. Assets combine typed `asset_observables` with tags from readable linked vulnerability reports; the overview includes only readable assets/reports.
- CTI opens full pages via native links and returns through browser history. The shared renderer handles known NVD/VirusTotal/URLhaus summaries, with JSON fallback for unknown analyzers. Analyzer links allow only HTTP(S), never domain-substring validation.

## Entry Points and Coverage

- Worker: `src/worker/worker/bots/intelowl_bot.py`, `src/worker/worker/bots/ioc_bot.py`, `src/worker/worker/intelowl_taranis_setup.py`
- Core: `src/core/core/model/ioc.py`, `src/core/core/model/asset.py`, `src/core/core/service/cti.py`, `src/core/core/service/task.py`
- Contract/UI: `src/models/models/cti.py`, `src/frontend/frontend/templates/shared/cti_dialog.html`
- CTI endpoints: Assess news-items/stories, Analyze report-items, and assets (individual/overview).

Tests: `src/worker/tests/bots/test_intelowl_bot.py`, `src/core/tests/application/worker_pipeline/test_intelowl_enrichment.py`, `src/frontend/tests/unit/views/test_report_intelowl_view.py`. Setup smoke: `uv run taranis-intelowl-setup --self-test` from `src/worker`.
