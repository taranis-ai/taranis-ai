# RBAC ACL Behavior

## When To Load

RoleBasedAccess, ACLs, TLP, content/reference visibility, source-group inheritance, or admin/config permissions.

## Contracts

- ACLs restrict user-facing content/reference data, not admin/config management. Config routes use `CONFIG_*` permissions and must not pass `current_user` into ACL-aware model calls.
- `ADMIN_OPERATIONS` bypasses RoleBasedAccess, but not role TLP restrictions. Never infer this bypass from the `Admin` role name.
- Source access comes from direct source ACLs or current source-group membership. A source-group `*` ACL includes all sources, even ungrouped ones. Read-only ACLs do not grant writes.
- Assess content and source/group reference lists use the same visibility rules.
- Manual story/report bot actions enforce item-level write access and TLP before queueing; the worker API key cannot elevate a user's request.
- Core report/product deletion requires object-level write access in addition to module delete permission. Reports also enforce TLP; products use their current Product Type ACL. Denials precede deletion and cache/realtime notifications.

Analyst Chat requires `ASSESS_ACCESS`, scopes every conversation to its owner, and runs generated story filters through `Story.get_by_filter(..., current_user)`. For Taranis story and reference data, only ACL/TLP-visible source and group catalogs and accessible bounded story summaries may leave core for the configured provider. User-provided analyst prompts, latest messages, and conversation history also go to the provider. Recent story references must be rechecked through the same story path before reuse in a follow-up.

## Entry Points and Coverage

`src/core/core/service/role_based_access.py`; model `get_filter_query_with_acl`/per-item checks; admin routes in `src/core/core/api/config.py`.

Tests: `src/core/tests/application/mixed_flows/security/test_rbac.py`.
