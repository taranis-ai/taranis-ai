# RBAC ACL Behavior

## When To Load

RoleBasedAccess, ACLs, TLP, content/reference visibility, source-group inheritance, or admin/config permissions.

## Contracts

- ACLs restrict user-facing content/reference data, not admin/config management. Config routes use `CONFIG_*` permissions and must not pass `current_user` into ACL-aware model calls.
- `ADMIN_OPERATIONS` bypasses RoleBasedAccess, but not role TLP restrictions. Never infer this bypass from the `Admin` role name.
- Source access comes from direct source ACLs or current source-group membership. A source-group `*` ACL includes all sources, even ungrouped ones. Read-only ACLs do not grant writes.
- Assess content and source/group reference lists use the same visibility rules.
- Manual story/report bot actions enforce item-level write access and TLP before queueing; the worker API key cannot elevate a user's request.

Story content updates (PUT/PATCH and bulk updates) and item reordering share `Story.allowed_to_update`, requiring ASSESS_UPDATE, story TLP access, write ACL access to every linked news item, and no `rt_id` story attribute before any mutation. User-scoped story list, detail, and bookmark responses expose this decision as `can_edit`; the frontend defaults it to false and uses it for edit links, fields, ordering, tags, and manual bot controls. Direct news-item edits and tag writes also check the parent story. Frontend story caches are keyed by user. Trusted bot updates without a user preserve their existing behavior.

## Entry Points and Coverage

`src/core/core/service/role_based_access.py`; model `get_filter_query_with_acl`/per-item checks; admin routes in `src/core/core/api/config.py`.

Tests: `src/core/tests/application/mixed_flows/security/test_rbac.py`.
