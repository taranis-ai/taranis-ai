# MISP Auto-Update

## When To Load

Scheduled MISP pushes, proposal warnings, `has_proposals`, or `StoryMispAutoUpdate`.

## Contracts

- Configuration stores connector/enabled state in the Advanced story editor. Only authenticated users with `CONNECTOR_USER_ACCESS` may change it or request connector choices; others can see status/proposal links. Bot payloads cannot change configuration.
- Approved user/bot content mutations refresh a push scheduled five minutes later. This includes story/news edits, deletion, tags (including tag deletion), attributes, language, grouping, report membership/title, and completed bot results. Only schedule after commit.
- Inbound MISP/conflict ingestion and outbound sync-result application do not schedule feedback pushes. `NewsItemConflictService` uses model primitives for this boundary; ingestion cancels jobs for deleted stories.
- Story/connector/forced-source cleanup cancels obsolete jobs; surviving mixed-source stories are refreshed after forced source deletion.
- Automatic updates of unowned events skip; manual runs retain proposal behavior. External proposals leave auto-update enabled and set the event URL in shared `has_proposals`; successful automatic pushes clear it. Proposal lookup errors fail closed.
- Worker returns explicit sync/blocked/skipped results; entirely failed execution raises curated `misp_sync_failed`. Core ignores invalid individual entries while applying other results, and timestamps/revisions proposal changes. Cards show only the enabled badge; editor status includes proposals independently.
- Empty connector timeout uses the five-second default.

## Entry Points and Coverage

`src/core/core/model/story.py`, `src/core/core/service/misp_auto_update.py`, `src/core/core/service/misp_story_sync.py`, `src/worker/worker/connectors/misp_connector.py`, `src/frontend/frontend/templates/assess/story_edit_content.html`.

Tests: `src/core/tests/application/user_workspace/assessment/test_misp_auto_update.py`, `src/frontend/tests/unit/views/test_story_view.py`, `src/worker/tests/connectors/test_misp_connector.py`.
