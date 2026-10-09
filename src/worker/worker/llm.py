import asyncio
from collections.abc import Coroutine
from typing import Any

from llm_bot.client import LLMClient, UpstreamLLMError
from llm_bot.tasks.llm_utils import LLMTask
from models.llm import LLMEndpoint
from niquests.exceptions import RequestException
from rq import Retry

from worker.bot_api import BotServiceUnavailableError
from worker.llm_batch import BatchProcessor
from worker.log import logger


class LLMConfigurationError(RuntimeError):
    public_message = "Configure an LLM endpoint in Admin Settings > LLM Endpoints."
    reason = "llm_not_configured"
    retryable = False

    def __init__(self):
        super().__init__(self.public_message)


def get_llm_client(parameters: dict) -> LLMClient:
    endpoint = parameters.get("llm_endpoint")
    if not endpoint:
        raise LLMConfigurationError
    config = LLMEndpoint.model_validate(endpoint)
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
    except (RequestException, UpstreamLLMError):
        logger.exception("LLM provider request failed")
        raise BotServiceUnavailableError from None
    except Exception:
        logger.exception("LLM task failed")
        raise RuntimeError("LLM task failed") from None


def run_llm_tasks[T](tasks: list[LLMTask[T]], client: LLMClient, parameters: dict) -> list[T] | Retry:
    if parameters["llm_endpoint"].get("processing_mode") == "openrouter_batch":
        processor = BatchProcessor(client, parameters["_llm_batch_state"], parameters["_save_llm_batch_state"])
        results = processor.process(tasks)
        return Retry(max=600, interval=300) if results is None else results
    return [run_llm_task(task.run(client)) for task in tasks]
