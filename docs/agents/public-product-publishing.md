# Public Product Publishing

## When To Load
Product publishing, Taranis Publisher, public reports, `/reports/<product-id>`, or files under `/app/data/published-reports`.

## Expected Behavior
Taranis always seeds a built-in `TARANIS_PUBLISHER` preset during first startup and restores it when missing during later startups. The built-in preset cannot be deleted; administrators may still create additional presets of the same type. Publishing a rendered product with such a preset copies its current render into persistent storage, stores the stable public URL as the product's `last_published_url`, and returns it. Product details always show either a direct link to the latest successful publication or an unpublished empty state. The report URL is intentionally reachable without authentication. The worker-only write endpoint remains protected by the worker API key.

## Code Paths
Publisher dispatch and the Taranis publisher live under `src/worker/worker/publishers/`. Core persistence and serving live in `src/core/core/service/product.py`, with authenticated worker routing in `src/core/core/api/worker.py`, its contract in `src/core/core/static/openapi3_1.yaml`, and public routing in `src/core/core/api/publish.py`. Ingress proxies `/reports` to core through `src/ingress/extras/default.conf.template`.

## Data Flow
Core seeds the built-in preset after worker types are available, using the same idempotent path for new and existing databases. The publisher worker validates that a rendered product exists, then calls the API-key-protected core publish endpoint. Core resolves `DATA_FOLDER` to an absolute path and atomically writes the decoded render to `<resolved-data-folder>/published-reports/<product-id>`; containers set `DATA_FOLDER=/app/data`. The public read path uses the same resolved directory so Flask serves the file independently of its application root. After the file replacement succeeds, core validates and persists the canonical `/reports/<database-loaded-product-id>` URL and invalidates the frontend product cache. Failed publications leave the previous URL unchanged. Public requests to `/reports/<product-id>` are proxied to core and served with the product MIME type plus sandbox and no-sniff headers.

## Testing
Run `cd src/core && uv run pytest tests/application/user_workspace/publishing/test_publish_api.py`, `cd src/worker && uv run pytest worker/tests/publishers/test_taranis_publisher.py`, and `cd src/frontend && uv run pytest tests/unit/views/test_product_view.py`.

## Pitfalls
Treat every published report as public data. Filesystem paths and public URLs use the product UUID reloaded from the database, never the request path value, to avoid reflected XSS and path traversal. Persisted publication links must be root-relative same-origin URLs or absolute HTTP(S) URLs without credentials or surrounding whitespace; unsafe links must never reach an `href`. Product type changes are unsupported, so the MIME type remains stable. Republishing the same product atomically replaces the existing file and updates the stored URL to the latest successful destination.
