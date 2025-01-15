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

        logger.info(f"Clustering {len(data)} news items")
        if all(len(story["news_items"]) == 1 for story in data):
            if cluster := self.bot_api.api_post("/initial-clustering", {"data": data}):
                self.core_api.news_items_grouping_multiple(cluster["event_clusters"])
                return {"message": f"Initial Clustering done with: {len(data)} news items"}

        already_clustered, to_cluster = self.separate_data(data)
        if cluster := self.bot_api.api_post("/incremental-clustering", {"to_cluster": to_cluster, "already_clustered": already_clustered}):
            self.core_api.news_items_grouping_multiple(cluster["event_clusters"])
            return {"message": f"incremental Clustering done with: {len(data)} news items"}

        return {"message": "No clustering done"}

    def separate_data(self, data):
        already_clustered = []
        to_cluster = []

        for story in data:
            if len(story["news_items"]) > 1:
                already_clustered.append(story)
            else:
                to_cluster.append(story)

        return already_clustered, to_cluster
