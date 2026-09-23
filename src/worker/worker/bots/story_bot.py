import asyncio

from llm_bot.client import LLMClient, UpstreamLLMError
from llm_bot.schemas import ClusterRequest
from llm_bot.tasks.cluster import cluster_stories
from niquests.exceptions import RequestException

from worker.bot_api import BotServiceUnavailableError
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
        try:
            request = ClusterRequest.model_validate(
                {"stories": [{"id": story["id"], "tags": story.get("tags", {}), "summary": story.get("summary")} for story in data]}
            )
            response = asyncio.run(cluster_stories(request, client=LLMClient(timeout=parameters.get("REQUESTS_TIMEOUT"))))
        except (RequestException, UpstreamLLMError):
            logger.exception("Story clustering LLM request failed")
            raise BotServiceUnavailableError from None
        except Exception:
            logger.exception("Story clustering failed")
            raise RuntimeError("Story clustering failed") from None

        clusters = [cluster for cluster in response.cluster_ids.event_clusters if len(cluster) > 1]
        if not clusters:
            return {"message": f"{response.message}. No clusters found."}

        self.core_api.news_items_grouping_multiple(clusters)
        return {"message": response.message}
