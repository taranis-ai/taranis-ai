# Agent Memory

Read matching memories before planning or editing application behavior. Code and tests are authoritative. Operational references own shared rules; feature memories own distinct contracts and pitfalls.

## Operational References

- [Development Workflow](development-workflow.md): setup, validation, signoff, and development conventions. Required before application changes or validation.
- [Architecture and Boundaries](architecture-and-boundaries.md): components, API boundaries, persistence, and datetimes. Required before changes to those areas.
- [Frontend Development](frontend-development.md): HTMX, Alpine, browser state, and shared UI contracts. Required before frontend changes.
- [Test Design](test-design.md): coverage and fixture conventions. Required before test changes.
- [Frontend E2E Harness](frontend-e2e-harness.md): isolated Compose stacks, service selection, and diagnostics.
- [Release Gate Tests](release-gate-tests.md): validation against published images.

## Feature Memories

- [Named Development Databases](named-development-databases.md): local dataset cloning, selection, process coordination, and Redis isolation.
- [Redis Runtime State](redis-runtime-state.md): disposable Redis/RQ state, persistence settings, and restart recovery.
- [Story Export](story-export.md): Settings and Assess downloads, metadata, import contracts, dates, and access checks.
- [Telemetry](telemetry.md): Sentry initialization, OTLP traces and metrics, RQ trace propagation, and the optional Grafana LGTM Compose profile.
- [Analyst Chat](analyst-chat.md): persistent chat workflow, Responses and Chat Completions integration, Assess search planning, privacy, ownership, and deployment configuration.
- [LLM Endpoints](llm-endpoints.md): shared provider settings, feature assignments, secrets, and worker execution.
- [Global Settings](global-settings.md): transaction-scoped read caching, defaults, and invalidation.
- [News Item Creation](news-item-creation.md): method chooser, independent drafts, validation, and file-import retry.
- [News Item Ordering](news-item-ordering.md): local shared item order, editor controls, conflict normalization, and ungrouping title fallback.
- [Story Cards](story-cards.md): source icons, frequency ranking, and shared story enrichment.
- [Assess Filters](assess-filters.md): sidebar queries, saved filters, pagination, and cache invalidation.
- [Story Bookmarks](story-bookmarks.md): private collections, ordering, and Assess action context.
- [Analyst Review](analyst-review.md): Shift/Unread triage and Report-to-Publish handoff.
- [Analyze Reports](analyze-reports.md): report lists/editors, story-count sorting, lightweight publishing choices, and cache contracts.
- [Dashboard Cards](dashboard-cards.md): workflow counts and UTC week boundaries.
- [PizzINT Dashboard](pizzint-dashboard.md): opt-in external signal, cache, and stale fallback.
- [OSINT Source Management](osint-source-management.md): bulk creation/deletion, curated lists, and transactions.
- [Collector HTTP State](collector-http-state.md): validators, request scoping, dates, and 304 handling.
- [Fuzzy Deduplication and Collection Updates](fuzzy-deduplication.md): source/URL identity, revisions, CTPH grouping, concurrency, and backfill.
- [HTTP Client Lifetimes](http-clients.md): pooling, service/source policies, credentials, streaming cleanup, and SDK boundaries.
- [RSS Source Health](rss-source-health.md): feed detection, empty feeds, and entry limits.
- [Mastodon Collector](mastodon-collector.md): timelines, pagination, tokens, and cursors.
- [Bot Run Order DAG](bot-run-order-dag.md): bot dependencies and scheduling.
- [Story Clustering](story-clustering.md): direct worker library integration, reduced input, and provider configuration.
- [IntelOwl Enrichment](intelowl-enrichment.md): IOC persistence, CTI aggregation, and analyzer setup.
- [MISP Auto-Update](misp-auto-update.md): scheduled pushes, proposals, and feedback prevention.
- [Worker Parameters](worker-parameters.md): registry, configuration semantics, secrets, and migration.
- [Worker Task Notifications](worker-task-notifications.md): queue priority, results, and My Tasks.
- [Scheduler Dashboard](scheduler-dashboard.md): RQ lists, refresh, failures, and history.
- [Realtime Events](realtime-events.md): Centrifugo, authentication, reconnects, broadcasts, and presence.
- [Notification Center](notification-center.md): tab-session notification history.
- [Public Product Publishing](public-product-publishing.md): copying, rendering, and public files.
- [RBAC ACL Behavior](rbac-acl.md): content ACLs, TLP, and admin isolation.
- [Authentication Cookies](authentication-cookies.md): cookie scope, renewal, and revocation.
- [Audit Logging](audit-logging.md): metadata-only JSONL security events.
- [Admin User Import/Export](admin-user-import-export.md): JSON format, duplicates, and passwordless users.
- [Admin User CLI](admin-user-cli.md): existing-user password and role repair.
- [Initial User Onboarding](initial-user-onboarding.md): global defaults and per-user overrides.
- [Presenter Template API](template-api.md): template names, Pydantic responses, sorting, and admin routing.

## Maintaining Memories

Keep load triggers, distinct contracts/pitfalls, and useful code/test entry points. Link shared rules instead of copying them; validation commands belong in [Development Workflow](development-workflow.md).

Update the owning memory when behavior, paths, caching, or validation changes. Add and index substantial recurring workflows.

Omit cosmetic details, exhaustive symbol lists, generic advice, repeated commands, and branch history. Preserve security, transactions, defaults, failure behavior, operational limits, and relevant migration/rollback requirements.
