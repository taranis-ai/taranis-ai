from prefect import flow, task
from worker.log import logger
from models.prefect import BotTaskRequest
from worker.core_api import CoreApi
import worker.bots


@task
def store_task_result(bot_id: str, result: dict, status: str = "SUCCESS"):
    """Store bot task result in the Task table via Core API"""
    core_api = CoreApi()
    task_id = f"bot_task_{bot_id}"

    task_data = {
        "task_id": task_id,
        "status": status,
        "result": result,
        "task": f"bot_task_{bot_id}",
    }

    logger.info(f"[bot_task] Storing result for task {task_id}: {result}")
    core_api.store_task_result(task_data)

    # Trigger SSE event to notify frontend that news items have been updated
    core_api.trigger_sse_news_items_updated()


@task
def get_bot_config(bot_id: int):
    """Get bot configuration from CoreApi"""
    logger.info(f"[bot_task] Getting bot config for {bot_id}")

    core_api = CoreApi()
    if bot_config := core_api.get_bot_config(bot_id):
        return bot_config
    else:
        raise ValueError(f"Bot with id {bot_id} not found")


@task
def execute_bot_by_config(bot_config: dict, filter_params: dict | None = None):
    """Execute bot using config"""
    logger.info("[bot_task] Executing bot by config")

    bot_type = bot_config.get("type")
    if not bot_type:
        raise ValueError("Bot has no type")

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

    bot = bots.get(bot_type)
    if not bot:
        raise ValueError("Bot type not implemented")

    bot_params = bot_config.get("parameters")
    if not bot_params:
        raise ValueError("Bot has no parameters")

    if filter_params:
        bot_params["filter"] = filter_params

    return bot.execute(bot_params)


@flow(name="bot-task-flow")
def bot_task_flow(request: BotTaskRequest):
    try:
        logger.info("[bot_task_flow] Starting bot task")

        # Get bot config
        bot_config = get_bot_config(request.bot_id)

        # Execute bot
        result = execute_bot_by_config(bot_config, request.filter)

        logger.info("[bot_task_flow] Bot task completed successfully")

        return result

    except Exception:
        logger.exception("[bot_task_flow] Bot task failed")
        raise
