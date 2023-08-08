from celery import shared_task

from worker.log import logger
from worker.core_api import CoreApi
import worker.bots
from requests.exceptions import ConnectionError

bots = {
    "ANALYST_BOT": worker.bots.AnalystBot(),
    "GROUPING_BOT": worker.bots.GroupingBot(),
    "NLP_BOT": worker.bots.NLPBot(),
    "TAGGING_BOT": worker.bots.TaggingBot(),
    "WORDLIST_BOT": worker.bots.WordlistBot(),
    "WORDLIST_UPDATER_BOT": worker.bots.WordlistUpdaterBot(),
}


@shared_task(time_limit=60)
def collect(source_id: str):
    import worker.collectors as collectors

    core_api = CoreApi()
    err = None
    try:
        source = core_api.get_osint_source(source_id)
    except ConnectionError as e:
        logger.critical(e)
        return str(e)

    if not source:
        logger.error(f"Source with id {source_id} not found")
        return f"Source with id {source_id} not found"

    if source["type"] == "RSS_COLLECTOR":
        err = collectors.RSSCollector().collect(source)
    else:
        return f"Collector {source['type']} not implemented"

    if err:
        core_api.update_osintsource_status(source_id, {"error": err})
        return err

    return f"Succesfully collected source {source_id}"


@shared_task(time_limit=180)
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
        return f"Bot {bot_type} not implemented"

    bot_params = bot_config.get(bot_type)
    if not bot_params:
        logger.error(f"Bot with id {bot_id} has no params")
        return

    if filter:
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
