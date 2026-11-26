#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "Error: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

run_step() {
  printf '\n==> %s\n' "$1"
}

masked_url() {
  python3 - "$1" <<'PY'
import sys
from urllib.parse import urlparse, urlunparse

uri = sys.argv[1]
parsed = urlparse(uri)
if parsed.password:
    netloc = f"{parsed.username}:***@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"
else:
    netloc = parsed.netloc
print(urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)))
PY
}

run_core_db_setup() {
  local core_dir="$1"
  local database_url="$2"
  local label="$3"
  local sample_action="$4"

  run_step "$label"
  (
    cd "$core_dir"
    env \
      SQLALCHEMY_DATABASE_URI="$database_url" \
      DEBUG=true \
      DISABLE_SCHEDULER=true \
      TARANIS_CORE_SENTRY_DSN= \
      uv run --frozen python - "$sample_action" <<'PY'
import sys

from flask import Flask

from core.managers import db_manager
from core.managers.db_manager import db
from core.model.news_item import NewsItem
from core.model.product import Product
from core.model.product_type import ProductTypeReportType
from core.model.report_item import ReportItem
from core.model.story import Story


# Each row follows a product back to its report, story, and source news item.
samples = [
    ("Flood bulletin", "Flood assessment", "River levels rising", "Gauge reaches flood stage"),
    ("Port bulletin", "Port assessment", "Harbor reopens", "Ferry service resumes"),
]


def seed_samples():
    type_pair = db.session.execute(db.select(ProductTypeReportType).limit(1)).scalar_one()
    for product_title, report_title, story_title, news_title in samples:
        story = Story(title=story_title, news_items=[NewsItem(title=news_title)])
        report = ReportItem(title=report_title, report_item_type_id=type_pair.report_item_type_id)
        report.stories = [story]
        product = Product(title=product_title, product_type_id=type_pair.product_type_id)
        product.report_items = [report]
        db.session.add(product)
    db.session.commit()


def verify_samples():
    query = (
        db.select(Product.title, ReportItem.title, Story.title, NewsItem.title)
        .select_from(Product)
        .join(Product.report_items)
        .join(ReportItem.stories)
        .join(Story.news_items)
        .where(Product.title.in_([sample[0] for sample in samples]))
    )
    rows = db.session.execute(query).all()
    if sorted(rows) != sorted(samples):
        raise SystemExit(f"Migration sample mismatch. Expected {samples!r}, found {rows!r}")


app = Flask(__name__)
app.config.from_object("core.config.Config")
with app.app_context():
    db_manager.initialize(app, initial_setup=True)
    if sys.argv[1] == "seed":
        seed_samples()
    verify_samples()
PY
  )
}

run_pytest_validation() {
  local core_dir="$1"
  local database_url="$2"
  local pytest_target="$3"

  run_step "Validate migrated branch database with pytest target: $pytest_target"
  (
    cd "$core_dir"
    env \
      SQLALCHEMY_DATABASE_URI="$database_url" \
      DEBUG=true \
      DISABLE_SCHEDULER=true \
      TARANIS_CORE_SENTRY_DSN= \
      uv run --frozen --extra dev pytest "$pytest_target"
  )
}

cleanup() {
  local status=$?

  if [ "${KEEP_MIGRATION_TEST_DB:-0}" != "1" ]; then
    if [ -n "${PG_CONTAINER:-}" ]; then
      "$CONTAINER_CLI" rm -f -v "$PG_CONTAINER" >/dev/null 2>&1 || true
    fi
    if [ -n "${MASTER_WORKTREE:-}" ] && [ -d "$MASTER_WORKTREE" ]; then
      git worktree remove --force "$MASTER_WORKTREE" >/dev/null 2>&1 || true
    fi
    if [ -n "${TMP_DIR:-}" ]; then
      rm -rf "$TMP_DIR"
    fi
    git worktree prune >/dev/null 2>&1 || true
  else
    echo
    echo "Keeping migration test resources:"
    echo "  worktree: ${MASTER_WORKTREE:-}"
    echo "  container: ${PG_CONTAINER:-}"
    echo "  master database: ${MASTER_DB:-}"
    echo "  branch database: ${BRANCH_DB:-}"
  fi

  exit "$status"
}

require_command git
require_command python3
require_command uv

CONTAINER_CLI="${CONTAINER_CLI:-podman}"
require_command "$CONTAINER_CLI"

if [ "${CONTAINER_CLI##*/}" = "podman" ] && [ -n "${SNAP_REAL_HOME:-}" ] && [ -n "${SNAP_USER_DATA:-}" ]; then
  case "${XDG_DATA_HOME:-}" in
    "$SNAP_USER_DATA"/*) export XDG_DATA_HOME="$SNAP_REAL_HOME/.local/share" ;;
  esac
fi

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null)" || fail "Run this command from inside the taranis-ai git worktree."
cd "$ROOT_DIR"

BASE_REF="${BASE_REF:-${1:-origin/master}}"
CURRENT_REF="$(git rev-parse --abbrev-ref HEAD)"
PYTEST_TARGET="${PYTEST_TARGET:-tests/unit}"
RUN_ID="$(date +%Y%m%d%H%M%S)-$$"
TMP_DIR="$(mktemp -d)"
MASTER_WORKTREE="$TMP_DIR/master"
PG_CONTAINER="taranis-migration-test-$RUN_ID"
PG_IMAGE="${PG_IMAGE:-docker.io/library/postgres:18-alpine}"
PG_USER="taranis"
PG_PASSWORD="supersecret"
MASTER_DB="taranis_master_${RUN_ID//-/_}"
BRANCH_DB="taranis_branch_${RUN_ID//-/_}"
DUMP_FILE="$TMP_DIR/master.dump.sql"

trap cleanup EXIT

run_step "Create temporary worktree from $BASE_REF"
git worktree add --detach "$MASTER_WORKTREE" "$BASE_REF" >/dev/null

run_step "Start disposable PostgreSQL with $CONTAINER_CLI"
"$CONTAINER_CLI" run \
  --detach \
  --name "$PG_CONTAINER" \
  -e POSTGRES_USER="$PG_USER" \
  -e POSTGRES_PASSWORD="$PG_PASSWORD" \
  -e POSTGRES_DB=postgres \
  -p 127.0.0.1::5432 \
  "$PG_IMAGE" >/dev/null

POSTGRES_READY=false
for _ in {1..60}; do
  # The image starts a temporary socket-only server while initializing. Probe
  # TCP so only the final PostgreSQL process can satisfy the readiness check.
  if "$CONTAINER_CLI" exec "$PG_CONTAINER" pg_isready -h 127.0.0.1 -U "$PG_USER" -d postgres >/dev/null 2>&1; then
    POSTGRES_READY=true
    break
  fi
  sleep 1
done

if [ "$POSTGRES_READY" != "true" ]; then
  echo "PostgreSQL container state:" >&2
  "$CONTAINER_CLI" inspect \
    --format 'status={{.State.Status}} running={{.State.Running}} exit_code={{.State.ExitCode}}' \
    "$PG_CONTAINER" >&2 || true
  echo "PostgreSQL container logs:" >&2
  "$CONTAINER_CLI" logs "$PG_CONTAINER" >&2 || true
  fail "PostgreSQL did not become ready."
fi

PG_PORT="$("$CONTAINER_CLI" port "$PG_CONTAINER" 5432/tcp | sed -E 's/.*:([0-9]+)$/\1/' | head -n 1)"
[ -n "$PG_PORT" ] || fail "Could not determine PostgreSQL host port."

"$CONTAINER_CLI" exec "$PG_CONTAINER" createdb -U "$PG_USER" "$MASTER_DB"
"$CONTAINER_CLI" exec "$PG_CONTAINER" createdb -U "$PG_USER" "$BRANCH_DB"

MASTER_DATABASE_URL="postgresql+psycopg://$PG_USER:$PG_PASSWORD@127.0.0.1:$PG_PORT/$MASTER_DB"
BRANCH_DATABASE_URL="postgresql+psycopg://$PG_USER:$PG_PASSWORD@127.0.0.1:$PG_PORT/$BRANCH_DB"

echo "Base ref: $BASE_REF"
echo "Current branch: $CURRENT_REF"
echo "Master database: $(masked_url "$MASTER_DATABASE_URL")"
echo "Branch database: $(masked_url "$BRANCH_DATABASE_URL")"

run_core_db_setup "$MASTER_WORKTREE/src/core" "$MASTER_DATABASE_URL" "Create and seed database using $BASE_REF" seed

run_step "Copy master database into branch database"
"$CONTAINER_CLI" exec "$PG_CONTAINER" pg_dump --no-owner --no-privileges -U "$PG_USER" -d "$MASTER_DB" >"$DUMP_FILE"
"$CONTAINER_CLI" exec -i "$PG_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$BRANCH_DB" <"$DUMP_FILE" >/dev/null

run_step "Move copied database into a non-default schema"
# Leave no public schema behind: hard-coded application schema references must
# fail instead of silently reading or changing the wrong objects.
"$CONTAINER_CLI" exec -i "$PG_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$BRANCH_DB" \
  -v branch_db="$BRANCH_DB" -v migration_schema="migration_${RUN_ID//-/_}" <<'SQL'
ALTER SCHEMA public RENAME TO :"migration_schema";
ALTER DATABASE :"branch_db" SET search_path TO :"migration_schema";
SQL

run_core_db_setup "$ROOT_DIR/src/core" "$BRANCH_DATABASE_URL" "Apply current branch migrations and verify sample data" verify
run_pytest_validation "$ROOT_DIR/src/core" "$BRANCH_DATABASE_URL" "$PYTEST_TARGET"

run_step "Migration test completed"
echo "Migrated $BASE_REF database successfully using current branch migrations and pytest target $PYTEST_TARGET."
