from typing import Mapping, Tuple

from worker.bot_api import BotApi
from worker.config import Config
from worker.log import logger

from .base_bot import BaseBot


class StoryBot(BaseBot):
    def __init__(self, language="en"):
        super().__init__()

        self.type = "STORY_BOT"
        self.name = "Story Clustering Bot"
        self.description = "Bot for clustering NewsItems to stories via natural language processing"
        self.language = language

    def execute(self, parameters: dict | None = None) -> Tuple[Mapping[str, dict[str, str] | str], str]:
        if not parameters:
            parameters = {}
        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}, self.type

        self.bot_api = BotApi(
            bot_endpoint=parameters.get("BOT_ENDPOINT", Config.STORY_API_ENDPOINT),
            bot_api_key=parameters.get("BOT_API_KEY", Config.BOT_API_KEY),
        )

        logger.info(f"Clustering {len(data)} news items")

        if response := self.bot_api.api_post("/", {"stories": data}):
            cluster_data = response.get("cluster_ids", {})
            message = response.get("message", "")
            if not cluster_data or not cluster_data.get("event_clusters"):
                return {"message": f"{message}. No clusters found."}, self.type

            self.core_api.news_items_grouping_multiple(cluster_data.get("event_clusters", []))
            return {"message": message}, self.type

        raise RuntimeError(f"Did not receive clustering information from Story Bot at {self.bot_api.api_url}")
