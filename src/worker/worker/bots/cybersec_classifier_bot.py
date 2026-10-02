from typing import Any

from worker.bot_api import BotApi
from worker.config import Config
from worker.log import logger

from .base_bot import BaseBot


class CyberSecClassifierBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "CYBERSEC_CLASSIFIER_BOT"
        self.name = "Cybersecurity classification bot"

    def execute(self, parameters: dict | None = None) -> dict[str, Any]:
        if not parameters:
            parameters = {}

        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        self.bot_api = BotApi(
            bot_endpoint=parameters.get("BOT_ENDPOINT", Config.CYBERSEC_CLASSIFIER_API_ENDPOINT),
            bot_api_key=parameters.get("BOT_API_KEY", Config.BOT_API_KEY),
            requests_timeout=parameters.get("REQUESTS_TIMEOUT"),
        )

        num_news_items = 0
        item_attributes = {}
        story_attributes = {}
        for story in data:
            story_class_list = []
            story_cybersecurity_status = "incomplete"
            for news_item in story.get("news_items", []):
                result = self._process_news_item(news_item, item_attributes)
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

            attributes = [{"key": "cybersecurity", "value": story_cybersecurity_status}, {"key": self.type, "value": 1}]
            story_attributes[story["id"]] = attributes

        return {
            "message": f"Classified {num_news_items} news items",
            "changes": {"item_attributes": item_attributes, "story_attributes": story_attributes},
        }

    def _classify_news_item(self, content: str) -> dict | None:
        class_result = self.bot_api.api_post("/", {"text": content})

        if not class_result:
            return None
        if "error" in class_result:
            logger.error(class_result["error"])
            return None

        logger.debug(f"Predicted class: {max(class_result, key=class_result.get)}")
        return class_result

    def _process_news_item(self, news_item: dict, item_attributes: dict) -> str:
        news_item_content = news_item.get("content", "")
        news_item_id = news_item.get("id", "")

        logger.debug(f"Classifying news item with id: {news_item_id}.")
        class_result = self._classify_news_item(news_item_content)
        if not class_result:
            return "none"

        status = "yes" if class_result.get("cybersecurity", 0.0) > Config.CYBERSEC_CLASSIFIER_THRESHOLD else "no"

        item_attributes[news_item_id] = [
            {"key": "cybersecurity_bot", "value": status},
            {"key": "cybersecurity_bot_score", "value": str(class_result.get("cybersecurity", "N/A"))},
        ]

        return status
