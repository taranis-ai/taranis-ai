# Development Workflow

## When To Load

Before application edits, validation, development setup changes, or local startup advice.

## Environment and Startup

- Use `uv`, not `pip`. In each `src` component, install with `uv sync --all-extras --dev` and run commands with `uv run` (or activate `.venv`). Dependency versions live in `pyproject.toml`; regenerate lockfiles with their tools rather than manually merging them.
- Before suggesting startup, ask which workflow the developer wants: `./dev/start_dev.sh` (default if no preference), manual non-tmux startup, or the tmux workflow in `dev/README.md`. Do not assume tmux.
- Manual non-tmux startup: `docker compose -f dev/compose.yml up -d`, then run `./install_and_run_dev.sh` separately in `src/core`, `src/frontend`, and `src/worker`.
- `start_dev.sh` supports macOS with Homebrew/Podman, Ubuntu, and Debian 13.

## Validation

Run component commands from that component's directory; CI definitions are in `.github/workflows`. Read [Test Design](test-design.md) before changing tests and [Frontend E2E Harness](frontend-e2e-harness.md) for browser-stack details.

- For branch-wide validation or CI regressions: `uv run pytest` in core and frontend, then `uv run pytest tests/playwright --e2e-ci` in frontend. Narrow targets are for isolating failures after reproduction; they do not replace signoff.
- Lint changed components with `uv run ruff check`; use `--fix` and `uv run ruff format` as appropriate. After Python edits, run `./dev/check_pyrefly.sh` from the repository root.
- Models has no unit tests. Worker browser-scraping tests require Playwright browsers.
- Core tests use in-process Redis fakes to avoid affecting running instances. Do not uncomment disabled E2E admin tests on `master` without proving they pass.
- Project Codex configuration filters inherited `DEBUG` values so the extension's `DEBUG=release` cannot override component boolean settings.

### Feature Signoff Loop

After implementing and committing a feature, humans and agents run from the repository root:

```bash
./dev/test_push_signoff.sh
```

It requires a clean worktree, runs the full lint/unit/E2E pipeline, then pushes and signs off only on success. Each full E2E run uses a fresh isolated Compose stack and removes it afterward. If validation fails, fix and commit, then rerun this same script; focused E2E targets are not the feature gate.

## Development Conventions

- Root `README.md` is curated product documentation; edit it only when explicitly requested. Use scoped documentation for development and deployment changes. `.github/CODEOWNERS` assigns root `README.md` and the ownership file to `@b3n4kh`. On `master`, enable **Require review from Code Owners** and **Dismiss stale pull request approvals when new commits are pushed**; ownership rules take effect after the file reaches the PR's base branch. Stale approval dismissal applies to all PRs. GitHub requests Ben's review on ready-for-review PRs from other authors. His existing review bypass remains available to him, but agents must never use it for these files. GitHub cannot accept self-approval on PRs authored by his account, so those require his explicit manual decision.
- Keep changes simple and focused. Prefer flat settings JSON and direct values; avoid forced DRY abstractions, unnecessary metadata, and compatibility aliases or migrations for unreleased branch-only behavior.
- Use `fix/`, `feature/`, or `chore/` branch prefixes. Never use `git add -A`; stage intended files only.
- Fix tests/lint before committing. Omit test-pass counts from commit messages and change-history comments from code.
- Add `from __future__ import annotations` only when Python 3.13 compatibility requires postponed evaluation for forward references, circular imports, or `TYPE_CHECKING` annotations.
