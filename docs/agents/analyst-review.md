# Analyst Review

## When To Load

Start analyst review, `/analyst-review/*`, `/api/assess/analyst-review/*`, Add/Dismiss/Skip, or guided Report-to-Publish handoff.

## Contracts

- Start with an incomplete Report or create one with a title and Report Type. Core supplies a fixed newest-first snapshot of Shift/Unread Story IDs; frontend stores queue/progress in user-scoped Redis with a four-hour expiry.
- Add attaches the Story, marks it read, and clears important in one core transaction, including membership-derived attributes/revisions. Dismiss marks read and clears important. Skip only advances Redis state.
- Advance Add/Dismiss only after core succeeds; failures retain the Story and progress. `A`/`D`/`S` use the shared Assess shortcut guard.
- After the queue empties, enter Report editing when requested or when the Report has a Story field or incomplete required field. Review state is valid only for that run's Report. Saving continues to Publish.
- Publish opens the sole Product already containing the Report, or a new Product with that Report preselected when there are zero/multiple matches. Delete review state at this handoff; never publish automatically.
- Preserve ordinary Assess/Report/Product flows outside a review run. The dashboard entry retains its permission gate.

## Entry Points and Coverage

Frontend: `src/frontend/frontend/views/analyst_review_views.py`, `src/frontend/frontend/templates/analyst_review/`, `src/frontend/frontend/views/report_views.py`. Core: `src/core/core/service/analyst_review.py`, `src/core/core/api/assess.py`; snapshot/type metadata in `src/core/core/model/story.py` and `src/core/core/model/report_item_type.py`.

Tests: `src/core/tests/application/user_workspace/assessment/test_assess_api.py`, `src/core/tests/application/user_workspace/analysis/test_analyze_api.py`, `src/frontend/tests/unit/views/test_analyst_review_view.py`, `src/frontend/tests/playwright/test_e2e_workflow.py`.
