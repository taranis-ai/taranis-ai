import worker.bots
from worker.log import logger
from worker.core_api import CoreApi

core_api = CoreApi()

bots = {
    "analyst_bot": worker.bots.AnalystBot(),
    "grouping_bot": worker.bots.GroupingBot(),
    "tagging_bot": worker.bots.TaggingBot(),
    "wordlist_bot": worker.bots.WordlistBot(),
    "wordlist_updater_bot": worker.bots.WordlistUpdaterBot(),
    "nlp_bot": worker.bots.NLPBot(),
    "story_bot": worker.bots.StoryBot(),
    "ioc_bot": worker.bots.IOCBot(),
    "summary_bot": worker.bots.SummaryBot(),
}


def execute_by_config(bot_config: dict, filter: dict | None = None):
    bot_type = bot_config.get("type")
    if not bot_type:
        logger.error("Bot has no type")
        return

    bot = bots.get(bot_type)
    if not bot:
        return "Bot type not implemented"

    bot_params = bot_config.get("parameters")
    if not bot_params:
        logger.error("Bot with has no params")
        return

    if filter:
        bot_params |= filter
    return bot.execute(bot_params)


def execute_by_id(bot_id: str, filter: dict | None = None):
    bot_config = core_api.get_bot_config(bot_id)
    if not bot_config:
        logger.error(f"Bot with id {bot_id} not found")
        return

    return execute_by_config(bot_config, filter)


def execute_by_configs(bot_configs: list[dict], filter: dict | None = None):
    return [execute_by_config(bot_config, filter=filter) for bot_config in bot_configs]


def execute_by_type(bot_type: str, *args, **kwargs):
    if bot := bots.get(bot_type):
        return bot.execute(*args, **kwargs)
