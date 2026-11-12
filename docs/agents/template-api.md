# Presenter Template API

Load for: Template service, presenter template administration, template responses, filename sorting.

## Contracts

Detail/list responses contain `name`, nullable base64 `content`, and `validation_status`. Creation requests use `name`; update/delete routes use the filename. Sorting uses `name_asc` and `name_desc` case-insensitively. Missing or unreadable templates retain their validation status and null content.

## Code Paths

- Core: `src/core/core/service/template_service.py`, `src/core/core/api/config.py`
- Client model: `src/models/models/admin.py` (`Template`)
- Admin UI: `src/frontend/frontend/views/admin_views/template_views.py`, `src/frontend/frontend/templates/template/`
- Contract: `src/core/core/static/openapi3_1.yaml`

## Data Flow

Core serializes `TemplateResponse` at the HTTP boundary. Frontend `Template.id` supplies the filename (or `0` for new forms) to shared admin routing; it is not an API field.

## Coverage

Core template service tests cover content states, ordering, and a filesystem-backed API lifecycle. The admin template management E2E covers creating, editing, and deleting via the UI.

## Pitfalls

Deploy Core and Frontend together; see `docs/releasing.md`. Preserve null content when serializing missing templates. Keep exception details server-side.
Presenter templates may intentionally render analyst-authored Story summary HTML; see [Public Product Publishing](public-product-publishing.md) and [#780](https://github.com/taranis-ai/taranis-ai/pull/780) for the separate Jinja, preview, and published-product boundaries.
