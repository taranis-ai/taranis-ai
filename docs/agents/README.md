# Agent Memory

This folder contains operational and feature context for coding agents working on taranis.ai.

Use these files when a task mentions a related feature, workflow, route, model, template, or expected behavior. Read the matching memory before planning or editing code. Treat memory files as orientation and expected-behavior notes; code and tests remain the final source of truth.

## Operational References

- [Development Workflow](development-workflow.md) - environment setup, startup choices, validation commands, test conventions, and development rules. Read before application changes or validation.
- [Architecture and Boundaries](architecture-and-boundaries.md) - component roles, RQ tasks, frontend/API boundaries, migrations, and UTC datetime handling. Read before component, API, persistence, queue, or datetime changes.

## Feature Memories

- [Assess Filters](assess-filters.md) - assess sidebar filters, filter-list loading, default filters, omnisearch filter handling, and related cache behavior.
- [RBAC ACL Behavior](rbac-acl.md) - RoleBasedAccess ACL boundaries, ADMIN_OPERATIONS bypass, OSINT source-group inheritance, and config/admin ACL isolation.
- [Audit Logging](audit-logging.md) - core audit logging scope, JSONL fields, security limits, and tests.
- [Admin User Import/Export](admin-user-import-export.md) - admin user export/import JSON format, duplicate handling, passwordless external users, and UI notification behavior.
- [Bot Run Order DAG](bot-run-order-dag.md) - post-collection bot DAG configuration, admin run-order UI, and dependent bot scheduling.
- [IntelOwl Enrichment](intelowl-enrichment.md) - IntelOwl enrichment bot behavior, summary-only persistence, email analyzer setup, and story/report task flow.
- [Admin User CLI](admin-user-cli.md) - operational password reset and role repair through `taranis-cli` inside the core container.
- [Initial User Onboarding](initial-user-onboarding.md) - startup flag for completing onboarding on the pre-seeded `admin` and `user` accounts.
- [Release Gate Tests](release-gate-tests.md) - Docker/Compose release gates that run expensive checks against already published GHCR images.
- [Story Bookmarks](story-bookmarks.md) - bookmark collections, the Assess bookmark bar, instant single-story bookmarking, and bookmark cache invalidation.
- [Worker Task Notifications](worker-task-notifications.md) - frontend notifications for worker-backed actions when tasks are queued but no workers are connected.
- [Authentication Cookies](authentication-cookies.md) - JWT/CSRF cookie names, deployment suffixes, base-path scoping, and auth cookie consumers.
- [Public Product Publishing](public-product-publishing.md) - Taranis publisher presets, persistent report files, and unauthenticated public report URLs.

## File Format

Each memory should use this structure:

```md
# Feature Name

## When To Load
Keywords, routes, modules, UI names, or workflows that should trigger reading this file.

## Expected Behavior
Short product-level behavior and important invariants.

## Code Paths
Frontend, core, models, templates, tests, and docs paths.

## Data Flow
Brief request/cache/state flow across frontend/core/worker if relevant.

## Testing
Primary test files and recommended validation commands.

## Pitfalls
Known boundaries, security concerns, cache invalidation, migration notes, or flaky areas.
```
