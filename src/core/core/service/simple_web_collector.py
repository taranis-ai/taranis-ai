from typing import Any


def get_simple_web_collector_url(source: dict[str, Any]) -> str:
    return str(source.get("parameters", {}).get("WEB_URL") or "").strip()
