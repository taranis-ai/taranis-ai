# Public Product Publishing

## When To Load

Product copy/type changes, Taranis Publisher, `/reports/<product-id>`, or persisted public reports.

## Contracts

- Create copy opens `/publish/0?copy_from=<id>` without writing. Prefill type, title plus " Copy", description, and Report Items only; render/publication fields start empty. Fetch through user-scoped persistence (404 if missing), retain unsaved-edit discard confirmation, and save through ordinary creation.
- With no reports, any ACL-visible Product Type is allowed. Otherwise the type must support every selected typed report; untyped legacy reports impose no restriction. A type change clears the render; a MIME change also clears/disables publication until republished.
- Startup idempotently restores the non-deletable built-in `TARANIS_PUBLISHER` preset after worker types exist; additional presets are allowed.
- Presenter callbacks carry a hash of the exact render inputs. Reject stale/missing revisions rather than overwriting newer product state.
- Publishing copies the current render through a worker-key-protected endpoint into `<resolved DATA_FOLDER>/published-reports/<product-id>` (containers use `/app/data`). Use atomic replacement and update `last_published_url` only on success; failures retain the previous URL.
- `/reports/<product-id>` is intentionally unauthenticated, proxied to core, and served with the product MIME type, sandbox, and no-sniff headers. A MIME-changing edit disables this route even while the old file remains for replacement.
- Paths and canonical public URLs use the database-reloaded UUID, never the raw request value. Publication links must be same-origin root-relative or absolute HTTP(S), without credentials/whitespace; reject unsafe hrefs.
- Report/product request schemas remain closed to undeclared fields.

## Entry Points and Coverage

`src/worker/worker/publishers/`, `src/core/core/service/product.py`, `src/core/core/api/worker.py`, `src/core/core/api/publish.py`, `src/ingress/extras/default.conf.template`; API contract in `src/core/core/static/openapi3_1.yaml`.

Tests: `src/core/tests/application/user_workspace/publishing/test_publish_api.py`, `src/worker/tests/publishers/test_taranis_publisher.py`, `src/frontend/tests/unit/views/test_product_view.py`.
