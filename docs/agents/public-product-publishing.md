# Public Product Publishing

## When To Load

Product copy/type changes, Taranis Publisher, `/reports/<product-id>`, or persisted public reports.

## Contracts

- Product creation and row deletion use native links and POST forms enhanced by HTMX, so both workflows remain available when JavaScript is disabled. On an existing product, compatible report items are also rendered as a native checkbox table inside a `noscript` fallback; the Alpine-powered searchable table remains the enhanced JavaScript experience.
- The enhanced report picker uses `x-cloak` until Alpine initializes. Do not hide it with CSS inside the `noscript` fallback: HTMX's fragment parser activates that style after create/save and hides the picker even with JavaScript enabled. The existing publishing browser workflow checks visibility after creation; the no-JavaScript workflow covers the native fallback.
- Create copy opens `/publish/0?copy_from=<id>` without writing. Prefill type, title plus " Copy", description, and Report Items only; render/publication fields start empty. Fetch `/api/publish/product-metadata/<id>` through user-scoped persistence without reading the deferred render (404 if missing, 403 if the Product Type is inaccessible), retain unsaved-edit discard confirmation, and save through ordinary creation.
- With no reports, any ACL-visible Product Type is allowed. Otherwise the type must support every selected typed report; untyped legacy reports impose no restriction. A type change clears the render; a MIME change also clears/disables publication until republished.
- Startup idempotently restores the non-deletable built-in `TARANIS_PUBLISHER` preset after worker types exist; additional presets are allowed.
- Presenter callbacks carry a hash of the exact render inputs. Reject stale/missing revisions rather than overwriting newer product state.
- Publishing copies the current render through a worker-key-protected endpoint into `<resolved DATA_FOLDER>/published-reports/<product-id>` (containers use `/app/data`). Use atomic replacement and update `last_published_url` only on success; failures retain the previous URL.
- `/reports/<product-id>` is intentionally unauthenticated, proxied to core, and served with the product MIME type, sandbox, and no-sniff headers. A MIME-changing edit disables this route even while the old file remains for replacement.
- Intended functionality / clarified requirement: authorized analysts may author HTML in Story summaries and include it in generated HTML products through templates such as `<div>{{ story.summary }}</div>`. Assess Story cards escape the summary; product templates decide whether to render HTML or apply `|e` for plain text. Do not impose blanket stripping or escaping. `ImmutableSandboxedEnvironment` restricts server-side Jinja operations, not HTML content. The preview iframe's `sandbox` and the published response's sandbox CSP protect browser contexts separately; neither guarantees every output is safe. Template path and sandbox hardening: [#780](https://github.com/taranis-ai/taranis-ai/pull/780).
- Paths and canonical public URLs use the database-reloaded UUID, never the raw request value. Publication links must be same-origin root-relative or absolute HTTP(S), without credentials/whitespace; reject unsafe hrefs.
- Report/product request schemas remain closed to undeclared fields.
- Product lists exclude deferred renders before serialization; the report editor uses a lightweight ACL-filtered product-choice catalog. See [Analyze Reports](analyze-reports.md).
- Product search joins each Product to its actual Product Type before filtering, counting, and applying ACLs. Title, creation time, presenter type, and report-count sorts run in SQL before paging, ending in a direction-matching Product ID tie breaker. `order` is the table parameter; `sort` and `DATE_ASC`/`DATE_DESC` remain accepted. The default is newest first. Search uses 250 ms debounce and retains page size/sort when resetting to page one.
- Lists batch-load Product Type labels and report IDs without Report attributes. Editor compatible-report metadata also avoids attributes and applies report ACL/TLP visibility. Authenticated Product detail, metadata, and render downloads check Product Type read access.
- Editor-only catalogs are not fetched on the list. `/api/publish/product-type-choices` supplies ACL-visible IDs/titles and compatible report-type IDs without presenter parameters, using batched relationships. It shares the `product_type` list-cache namespace with an endpoint-specific key. Copy metadata uses `product_metadata`; Product/Report writes and access changes invalidate it.
- With JavaScript, HTML/JSON/text previews load only after **Load preview**, using a local Alpine state and an inert template. Preserve the iframe's empty sandbox and authored content. PDF preview behavior is unchanged; without JavaScript, the native preview still renders automatically.

## Entry Points and Coverage

`src/worker/worker/publishers/`, `src/core/core/service/product.py`, `src/core/core/api/worker.py`, `src/core/core/api/publish.py`, `src/ingress/extras/default.conf.template`; API contract in `src/core/core/static/openapi3_1.yaml`.

Tests: `src/core/tests/application/user_workspace/publishing/test_publish_api.py`, `src/worker/tests/publishers/test_taranis_publisher.py`, `src/frontend/tests/unit/views/test_product_view.py`, and `src/frontend/tests/playwright/test_no_javascript.py`. The native product/report workflow selects compatible seeded types explicitly; picker ordering is not a compatibility guarantee.
