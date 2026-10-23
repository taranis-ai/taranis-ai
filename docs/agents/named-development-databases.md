# Named Development Databases

Load for: local dataset cloning or switching, `dev/db.sh`, or development
startup changes affecting database selection. Operator usage lives in
[dev/README.md](../../dev/README.md#named-local-databases).

## Contracts

- `enable` prepares a disposable database and installs an opt-in `post-checkout`
  hook. `refresh` repeats the lifecycle explicitly; `disable` removes the enable
  marker without deleting databases or changing selection. Each branch checkout
  (including branches at the same commit) stops applications, fetches `origin/master`,
  checks the template's recorded commit, builds/seeds a replacement template using
  master's code when needed, clones a fresh disposable database, clears configured
  Redis queues/caches, changes selection, and restarts with branch migrations.
  File-only checkouts are ignored. Fetch/setup failures do not reuse stale master.
- Templates are fresh master seed databases, not copies of the original local
  dataset. They reject application connections. Template initialization uses a
  temporary detached worktree, suppresses its checkout hooks, sanitizes Git-local
  environment variables, and stores private diagnostics in `template-setup.log`.
  Full commit IDs identify templates; checkout-specific hashes namespace databases.
  A database must carry this checkout's ownership comment before automatic deletion.
  Existing named databases are never adopted or deleted merely by name.
- Prepare the replacement before deleting the old disposable database. Startup
  failure restores the previous selection and stops applications; old data survives,
  target migrations and flushed Redis state are not undone. Successful readiness
  removes older owned databases/templates. Hook failure does not undo Git checkout;
  retry `refresh` before restarting applications. SQL clients are never forcibly
  disconnected. A failed target can remain for inspection until the next refresh.
- Helpers and a runner are saved in the checkout's Git directory under
  `taranis-branch-databases/`; the hook continues working on master without these
  tracked scripts. Existing hooks are chained, including hooks ending with `exit`.
  A root guard prevents worktree creation or unrelated checkouts from rotating this
  database. External shared hook directories and symlinked hooks are rejected.
  Re-enabling updates the saved helpers. The runner uses Core's existing environment
  without syncing it while old applications are running; application restart syncs
  the target branch's dependencies normally. Automation requires the configured
  standard tmux session; `--stopped` is only an explicit one-off assertion.
- `list` reads PostgreSQL database sizes and marks the selection saved in Core's
  `.env`. `clone` copies the selected database with `CREATE DATABASE … TEMPLATE`,
  rejects an existing destination, and leaves selection unchanged. Cloning leaves
  applications stopped so current-branch startup migrations cannot alter the source.
- `switch` checks connectivity before stopping applications, requires both the
  current and target databases to have no connected clients, clears configured
  Redis state, atomically changes Core's `DB_DATABASE`, and restarts existing
  application panes. Startup failure stops target processes and restores the
  previous selection without restarting it or reversing target migrations.
  Never force-disconnect database clients. Manual switching never drops databases.
- The standard existing tmux session is `taranis`; `--session` selects another.
  Only recognized windows from the selected checkout are managed. Core, frontend,
  worker, and optional cron/dashboard panes stop; Tailwind and infrastructure stay
  running. `--stopped` is the caller's assertion that all applications are stopped
  and skips process management and restart. SQL idleness cannot prove workers or
  cron are stopped. Run commands outside managed application panes. Follow
  [Development Workflow](development-workflow.md) before choosing a startup
  workflow for a developer.
- Connection settings use the selected checkout's component `.env` files and
  development defaults. A regular Core `.env` is required. Inherited database
  connection, Redis/cache, Core URL, and Flask host/port overrides are rejected;
  move overrides into component `.env` files and unset shell variables. Managed
  restarts clear these inherited settings so stale tmux environments cannot
  redirect applications away from the checked configuration. Explicit database
  URI/schema overrides are also rejected so the saved selection takes effect.
  PostgreSQL and Redis endpoints must be loopback hosts. PostgreSQL connects
  directly from the host through the `postgres` maintenance database, independent
  of Docker or Podman. Cloning requires source ownership and `CREATEDB` privileges
  or superuser access. Names are restricted and system names are reserved.
- Switching flushes configured `REDIS_URL` and `CACHE_REDIS_URL` logical databases
  across Core, frontend, and worker, including the default broker when unset.
  These must be dedicated development databases. Other logical databases remain
  untouched. Queue loss and startup recovery follow [Redis Runtime State](redis-runtime-state.md).
- Copies contain PostgreSQL data only. External files remain shared; there is no
  backup lifecycle. Manual copies have no Git branch association. Each copy consumes database-sized
  storage plus WAL overhead. PostgreSQL template cloning excludes database-level
  settings and grants; see the [PostgreSQL reference](https://www.postgresql.org/docs/18/sql-createdatabase.html).

## Code and Coverage

`dev/db.sh` runs `dev/databases.py` in Core's `uv` environment;
`dev/database_processes.py` coordinates tmux panes and application readiness;
`dev/database_branches.py` builds master templates and installs checkout hooks.
`dev/test_named_databases.sh` covers cloning, selection, Redis isolation, real Git
checkouts (including master without helpers and branches sharing a commit), master
updates, startup initialization, ownership collisions, existing hooks, and failure
behavior against disposable PostgreSQL and Redis containers.
`dev/tests/test_database_processes.py` exercises process restarts on a private
tmux server. Run these checks explicitly when changing the helpers. The dedicated
`.github/workflows/test_named_databases.yaml` workflow runs them for changes to
the helpers, their coverage, or Core's dependency configuration. It also supports
manual runs and is independent of local signoff; the shared application pipeline
does not run these checks. Shared feature completion requirements remain in
[Development Workflow](development-workflow.md#feature-signoff-loop).
