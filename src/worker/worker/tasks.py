from celery import shared_task

from worker.log import logger
from worker.core_api import CoreApi
import worker.bots

bots = {
    "ANALYST_BOT": worker.bots.AnalystBot(),
    "GROUPING_BOT": worker.bots.GroupingBot(),
    "NLP_BOT": worker.bots.NLPBot(),
    "TAGGING_BOT": worker.bots.TaggingBot()
}

@shared_task
def collect(source_id: str):
    import worker.collectors as collectors

    core_api = CoreApi()
    source = core_api.get_osint_source(source_id)
    if not source:
        logger.error(f"Source with id {source_id} not found")
        return

    if source["type"] == "RSS_COLLECTOR":
        return collectors.RSSCollector().collect(source)
    return "Not implemented"

@shared_task
def execute_bot(bot_id: str, filter: dict | None = None):

    core_api = CoreApi()
    bot_config = core_api.get_bot_config(bot_id)
    if not bot_config:
        logger.error(f"Bot with id {bot_id} not found")
        return

    if bot := bots.get(bot_config["type"]):
        bot_params : dict = bot_config[bot_config["type"]]
        bot_params |= filter
        return bot.execute(bot_params)

    return "Not implemented"


@shared_task
def cleanup_token_blacklist():
    core_api = CoreApi()
    core_api.cleanup_token_blacklist()
    return "Token blacklist cleaned up"
