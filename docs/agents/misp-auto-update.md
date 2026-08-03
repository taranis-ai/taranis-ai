# MISP Auto-Update

## When To Load

MISP auto-update, MISP proposal warnings, `has_proposals`, `StoryMispAutoUpdate`, or scheduled story-to-MISP pushes.

## Expected Behavior

Auto-update configuration stores only a MISP connector and whether it is enabled. Story edits schedule a push after five minutes. An external MISP proposal leaves auto-update enabled and stores the event URL in `has_proposals`; a successful automatic push removes that attribute.

## Code Paths

- Core configuration and response: `src/core/core/model/story.py`
- Scheduling: `src/core/core/service/misp_auto_update.py`
- Worker result application: `src/core/core/service/misp_story_sync.py`
- MISP push and blocked payload: `src/worker/worker/connectors/misp_connector.py`
- UI: `src/frontend/frontend/templates/assess/story_card.html` and `src/frontend/frontend/templates/assess/story_edit_content.html`

## Data Flow

Story changes enqueue `connector_task` after five minutes. The worker returns either a normal MISP sync result or a blocked result containing the MISP event URL. Core persists that URL as `has_proposals`, which the frontend renders independently of the enabled badge.

## Testing

- Core: `src/core/tests/application/user_workspace/assessment/test_misp_auto_update.py`
- Worker: `src/worker/tests/connectors/test_misp_connector.py`
- Run focused tests from `src/core` and `src/worker` with `uv run pytest`.

## Pitfalls

`has_proposals` is shared with the MISP collector. Do not add proposal status fields or a migration for the branch-only auto-update table.
