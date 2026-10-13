import os
import sys

import requests

from core.config import Config


def main() -> int:
    port = int(os.getenv("GRANIAN_PORT", "8080"))

    url = f"http://127.0.0.1:{port}{Config.APPLICATION_ROOT}api/health"

    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 503:
            services = response.json().get("services", {})
            # Keep Core reachable so workers can report recovery and admins can repair endpoints.
            if services.get("worker_endpoints") == "down" and all(
                services.get(name) in {"up", "n/a"} for name in ("database", "seed_data", "broker", "workers")
            ):
                return 0
        response.raise_for_status()
        return 0
    except (requests.RequestException, ValueError, AttributeError) as exc:
        print(f"core healthcheck failed: {exc}", file=sys.stderr)
        return 1
