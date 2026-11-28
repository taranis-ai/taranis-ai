"""Small synthetic requests exercise the same endpoints used by bot jobs."""

from llm_bot.client import UpstreamLLMError
from llm_bot.decisions_client import ChoiceQuestion
from llm_bot.tasks.llm_utils import LLMTask
from models.llm import EmbeddingDimensionMismatch, EmbeddingDimensions, EndpointFormatCheck, LLMProvider
from niquests.exceptions import ConnectionError, HTTPError, RequestException, SSLError, Timeout
from pydantic import TypeAdapter
from rq import Retry, get_current_job

from worker.core_api import CoreApi
from worker.embedding import create_embedding
from worker.http_client import http_request, http_session_scope
from worker.llm import LLMTaskError, get_decisions_client, get_llm_client, run_llm_tasks
from worker.llm_batch import BatchExecutionError
from worker.log import logger
from worker.task_events import task_started
from worker.telemetry import instrument_job


@instrument_job
@http_session_scope()
@task_started
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
        details = {}
        healthy = probe(kind, config, state, job.save_meta if job else None, snapshot.get("extraction"), details)
        if isinstance(healthy, Retry):
            return healthy
        if state is not None:
            assert job is not None
            job.meta.pop("llm_batch_probe", None)
            job.save_meta()
        if core.api_post(route, {"check_id": check_id, "healthy": healthy, **details}) is None:
            raise RuntimeError("Could not save endpoint check result")
    except RequestException:
        logger.exception("Endpoint check could not contact Core")
        raise RuntimeError("Endpoint check could not contact Core") from None
    if not healthy:
        failures = [
            EndpointFormatCheck.model_validate(check).public_message(api_format)
            for api_format, check in details.get("formats", {}).items()
            if check["status"] == "down"
        ]
        raise RuntimeError("Endpoint check failed. " + " ".join(failures))


def probe(
    kind: str,
    config: dict,
    batch_state: dict | None = None,
    save_batch_state=None,
    extraction: dict | None = None,
    details: dict | None = None,
) -> bool | Retry:
    if details is None:
        details = {}
    if kind != "llm":
        return False
    try:
        if "api_formats" in config:
            provider = LLMProvider.model_validate({"name": "Probe", **config})
            formats = {api_format: provider.for_format(api_format) for api_format in provider.api_formats}
        else:
            formats = {config["api_format"]: config}
    except (ValueError, TypeError, KeyError):
        logger.exception("Invalid endpoint check configuration")
        return False
    healthy = True
    pending = None
    checks = details.setdefault("formats", {})
    for api_format, endpoint in formats.items():
        state = batch_state.setdefault(api_format, {}) if batch_state is not None else None
        if state is not None and "healthy" in state:
            result = state["healthy"]
            format_details = state
        else:
            format_details = {}
            result = _probe_format(endpoint, state, save_batch_state, extraction, format_details)
            if state is not None and not isinstance(result, Retry):
                state.update(healthy=result, **format_details)
                if save_batch_state:
                    save_batch_state()
        check = {"status": "pending" if isinstance(result, Retry) else "up" if result else "down"}
        if not result:
            check["failure_reason"] = format_details.get("failure_reason", "invalid_response")
            if format_details.get("http_status") is not None:
                check["http_status"] = format_details["http_status"]
        checks[api_format] = check
        if "embedding_dimensions" in format_details:
            details["embedding_dimensions"] = format_details["embedding_dimensions"]
        if isinstance(result, Retry):
            pending = result
        else:
            healthy = healthy and result
    return pending if pending is not None else healthy


def _probe_format(config: dict, batch_state: dict | None, save_batch_state, extraction: dict | None, details: dict) -> bool | Retry:
    text = "Reply with OK."
    try:
        if config["api_format"] in {"systemone", "openai_decisions"}:
            client = get_decisions_client({"llm_endpoint": {"name": "Probe", **config}})
            questions = {"probe": ChoiceQuestion("Choose OK.", {"OK": "The requested answer", "other": "Any other answer"})}
            response = http_request(
                "POST",
                client.url,
                json=client.build_request(text, questions),
                headers={"Authorization": f"Bearer {client.api_key}"} if client.api_key else {},
                timeout=min(client.timeout, 120),
                verify=True,
            )
            response.raise_for_status()
            client.parse_response(response.json(), questions)
            return True
        if config["api_format"] == "embeddings":
            vector = create_embedding(
                "Synthetic endpoint check", {**config, "timeout": min(config["timeout"], 120)}, config.get("dimensions")
            )
            try:
                details["embedding_dimensions"] = TypeAdapter(EmbeddingDimensions).validate_python(len(vector))
            except ValueError:
                details["failure_reason"] = "embedding_dimensions_unsupported"
                return False
            return True
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
        payload: dict = {"messages": [{"role": "user", "content": text}]} if chat else {"input": text, "store": False}
        if config.get("model"):
            payload["model"] = config["model"]
        if extraction and extraction["api_format"] == config["api_format"] and extraction.get("reasoning_effort") is not None:
            if chat:
                payload["reasoning_effort"] = extraction["reasoning_effort"]
            else:
                payload["reasoning"] = {"effort": extraction["reasoning_effort"]}
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
    except EmbeddingDimensionMismatch:
        logger.exception("Endpoint embedding dimension check failed")
        details["failure_reason"] = "embedding_dimensions_mismatch"
        return False
    except HTTPError as exc:
        logger.exception("Endpoint HTTP check failed")
        status = (exc.response.status_code or 0) if exc.response is not None else 0
        if 400 <= status <= 599:
            details["http_status"] = status
        reason = {
            401: "authentication_failed",
            402: "billing_required",
            403: "forbidden",
            404: "not_found",
            408: "timeout",
            429: "rate_limited",
        }.get(status, "service_unavailable" if status >= 500 else "http_error")
        if status in {400, 422}:
            reason = "request_rejected" if config.get("model") else "model_missing"
        details["failure_reason"] = reason
    except Timeout:
        logger.exception("Endpoint check timed out")
        details["failure_reason"] = "timeout"
    except SSLError:
        logger.exception("Endpoint TLS check failed")
        details["failure_reason"] = "tls_failed"
    except (ConnectionError, RequestException):
        logger.exception("Endpoint connection check failed")
        details["failure_reason"] = "connection_failed"
    except BatchExecutionError:
        logger.exception("Endpoint batch check failed")
        details["failure_reason"] = "batch_failed"
    except LLMTaskError:
        logger.exception("Endpoint inference check failed")
        details["failure_reason"] = "provider_error"
    except (ValueError, TypeError, KeyError, IndexError, UpstreamLLMError):
        logger.exception("Endpoint output check failed")
        details["failure_reason"] = "invalid_response"
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
