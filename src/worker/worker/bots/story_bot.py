from .base_bot import BaseBot
from worker.log import logger
import datetime
from story_clustering.clustering import initial_clustering, incremental_clustering


class StoryBot(BaseBot):
    type = "STORY_BOT"
    name = "Story Clustering Bot"
    description = "Bot for clustering NewsItems to stories via naturale language processing"

    def __init__(self):
        super().__init__()

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
            if not data or type(data) != list:
                logger.critical("Error getting news items")
                return

            logger.info(f"Clustering {len(data)} news items")
            if all(len(aggregate["news_items"]) == 1 for aggregate in data):
                clustering_results = initial_clustering(data)
            else:
                already_clustered, to_cluster = self.separate_data(data)
                clustering_results = incremental_clustering(to_cluster, already_clustered)

            logger.info(f"Clustering results: {clustering_results['event_clusters']}")
            self.core_api.news_items_grouping_multiple(clustering_results["event_clusters"])

        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def separate_data(self, data):
        already_clustered = []
        to_cluster = []

        for aggregate in data:
            if len(aggregate["news_items"]) > 1:
                already_clustered.append(aggregate)
            else:
                to_cluster.append(aggregate)

        return already_clustered, to_cluster
