# Branch Development Database

`dev/db.sh BRANCH` is the entire feature: one Bash script, at most 200 lines, no hooks or helper modules.
Require the standard taranis tmux session, closed SQL clients and a clean checkout; pause app panes before switching.
Use local Compose PostgreSQL/Redis with default database credentials; exactly two reserved development databases.
Only drop databases marked as owned; never disconnect clients or touch the original `taranis` database.
Reject inherited database overrides and any `SQLALCHEMY_DATABASE_URI` key in Core's `.env` before stopping panes;
parse `.env` with Core's dotenv parser, including quoted and case-insensitive keys, since a URI overrides `DB_DATABASE`.
Fetch master, refresh template, switch, clone, flush Redis, save Core's `.env`, and restart panes with migrations.
Disable any legacy enable marker; do not add a framework, Python helpers, a dedicated harness or CI job.
Validate against disposable services locally, then run the standard signoff script.
