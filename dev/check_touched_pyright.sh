#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

mode="changed"
if [[ "${1:-}" == "--staged" ]]; then
  mode="staged"
  shift
elif [[ "${1:-}" == "--all" ]]; then
  mode="all"
  shift
fi

changed_file="$(mktemp)"
candidate_file="$(mktemp)"
trap 'rm -f "$changed_file" "$candidate_file"' EXIT

case "$mode" in
  staged)
    git diff --cached --name-only --diff-filter=ACMRTUXB
    ;;
  all)
    git ls-files
    git ls-files --others --exclude-standard
    ;;
  *)
    git diff --name-only --diff-filter=ACMRTUXB
    git diff --cached --name-only --diff-filter=ACMRTUXB
    git ls-files --others --exclude-standard
    ;;
esac | awk 'NF && !seen[$0]++' > "$changed_file"

if (($#)); then
  for path in "$@"; do
    path="${path#"$repo_root"/}"
    path="${path#./}"
    printf '%s\n' "$path"
  done
else
  cat "$changed_file"
fi > "$candidate_file"

files=()
while IFS= read -r file; do
  case "$file" in
    src/core/*.py|src/frontend/*.py|src/models/*.py|src/worker/*.py)
      [[ -f "$file" ]] && files+=("$file")
      ;;
  esac
done < <(grep -Fxf "$changed_file" "$candidate_file" | awk 'NF && !seen[$0]++')

if ((${#files[@]} == 0)); then
  echo "pyright: no Python files"
  exit 0
fi

status=0
for component in core frontend models worker; do
  rel_files=()
  for file in "${files[@]}"; do
    case "$file" in
      src/"$component"/*.py)
        rel_files+=("${file#src/$component/}")
        ;;
    esac
  done

  if ((${#rel_files[@]} == 0)); then
    continue
  fi

  echo "pyright: src/$component"
  (
    cd "src/$component"
    uv run --frozen --all-extras pyright "${rel_files[@]}"
  ) || status=$?
done

exit "$status"
