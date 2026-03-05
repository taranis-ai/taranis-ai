import os
import sys

import requests

from core.config import Config


def main() -> int:
    port = int(os.getenv("GRANIAN_PORT", "8080"))

    url = f"http://127.0.0.1:{port}{Config.APPLICATION_ROOT}api/isalive"

    try:
        requests.get(url, timeout=5).raise_for_status()
        return 0
    except Exception as exc:
        print(f"core healthcheck failed: {exc}", file=sys.stderr)
        return 1
