# Named Development Databases

`dev/db.sh enable` installs a checkout-local hook; `refresh` retries and `disable` stops rotation.
Branch switches fetch master, refresh its seeded template, clone, flush configured Redis, and restart with migrations.
Only owned disposable databases are deleted, after replacement startup; named databases and external files survive.
Failed startup stops apps and restores selection; Git checkout, migrations and Redis flushes are not undone.
`dev/database_processes.sh` controls the standard tmux panes; `--stopped` skips process management once.
Settings come from component `.env` files; require loopback databases, reject inherited connection overrides.
Helpers live in Git's `taranis-branch-databases/` directory so hooks work across branches; re-enable to update.
Run `./dev/test_named_databases.sh` locally; feature completion still requires the standard signoff script.
