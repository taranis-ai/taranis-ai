# Worker Parameters

## When To Load

Worker parameter contracts/forms, configured/effective values, secrets, SFTP host trust, dispatch, seeding, or registry migration.

## Contracts

- `src/models/models/worker_parameters.py` is the sole intrinsic contract: one registry entry and `extra="forbid"` Pydantic model per `WORKER_TYPES` member. It owns external uppercase names, native types, defaults, order, constraints, labels/help, secrets, and exceptional widgets.
- Persist only explicitly configured native values, even when equal to defaults. Human APIs return configured non-secrets and `********` markers. Worker APIs validate/expand defaults and include raw secrets; workers revalidate before adding transient task filters.
- Frontend renders validation-mode JSON Schema with aliases. Use standard schema metadata first; `json_schema_extra` is for widgets schema cannot express. Required controls stay visible, optional controls are collapsed but submitted. Type changes replace the shared section; Assess create-from-URL is separate.
- POST creates; `PUT.parameters` replaces non-secrets while preserving omitted/masked configured secrets; PATCH merges, with `null` removing a value and omission retaining it. Worker type is immutable.
- Sources/bots may be incomplete only while disabled; enabling/executing fully validates. Connector contract failures persist `invalid_parameters` before aborting. Stateful reference/template/DAG/deployment checks remain in core/frontend.
- Secret inputs submit only after Replace/Clear. Reveal is an audited, non-cacheable POST requiring the resource's update permission; invalid requests return static 400.
- Compatibility contracts: omitted email subject expands to empty; TAXII bearer auth uses `bearer`; Kafka supports PLAINTEXT, SSL, SASL_PLAINTEXT, and SASL_SSL.
- SFTP requires an uploaded/pasted OpenSSH `HOST_KEY` or explicit `ACCEPT_ANY_HOST_KEY=true` (default false). Verified mode pins the key to the URL hostname/port; bypass ignores it and uses insecure `AutoAddPolicy`. Each upload uses a fresh client; no filesystem trust store is loaded.
- The opt-in branch has a rule-specific `codeql[...]` accepted-risk annotation. Python CI includes `AlertSuppression.ql` to mark SARIF results; GitHub alert #268 is separately dismissed as accepted risk because code scanning does not apply inline suppressions automatically. Keep verification enabled by default and the rule active elsewhere.
- The `public-key` widget reads a local file into the submitted textarea. Validation errors rebuild context from submitted values so publisher parameters remain editable. Setup/rollback: [SFTP host trust](../../deploy/README.md#sftp-publisher-host-trust).

## Migration

`src/core/migrations/20260818_01_Wp4rM-worker-parameter-registry.py` is destructive with no reconstructive downgrade. Deployment requires a verified database snapshot; rollback restores it with prior compatible images.

Unsupported types/invalid enabled source or bot configs fail with owner table/ID/type rather than discarding records. Incomplete connector/product-type/publisher-preset configs remain repairable but must validate before execution. Mappings: `TAGGING_BOT.KEYWORDS` to `REGULAR_EXPRESSION` if canonical value is absent; TAXII `token` to `bearer`.

## Entry Points and Coverage

Contract above; policy: `src/core/core/service/worker_parameters.py`; human/worker APIs: `src/core/core/api/config.py`, `src/core/core/api/worker.py`; forms: `src/frontend/frontend/views/admin_views/admin_base_view.py`, `src/frontend/frontend/templates/partials/worker_parameters.html`.

Tests: `src/core/tests/unit/test_worker_parameter_registry.py`, `src/core/tests/unit/test_worker_parameter_service.py`, configuration/import tests in `src/core/tests/application/admin_console/configuration/`, frontend admin forms/workflows, and worker dispatch tests. Browser flows must expand optional settings before interacting with them.

SFTP: `src/worker/worker/publishers/sftp_publisher.py`; real SSH coverage in `src/worker/tests/publishers/test_sftp_publisher.py`; upload, persistence, bypass, and validation recovery in `src/frontend/tests/playwright/test_e2e_admin.py::TestEndToEndAdmin::test_publisher_presets`.
