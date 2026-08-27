# AGENTS Instructions

Project guidance for coding agents working on taranis.ai.

## Agent Persona

Name: jipitiii

## Project Overview

taranis.ai is an OSINT application. See [README.md](README.md) for product context.

## Required Reading

- Before editing application code or running validation, read [Development Workflow](docs/agents/development-workflow.md).
- Before editing `src/core`, `src/frontend`, `src/worker`, models, API boundaries, queues, persistence, or datetime handling, also read [Architecture and Boundaries](docs/agents/architecture-and-boundaries.md).
- Before any `src/frontend` change, also read [Frontend Development](docs/agents/frontend-development.md).
- For an application feature, workflow, route, model, template, or user-facing behavior, first inspect [Agent Memory](docs/agents/README.md) and read every matching memory before planning or editing.

Memory files provide expected behavior, code paths, tests, and known pitfalls; implementation remains the source of truth. Update a matching memory when behavior, code paths, cache behavior, validation, or test strategy changes. Add and index a memory for substantial recurring workflows.

## Exception Handling

- Never expose `str(exc)`, `repr(exc)`, tracebacks, or other exception-derived text in HTTP responses, rendered UI, or worker results. Log the exception server-side and return a static message, an explicitly curated `public_message`, or the project's validation-error formatter.

## Test Discipline

Review every newly added test against the existing test suite. Remove tests that duplicate existing coverage or rely so heavily on mocking that they do not meaningfully exercise behavior. Keep a new test only when it adds necessary, effective coverage—the best code is no code, and that applies to test code too.

At the end of feature development, humans and agents run `./dev/test_push_signoff.sh`, not a focused E2E target. If validation fails, fix and commit the problem, then run the same script again. Its full E2E run uses `--e2e-keep-stack`: the first call starts the named `taranis-e2e` stack and later calls restart code-bearing services while reusing the stack and test data. Do not tear down the stack between fix-and-rerun attempts or run these attempts concurrently. Reset it only when retained state is suspected; CI provides the final isolated run. See [Development Workflow](docs/agents/development-workflow.md#feature-signoff-loop).
