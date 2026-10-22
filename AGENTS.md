# Agent Instructions

Agent name: jipitiii. taranis.ai is an OSINT application; see [README.md](README.md) for product context.

## Required Reading

- Before application edits or validation: [Development Workflow](docs/agents/development-workflow.md).
- Before component, model, API, queue, persistence, or datetime edits: [Architecture and Boundaries](docs/agents/architecture-and-boundaries.md).
- Before any `src/frontend` edit: [Frontend Development](docs/agents/frontend-development.md).
- Before planning or editing application behavior: inspect [Agent Memory](docs/agents/README.md) and read every matching memory. Code remains authoritative; update memories when contracts, paths, caching, or validation change. Add and index substantial recurring workflows.

## Security and Git

- Never expose exception-derived text (`str(exc)`, `repr(exc)`, tracebacks) in HTTP, UI, or worker results. Log server-side; return static messages, curated `public_message`, or the shared validation formatter.
- Never attribute commits to tools. Human attribution and required third-party notices remain allowed.
- Edit root `README.md` only on explicit request and only when existing information changed. Put development/deployment notes in scoped docs; update `deploy/README.md` only for upgrades requiring manual intervention.
- Root `README.md` and `.github/CODEOWNERS` changes require Ben's explicit review. Never bypass review, dismiss reviews, or weaken protection to merge them, including when using his account.

## Pull Requests

[Contributing](CONTRIBUTING.md) and the mandatory [PR template](.github/pull_request_template.md) process apply to outside collaborators. [taranis-ai/ait](https://github.com/orgs/taranis-ai/teams/ait) core members may omit template sections, prompts, contributor confirmations, and review-time estimates. Shared code, security, testing, licensing, attribution, and review rules still apply.

Use the human contributor's known membership or explicit statement, never repository write access alone. Do not request external-contributor disclosures from core members. For outside collaborators, obtain missing prompts before requesting review; leave human confirmations unchecked unless explicitly provided. Agents cannot establish a human's understanding or responsibility.

## Tests and Signoff

- Keep tests/docs proportional to risk. For small helpers, default to one focused behavior test and a short update to existing docs; add more only for distinct risks. Do not add a test matrix or standalone memory.
- Add coverage only for uncovered behavior or material risks. Prefer extending existing tests; remove duplicates and mock-only tests. Zero new tests is appropriate when coverage suffices.
- **No new tests, fixtures, helpers, or browser steps for cosmetic changes** (copy, labels, tooltips, icons, colors, spacing, layout). Update affected selectors/assertions only; use existing checks and brief browser inspection.
- After feature development, commit and run `./dev/test_push_signoff.sh`. On failure, fix, commit, and rerun it. Focused E2E runs do not replace signoff; full E2E runs create and remove fresh isolated Compose stacks. See [the signoff loop](docs/agents/development-workflow.md#feature-signoff-loop).
