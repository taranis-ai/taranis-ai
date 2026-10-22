# RBAC ACL Behavior

Load for: RoleBasedAccess, ACLs, TLP, content/reference visibility, source-group inheritance, or admin/config permissions.

## Contracts

- ACLs restrict user-facing content/reference data, not admin/config management. Config routes use `CONFIG_*` permissions and must not pass `current_user` into ACL-aware model calls.
- `ADMIN_OPERATIONS` bypasses RoleBasedAccess, but not role TLP restrictions. Never infer this bypass from the `Admin` role name.
- Report queries require every TLP attribute to be readable, matching per-report access. Reports without TLP remain visible; red clearance retains its bypass. Shared checks keep lists, product restrictions, and type choices consistent without duplicate rows.
- Source access comes from direct source ACLs or current source-group membership. A source-group `*` ACL includes all sources, even ungrouped ones. Read-only ACLs do not grant writes.
- Assess content and source/group reference lists use the same visibility rules.
- [Selected story exports](story-export.md) require read access to every linked source and both story/news-item TLP access; any unavailable selection fails without a partial download.
- Manual story/report bot actions enforce item-level write access and TLP before queueing; the worker API key cannot elevate a user's request.
- Core report/product deletion requires object-level write access in addition to module delete permission. Reports also enforce TLP; products use their current Product Type ACL. Denials precede deletion and cache/realtime notifications.
- Product lists, detail, copy metadata, and render downloads require Product Type read access. Restricted linked Reports permit metadata-only editing, preserve existing output, and block user-initiated copy/render/publish; see [Public Product Publishing](public-product-publishing.md). Report metadata remains ACL/TLP-filtered, including legacy untyped Reports.

Analyst Chat requires `ASSESS_ACCESS`, scopes every conversation to its owner, and runs generated story filters through `Story.get_by_filter(..., current_user)`. For Taranis story and reference data, only ACL/TLP-visible source and group catalogs and accessible bounded story summaries may leave core for the configured provider. User-provided analyst prompts, latest messages, and conversation history also go to the provider. Recent story references must be rechecked through the shared story path before reuse in a follow-up.

Story content updates (PUT/PATCH and bulk updates) and item reordering share `Story.allowed_to_update`, requiring ASSESS_UPDATE, story TLP access, write ACL access to every linked news item, and no `rt_id` story attribute before any mutation. User-scoped story list, detail, and bookmark responses expose this decision as `can_edit`; the frontend defaults it to false and uses it for edit links, fields, ordering, tags, and manual bot controls. Direct news-item edits, tag writes, and the attributes endpoint also check the parent story. Paged serialization batches writable source IDs through the shared source/group ACL query, while mutation paths always check live object permissions. Frontend story caches are keyed by user. Trusted bot updates without a user preserve their existing behavior.

## Code and Tests

`src/core/core/service/role_based_access.py`; model `get_filter_query_with_acl`/per-item checks; admin routes in `src/core/core/api/config.py`.

Tests: `src/core/tests/application/mixed_flows/security/test_rbac.py`.
