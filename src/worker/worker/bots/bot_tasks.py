"""RQ Bot Tasks

Functions for executing bots to process news items.
"""

from rq import get_current_job

import worker.bots
from worker.core_api import CoreApi, build_failure_task_result, build_success_task_result
from worker.log import logger


def bot_task(bot_id: str, filter: dict | None = None):
    """Execute a bot to process news items.

    Args:
        bot_id: ID of the bot to execute
        filter: Optional filter to limit which items the bot processes

    Returns:
        Result from the bot execution

    Raises:
        ValueError: If bot not found or misconfigured
    """
    job = get_current_job()
    core_api = CoreApi()
    task_name = f"bot_{bot_id}"
    task_id = job.id if job else task_name
    worker_type = "BOT_TASK"

    logger.info(f"Starting bot task with job id {job.id if job else 'manual'}")

    try:
        bot_config = core_api.get_bot_config(bot_id)
        if not bot_config:
            raise ValueError(f"Bot with id {bot_id} not found")

        worker_type = bot_config.get("type", worker_type).upper()
        bot_result = _execute_by_config(bot_config, filter, bot_id)
        if bot_result is None:
            raise RuntimeError(f"Bot {bot_id} returned no result")
        core_api.save_task_result(
            task_id,
            task_name,
            "SUCCESS",
            worker_id=bot_id,
            worker_type=worker_type,
            result=build_success_task_result(
                default_message=f"Bot {bot_id} executed successfully",
                output=bot_result,
                base_data={"bot_id": bot_id},
                merge_dict_data=False,
            ),
        )
        return (
            {"worker_id": bot_id, "worker_type": worker_type, **bot_result}
            if isinstance(bot_result, dict)
            else {"worker_id": bot_id, "worker_type": worker_type, "result": bot_result}
        )
    except Exception as exc:
        error_message = str(exc)
        if not (isinstance(exc, ValueError) and error_message == f"Bot with id {bot_id} not found"):
            error_message = f"Bot execution failed: {error_message}"
        core_api.save_task_result(
            task_id,
            task_name,
            "FAILURE",
            worker_id=bot_id,
            worker_type=worker_type,
            result=build_failure_task_result(
                error_message,
                reason=(
                    "bot_not_found"
                    if isinstance(exc, ValueError) and str(exc) == f"Bot with id {bot_id} not found"
                    else "bot_empty_result"
                    if str(exc) == f"Bot {bot_id} returned no result"
                    else "bot_execution_failed"
                ),
                data={"bot_id": bot_id},
            ),
        )
        raise


def _execute_by_config(bot_config: dict, filter: dict | None = None, bot_id: str | None = None):
    """Execute a bot based on its configuration.

    Args:
        bot_config: Bot configuration dictionary
        filter: Optional filter for bot execution

    Returns:
        Result from the bot execution
    """
    bots = {
        "analyst_bot": worker.bots.AnalystBot(),
        "grouping_bot": worker.bots.GroupingBot(),
        "tagging_bot": worker.bots.TaggingBot(),
        "wordlist_bot": worker.bots.WordlistBot(),
        "nlp_bot": worker.bots.NLPBot(),
        "story_bot": worker.bots.StoryBot(),
        "ioc_bot": worker.bots.IOCBot(),
        "summary_bot": worker.bots.SummaryBot(),
        "sentiment_analysis_bot": worker.bots.SentimentAnalysisBot(),
        "cybersec_classifier_bot": worker.bots.CyberSecClassifierBot(),
    }

    bot_type = bot_config.get("type")
    if not bot_type:
        raise ValueError("Bot has no type")

    bot = bots.get(bot_type)
    if not bot:
        raise ValueError(f"Bot type '{bot_type}' not implemented")
    bot_params = bot_config.get("parameters")
    if not bot_params:
        raise ValueError("Bot has no parameters")

    if filter:
        bot_params["filter"] = filter

    return bot.execute(bot_params)
