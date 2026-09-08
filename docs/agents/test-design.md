# Test Design

## When To Load

Before adding, removing, or changing tests.

## Coverage

Test stable product contracts through their normal API, user, worker, or persistence boundary and assert observable results. Prefer complete workflows over separate assertions/tests for incidental markup or internal calls.

Before keeping a new test, compare existing coverage and extend the nearest relevant test when possible. Remove duplicates and mock-only orchestration tests. Do not preserve unmerged branch mistakes as dedicated regression/migration tests; cover any missing durable contract in its owning workflow. Released-schema upgrade tests remain appropriate.

## Fixtures

- Reuse the nearest `conftest.py`. Core shared application fixtures belong in `src/core/tests/application/conftest.py`, cluster fixtures locally, and cross-application payload/setup fixtures in `src/core/tests/conftest.py`.
- Put shared builders in `src/core/tests/application/support/` and large data in fixtures or `src/core/tests/test_data/`.
- Do not create inline fake classes/ad-hoc doubles inside tests or use autouse fixtures. Request fixtures explicitly or use module/class `pytest.mark.usefixtures`.
- Prefer frontend E2E coverage for cross-component cache invalidation, scheduling, and seeding. Reuse established test selectors; prefer `data-test-id` for new ones.

## Entry Points

Tests live under each component's `tests/`; frontend browser tests are in `src/frontend/tests/playwright/`. Commands and signoff: [Development Workflow](development-workflow.md). Stack selection and diagnostics: [Frontend E2E Harness](frontend-e2e-harness.md).
