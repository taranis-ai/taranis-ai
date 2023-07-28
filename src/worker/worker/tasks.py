from celery import shared_task

from worker.log import logger
from worker.core_api import CoreApi
import worker.bots

bots = {
    "ANALYST_BOT": worker.bots.AnalystBot(),
    "GROUPING_BOT": worker.bots.GroupingBot(),
    "NLP_BOT": worker.bots.NLPBot(),
    "TAGGING_BOT": worker.bots.TaggingBot(),
    "WORDLIST_UPDATER_BOT": worker.bots.WordlistUpdaterBot(),
}

@shared_task(time_limit=60)
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

@shared_task(time_limit=60)
def execute_bot(bot_id: str, filter: dict | None = None):

    core_api = CoreApi()
    bot_config = core_api.get_bot_config(bot_id)
    if not bot_config:
        logger.error(f"Bot with id {bot_id} not found")
        return

    bot_type = bot_config.get("type")
    if not bot_type:
        logger.error(f"Bot with id {bot_id} has no type")
        return

    bot = bots.get(bot_type)
    if not bot:
        return "Not implemented"

    bot_params = bot_config.get(bot_type)
    if not bot_params:
        logger.error(f"Bot with id {bot_id} has no params")
        return

    bot_params |= filter
    return bot.execute(bot_params)


@shared_task(time_limit=10)
def cleanup_token_blacklist():
    core_api = CoreApi()
    core_api.cleanup_token_blacklist()
    return "Token blacklist cleaned up"

@shared_task(time_limit=30)
def gather_word_list(word_list_id: int):
    core_api = CoreApi()
    word_list = core_api.get_word_list(word_list_id)
    if not word_list:
        logger.error(f"Word list with id {word_list_id} not found")
        return
    bots["WORDLIST_UPDATER_BOT"].execute(word_list)
    return "Word list updated"

