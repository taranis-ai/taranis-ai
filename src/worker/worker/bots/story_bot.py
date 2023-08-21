from .base_bot import BaseBot
from worker.log import logger
import datetime


class NLPBot(BaseBot):
    type = "STORY_BOT"
    name = "Story Clustering Bot"
    description = "Bot for clustering NewsItems to stories via naturale language processing"

    def __init__(self):
        super().__init__()
        logger.error("Story Clustering Bot not implemented yet")

    def execute(self, parameters=None):
        if not parameters:
            return
        try:
            source_group = parameters.get("SOURCE_GROUP")
            source = parameters.get("SOURCE")

            limit = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
            filter_dict = {"timestamp": limit}
            if source_group:
                filter_dict["source_group"] = source_group
            if source:
                filter_dict["source"] = source

            data = self.core_api.get_news_items_aggregate(filter_dict)
            if not data:
                logger.critical("Error getting news items")
                return

            logger.error("Story Clustering Bot not implemented yet")

        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
