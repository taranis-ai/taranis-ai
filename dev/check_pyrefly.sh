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

candidate_file="$(mktemp)"
trap 'rm -f "$candidate_file"' EXIT

if (($#)); then
  for path in "$@"; do
    path="${path#"$repo_root"/}"
    path="${path#./}"
    if [[ -d "$path" ]]; then
      find "$path" -type f -name '*.py'
    else
      printf '%s\n' "$path"
    fi
  done
else
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
  esac
fi > "$candidate_file"

files=()
while IFS= read -r file; do
  case "$file" in
    src/core/core/*.py|src/frontend/frontend/*.py|src/models/models/*.py|src/worker/worker/*.py)
      [[ -f "$file" ]] && files+=("$file")
      ;;
  esac
done < <(awk 'NF && !seen[$0]++' "$candidate_file")

if ((${#files[@]} == 0)); then
  echo "pyrefly: no Python files"
  exit 0
fi

status=0
for component in core frontend models worker; do
  rel_files=()
  for file in "${files[@]}"; do
    case "$file" in
      src/"$component"/*.py)
        rel_files+=("${file#src/"$component"/}")
        ;;
    esac
  done

  if ((${#rel_files[@]} == 0)); then
    continue
  fi

  echo "pyrefly: src/$component"
  (
    cd "src/$component"
    uvx pyrefly check --summarize-errors "${rel_files[@]}"
  ) || status=$?
done

exit "$status"
