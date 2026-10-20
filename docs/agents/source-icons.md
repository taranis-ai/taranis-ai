# Source Icon Discovery

## When To Load

Collector favicons, Apple touch icons, feed images, or worker icon uploads.

## Contracts

- `BaseWebCollector.update_favicon` owns the best-effort discovery/upload chain. RSS supplies feed icon/image/logo candidates and the feed website link (feed origin root when absent); RT supplies its standard static icon endpoint. Simple Web uses its configured page.
- Feed/RT candidates take priority. Website discovery tries declared Apple touch icons before regular icons, followed by root Apple touch/precomposed/favicon paths. Resolve relative URLs against the redirected page and HTML base URL. Deduplicate candidates without URL fragments and fetch only HTTP(S) icons.
- A missing, empty, non-image, or Core-rejected candidate must not abort collection or stop remaining fallbacks. Core owns raster-image validation, size limits, and PNG normalization; skip SVG rather than introducing a separate conversion path.
- Discovery requests use the existing task HTTP pool, source proxy, five-second timeout, and no primary-resource validators. Explicit requests outside the configured source origin retain only User-Agent/Accept/Accept-Language headers. Discovery must not update primary HTTP validator state.
- Discovery retains initial-collection timing; it does not refresh existing icons on later manual/scheduled runs. Preview does not upload icons.

## Entry Points and Coverage

`src/worker/worker/collectors/base_web_collector.py`, `rss_collector.py`, and `rt_collector.py`; `src/worker/worker/core_api.py` uploads to Core's worker icon endpoint. Core validation lives in `src/core/core/model/osint_source.py`.

Extend `src/worker/tests/collectors/test_collector.py` for discovery and failure behavior. Existing `test_osint_source_icon.py` in Core covers decoding/normalization; do not duplicate that image-processing coverage in Worker.
