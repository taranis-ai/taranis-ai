# Public Product Publishing

## When To Load
Product publishing, Taranis Publisher, public reports, `/reports/<product-id>`, or files under `/app/data/published-reports`.

## Expected Behavior
An administrator can create a publisher preset of type `TARANIS_PUBLISHER`. Publishing a rendered product with that preset copies its current render into persistent storage and returns a stable public URL. The report URL is intentionally reachable without authentication. The worker-only write endpoint remains protected by the worker API key.

## Code Paths
Publisher dispatch and the Taranis publisher live under `src/worker/worker/publishers/`. Core persistence and serving live in `src/core/core/service/product.py`, with authenticated worker routing in `src/core/core/api/worker.py`, its contract in `src/core/core/static/openapi3_1.yaml`, and public routing in `src/core/core/api/publish.py`. Ingress proxies `/reports` to core through `src/ingress/extras/default.conf.template`.

## Data Flow
The publisher worker validates that a rendered product exists, then calls the API-key-protected core publish endpoint. Core atomically writes the decoded render to `DATA_FOLDER/published-reports/<product-id>`; containers set `DATA_FOLDER=/app/data`. Public requests to `/reports/<product-id>` are proxied to core and served with the product MIME type plus sandbox and no-sniff headers.

## Testing
Run `cd src/core && uv run pytest tests/application/user_workspace/publishing/test_publish_api.py` and `cd src/worker && uv run pytest worker/tests/publishers/test_taranis_publisher.py`.

## Pitfalls
Treat every published report as public data. The URL uses the product UUID instead of its title to avoid collisions and path traversal. Product type changes are unsupported, so the MIME type remains stable. Republishing the same product atomically replaces the existing file and preserves its URL.
