from typing import Any


def get_simple_web_collector_url(source: dict[str, Any]) -> str:
    collector_parameters = source.get("parameters", {})
    if not isinstance(collector_parameters, dict):
        return ""
    return str(collector_parameters.get("WEB_URL") or "").strip()
