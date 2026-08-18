# MISP Parameters

## When To Load
MISP collector or connector parameters, PyMISP setup, request timeouts, SSL verification, proxy settings, or additional headers.

## Expected Behavior
MISP collector and connector worker payloads use the same schema keys and defaults. Core normalizes empty timeouts, SSL checks, and the optional global proxy before enqueueing work. Preseed rules provide early validation metadata; shared models remain the final payload validation boundary.

## Code Paths
- Shared models: `src/models/models/admin.py`
- Persisted parameter validation: `src/core/core/model/parameter_value.py`
- Core payload normalization: `src/core/core/model/worker.py`
- Worker runtime conversion: `src/worker/worker/misp_parameters.py`

## Data Flow
Core serializes collector or connector parameters, applies the configured timeout default, and resolves the global proxy only when enabled. The worker converts `PROXY_SERVER` into HTTP and HTTPS proxy entries because PyMISP only uses those protocols; generic web collectors handle their proxy map separately. MISP headers start empty so PyMISP retains its own User-Agent unless `ADDITIONAL_HEADERS` or `USER_AGENT` explicitly overrides it.

## Testing
- Core validation and normalization: `src/core/tests/unit/test_misp_parameters.py`
- Connector API validation: `src/core/tests/application/admin_console/configuration/test_config_api.py`
- Worker behavior: `src/worker/tests/connectors/test_misp_connector.py`, `src/worker/tests/collectors/test_collector.py`

## Pitfalls
Connector payloads use `SSL_CHECK`, `PROXY_SERVER`, `ADDITIONAL_HEADERS`, and `USER_AGENT`; worker code converts them into the `ssl`, `proxies`, and `headers` runtime arguments expected by PyMISP. Empty `REQUEST_TIMEOUT` values are valid stored input and normalize to the core request timeout; non-empty values must be positive integers.
