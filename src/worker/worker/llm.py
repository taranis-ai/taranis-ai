import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import replace
from functools import partial
from typing import Any

from llm_bot.client import LLMClient, UpstreamLLMError
from llm_bot.tasks.llm_utils import InvalidLLMOutputError, LLMTask, MissingOutputTextError
from models.llm import LLMEndpoint
from niquests.exceptions import RequestException, Timeout
from pydantic import ValidationError
from rq import Retry
from rq.timeouts import JobTimeoutException

from worker.bot_api import BotServiceUnavailableError
from worker.llm_batch import BatchProcessor
from worker.log import logger


class LLMConfigurationError(RuntimeError):
    public_message = "Configure and enable an LLM endpoint in Admin Settings > LLM Endpoints."
    reason = "llm_not_configured"
    retryable = False

    def __init__(self):
        super().__init__(self.public_message)


class LLMTaskError(RuntimeError):
    def __init__(self, public_message: str, reason: str, *, retryable: bool = False):
        self.public_message = public_message
        self.reason = reason
        self.retryable = retryable
        super().__init__(public_message)


def get_llm_client(parameters: dict) -> LLMClient:
    endpoint = parameters.get("llm_endpoint")
    if not endpoint:
        raise LLMConfigurationError
    config = LLMEndpoint.model_validate(endpoint)
    if not config.enabled:
        raise LLMConfigurationError
    client = LLMClient(
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
        api_mode=config.api_format,
        timeout=parameters.get("REQUESTS_TIMEOUT") or config.timeout,
    )
    # The library treats an empty model as an environment fallback. Settings own it here.
    client.model = config.model
    return client


def run_llm_task[T](task: Coroutine[Any, Any, T]) -> T:
    try:
        return asyncio.run(task)
    except JobTimeoutException:
        logger.exception("LLM execution exceeded the RQ job deadline")
        raise
    except Timeout:
        logger.exception("LLM provider request timed out")
        raise LLMTaskError(
            "LLM provider request timed out. Check the endpoint and REQUESTS_TIMEOUT.", "llm_request_timeout", retryable=True
        ) from None
    except (RequestException, UpstreamLLMError):
        logger.exception("LLM provider request failed")
        raise BotServiceUnavailableError from None
    except (ValidationError, InvalidLLMOutputError, MissingOutputTextError, ValueError):
        logger.exception("LLM provider returned invalid output")
        raise LLMTaskError("LLM provider returned invalid output. Check the model and worker logs.", "llm_invalid_output") from None
    except Exception:
        logger.exception("LLM task failed")
        raise LLMTaskError("LLM processing failed. Check the worker logs for details.", "llm_processing_failed") from None


def _record_response[T](response: dict, *, parser: Callable[[dict], T], saved: dict, recovered: bool = False) -> T:
    result = parser(response)
    saved.update(response=response, recovered=recovered)
    return result


def run_llm_tasks[T](
    tasks: list[LLMTask[T]], client: LLMClient, parameters: dict, *, on_result: Callable[[int, T], None] | None = None
) -> list[T] | Retry:
    state = parameters.get("_llm_batch_state", {})
    save_state = parameters.get("_save_llm_batch_state") or (lambda: None)
    if parameters["llm_endpoint"].get("processing_mode") == "openrouter_batch":
        processor = BatchProcessor(client, state, save_state)
        results = processor.process(tasks)
        if results is None:
            return Retry(max=600, interval=300)
        for index in range(state.get("completed_items", 0), len(results)):
            if on_result:
                on_result(index, results[index])
            state["completed_items"] = index + 1
            save_state()
        return results

    responses = state.setdefault("responses", [])
    results = []
    for index, task in enumerate(tasks):
        if index < len(responses):
            saved = responses[index]
            parser = task.recover_response if saved["recovered"] else task.parse_response
            assert parser is not None
            results.append(parser(saved["response"]))
            continue
        saved = {}

        recorded_task = replace(
            task,
            parse_response=partial(_record_response, parser=task.parse_response, saved=saved),
            recover_response=partial(_record_response, parser=task.recover_response, saved=saved, recovered=True)
            if task.recover_response
            else None,
        )
        result = run_llm_task(recorded_task.run(client))
        if on_result:
            on_result(index, result)
        responses.append(saved)
        save_state()
        results.append(result)
    return results
