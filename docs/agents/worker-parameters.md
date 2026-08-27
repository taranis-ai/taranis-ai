# Worker Parameters

## When To Load

Load for worker types, collector/bot/connector/product-type/publisher-preset parameters, configuration forms, parameter validation, secret reveal, worker dispatch, pre-seeding, or the worker-parameter migration.

## Expected Behavior

`src/models/models/worker_parameters.py` is the only intrinsic worker-parameter contract. Every `WORKER_TYPES` member has exactly one registry entry and one Pydantic model with `extra="forbid"`. Models own uppercase external names, native types, defaults, field order, constraints, labels, tooltip descriptions, secret status, and exceptional UI widgets.

Database JSON columns contain only explicitly configured names with their native validated values. Explicit values are retained even when equal to defaults. Core returns configured non-secret values and `********` secret markers to human-facing APIs. Worker-authenticated responses validate the configured values, expand model defaults, preserve native Pydantic types, and include raw secrets. Workers validate that effective payload again before dispatch; transient task filters are added only afterwards.

## Code Paths

- Contract and adapters: `src/models/models/worker_parameters.py`
- Core parameter policy: `src/core/core/service/worker_parameters.py`
- Owner models: `src/core/core/model/{osint_source,bot,connector,product_type,publisher_preset}.py`
- Configuration and secret API: `src/core/core/api/config.py`
- Worker API: `src/core/core/api/worker.py`
- Frontend schema adapter: `src/frontend/frontend/views/admin_views/admin_base_view.py`
- Shared form partial: `src/frontend/frontend/templates/partials/worker_parameters.html`
- Migration: `src/core/migrations/20260818_01_Wp4rM-worker-parameter-registry.py`

## Data Flow

Frontend imports the registry and renders `model_json_schema(mode="validation", by_alias=True)`. Standard schema types, enums, defaults, required fields, patterns, and numeric bounds drive controls. `Field(title=...)` is the label and `Field(description=...)` is tooltip/help text. `json_schema_extra` is only for behavior JSON Schema cannot express, such as cron, template, word-list, or preferred textarea widgets.

POST creates a full configuration. `PUT.parameters` replaces non-secret configuration while preserving omitted or masked configured secrets. `PATCH.parameters` merges keys; `null` removes a configured value and omitted keys remain unchanged. Worker type is immutable. Sources and bots may be incomplete only while disabled, and enabling or executing them performs full validation. Connector tasks persist parameter-contract failures with the `invalid_parameters` reason before aborting execution. Email publisher subjects remain optional for compatibility with existing presets; an omitted subject expands to an empty string for worker execution. TAXII bearer authentication uses the `bearer` value expected by the worker. Kafka publishers support `PLAINTEXT`, `SSL`, `SASL_PLAINTEXT`, and `SASL_SSL`.

Secret inputs are not submitted until Replace or Clear is selected. Reveal is an audited POST authorized by the resource's update permission and is non-cacheable. Audit records remain metadata-only.
Invalid reveal requests are logged server-side and return a static `400` error without exception-derived text.

## Testing

- Registry/service: `src/core/tests/unit/test_worker_parameter_registry.py`, `test_worker_parameter_service.py`
- Core configuration/import: `src/core/tests/application/admin_console/configuration`
- Frontend forms: `src/frontend/tests/unit/views`
- Worker dispatch: `src/worker/tests`
- Run Ruff in all four components and `./dev/check_pyrefly.sh` from the repository root.

## Pitfalls

- Never add validation metadata back to owner rows or create a parallel frontend catalog.
- Preserve validated native types across persistence, human-facing APIs, and worker execution; do not turn booleans, numbers, objects, or lists back into strings.
- Template existence, referenced bot/word-list ids, DAG validity, and deployment availability remain stateful core/frontend checks.
- The destructive migration has no reconstructive downgrade. Deployment requires a verified database snapshot; rollback restores it and redeploys the previous compatible images.
- Migration failures for unsupported worker types or invalid enabled source/bot configurations identify the owner table, owner ID, and worker type; they never silently discard an owner. Incomplete connector, product-type, and publisher-preset configurations are retained for administrators to repair and are fully validated before execution.
- `TAGGING_BOT.KEYWORDS` is migrated to `REGULAR_EXPRESSION` when no canonical value exists, and TAXII `AUTH_TYPE=token` is migrated to `bearer`.
