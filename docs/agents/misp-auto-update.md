# MISP Auto-Update

## When To Load

MISP auto-update, MISP proposal warnings, `has_proposals`, `StoryMispAutoUpdate`, or scheduled story-to-MISP pushes.

## Expected Behavior

Auto-update configuration stores only a MISP connector and whether it is enabled. It appears in the Advanced story editor; only users with `CONNECTOR_USER_ACCESS` can change it, while other users can see its status and proposal link. Approved user and bot content mutations schedule a push after five minutes; inbound MISP changes do not. An automatic update of an unowned MISP event completes as skipped, while manual execution retains its proposal behavior. An external MISP proposal leaves auto-update enabled and stores the event URL in `has_proposals`; a successful automatic push removes that attribute. Story cards show only the enabled badge.

An empty MISP connector request timeout uses the five-second default.

## Code Paths

- Core configuration and response: `src/core/core/model/story.py`
- Scheduling: `src/core/core/service/misp_auto_update.py`
- Worker result application: `src/core/core/service/misp_story_sync.py`
- MISP push and blocked payload: `src/worker/worker/connectors/misp_connector.py` returns explicit blocked/skipped outcomes to its sender.
- UI: `src/frontend/frontend/templates/assess/story_card.html` and `src/frontend/frontend/templates/assess/story_edit_content.html`

## Data Flow

Assess, report, and bot workflow services refresh autosync jobs after successful commits for normal story/content mutations: story edits, direct news-item edits and deletions, tags, attributes, language, grouping, ungrouping, report membership/title changes, and completed bot-task results. Tag deletion also refreshes every affected story. `NewsItemConflictService` is the inbound, no-feedback boundary for conflict resolution: it uses model primitives without refreshing surviving stories and cancels jobs only for candidate stories deleted during ingestion. Story, connector, and forced source cleanup cancel jobs for deleted stories or configurations; mixed-source stories surviving forced source deletion are refreshed. Direct `/worker/stories` and `/worker/misp/stories` ingestion and outbound sync-result application continue through model paths, so they do not schedule feedback updates, but ingestion cancels jobs for stories it deletes. Bot story-update payloads cannot change auto-update configuration. The worker returns either a normal MISP sync result or a blocked result containing the MISP event URL. Core persists that URL as `has_proposals`, timestamps and revisions the story, and the frontend renders it independently of the enabled badge. Proposal lookup errors fail closed, so no automatic update is sent while proposal status is unknown. Invalid individual sync entries are ignored so other results in the task still apply.

## Testing

- Core: `src/core/tests/application/user_workspace/assessment/test_misp_auto_update.py`
- Frontend: `src/frontend/tests/unit/views/test_story_view.py`
- Worker: `src/worker/tests/connectors/test_misp_connector.py` (including aggregate blocked status and configured PyMISP timeout)
- Run focused tests from `src/core` and `src/worker` with `uv run pytest`.

## Pitfalls

`has_proposals` is shared with the MISP collector. Do not add proposal status fields or a migration for the branch-only auto-update table.

Only request MISP connectors for users with `CONNECTOR_USER_ACCESS`; core must reject configuration updates unless an explicitly authenticated user has that permission. Story list and detail serialization both include configured auto-update state for the shared story card.
