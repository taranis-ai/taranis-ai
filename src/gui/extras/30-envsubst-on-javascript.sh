#!/bin/sh

# This script is started when Docker container starts.
# It goes through /usr/share/nginx/html/js/*.js, and replaces
# occurences of $VUE_SOMETHING by the contents of
# environment variables of that name.

set -e

ME=$(basename $0)

vue_envsubst() {
  local js_dir="${VUE_ENVSUBST_JS_DIR:-/usr/share/nginx/html/js}"

  [ -d "$js_dir" ] || return 0
  if [ ! -w "$js_dir" ]; then
    echo >&3 "$ME: ERROR: $js_dir exists, but is not writable"
    return 0
  fi

  cd "$js_dir"
  local defined_envs FILE
  defined_envs=$(printf '${%s} ' $(env | fgrep VUE_ | cut -d= -f1))

  for FILE in *.js ; do
    if [ ! -f ".$FILE.processed" ]; then
      mv "$FILE" "$FILE.orig"
      if envsubst "$defined_envs" < "$FILE.orig" > "$FILE"; then
        rm "$FILE.orig"
        touch ".$FILE.processed"
      else
        mv "$FILE.orig" "$FILE"
      fi
    fi
  done
}

vue_envsubst

exit 0
