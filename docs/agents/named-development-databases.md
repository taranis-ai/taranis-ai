# Named Development Databases

Load for `dev/db.sh`, dataset selection, checkout hooks, or local database startup.
Operator commands: [dev/README.md](../../dev/README.md#named-local-databases).

## Contracts

- `enable` installs a checkout-local `post-checkout` hook; `refresh` runs it now;
  `disable` stops automation without changing data or selection. Each branch
  checkout fetches `origin/master`, updates its seeded template when the commit
  changes, clones a fresh database, clears configured Redis, and restarts with
  branch migrations. Same-commit branches rotate; file checkouts do not.
- Build templates with master's code in a detached worktree, with hooks disabled
  and Git-local environment removed. Templates reject application connections.
  A failed fetch/setup must not reuse stale master. Diagnostics are private in
  the checkout Git directory's `taranis-branch-databases/template-setup.log`.
- Namespace databases per checkout and require ownership comments before deletion.
  Keep the previous disposable database until replacement readiness succeeds.
  Startup failure stops applications and restores selection; target migrations
  and Redis flushes are not reversed. Git checkout itself is not undone.
- Save helpers under `taranis-branch-databases/` in the checkout's Git directory
  so the hook works on master without tracked helpers. Chain existing hooks;
  reject external/shared hook paths and symlinks. Guard unrelated worktrees.
  Re-enable to update the snapshot. Use Core's existing environment without
  syncing it until the old applications have stopped.
- Manage only recognized panes from this checkout's standard tmux session.
  Keep Tailwind/infrastructure running. `--stopped` asserts all applications are
  stopped and skips management/restart once. SQL idleness alone cannot prove that
  workers/cron stopped; never force-disconnect clients.
- Read component `.env` files and development defaults. Require a regular Core
  `.env`, loopback PostgreSQL/Redis, and no inherited connection overrides or
  explicit SQLAlchemy URI/schema. Atomically write `DB_DATABASE`; retain exact
  bytes and permissions for rollback. Clone operations need source ownership and
  `CREATEDB`. Reject system/reserved database names.
- Flush all configured broker/cache logical databases across Core, frontend and
  worker, including default Redis when unset. Other logical databases are retained.
  See [Redis Runtime State](redis-runtime-state.md) for job loss and recovery.
- Manual `clone` keeps selection and leaves apps stopped; `switch` selects an
  existing database with the same Redis/restart/rollback steps. Neither deletes
  named databases. Copies include PostgreSQL only; external files remain shared.

## Validation

`dev/databases.py` owns selection and switching; `database_branches.py` owns
master templates/hooks; `database_processes.py` owns tmux/readiness.
`dev/test_named_databases.sh` starts disposable PostgreSQL/Redis and runs
`dev/tests/named_databases.py`; the fixture origin explicitly uses `origin/master`
so shallow, detached CI checkouts work. CI fetches this ref before the harness.
The integration flow covers rotation, pending migrations, master updates, Redis,
existing hooks, ownership collisions and failure recovery. `dev/tests/test_database_processes.py`
covers tmux on a private server. Both run in **Development database helpers** CI;
feature completion still requires [signoff](development-workflow.md#feature-signoff-loop).
