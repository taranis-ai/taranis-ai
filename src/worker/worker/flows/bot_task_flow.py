from prefect import flow, task
from core.log import logger
from models.bot import BotTaskRequest
from core.model.bot import Bot
from worker.bots.registry import BOT_REGISTRY
import json


@task
def fetch_bot_info(bot_id: int):
    logger.info(f"[bot_task] Fetching bot {bot_id}")

    bot = Bot.get(bot_id)
    if not bot:
        raise ValueError(f"Bot {bot_id} not found")

    return bot


@task
def parse_filters(filter_dict: dict | None):
    """Parse and prepare filters for bot execution"""
    if not filter_dict:
        return {}

    logger.info(f"[bot_task] Parsing filters: {filter_dict}")

    parsed_filters = {}
    for key, value in filter_dict.items():
        if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
            parsed_filters[key] = json.loads(value)
        else:
            parsed_filters[key] = value

    return parsed_filters


@task
def execute_bot_logic(bot: Bot, filters: dict):
    logger.info(f"[bot_task] Executing bot {bot.id} with filters: {filters}")

    bot_class = BOT_REGISTRY.get(bot.type)
    if not bot_class:
        raise ValueError(f"Unsupported bot type: {bot.type}")

    bot_instance = bot_class(bot)

    result = bot_instance.execute(filters=filters) if filters else bot_instance.execute()

    logger.info(f"[bot_task] Bot {bot.id} executed successfully")
    return result


@task
def update_bot_execution_stats(bot: Bot, result):
    logger.info(f"[bot_task] Updating execution stats for bot {bot.id}")

    bot.update_last_execution()
    if result:
        bot.log_execution_result(result)

    return bot


@flow(name="bot-task-flow")
def bot_task_flow(request: BotTaskRequest):
    try:
        logger.info(f"[bot_task_flow] Starting execution of bot {request.bot_id}")

        bot = fetch_bot_info(request.bot_id)
        filters = parse_filters(request.filter)
        result = execute_bot_logic(bot, filters)
        bot = update_bot_execution_stats(bot, result)

        logger.info(f"[bot_task_flow] Successfully executed bot {request.bot_id}")
        return {
            "message": f"Executing Bot {request.bot_id} scheduled",
            "id": request.bot_id,
            "result": result,
        }

    except Exception as e:
        logger.exception(f"[bot_task_flow] Failed to execute bot {request.bot_id}")
        return {
            "error": "Could not reach rabbitmq",
            "details": str(e),
        }
