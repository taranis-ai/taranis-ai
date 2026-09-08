# Presenter Template API

## When To Load
Template service, presenter template administration, template responses, filename sorting.

## Expected Behavior
Detail/list responses contain `name`, nullable base64 `content`, and `validation_status`. Creation requests use `name`; update/delete routes use the filename. Sorting uses `name_asc` and `name_desc` case-insensitively. Missing or unreadable templates retain their validation status and null content.

## Code Paths
- Core: `src/core/core/service/template_service.py`, `src/core/core/api/config.py`
- Client model: `src/models/models/admin.py` (`Template`)
- Admin UI: `src/frontend/frontend/views/admin_views/template_views.py`, `src/frontend/frontend/templates/template/`
- Contract: `src/core/core/static/openapi3_1.yaml`

## Data Flow
Core builds Pydantic `TemplateResponse` objects and serializes them at the HTTP boundary. The frontend `Template` stores `name`; its `id` property supplies the filename to shared admin routing/table actions and the `0` sentinel for unpopulated forms. That property is not a serialized API field.

## Testing
Core template service tests cover content states, ordering, and a filesystem-backed API lifecycle. The existing admin template management E2E covers creating, editing, and deleting via the UI. Run `./dev/test_push_signoff.sh` for full signoff.

## Pitfalls
Deploy Core and Frontend together; see `docs/releasing.md`. Preserve null content when serializing missing templates. Keep exception details server-side.
