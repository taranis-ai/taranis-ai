from .base_bot import BaseBot
from worker.log import logger
from story_clustering.clustering import create_corpus, incremental_clustering_v2, extract_events_from_corpus, to_json_events
from worker.story_clustering.clustering_tasks import initial_clustering
from story_clustering.document_representation import CorpusEncoder
import json


class StoryBot(BaseBot):
    def __init__(self, language="en"):
        super().__init__()
        import story_clustering  # noqa: F401

        self.type = "STORY_BOT"
        self.name = "Story Clustering Bot"
        self.description = "Bot for clustering NewsItems to stories via natural language processing"
        self.language = language
        self.initialize_models()

    def execute(self, parameters: dict | None = None):
        if not parameters:
            parameters = {}
        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        logger.info(f"Clustering {len(data)} news items")
        if all(len(story["news_items"]) == 1 for story in data):
            corpus = create_corpus(data)
            initial_clustering.apply_async(args=[json.dumps(corpus, cls=CorpusEncoder)], queue="bots")
        else:
            already_clustered, to_cluster = self.separate_data(data)
            clustering_results = incremental_clustering_v2(to_cluster, already_clustered)
            logger.info(f"Clustering results: {clustering_results['event_clusters']}")
            self.core_api.news_items_grouping_multiple(clustering_results["event_clusters"])

    def initial_clustering_event_handler(self, corpus):
        events = extract_events_from_corpus(corpus=corpus)
        clustering_results = to_json_events(events)
        logger.info(f"Clustering results: {clustering_results['event_clusters']}")
        self.core_api.news_items_grouping_multiple(clustering_results["event_clusters"])
        return f"Clustering {len(clustering_results["event_clusters"])} news items"

    def separate_data(self, data):
        already_clustered = []
        to_cluster = []

        for story in data:
            if len(story["news_items"]) > 1:
                already_clustered.append(story)
            else:
                to_cluster.append(story)

        return already_clustered, to_cluster
