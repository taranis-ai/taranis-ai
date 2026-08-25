# Test Design

## When To Load

Before adding, removing, or changing any test in the repository, including unit, integration, browser, end-to-end, migration, and regression tests.

## Expected Behavior

Tests describe stable, existing product functionality and the final behavior users and supported integrations depend on.

Never add a dedicated migration or regression test solely for a bug introduced on an unmerged branch. The test suite must not preserve the history of branch-local implementation mistakes. If such a mistake reveals missing coverage of a real product contract, cover that contract in the nearest existing functionality or workflow test.

For user-facing behavior, test the complete interaction and resulting UI state. Prefer one workflow test such as loading new Assess stories and verifying the refreshed Assess UI over separate tests for each element that happened to disappear during development.

## Code Paths

- Core tests: `src/core/tests/`
- Frontend unit tests: `src/frontend/tests/unit/`
- Frontend browser and end-to-end tests: `src/frontend/tests/playwright/`
- Component test configuration: `src/*/pyproject.toml`

## Data Flow

Start from a stable public behavior: an API operation, user action, worker workflow, or persisted domain rule. Exercise that behavior through its normal boundary and assert the final observable state. Treat internal calls and individual markup elements as implementation details unless they are themselves a supported contract.

## Testing

Before keeping a new test, compare it with the existing suite and ask whether it adds durable coverage of specific existing functionality. Extend or strengthen the nearest workflow test when possible. Remove duplicate, branch-history-specific, or mock-only orchestration tests.

## Pitfalls

- Do not name or scope tests around a branch-local bug or its former failure mode.
- Do not create one test per DOM element when one interaction-level UI assertion covers the workflow.
- Do not mistake implementation-call assertions for product behavior.
- Database migration tests remain appropriate when they validate a real released-schema upgrade path; this prohibition concerns tests that merely memorialize unmerged branch mistakes.
