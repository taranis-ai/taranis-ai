from llm_bot.schemas import CybersecClassificationRequest
from llm_bot.tasks.cybersec_classification import classify_cybersecurity_text

from worker.config import Config
from worker.llm import get_llm_client, run_llm_task
from worker.log import logger

from .base_bot import BaseBot


class CyberSecClassifierBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "CYBERSEC_CLASSIFIER_BOT"
        self.name = "Cybersecurity classification bot"

    def execute(self, parameters: dict | None = None) -> dict[str, dict[str, str] | str]:
        if not parameters:
            parameters = {}

        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        self.llm_client = get_llm_client(parameters)
        self.classification_threshold = parameters.get("CLASSIFICATION_THRESHOLD", Config.CYBERSEC_CLASSIFIER_THRESHOLD)

        num_news_items = 0
        for story in data:
            story_class_list = []
            story_cybersecurity_status = "incomplete"
            for news_item in story.get("news_items", []):
                result = self._process_news_item(news_item)
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
            self.core_api.update_story_attributes(story.get("id", ""), attributes)

        return {"message": f"Classified {num_news_items} news items"}

    def _classify_news_item(self, content: str) -> dict | None:
        if not content.strip():
            return None
        request = CybersecClassificationRequest(text=content)
        return run_llm_task(classify_cybersecurity_text(request, client=self.llm_client)).model_dump()

    def _process_news_item(self, news_item: dict) -> str:
        news_item_content = news_item.get("content", "")
        news_item_id = news_item.get("id", "")

        logger.debug(f"Classifying news item with id: {news_item_id}.")
        class_result = self._classify_news_item(news_item_content)
        if not class_result:
            return "none"

        status = "yes" if class_result.get("cybersecurity", 0.0) > self.classification_threshold else "no"

        if self.core_api.update_news_item_attributes(
            news_item_id,
            [
                {"key": "cybersecurity_bot", "value": status},
                {"key": "cybersecurity_bot_score", "value": str(class_result.get("cybersecurity", "N/A"))},
            ],
        ):
            logger.debug(f"Successfully updated news item {news_item_id} with cybersecurity attributes.")
        else:
            logger.error(f"Failed to update news item {news_item_id} with cybersecurity attributes.")

        return status
