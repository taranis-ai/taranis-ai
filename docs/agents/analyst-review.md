# Analyst Review

## When To Load

Load this memory for the dashboard **Start analyst review** card, `/analyst-review/*` frontend routes, `/api/assess/analyst-review/*` endpoints, Add/Dismiss/Skip triage, or the guided Report-to-Publish handoff.

## Expected Behavior

- Starting a run selects an incomplete Report or creates one from a title and Report Type.
- Each run uses a fixed, newest-first snapshot of Stories matching Shift and Unread at start time.
- The review page shows one Story at a time. Add attaches it to the active Report, marks it read, and clears important. Dismiss marks it read and clears important. Skip has no persistent Story effect.
- Add and Dismiss advance only after the core mutation succeeds. Core applies each Add as one database transaction across Story status, Report membership, membership-derived attributes, and revisions.
- The `A`, `D`, and `S` shortcuts use the shared Assess shortcut guard, so they do not fire while typing or while a dialog is open.
- Runs enter the Report step when requested or when the Report has a Story field or an incomplete required field. Saving that step continues to Publish.
- Publish opens the sole existing Product that already contains the Report. With zero or multiple matches it opens a new Product with the Report preselected. It never publishes automatically.

## Code Paths

- Frontend orchestration: `src/frontend/frontend/views/analyst_review_views.py`
- Frontend routes: `src/frontend/frontend/router/assess.py`
- Start/review templates: `src/frontend/frontend/templates/analyst_review/`
- Dashboard entry: `src/frontend/frontend/views/dashboard_views.py`, `src/frontend/frontend/templates/dashboard/user_item_cards.html`
- Report handoff: `src/frontend/frontend/views/report_views.py`, `src/frontend/frontend/templates/analyze/report.html`
- Core API and transaction: `src/core/core/api/assess.py`, `src/core/core/service/analyst_review.py`
- Snapshot and Report Type metadata: `src/core/core/model/story.py`, `src/core/core/model/report_item_type.py`
- Shared API models: `src/models/models/assess.py`, `src/models/models/report.py`

## Data Flow

The frontend asks core for the Shift/Unread Story IDs once, then stores the ordered IDs and progress under a user-scoped Redis key with a four-hour expiry. Add and Dismiss call the dedicated core action endpoint; Skip only advances Redis state. Core publishes the usual realtime and cache-invalidation events after successful mutations. When the queue is empty, frontend state carries the active Report through an optional Report edit and is deleted when Publish is reached.

## Testing

- Core behavior: `src/core/tests/application/user_workspace/assessment/test_assess_api.py`
- Report Type metadata: `src/core/tests/application/user_workspace/analysis/test_analyze_api.py`
- Frontend queue behavior: `src/frontend/tests/unit/views/test_analyst_review_view.py`
- Browser workflow: `src/frontend/tests/playwright/test_e2e_workflow.py`
- Finish feature work with `./dev/test_push_signoff.sh` as required by the development workflow.

## Pitfalls

- Keep the queue server-side and user-scoped; a client-provided Story list would weaken snapshot stability and authorization.
- Do not split Add into separate Report and Story requests. Partial success would violate the triage contract.
- A failed core action must render the same Story and leave progress unchanged.
- Report review state is valid only after the queue is empty and only for the Report bound to that run.
- Preserve ordinary Assess, Report, and Product routes when no review run is present.
