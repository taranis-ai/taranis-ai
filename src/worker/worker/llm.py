import asyncio
from collections.abc import Coroutine
from typing import Any, cast

from llm_bot.client import LLMClient, UpstreamLLMError
from models.llm import LLMEndpoint
from niquests.exceptions import RequestException

from worker.bot_api import BotServiceUnavailableError
from worker.llm_batch import BatchExecutionError, BatchLLMClient, BatchPending
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
    client_type = BatchLLMClient if config.processing_mode == "openrouter_batch" else LLMClient
    batch_options = {"state": parameters["_llm_batch_state"]} if config.processing_mode == "openrouter_batch" else {}
    client = client_type(
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
        api_mode=config.api_format,
        timeout=parameters.get("REQUESTS_TIMEOUT") or config.timeout,
        **batch_options,
    )
    # The library treats an empty model as an environment fallback. Settings own it here.
    client.model = config.model
    if isinstance(client, BatchLLMClient):
        client.poll()
    return client


def run_llm_task[T](task: Coroutine[Any, Any, T]) -> T:
    try:
        return asyncio.run(task)
    except (BatchPending, BatchExecutionError):
        raise
    except (RequestException, UpstreamLLMError):
        logger.exception("LLM provider request failed")
        raise BotServiceUnavailableError from None
    except Exception:
        logger.exception("LLM task failed")
        raise RuntimeError("LLM task failed") from None


def run_llm_tasks[T](tasks: list[Coroutine[Any, Any, T]], client: LLMClient) -> list[T]:
    async def run():
        if isinstance(client, BatchLLMClient):
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, BaseException) and not isinstance(result, BatchPending):
                    raise result
            for result in results:
                if isinstance(result, BatchPending):
                    raise result
            return cast(list[T], results)
        try:
            return [await task for task in tasks]
        finally:
            for task in tasks:
                task.close()

    return run_llm_task(run())
