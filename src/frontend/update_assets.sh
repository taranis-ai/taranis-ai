#!/bin/bash

set -euo pipefail

SCRIPT_PATH="$( readlink -f "${BASH_SOURCE[0]}" )"
SCRIPT_DIR="$( dirname "$SCRIPT_PATH" )"
static_dir="${SCRIPT_DIR}/frontend/static"

JS_STATIC_DIR="${static_dir}/vendor/js"
CSS_STATIC_DIR="${static_dir}/vendor/css"
ASSETS_STATIC_DIR="${static_dir}/vendor/assets"

mkdir -p "$JS_STATIC_DIR" "$CSS_STATIC_DIR" "$ASSETS_STATIC_DIR"

# Define URLs and target directories
declare -A files=(
  ["https://cdn.jsdelivr.net/npm/tom-select/dist/css/tom-select.css"]="${CSS_STATIC_DIR}/tom-select.css"
  ["https://cdn.jsdelivr.net/npm/tom-select/dist/js/tom-select.complete.min.js"]="${JS_STATIC_DIR}/tom-select.complete.min.js"
  ["https://cdn.jsdelivr.net/npm/tom-select/dist/js/tom-select.complete.min.js.map"]="${JS_STATIC_DIR}/tom-select.complete.min.js.map"
  ["https://eugit.opencloud.lu/MISP/MISP/raw/commit/be88ddc16d55013651c1e11635b1062bea9a487a/INSTALL/logos/misp-logo.svg"]="${ASSETS_STATIC_DIR}/misp-logo.svg"
  ["https://cdn.jsdelivr.net/npm/alpinejs/dist/cdn.min.js"]="${JS_STATIC_DIR}/alpinejs.min.js"
  ["https://cdn.jsdelivr.net/npm/fuse.js/dist/fuse.js"]="${JS_STATIC_DIR}/fuse.js"
  ["https://cdn.jsdelivr.net/npm/htmx.org/dist/htmx.min.js"]="${JS_STATIC_DIR}/htmx.min.js"
  ["https://github.com/saadeghi/daisyui/releases/latest/download/daisyui.js"]="${JS_STATIC_DIR}/daisyui.js"
  ["https://registry.npmjs.org/monaco-editor/-/monaco-editor-0.52.2.tgz"]="${JS_STATIC_DIR}/monaco-editor-0.52.2.tgz"
)

# Download the latest versions
for url in "${!files[@]}"; do
  target="${files[$url]}"
  echo "Downloading $url to $target"
  curl --retry 3 --retry-delay 5 --fail --silent --show-error --location "$url" -o "$target"
done

pushd $JS_STATIC_DIR > /dev/null
mkdir -p vs
tar -xzf monaco-editor-0.52.2.tgz --strip-components=2 package/min/vs
rm -f monaco-editor-0.52.2.tgz
popd > /dev/null

echo "All files downloaded successfully."
