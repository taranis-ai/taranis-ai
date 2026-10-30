#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"
operation="${1:-inventory}"
if [ "$#" -gt 0 ]; then shift; fi
case "$operation" in
  inventory|pilot|baseline|report|correctness) ;;
  *) echo "Usage: $0 {inventory|pilot|baseline|report|correctness} [runner options]" >&2; exit 2 ;;
esac
export ORM_BASE_COMMIT
ORM_BASE_COMMIT="$(python3 -c 'import json; print(json.load(open("src/core/tests/performance/orm/baseline/manifest-v1.json"))["base_commit"])')"
if [ "$operation" = report ]; then
  cd src/core
  exec uv run --frozen --no-sync python -m tests.performance.orm.runner report "$@"
fi
run_id="$(date -u +%Y%m%dt%H%M%Sz)-$$"
export ORM_ARTIFACT_DIR="${ORM_ARTIFACT_DIR:-$ROOT_DIR/.orm-artifacts/$run_id}"
if [ -e "$ORM_ARTIFACT_DIR/source-commit.txt" ] || [ -e "$ORM_ARTIFACT_DIR/environment.json" ]; then
  echo "Choose a new ORM_ARTIFACT_DIR; prior runs are immutable." >&2
  exit 2
fi
mkdir -p "$ORM_ARTIFACT_DIR"
ORM_ARTIFACT_DIR="$(cd "$ORM_ARTIFACT_DIR" && pwd)"
export ORM_ARTIFACT_DIR
compose=(docker compose -p "taranis-orm-$run_id" -f dev/orm/compose.yml)
cleanup() { "${compose[@]}" down --volumes --remove-orphans >"$ORM_ARTIFACT_DIR/teardown.log" 2>&1; }
trap cleanup EXIT
git rev-parse HEAD >"$ORM_ARTIFACT_DIR/source-commit.txt"
git status --porcelain >"$ORM_ARTIFACT_DIR/worktree.txt"
docker version --format '{{json .}}' >"$ORM_ARTIFACT_DIR/container-runtime.json"
git diff HEAD -- src/core src/models dev/orm dev/profile_orm.sh >"$ORM_ARTIFACT_DIR/source.patch"
python3 - "$ORM_ARTIFACT_DIR/source-files.json" <<'PY'
import hashlib
import json
import subprocess
import sys
from pathlib import Path

files = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--",
                                 "src/core", "src/models", "dev/orm", "dev/profile_orm.sh"]).decode().split("\0")
hashes = {}
for name in files:
    path = Path(name)
    if name and path.is_file():
        with path.open("rb") as stream:
            hashes[name] = hashlib.file_digest(stream, "sha256").hexdigest()
Path(sys.argv[1]).write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")
PY
"${compose[@]}" config >"$ORM_ARTIFACT_DIR/compose.yml"
"${compose[@]}" build core >"$ORM_ARTIFACT_DIR/build.log" 2>&1
"${compose[@]}" up -d --wait database redis >"$ORM_ARTIFACT_DIR/startup.log" 2>&1
"${compose[@]}" exec -T database psql -U orm_profile -d orm_profile \
  -c 'CREATE EXTENSION IF NOT EXISTS pg_stat_statements' \
  -c "COMMENT ON DATABASE orm_profile IS 'taranis-orm-disposable-v1'" >"$ORM_ARTIFACT_DIR/extension.log"
if [ -n "${ORM_SNAPSHOT:-}" ]; then
  : "${ORM_SNAPSHOT_MANIFEST:?provide metadata for the sanitized snapshot}"
  uv run --directory src/core --frozen --no-sync python -c \
    'import sys; from tests.performance.orm.dataset import validate_snapshot; validate_snapshot(sys.argv[1], sys.argv[2])' \
    "$ORM_SNAPSHOT" "$ORM_SNAPSHOT_MANIFEST"
  cp "$ORM_SNAPSHOT_MANIFEST" "$ORM_ARTIFACT_DIR/snapshot.json"
  "${compose[@]}" exec -T database pg_restore --no-owner --no-acl --exit-on-error -U orm_profile -d orm_profile <"$ORM_SNAPSHOT" >"$ORM_ARTIFACT_DIR/restore.log" 2>&1
fi
status=0
"${compose[@]}" run --rm -T --user "$(id -u):$(id -g)" core uv run --frozen --no-sync python -m tests.performance.orm.runner "$operation" "$@" >"$ORM_ARTIFACT_DIR/runner.log" 2>&1 || status=$?
"${compose[@]}" logs --no-color >"$ORM_ARTIFACT_DIR/compose.log" 2>&1
cat "$ORM_ARTIFACT_DIR/runner.log"
echo "ORM artifacts: $ORM_ARTIFACT_DIR"
exit "$status"
