# MISP Auto-Update

## When To Load

MISP auto-update, MISP proposal warnings, `has_proposals`, `StoryMispAutoUpdate`, or scheduled story-to-MISP pushes.

## Expected Behavior

Auto-update configuration stores only a MISP connector and whether it is enabled. It appears in the Advanced story editor; only users with `CONNECTOR_USER_ACCESS` can change it, while other users can see its status and proposal link. Approved user and bot content mutations schedule a push after five minutes; inbound MISP changes do not. An external MISP proposal leaves auto-update enabled and stores the event URL in `has_proposals`; a successful automatic push removes that attribute. Story cards show only the enabled badge.

## Code Paths

- Core configuration and response: `src/core/core/model/story.py`
- Scheduling: `src/core/core/service/misp_auto_update.py`
- Worker result application: `src/core/core/service/misp_story_sync.py`
- MISP push and blocked payload: `src/worker/worker/connectors/misp_connector.py` returns explicit blocked/skipped outcomes to its sender.
- UI: `src/frontend/frontend/templates/assess/story_card.html` and `src/frontend/frontend/templates/assess/story_edit_content.html`

## Data Flow

Assess and bot entry points schedule autosync after successful commits for normal story/content mutations: story edits, direct news-item edits and deletion, tags, attributes, language, grouping, and ungrouping. The dedicated `/worker/misp/stories` ingestion endpoint does not schedule, and lower-level mutation methods do not inspect origin. Applying outbound sync results also does not schedule another update. Origin is never inferred from `last_change`. The worker returns either a normal MISP sync result or a blocked result containing the MISP event URL. Core persists that URL as `has_proposals`, timestamps and revisions the story, and the frontend renders it independently of the enabled badge. Proposal lookup errors fail closed, so no automatic update is sent while proposal status is unknown. Invalid individual sync entries are ignored so other results in the task still apply.

## Testing

- Core: `src/core/tests/application/user_workspace/assessment/test_misp_auto_update.py`
- Frontend: `src/frontend/tests/unit/views/test_story_view.py`
- Worker: `src/worker/tests/connectors/test_misp_connector.py` (including aggregate blocked status and configured PyMISP timeout)
- Run focused tests from `src/core` and `src/worker` with `uv run pytest`.

## Pitfalls

`has_proposals` is shared with the MISP collector. Do not add proposal status fields or a migration for the branch-only auto-update table.

Only request MISP connectors for users with `CONNECTOR_USER_ACCESS`; core must reject direct configuration updates without that permission.
