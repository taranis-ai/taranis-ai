# RBAC ACL Behavior

## When To Load
ACL, RoleBasedAccess, RBAC, permissions, Assess source visibility, OSINT source groups, config/admin access, report/product/word-list access.

## Expected Behavior
RoleBasedAccess ACLs restrict user-facing content and reference data, not admin/config management workflows. Users with `ADMIN_OPERATIONS` bypass RoleBasedAccess ACL checks, but TLP restrictions still apply unless their role TLP allows access.

OSINT source visibility can be granted by a direct OSINT Source ACL or inherited from an OSINT Source Group ACL. A source-group ACL grants access to the group's current member sources; an OSINT Source Group `*` ACL grants all sources, including ungrouped sources. Read-only ACLs grant read access only; writable ACLs grant write access where a user-facing workflow already enforces ACL write checks.

## Code Paths
Core ACL evaluation lives in `src/core/core/service/role_based_access.py`. OSINT source, source-group, news-item, story, report, product, and word-list models call it through `get_filter_query_with_acl` or per-item access checks. Admin/config routes in `src/core/core/api/config.py` should rely on `CONFIG_*` permissions and should not pass `current_user` into ACL-aware model calls.

## Data Flow
Assess story/news queries join through OSINT sources, then RoleBasedAccess filters the source ids visible to the current user. Assess source and source-group reference lists use the same ACL service so filter options match content visibility. Config APIs authenticate with `CONFIG_*` permissions and fetch unfiltered configuration data.

## Testing
Primary coverage is in `src/core/tests/application/mixed_flows/security/test_rbac.py`. Run `cd src/core && uv run pytest tests/application/mixed_flows/security/test_rbac.py` after changing ACL behavior.

## Pitfalls
Do not use ACLs as a second permission layer for admin/config pages. Do not tie superadmin behavior to the `Admin` role name; use the `ADMIN_OPERATIONS` permission. Do not bypass TLP from RoleBasedAccess helpers.
