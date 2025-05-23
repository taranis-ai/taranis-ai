from celery import Task

import worker.bots
from worker.log import logger
from worker.core_api import CoreApi


class BotTask(Task):
    name = "bot_task"
    max_retries = 3
    priority = 2
    default_retry_delay = 60
    time_limit = 18000

    def __init__(self):
        self.core_api = CoreApi()
        self.bots = {
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

    def run(self, bot_id: str, filter: dict | None = None):
        logger.info(f"Starting bot task {self.name}")
        if bot_config := self.core_api.get_bot_config(bot_id):
            return self.execute_by_config(bot_config, filter)

        raise ValueError(f"Bot with id {bot_id} not found")

    def execute_by_config(self, bot_config: dict, filter: dict | None = None):
        bot_type = bot_config.get("type")
        if not bot_type:
            raise ValueError("Bot has no type")

        bot = self.bots.get(bot_type)
        if not bot:
            raise ValueError("Bot type not implemented")

        bot_params = bot_config.get("parameters")
        if not bot_params:
            raise ValueError("Bot has no parameters")

        if filter:
            bot_params["filter"] = filter
        return bot.execute(bot_params)
