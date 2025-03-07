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
            parameters = {}
        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        self.bot_api.api_url = parameters.get("BOT_ENDPOINT", Config.STORY_API_ENDPOINT)

        logger.info(f"Clustering {len(data)} news items")
        if cluster := self.bot_api.api_post("/", {"stories": data}):
            self.core_api.news_items_grouping_multiple(cluster["cluster_ids"]["event_clusters"])
            return {"message": f"incremental Clustering done with: {len(data)} news items"}

        return {"message": "No clustering done"}
