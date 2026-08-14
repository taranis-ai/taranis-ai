import json
from typing import Any


def parse_misp_runtime_parameters(parameters: dict[str, Any]) -> tuple[bool, dict[str, str] | None, dict[str, Any], int]:
    headers: dict[str, Any] = {"User-Agent": "TaranisAI/1.0"}
    if additional_headers := parameters.get("ADDITIONAL_HEADERS"):
        headers.update(json.loads(additional_headers))
    if user_agent := parameters.get("USER_AGENT"):
        headers["User-Agent"] = user_agent

    proxy_server = parameters.get("PROXY_SERVER")
    proxies = {protocol: proxy_server for protocol in ("http", "https", "ftp")} if proxy_server else None
    return parameters["SSL_CHECK"] == "true", proxies, headers, int(parameters["REQUEST_TIMEOUT"])
