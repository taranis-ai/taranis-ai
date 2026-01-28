"""RQ Bot Tasks

Functions for executing bots to process news items.
"""

from rq import get_current_job

import worker.bots
from worker.core_api import CoreApi
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

    logger.info(f"Starting bot task with job id {job.id if job else 'manual'}")

    # Initialize result tracking
    result_message = "Bot executed successfully"
    task_status = "SUCCESS"
    task_id = job.id if job else f"bot_{bot_id}"

    try:
        if bot_config := core_api.get_bot_config(bot_id):
            result = _execute_by_config(bot_config, filter)

            # Save successful result to database
            _save_task_result(task_id, f"bot_{bot_id}", result, task_status, core_api)
            return result

        # Bot not found
        result_message = f"Bot with id {bot_id} not found"
        task_status = "FAILURE"
        _save_task_result(task_id, f"bot_{bot_id}", {"error": result_message}, task_status, core_api)
        raise ValueError(result_message)

    except Exception as e:
        result_message = f"Bot execution failed: {str(e)}"
        task_status = "FAILURE"
        _save_task_result(task_id, f"bot_{bot_id}", {"error": result_message}, task_status, core_api)
        raise


def _execute_by_config(bot_config: dict, filter: dict | None = None):
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


def _save_task_result(job_id: str, task_name: str, result: dict, status: str, core_api):
    """Save task result to database via Core API.

    Args:
        job_id: RQ job ID
        task_name: Task identifier (e.g., 'bot_123')
        result: Result data dictionary from bot execution
        status: Task status ('SUCCESS' or 'FAILURE')
        core_api: CoreApi instance for making API calls
    """
    try:
        task_data = {"id": job_id, "task": task_name, "result": result, "status": status}
        if core_api.api_put("/worker/task-results", task_data):
            logger.debug(f"Saved task result for {task_name}: {status}")
    except Exception as e:
        logger.error(f"Failed to save task result for {task_name}: {e}")
