#!/usr/bin/env bash
set -euo pipefail

root=$(git rev-parse --show-toplevel)
dir="$root/dev/.collaboration-demo"
compose="$root/docker/compose.yml"
override="$root/dev/compose.collaboration-demo.yml"
mkdir -p "$dir"
declare -A ports=([alpha]=8081 [bravo]=8082 [charlie]=8083)
declare -A hosts=([alpha]=alpha.local.taranis.ai [bravo]=bravo.local.taranis.ai [charlie]=charlie.local.taranis.ai)
die() { echo "collaboration demo: $*" >&2; exit 1; }
env_file() { echo "$dir/$1.env"; }

make_env() {
  local name=$1 file; file=$(env_file "$name")
  [[ -e "$file" ]] && { [[ "$file" == "$dir/"* ]] || die "refusing env outside demo directory"; return; }
  python3 - "$name" "${ports[$name]}" "${hosts[$name]}" "$file" <<'PY'
import secrets, sys
name, port, host, path = sys.argv[1:]
values = {
    "COMPOSE_PROJECT_NAME": f"taranis-collab-{name}",
    "DOCKER_IMAGE_NAMESPACE": "taranis-collaboration-demo",
    "TARANIS_TAG": "branch", "TARANIS_PORT": port, "TARANIS_BASE_PATH": "/",
    "DB_DATABASE": "taranis", "DB_USER": "taranis",
    "POSTGRES_PASSWORD": secrets.token_urlsafe(32), "REDIS_PASSWORD": secrets.token_urlsafe(32),
    "JWT_SECRET_KEY": secrets.token_urlsafe(32), "API_KEY": secrets.token_urlsafe(32),
    "BOT_API_KEY": secrets.token_urlsafe(32), "CENTRIFUGO_API_KEY": secrets.token_urlsafe(32),
    "CENTRIFUGO_CONNECT_PROXY_SECRET": secrets.token_urlsafe(32), "REALTIME_ENABLED": "true",
    "COLLABORATION_INSTANCE_URL": f"http://{host}",
    "CENTRIFUGO_ALLOWED_ORIGINS": f"http://{host}", "TARANIS_CORE_URL": "http://core:8080/api",
    "TARANIS_CORE_UPSTREAM": "core:8080", "TARANIS_FRONTEND_UPSTREAM": "frontend:8080",
    "TARANIS_REALTIME_UPSTREAM": "centrifugo:8000",
}
with open(path, "x", encoding="utf-8") as f:
    f.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
PY
}

check() {
  command -v docker >/dev/null || die "docker is required"
  command -v python3 >/dev/null || die "python3 is required"
  docker compose version >/dev/null || die "Docker Compose is required"
  [[ -f "$root/dev/nginx.collaboration-demo.conf" ]] || die "missing host Nginx sample"
  rg -q 'alpha.local.taranis.ai|bravo.local.taranis.ai|charlie.local.taranis.ai' "$root/dev/nginx.collaboration-demo.conf" || die "invalid host Nginx sample"
  for name in alpha bravo charlie; do make_env "$name"; done
  for host in "${hosts[@]}"; do getent hosts "$host" >/dev/null || die "$host does not resolve; add the documented /etc/hosts entries"; done
}
check_ports() {
  python3 - "${ports[alpha]}" "${ports[bravo]}" "${ports[charlie]}" <<'PY'
import socket, sys
for value in sys.argv[1:]:
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", int(value))) == 0:
            raise SystemExit(f"demo port {value} is already in use")
PY
}
run() { local name=$1; shift; docker compose --project-name "taranis-collab-$name" --env-file "$(env_file "$name")" -f "$compose" -f "$override" "$@"; }
all() { for name in alpha bravo charlie; do run "$name" "$@"; done; }
usage() { echo "usage: $0 build|up|down|reset|restart|status|start NAME|stop NAME|logs NAME [SERVICE]"; }

case "${1:-}" in
  build) check; tag=$(git branch --show-current | tr '/ ' '--'); sed -i "s/^TARANIS_TAG=.*/TARANIS_TAG=$tag/" "$dir"/*.env; all build core frontend workers ingress ;;
  up) check; check_ports; all up -d --wait; echo "alpha http://alpha.local.taranis.ai | bravo http://bravo.local.taranis.ai | charlie http://charlie.local.taranis.ai" ;;
  down) check; all down ;;
  reset) check; all down -v --remove-orphans ;;
  restart) check; all restart ;;
  status) check; all ps ;;
  start|stop) check; [[ -n "${2:-}" && -n "${ports[$2]:-}" ]] || die "expected alpha, bravo, or charlie"; run "$2" "$1" ;;
  logs) check; [[ -n "${2:-}" && -n "${ports[$2]:-}" ]] || die "expected alpha, bravo, or charlie"; run "$2" logs -f "${3:-}" ;;
  *) usage; exit 2 ;;
esac
