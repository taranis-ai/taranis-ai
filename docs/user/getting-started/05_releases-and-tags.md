---
title: "Releases and Container Tags"
linkTitle: "Releases and Tags"
weight: 5
description: >
  Understanding Taranis AI release strategy, container image tags, and their meaning for deployment and upgrades.
---
## Tags

Taranis AI publishes container images to GitHub Container Registry (`ghcr.io`) with different tagging strategies for core services and bots.

All images are available at [GitHub Container Registry](https://github.com/orgs/taranis-ai/packages).

### For Core Services (core, gui, worker, frontend)

Core Taranis AI services follow a **stable and tested** release process:

| Tag | Description | Use Case | Stability |
|-----|-------------|----------|-----------|
| `stable` | Latest manually tested and verified release | **Production deployments** | ✅ High |
| `1.2.3` (semver) | Specific version (semantic versioning) | **Pinned production deployments** | ✅ High |
| `latest` | Latest build from main branch | **Development/testing only** | ⚠️ May contain bugs |

## Upgrade support

Only upgrades to the immediately following Taranis AI release are tested and supported. For a larger version gap, upgrade one release at a time and verify the deployment after every step.

Review the [GitHub release notes](https://github.com/taranis-ai/taranis-ai/releases) before each upgrade. Follow [Maintenance](10_maintainance.md) for the upgrade, verification, and rollback procedure.

### For Bots

Bot containers follow a similar release process, with versions decoupled from the core Taranis AI services:

| Tag | Description | Use Case | Stability |
|-----|-------------|----------|-----------|
| `stable` | Latest manually tested and verified release | **Production deployments** | ✅ High |
| `1.2.3` (semver) | Specific version (semantic versioning) | **Pinned production deployments** | ✅ High |
| `latest` | Latest build from main branch | **Development/testing only** | ⚠️ May contain bugs |
