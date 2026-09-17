# RBAC ACL Behavior

## When To Load

RoleBasedAccess, ACLs, TLP, content/reference visibility, source-group inheritance, or admin/config permissions.

## Contracts

- ACLs restrict user-facing content/reference data, not admin/config management. Config routes use `CONFIG_*` permissions and must not pass `current_user` into ACL-aware model calls.
- `ADMIN_OPERATIONS` bypasses RoleBasedAccess, but not role TLP restrictions. Never infer this bypass from the `Admin` role name.
- Source access comes from direct source ACLs or current source-group membership. A source-group `*` ACL includes all sources, even ungrouped ones. Read-only ACLs do not grant writes.
- Assess content and source/group reference lists use the same visibility rules.
- `Story.visible_query` requires access to every item source and the stored story `TLP`, before counts/pagination. News-item details also check parent-story access.
- Item TLP uses its explicit attribute, then source TLP, then the global default. Story creation, item updates, and override changes refresh the stored `TLP`; access checks only read it. Source/global changes apply on the next refresh.
- TLP attributes accept only known levels or an empty inheritance value. Malformed persisted levels are logged and treated as RED on reads/transfers. Custom attribute inputs reserve `TLP` and `tlp_override` for the dedicated selectors.
- Startup backfills missing story `TLP` attributes in bounded batches before serving queries, using item/source/global inheritance and story overrides; existing stored classifications are preserved.
- `tlp_override` is an ordinary story attribute: empty/absent means inherit; otherwise the most restrictive item/override wins. Grouping preserves the stricter override; splitting copies it. Both refresh `TLP`.
- Manual story/report bot actions enforce item-level write access and TLP before queueing; the worker API key cannot elevate a user's request.
- Core report/product deletion requires object-level write access in addition to module delete permission. Reports also enforce TLP; products use their current Product Type ACL. Denials precede deletion and cache/realtime notifications.

Analyst Chat requires `ASSESS_ACCESS`, scopes every conversation to its owner, and runs generated story filters through `Story.get_by_filter(..., current_user)`. For Taranis story and reference data, only ACL/TLP-visible source and group catalogs and accessible bounded story summaries may leave core for the configured provider. User-provided analyst prompts, latest messages, and conversation history also go to the provider. Recent story references must be rechecked through the same story path before reuse in a follow-up.

Story content updates (PUT/PATCH and bulk updates) and item reordering share `Story.allowed_to_update`, requiring ASSESS_UPDATE, story TLP access, write ACL access to every linked news item, and no `rt_id` story attribute before any mutation. User-scoped story list, detail, and bookmark responses expose this decision as `can_edit`; the frontend defaults it to false and uses it for edit links, fields, ordering, tags, and manual bot controls. Direct news-item edits and tag writes also check the parent story. Frontend story caches are keyed by user. Trusted bot updates without a user preserve their existing behavior.

## Entry Points and Coverage

`src/core/core/service/role_based_access.py`; model `get_filter_query_with_acl`/per-item checks; admin routes in `src/core/core/api/config.py`.

Tests: `src/core/tests/application/mixed_flows/security/test_rbac.py`.
