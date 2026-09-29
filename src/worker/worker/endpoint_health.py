"""Small synthetic requests exercise the same endpoints used by bot jobs."""

from niquests.exceptions import RequestException

from worker.config import Config
from worker.core_api import CoreApi
from worker.http_client import http_request, http_session_scope
from worker.log import logger
from worker.telemetry import instrument_job


@instrument_job
@http_session_scope()
def check_endpoint(kind: str, endpoint_id: str, generation: str):
    core = CoreApi()
    route = f"/worker/endpoint-health/{kind}/{endpoint_id}"
    try:
        snapshot = core.api_get(route, {"generation": generation})
        if snapshot is None:
            raise RuntimeError("Could not load endpoint check configuration")
        if snapshot.get("skip"):
            return
        healthy = probe(kind, snapshot["config"])
        if core.api_post(route, {"generation": generation, "healthy": healthy}) is None:
            raise RuntimeError("Could not save endpoint check result")
    except RequestException:
        logger.exception("Endpoint check could not contact Core")
        raise RuntimeError("Endpoint check could not contact Core") from None
    if not healthy:
        raise RuntimeError("Endpoint check failed")


def probe(kind: str, config: dict) -> bool:
    text = "Reply with OK."
    chat = kind == "llm" and config["api_format"] == "chat_completions"
    if kind == "llm":
        url = f"{config['base_url']}/{'chat/completions' if chat else 'responses'}"
        payload = {"messages": [{"role": "user", "content": text}]} if chat else {"input": text, "store": False}
        if config.get("model"):
            payload["model"] = config["model"]
        api_key = config.get("api_key", "")
        timeout = min(config["timeout"], 120)
    else:
        parameters = config["parameters"]
        url = f"{parameters['BOT_ENDPOINT']}/"
        payload = {"text": "This is an endpoint connectivity test."}
        api_key = parameters.get("BOT_API_KEY", Config.BOT_API_KEY)
        timeout = min(parameters.get("REQUESTS_TIMEOUT") or Config.REQUESTS_TIMEOUT, 120)
    try:
        response = http_request(
            "POST",
            url,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=timeout,
            verify=True if kind == "llm" else Config.SSL_VERIFICATION,
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or "error" in result:
            return False
        if kind == "llm":
            if chat:
                return any(
                    isinstance(choice, dict) and isinstance(choice.get("message"), dict) and bool(choice["message"].get("content"))
                    for choice in result.get("choices", [])
                )
            return result.get("status") in {None, "completed"} and any(
                isinstance(item, dict)
                and item.get("type") == "message"
                and any(
                    isinstance(content, dict) and content.get("type") == "output_text" and bool(content.get("text"))
                    for content in item.get("content", [])
                )
                for item in result.get("output", [])
            )
        if config["type"] == "sentiment_analysis_bot":
            sentiment = result.get("sentiment", result)
            return isinstance(sentiment, dict) and bool(sentiment.get("label")) and isinstance(sentiment.get("score"), (int, float))
        if config["type"] == "cybersec_classifier_bot":
            return isinstance(result.get("cybersecurity"), (int, float))
        return all(isinstance(value, str) for value in result.values())
    except (RequestException, ValueError, TypeError):
        logger.exception(f"Endpoint probe failed for {kind}")
        return False
