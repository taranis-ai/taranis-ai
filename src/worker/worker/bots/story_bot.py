from .base_bot import BaseBot
from worker.log import logger
from worker.config import Config
from worker.bot_api import BotApi


class StoryBot(BaseBot):
    def __init__(self, language="en"):
        super().__init__()

        self.type = "STORY_BOT"
        self.name = "Story Clustering Bot"
        self.description = "Bot for clustering NewsItems to stories via natural language processing"
        self.language = language
        self.bot_api = BotApi(Config.STORY_API_ENDPOINT)

    def execute(self, parameters: dict | None = None):
        if not parameters:
            parameters = {"BOT_ENDPOINT": Config.STORY_API_ENDPOINT}
        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        self.bot_api.update_parameters(parameters=parameters)

        logger.info(f"Clustering {len(data)} news items")
        if response := self.bot_api.api_post("/", {"stories": data}):
            cluster_data = response.get("cluster_ids", {})
            message = response.get("message", "")
            if not cluster_data or not cluster_data.get("event_clusters"):
                return {"message": f"{message}. No clusters found."}

            self.core_api.news_items_grouping_multiple(cluster_data.get("event_clusters", []))
            return {"message": message}

        raise RuntimeError(f"Did not receive clustering information from Story Bot at {self.bot_api.api_url}")
