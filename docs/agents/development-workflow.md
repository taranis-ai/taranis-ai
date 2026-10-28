# Development Workflow

Read before application edits, validation, development setup changes, or local startup advice.

## Environment and Startup

- Use `uv`, not `pip`. In each `src` component, install with `uv sync --all-extras --dev` and run commands with `uv run` (or activate `.venv`). Dependency versions live in `pyproject.toml`; regenerate lockfiles with their tools rather than manually merging them.
- Before suggesting startup, ask which workflow the developer wants: `./dev/start_dev.sh` (default if no preference), manual non-tmux startup, or the tmux workflow in `dev/README.md`. Do not assume tmux.
- Manual non-tmux startup: `docker compose -f dev/compose.yml up -d`, then run `./install_and_run_dev.sh` separately in `src/core`, `src/frontend`, and `src/worker`.
- Automatic collection/scheduled bots require the opt-in cron process (`WITH_CRON_RQ=1`); the default launcher runs workers only. Manual jobs and queued retries still run. To exclude collectors/bots entirely, use the worker `WORKER_TYPES` override documented in `dev/README.md`. Core's legacy `DISABLE_SCHEDULER` setting does not stop standalone cron.
- `start_dev.sh` supports macOS with Homebrew/Podman, Ubuntu, and Debian 13.
- On macOS, worker startup and `dev/testpipeline.sh` prepend Homebrew's library directory to `DYLD_FALLBACK_LIBRARY_PATH` for WeasyPrint's GLib/Pango dependencies. Manual worker/test commands need the same export; see `dev/README.md`.

## Validation

Run component commands from that component's directory; CI definitions are in `.github/workflows`. Read [Test Design](test-design.md) before changing tests and [Frontend E2E Harness](frontend-e2e-harness.md) for browser-stack details.

- For branch-wide validation, run `./dev/testpipeline.sh` from the repository root. It syncs environments and runs audits, lint, unit tests, and the full isolated frontend E2E suite. Narrow targets isolate failures but do not replace signoff.
- `certifi` and Pillow are exempt from the one-week dependency cooling period so fixes for compromised CA roots and image-decoder advisories can be locked immediately. Upgrade only the affected packages with `uv lock --upgrade-package`; keep audit checks enabled.
- For other urgent security fixes, use a temporary package-specific upload cutoff that admits the reviewed fix while excluding later releases. Remove the cutoff once the fixed artifacts satisfy the normal one-week delay. The worker's Brotli cutoffs admit the October 22 fixes for CVE-2026-111497.
- Lint changed components with `uv run ruff check`; use `--fix` and `uv run ruff format` as appropriate. After Python edits, run `./dev/check_pyrefly.sh` from the repository root.
- Models has no unit tests. Worker browser-scraping tests require Playwright browsers.
- Core tests use a per-session temporary SQLite database and in-process Redis fakes to avoid affecting concurrent test runs or running instances. Do not uncomment disabled E2E admin tests on `master` without proving they pass.
- Project Codex configuration filters inherited `DEBUG` values so the extension's `DEBUG=release` cannot override component boolean settings.
- `jactionlint` reads `.github/jactionlint.yaml`. It allows version-tagged actions and the release action while keeping other workflow checks enabled.
- Workflows with `run` steps set `defaults.run.shell: bash` so a failing pipeline command fails the step. Keep exceptions explicit at the step level.
- The model package workflow disables uv caching because pushed tags publish package artifacts.
- The Copilot setup workflow validates matching changes on pull requests and on pushes to `master`; Copilot also runs its setup steps when an agent starts.
- CI checkout steps use `persist-credentials: false`; give later Git write steps credentials explicitly if a workflow needs them.
- CI job timeouts use twice the longest successful GitHub Actions job duration, rounded up to five minutes with a ten-minute minimum. Refresh them from `gh` job history when workloads change.
- CI concurrency is scoped by workflow: newer `master` image builds replace older ones, while pull request checks replace only older runs for that same PR. Manual checks can run independently. Model package tags run per tag; releases queue because they share the `stable` image tags, and only the highest numeric release tag updates `stable`.

### Feature Signoff Loop

After implementing and committing a feature, humans and agents run from the repository root:

```bash
./dev/test_push_signoff.sh
```

It requires a clean worktree, runs the full lint/unit/E2E pipeline, then pushes and signs off only on success. Each full E2E run uses a fresh isolated Compose stack and removes it afterward. If validation fails, fix and commit, then rerun this same script; focused E2E targets are not the feature gate.

## Development Conventions

- Before PR work, read [Contributing](../../CONTRIBUTING.md). Apply the human contributor’s status and review rules from [AGENTS.md](../../AGENTS.md#pull-requests); core members are exempt from the outside-contributor process.
- Follow [AGENTS.md](../../AGENTS.md#security-and-git) for root README and CODEOWNERS edits. On `master`, require Code Owner review and dismiss stale approvals. Ownership applies once CODEOWNERS reaches the base branch. GitHub cannot accept self-approval; PRs authored by Ben require his explicit manual decision.
- Keep changes simple and focused. Prefer flat settings JSON and direct values; avoid forced DRY abstractions, unnecessary metadata, and compatibility aliases or migrations for unreleased branch-only behavior.
- Use `fix/`, `feature/`, or `chore/` branch prefixes. Never use `git add -A`; stage intended files only.
- Fix tests/lint before committing. Omit test-pass counts from commit messages and change-history comments from code.
- Add `from __future__ import annotations` only when Python 3.13 compatibility requires postponed evaluation for forward references, circular imports, or `TYPE_CHECKING` annotations.
