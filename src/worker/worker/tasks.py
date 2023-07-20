from celery import shared_task

from worker.log import logger
from worker.core_api import CoreApi


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
    if source["type"] == "WEB_COLLECTOR":
        return collectors.WebCollector().collect(source)
    return "Not implemented"

@shared_task
def execute_bot(bot_id: str):
    import worker.bots as bots

    core_api = CoreApi()
    bot_config = core_api.get_bot_config(bot_id)
    if not bot_config:
        logger.error(f"Bot with id {bot_id} not found")
        return

    if bot_config["type"] == "ANALYST_BOT":
        return bots.AnalystBot().execute(bot_config)
    if bot_config["type"] == "GROUPING_BOT":
        return bots.GroupingBot().execute(bot_config)
    if bot_config["type"] == "NLP_BOT":
        return bots.NLPBot().execute(bot_config)
    if bot_config["type"] == "TAGGING_BOT":
        return bots.TaggingBot().execute(bot_config)

    return "Not implemented"


@shared_task
def cleanup_token_blacklist():
    core_api = CoreApi()
    core_api.cleanup_token_blacklist()
    return "Token blacklist cleaned up"
