#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

fail() { echo "Error: $*" >&2; exit 1; }
if [[ $# != 1 || "$1" == --help ]]; then
  echo "Usage: $0 EXISTING_LOCAL_BRANCH"
  echo "Run outside application panes in the taranis tmux session. Close SQL clients first; branch data and Redis state are discarded."
  if [[ "${1:-}" == --help ]]; then exit 0; fi
  exit 1
fi
branch="$1"
for command in git uv tmux pgrep "${CONTAINER_CLI:-podman}"; do
  command -v "$command" >/dev/null || fail "Missing command: $command"
done
root="$(git rev-parse --show-toplevel)"
cd "$root"
[[ -z "$(git status --porcelain)" ]] || fail "Commit or stash changes before switching."
git show-ref --verify --quiet "refs/heads/$branch" || fail "Create the local branch '$branch' first."
[[ -f src/core/.env && ! -L src/core/.env ]] || fail "Set up a regular src/core/.env first."
for setting in DB_DATABASE SQLALCHEMY_DATABASE_URI; do
  [[ -z "${!setting+x}" ]] || fail "Unset $setting; Core's .env must own the database selection."
done

tmux list-panes -t '=taranis:core' >/dev/null || fail "The standard taranis tmux session needs a core window."
panes=() pids=() scripts=()
for window in core frontend worker cron rq-dashboard; do
  row="$(tmux list-panes -t "=taranis:$window" -F '#{pane_id}|#{pane_pid}|#{pane_current_path}' 2>/dev/null)" || continue
  [[ "$row" != *$'\n'* ]] || fail "Use one pane per application window."
  IFS='|' read -r pane pid directory <<< "$row"
  component="$window" script=install_and_run_dev.sh
  case "$window" in
    cron) component=worker; script=install_and_run_cron.sh ;;
    rq-dashboard) component=worker; script=install_and_run_rq_dashboard.sh ;;
  esac
  [[ "$directory" == "$root/src/$component" ]] || fail "Application pane belongs to another checkout."
  [[ "$pane" != "${TMUX_PANE:-}" ]] || fail "Run this command outside application panes."
  panes+=("$pane"); pids+=("$pid"); scripts+=("$script")
done

cli="${CONTAINER_CLI:-podman}"
project="${COMPOSE_PROJECT_NAME:-taranis}"
pg="$("$cli" ps --filter "label=com.docker.compose.project=$project" --filter label=com.docker.compose.service=database --format '{{.ID}}')"
redis="$("$cli" ps --filter "label=com.docker.compose.project=$project" --filter label=com.docker.compose.service=redis --format '{{.ID}}')"
[[ -n "$pg" && "$pg" != *$'\n'* && -n "$redis" && "$redis" != *$'\n'* ]] || fail "Start one local development PostgreSQL/Redis stack."
pg_port="$("$cli" port "$pg" 5432/tcp | sed -nE '1s/.*:([0-9]+)$/\1/p')"
[[ "$pg_port" =~ ^[0-9]+$ ]] || fail "PostgreSQL needs a published host port."
sql() { "$cli" exec -i "$pg" psql -X -U taranis -d postgres -v ON_ERROR_STOP=1 -Atc "$1"; }
marker=taranis-dev-script
base=taranis_dev_base
database=taranis_dev
tag() { sql "SELECT COALESCE(shobj_description(oid, 'pg_database'), 'unmanaged') FROM pg_database WHERE datname = '$1'"; }
drop_owned() {
  local name="$1" ownership
  ownership="$(tag "$name")"
  [[ -n "$ownership" ]] || return 0
  [[ "$ownership" == "$marker" || "$ownership" == "$marker:"* ]] || fail "Refusing to delete unowned database '$name'."
  sql "DROP DATABASE $name"
}

git_dir="$(git rev-parse --absolute-git-dir)"
# Disable a previously installed version's hook; this script switches explicitly.
rm -f "$git_dir/taranis-branch-databases/enabled"
temporary="$(mktemp -d)"
env_file=""
cleanup() {
  git worktree remove --force "$temporary/master" >/dev/null 2>&1 || true
  rm -rf "$temporary"
  [[ -z "$env_file" ]] || rm -f "$env_file"
}
trap cleanup EXIT
trap 'echo "Stopped at line $LINENO. No rollback; fix the error and rerun." >&2' ERR

echo "Stopping application panes..."
for pane in "${panes[@]}"; do tmux send-keys -t "$pane" C-c; done
for pid in "${pids[@]}"; do
  for _ in {1..30}; do
    if ! pgrep -P "$pid" >/dev/null; then break; fi
    sleep 1
  done
  if pgrep -P "$pid" >/dev/null; then
    fail "An application is still stopping; inspect its tmux pane."
  fi
done

echo "Checking origin/master..."
git fetch --no-tags origin +refs/heads/master:refs/remotes/origin/master
revision="$(git rev-parse 'origin/master^{commit}')"
base_tag="$(tag "$base")"
if [[ "$base_tag" != "$marker:$revision" ]]; then
  echo "Rebuilding master template (setup log: $git_dir/db-template.log)..."
  drop_owned "$base"
  sql "CREATE DATABASE $base TEMPLATE template0"
  sql "COMMENT ON DATABASE $base IS '$marker:building'"
  git -c core.hooksPath=/dev/null worktree add --detach "$temporary/master" "$revision"
  (
    cd "$temporary/master/src/core"
    SQLALCHEMY_DATABASE_URI="postgresql+psycopg://taranis:supersecret@127.0.0.1:$pg_port/$base" \
      DEBUG=true QUEUE_ENABLED=false TARANIS_CORE_SENTRY_DSN='' OTEL_EXPORTER_OTLP_ENDPOINT='' \
      uv run --frozen python -c 'from core import create_app; create_app(db_setup=True)'
  ) > "$git_dir/db-template.log" 2>&1
  sql "ALTER DATABASE $base ALLOW_CONNECTIONS false"
  sql "COMMENT ON DATABASE $base IS '$marker:$revision'"
fi

echo "Switching to $branch and replacing the disposable database..."
git switch -- "$branch"
drop_owned "$database"
sql "CREATE DATABASE $database TEMPLATE $base"
sql "COMMENT ON DATABASE $database IS '$marker'"
"$cli" exec "$redis" redis-cli FLUSHALL
env_file="$(mktemp "$root/src/core/.env.XXXXXX")"
awk 'toupper($0) !~ /^[[:space:]]*(EXPORT[[:space:]]+)?DB_DATABASE[[:space:]]*=/' src/core/.env > "$env_file"
printf 'DB_DATABASE=%s\n' "$database" >> "$env_file"
mv "$env_file" src/core/.env
for index in "${!panes[@]}"; do
  tmux send-keys -t "${panes[$index]}" C-u
  tmux send-keys -t "${panes[$index]}" -l "env -u DB_DATABASE -u SQLALCHEMY_DATABASE_URI ./${scripts[$index]}"
  tmux send-keys -t "${panes[$index]}" Enter
done
echo "Application panes restarted; Core applies branch migrations during startup."
