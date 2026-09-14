# HTTP Client Lifetimes

## When To Load

HTTP clients, connection pooling, service/source request policies, frontend downloads, or HTTP dependency changes.

## Contracts

- Worker-owned HTTP uses Niquests. Every RQ task entry point and failure hook opens `http_session_scope()`. Nested scopes reuse the outer scope; all sessions close on success or exception. No live sessions are created at module import or worker startup. Standalone HTTP calls create and close a temporary scope.
- Service calls and external fetches use separate pools within that scope. Authorization, TLS verification, and proxies are passed per request; never put a source or bot credential in shared session defaults. SDK-owned transports (Mastodon.py, PyMISP, PyIntelOwl, TAXII) remain untouched.
- Service calls do not follow redirects and reject 3xx responses. Configure the final service endpoint, including any base path. HTTP/3 is disabled for service calls; external requests honor `DISABLE_HTTP3`. Neither policy retries automatically, including publishing or result submission.
- External requests follow redirects and retain cookies only within that redirect chain. Clear cookies after every fetch, including failures, preserving the previous isolation between article/icon/feed requests. Retain explicit source proxies and existing environment-proxy/`NO_PROXY` behavior.
- Worker connect timeouts are capped at 5 seconds for services and 10 seconds for external fetches, never exceeding the supplied timeout. Read timeouts retain the supplied value (`REQUESTS_TIMEOUT` for service clients, existing collector/icon limits for sources). These are socket inactivity limits, not whole-job deadlines.
- Frontend/core remain on Requests. Centrifugo keeps its existing pooled, best-effort, no-retry policy and 200 ms connect/300 ms read limits.
- Frontend `CoreApi` sessions are request-owned and keyed by bearer token. An explicitly supplied token takes precedence over the browser cookie. Request teardown closes every ordinary session; no token-bearing client is shared across requests. Connect timeouts are capped at 5 seconds and reads retain `REQUESTS_TIMEOUT`.
- Downloads own a separate session and response in an `ExitStack`. Request teardown closes unclaimed downloads. `stream_proxy` transfers ownership to the Flask response, whose iterator/final close releases both resources on completion, partial consumption, or abandonment. It must remain usable after request teardown without buffering the whole download.
- Shared models do not depend on an HTTP client. Build `WorkerProduct` from bytes and MIME type at the worker API boundary.

## Entry Points and Coverage

Worker: `src/worker/worker/http_client.py`, `core_api.py`, `bot_api.py`, `collectors/base_web_collector.py`, and task entry points. Frontend: `src/frontend/frontend/core_api.py` and `__init__.py`.

Extend existing coverage when refactoring HTTP clients: `src/worker/tests/collectors/test_collector.py` covers shared collector sessions and validators/304 behavior; `src/frontend/tests/unit/views/test_product_view.py` exercises the download endpoint through the real HTTP client and stream proxy; `src/frontend/tests/unit/test_data_persistence.py` covers bearer-token forwarding and caching. Existing auth tests own repeated `Set-Cookie` forwarding. Do not add standalone client suites or HTTP server fixtures for this refactor.

Worker tests currently alias Requests to Niquests for `requests-mock`; do not use those mocks as proof of SDK transport compatibility. Library consolidation or concurrent collection requires its own assessment; pooling does not automatically parallelize sequential fetches.
