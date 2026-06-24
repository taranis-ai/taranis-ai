# Agent Memory

This folder contains feature-level context for coding agents working on taranis.ai.

Use these files when a task mentions a related feature, workflow, route, model, template, or expected behavior. Read the matching memory before planning or editing code. Treat memory files as orientation and expected-behavior notes; code and tests remain the final source of truth.

## Memories

- [Assess Filters](assess-filters.md) - assess sidebar filters, filter-list loading, default filters, omnisearch filter handling, and related cache behavior.
- [Story Bookmarks](story-bookmarks.md) - bookmark collections, the Assess bookmark bar, instant single-story bookmarking, and bookmark cache invalidation.

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
