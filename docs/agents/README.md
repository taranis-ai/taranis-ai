# Agent Memory

Read matching memories before planning or editing related features, routes, models, or workflows. Code and tests remain the source of truth. Shared rules live in the operational references; feature memories record only distinct contracts and non-obvious pitfalls.

## Operational References

- [Development Workflow](development-workflow.md): setup, validation, signoff, and development conventions. Required before application changes or validation.
- [Architecture and Boundaries](architecture-and-boundaries.md): components, API boundaries, persistence, and datetimes. Required before changes to those areas.
- [Frontend Development](frontend-development.md): HTMX, Alpine, browser state, and shared UI contracts. Required before frontend changes.
- [Test Design](test-design.md): coverage and fixture conventions. Required before test changes.
- [Frontend E2E Harness](frontend-e2e-harness.md): isolated Compose stacks, service selection, and diagnostics.
- [Release Gate Tests](release-gate-tests.md): validation against published images.

## Feature Memories

- [Analyst Chat](analyst-chat.md) - persistent chat workflow, direct Responses API integration, Assess search planning, privacy, ownership, and deployment configuration.
- [Assess Filters](assess-filters.md): sidebar queries, saved filters, pagination, and cache invalidation.
- [Story Bookmarks](story-bookmarks.md): private collections, ordering, and Assess action context.
- [Analyst Review](analyst-review.md): Shift/Unread triage and Report-to-Publish handoff.
- [Dashboard Cards](dashboard-cards.md): workflow counts and UTC week boundaries.
- [PizzINT Dashboard](pizzint-dashboard.md): opt-in external signal, cache, and stale fallback.
- [OSINT Source Management](osint-source-management.md): bulk creation/deletion, curated lists, and transactions.
- [Collector HTTP State](collector-http-state.md): validators, request scoping, dates, and 304 handling.
- [RSS Source Health](rss-source-health.md): feed detection, empty feeds, and entry limits.
- [Mastodon Collector](mastodon-collector.md): timelines, pagination, tokens, and cursors.
- [Bot Run Order DAG](bot-run-order-dag.md): bot dependencies and scheduling.
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
- [Presenter Template API](template-api.md) - template names, Pydantic responses, sorting, and admin routing.

## Maintaining Memories

Keep a short load trigger, distinct behavior/invariants, and the most useful code and test entry points. Add flow or pitfalls sections only when they explain something not already stated. Test paths identify coverage; validation commands and signoff belong in [Development Workflow](development-workflow.md).

Update the owning memory when its contract, code paths, cache behavior, or test strategy changes. Link related memories instead of copying their rules. Add and index a memory for a substantial recurring workflow.

Omit obvious UI mechanics, CSS classes, exhaustive symbol/template inventories, generic engineering advice, repeated test commands, and branch history or promises about future PRs. Preserve security boundaries, transaction semantics, surprising defaults, failure behavior, and operational limitations. Document released migration/rollback requirements when still relevant.
