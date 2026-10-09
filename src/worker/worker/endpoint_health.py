"""Small synthetic requests exercise the same endpoints used by bot jobs."""

from llm_bot.tasks.llm_utils import LLMTask
from niquests.exceptions import RequestException
from rq import Retry, get_current_job

from worker.core_api import CoreApi
from worker.http_client import http_request, http_session_scope
from worker.llm import get_llm_client, run_llm_tasks
from worker.llm_batch import BatchExecutionError
from worker.log import logger
from worker.telemetry import instrument_job


@instrument_job
@http_session_scope()
def check_endpoint(kind: str, endpoint_id: str, check_id: str):
    core = CoreApi()
    route = f"/worker/endpoint-health/{kind}/{endpoint_id}"
    try:
        snapshot = core.api_get(route, {"check_id": check_id})
        if snapshot is None:
            raise RuntimeError("Could not load endpoint check configuration")
        if snapshot.get("skip"):
            return
        job = get_current_job()
        config = snapshot["config"]
        state = None
        if config.get("processing_mode") == "openrouter_batch":
            if not job:
                raise RuntimeError("Batch endpoint checks require a queued job")
            state = job.meta.setdefault("llm_batch_probe", {})
        healthy = probe(kind, config, state, job.save_meta if job else None)
        if isinstance(healthy, Retry):
            return healthy
        if state is not None:
            assert job is not None
            job.meta.pop("llm_batch_probe", None)
            job.save_meta()
        if core.api_post(route, {"check_id": check_id, "healthy": healthy}) is None:
            raise RuntimeError("Could not save endpoint check result")
    except RequestException:
        logger.exception("Endpoint check could not contact Core")
        raise RuntimeError("Endpoint check could not contact Core") from None
    if not healthy:
        raise RuntimeError("Endpoint check failed")


def probe(kind: str, config: dict, batch_state: dict | None = None, save_batch_state=None) -> bool | Retry:
    text = "Reply with OK."
    if kind != "llm":
        return False
    try:
        chat = config["api_format"] == "chat_completions"
        if config.get("processing_mode") == "openrouter_batch":
            parameters = {"llm_endpoint": config, "_llm_batch_state": batch_state, "_save_llm_batch_state": save_batch_state}
            client = get_llm_client(parameters)
            task = LLMTask("probe", text, "Reply briefly.", None, lambda response: response)
            results = run_llm_tasks([task], client, parameters)
            if isinstance(results, Retry):
                return results
            result = results[0]
            return bool(result.get("output_text")) if chat else _valid_responses_result(result)
        url = f"{config['base_url']}/{'chat/completions' if chat else 'responses'}"
        payload = {"messages": [{"role": "user", "content": text}]} if chat else {"input": text, "store": False}
        if config.get("model"):
            payload["model"] = config["model"]
        api_key = config.get("api_key", "")
        timeout = min(config["timeout"], 120)
        response = http_request(
            "POST",
            url,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=timeout,
            verify=True,
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or result.get("error") is not None:
            return False
        if chat:
            return any(
                isinstance(choice, dict) and isinstance(choice.get("message"), dict) and bool(choice["message"].get("content"))
                for choice in result.get("choices", [])
            )
        return _valid_responses_result(result)
    except (RequestException, ValueError, TypeError, KeyError, BatchExecutionError):
        logger.exception(f"Endpoint probe failed for {kind}")
        return False


def _valid_responses_result(result: dict) -> bool:
    return result.get("status") in {None, "completed"} and any(
        isinstance(item, dict)
        and item.get("type") == "message"
        and any(
            isinstance(content, dict) and content.get("type") == "output_text" and bool(content.get("text"))
            for content in item.get("content", [])
        )
        for item in result.get("output", [])
    )
