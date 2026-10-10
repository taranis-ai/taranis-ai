from llm_bot.schemas import CybersecClassificationRequest
from llm_bot.tasks.cybersec_classification import prepare_cybersec_classification
from rq import Retry

from worker.config import Config
from worker.llm import get_llm_client, run_llm_tasks
from worker.log import logger

from .base_bot import BaseBot


class CyberSecClassifierBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "CYBERSEC_CLASSIFIER_BOT"
        self.name = "Cybersecurity classification bot"

    def execute(self, parameters: dict | None = None) -> dict | Retry:
        if not parameters:
            parameters = {}

        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        self.llm_client = get_llm_client(parameters)
        self.classification_threshold = parameters.get("CLASSIFICATION_THRESHOLD", Config.CYBERSEC_CLASSIFIER_THRESHOLD)
        items = [item for story in data for item in story.get("news_items", []) if item.get("content", "").strip()]
        tasks = [prepare_cybersec_classification(CybersecClassificationRequest(text=item["content"])) for item in items]
        results = run_llm_tasks(tasks, self.llm_client, parameters)
        if isinstance(results, Retry):
            return results
        results = {item["id"]: result.model_dump() for item, result in zip(items, results, strict=True)}

        num_news_items = 0
        item_attributes = {}
        story_attributes = {}
        for story in data:
            story_class_list = []
            story_cybersecurity_status = "incomplete"
            for news_item in story.get("news_items", []):
                result = self._process_news_item(news_item, results.get(news_item["id"]), item_attributes)
                story_class_list.append(result)
                if result != "none":
                    num_news_items += 1

                status_set = frozenset(story_class_list)

                if "none" in status_set and len(status_set) > 1:
                    story_cybersecurity_status = "incomplete"
                else:
                    status_map = {
                        frozenset(["yes"]): "yes",
                        frozenset(["no"]): "no",
                        frozenset(["yes", "no"]): "mixed",
                        frozenset(["none"]): "none",
                    }
                    story_cybersecurity_status = status_map.get(status_set, "none")

            attributes = [{"key": "cybersecurity", "value": story_cybersecurity_status}]
            story_attributes[story["id"]] = attributes

        return {
            "message": f"Classified {num_news_items} news items",
            "changes": {"item_attributes": item_attributes, "story_attributes": story_attributes},
        }

    def _process_news_item(self, news_item: dict, class_result: dict | None, item_attributes: dict) -> str:
        news_item_id = news_item.get("id", "")

        logger.debug(f"Classifying news item with id: {news_item_id}.")
        if not class_result:
            return "none"

        status = "yes" if class_result.get("cybersecurity", 0.0) > self.classification_threshold else "no"

        item_attributes[news_item_id] = [
            {"key": "cybersecurity_bot", "value": status},
            {"key": "cybersecurity_bot_score", "value": str(class_result.get("cybersecurity", "N/A"))},
        ]

        return status
