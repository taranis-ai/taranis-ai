from llm_bot.schemas import ClusterRequest
from llm_bot.tasks.cluster import cluster_stories

from worker.llm import get_llm_client, run_llm_task
from worker.log import logger

from .base_bot import BaseBot


class StoryBot(BaseBot):
    def __init__(self, language="en"):
        super().__init__()

        self.type = "STORY_BOT"
        self.name = "Story Clustering Bot"
        self.description = "Bot for clustering NewsItems to stories via natural language processing"
        self.language = language

    def execute(self, parameters: dict | None = None) -> dict[str, dict[str, str] | str]:
        if not parameters:
            parameters = {}
        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}
        logger.info(f"Clustering {len(data)} stories")
        client = get_llm_client(self.core_api, "clustering", parameters)
        try:
            request = ClusterRequest.model_validate(
                {"stories": [{"id": story["id"], "tags": story.get("tags", {}), "summary": story.get("summary")} for story in data]}
            )
        except Exception:
            logger.exception("Invalid story clustering input")
            raise RuntimeError("Story clustering failed") from None
        response = run_llm_task(cluster_stories(request, client=client))

        clusters = [cluster for cluster in response.cluster_ids.event_clusters if len(cluster) > 1]
        if not clusters:
            return {"message": f"{response.message}. No clusters found."}

        self.core_api.news_items_grouping_multiple(clusters)
        return {"message": response.message}
