from celery import Task

import worker.bots
from worker.log import logger
from worker.core_api import CoreApi


class BotTask(Task):
    name = "bot_task"
    max_retries = 3
    default_retry_delay = 60
    time_limit = 1800

    def __init__(self):
        self.core_api = CoreApi()
        self.bots = {
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

    def run(self, *args, bot_id: str, filter: dict | None = None):
        logger.info(f"Starting bot task {self.name}")
        bot_config = self.core_api.get_bot_config(bot_id)
        if not bot_config:
            logger.error(f"Bot with id {bot_id} not found")
            return

        self.execute_by_config(bot_config, filter)
        return

    def execute_by_config(self, bot_config: dict, filter: dict | None = None):
        bot_type = bot_config.get("type")
        if not bot_type:
            logger.error("Bot has no type")
            return

        bot = self.bots.get(bot_type)
        if not bot:
            return "Bot type not implemented"

        bot_params = bot_config.get("parameters")
        if not bot_params:
            logger.error("Bot with has no params")
            return

        if filter:
            bot_params |= filter
        return bot.execute(bot_params)
