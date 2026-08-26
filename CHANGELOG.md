# Changelog

This file records notable changes to Taranis AI. Published release entries link to their authoritative GitHub releases.

## 1.5.0 - Upcoming

### Added

- Added one shared Pydantic parameter contract for every supported worker type.
- Added schema-derived configuration forms with labels, tooltip descriptions, validation constraints, defaults, and exceptional widget hints.
- Added parameter-aware `PATCH` support for sources, bots, connectors, product types, and publisher presets.
- Added masked secret fields and an audited, non-cacheable secret reveal endpoint.

### Changed

- Store configured worker parameters as validated native JSON values on their owning resources.
- Validate parameters in core before persistence and enqueueing, then revalidate expanded effective parameters in workers.
- Preserve omitted secrets during replacement updates and distinguish configured values from default-expanded worker values.
- Make OSINT source imports atomic across normalization, validation, and persistence.

### Removed

- Removed database-backed worker definitions, parameter validation metadata, parameter join tables, and worker catalog pre-seeding.
- Removed the worker-type administration page and the `/config/parameters`, `/config/worker-parameters`, and `/config/worker-types` APIs.
- Removed unsupported email and Twitter collector remnants.

### Fixed

- Aligned MISP connector parameters with the registered `SSL_CHECK`, `PROXY_SERVER`, and `ADDITIONAL_HEADERS` names and added safe parsing for stored request timeouts ([#996](https://github.com/taranis-ai/taranis-ai/issues/996)).
- Removed undeclared HTML presenter conversion and render-option parameters.
- Preserved legacy incomplete on-demand worker configurations during the worker-parameter migration and migrated tagging keywords without blocking startup.
- Added Kafka `SSL` and `SASL_SSL` transport support, migrated legacy TAXII token authentication to bearer, and preserved native parameter types during worker execution.

### Deployment notes

- This release contains a destructive worker-parameter database migration. Before deployment, create a database snapshot, verify that it can be restored, and record the snapshot identifier and restore verification.
- Before deployment, verify that `osint_source.type` contains no `EMAIL_COLLECTOR` or `TWITTER_COLLECTOR` rows. These unsupported collector remnants have no safe automatic conversion, so the migration stops and identifies the source instead of deleting it.
- Deploy core, frontend, worker, and shared-model images as one compatible release.
- Rollback requires restoring the verified pre-deployment snapshot and redeploying the previous images. The migration intentionally has no reconstructive downgrade.

## [1.4.3] - 2026-08-13

- Improved task scheduling, completed-task visibility, bot filtering, bookmark shortcuts, no-JavaScript story actions, deployment reliability, and development tooling.

## [1.4.2] - 2026-07-20

- Added operational user administration, audit logging, IntelOwl enrichment, public product publishing, deployment hardening, and multiple RBAC, task, cache, and UI fixes.

## [1.4.1] - 2026-07-01

- Added OmniSearch, story bookmarks, German translations, Kafka publishing, bot-generated story titles, improved Assess filtering, and worker/LLM service improvements.

## [1.4.0] - 2026-05-28

- Replaced Celery and RabbitMQ with Redis Queue and Redis-backed workers, collectors, and scheduling.
- Existing deployments had to finish Celery jobs and migrate their deployment manifests before upgrading.

[1.4.3]: https://github.com/taranis-ai/taranis-ai/releases/tag/1.4.3
[1.4.2]: https://github.com/taranis-ai/taranis-ai/releases/tag/1.4.2
[1.4.1]: https://github.com/taranis-ai/taranis-ai/releases/tag/1.4.1
[1.4.0]: https://github.com/taranis-ai/taranis-ai/releases/tag/1.4.0
