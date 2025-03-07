from prefect import flow, task
import worker.bots
from worker.log import logger
from worker.core_api import CoreApi
from worker.bots.base_bot import BaseBot


@task(retries=3, retry_delay_seconds=60, timeout_seconds=18000)
def execute_bot(bot_config: dict, filter: dict | None = None):
    bot_type = bot_config.get("type")
    if not bot_type:
        raise ValueError("Bot has no type")

    bots: dict[str, BaseBot] = {
        "analyst_bot": worker.bots.AnalystBot(),
        "grouping_bot": worker.bots.GroupingBot(),
        "tagging_bot": worker.bots.TaggingBot(),
        "wordlist_bot": worker.bots.WordlistBot(),
        "nlp_bot": worker.bots.NLPBot(),
        "story_bot": worker.bots.StoryBot(),
        "ioc_bot": worker.bots.IOCBot(),
        "summary_bot": worker.bots.SummaryBot(),
        "sentiment_analysis_bot": worker.bots.SentimentAnalysisBot(),
    }

    bot: BaseBot | None = bots.get(bot_type)
    if not bot:
        raise ValueError("Bot type not implemented")

    bot_params = bot_config.get("parameters")
    if not bot_params:
        raise ValueError("Bot has no parameters")

    if filter:
        bot_params["filter"] = filter

    return bot.execute(bot_params)


@flow(name="bot_task")
def bot_task(bot_id: str, filter: dict | None = None):
    logger.info("Starting bot task bot_task")
    core_api = CoreApi()
    bot_config = core_api.get_bot_config(bot_id)

    if not bot_config:
        logger.error(f"Bot with id {bot_id} not found")
        return {"error": f"Bot with id {bot_id} not found"}

    return execute_bot(bot_config, filter)
