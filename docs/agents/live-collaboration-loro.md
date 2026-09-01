# Loro Live Collaboration

## When To Load

Loro documents, collaboration channels, peer synchronization, collaborative story/report editing, document presence, or the `collab:` Centrifugo namespace.

## Expected Behavior

Collaborative text is stored in Loro documents, accepted updates are durable in Redis before publication, PostgreSQL stores checkpoints, and peer synchronization is best effort. Users may edit existing documents while disconnected; owner-controlled structural and scalar actions are durable pending intents. Reconnection submits intents against the owner metadata version, preserves owner state on conflicts, and requires explicit contributor resolution before finalization.

## Code Paths

- Core models: `src/core/core/model/collaboration_channel.py`, `collaboration_document.py`
- Core store/API: `src/core/core/service/collaboration_loro.py`, `collaboration_projection.py`, `src/core/core/api/collaboration.py`
- Realtime authorization: `src/core/core/api/realtime.py`
- Worker checkpoint/federation jobs: `src/worker/worker/misc/misc_tasks.py`
- Frontend workspace/editor: `src/frontend/frontend/router/collaboration.py`, `frontend/views/collaboration_views.py`, `frontend/static/js/collaboration.js`
- Demo: `dev/start_collaboration_demo.sh`, `dev/compose.collaboration-demo.yml`, `dev/nginx.collaboration-demo.conf`

## Data Flow

The browser loads a checkpoint and Redis stream tail, subscribes to `collab:<document_id>`, synchronizes by version vector, and posts binary updates. Core appends accepted updates to a Redis stream, publishes them locally, marks dirty work, and schedules checkpoint/federation jobs. PostgreSQL is updated only during checkpoints or finalization.

## Testing

Run `cd src/core && uv run pytest`, `cd src/worker && uv run pytest`, `cd src/frontend && deno task test:collaboration`, `./dev/check_pyrefly.sh`, and `cd src/frontend && deno check frontend/static/js/collaboration.js`. Validate demo Compose with `docker compose -f docker/compose.yml -f dev/compose.collaboration-demo.yml config`.

## Pitfalls

Do not restore the old collaboration tables, text-operation protocol, sidecar, or tests. Never accept an update into process-local state when Redis is unavailable. Presence is expiring Redis state only. Rich text must be projected from an allowlisted Loro/ProseMirror schema; never persist client HTML.
Story collaboration uses snapshot IDs in `CollaborationChannel.story_snapshots`; report drafts and members remain channel metadata. Non-owner story management, news-item moves, and report scalar updates use the pending-operation endpoint; Loro text and ProseMirror containers remain direct CRDT documents.
