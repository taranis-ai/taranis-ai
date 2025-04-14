from .base_bot import BaseBot
from worker.config import Config
from worker.bot_api import BotApi
from worker.log import logger


class CyberSecClassifierBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "CYBERSEC_CLASSIFIER_BOT"
        self.name = "Cybersecurity classification bot"
        self.bot_api = BotApi(Config.CYBERSEC_CLASSIFIER_API_ENDPOINT)

    def execute(self, parameters: dict | None = None) -> dict:
        if not parameters:
            parameters = {}

        if not parameters.get("filter"):
            parameters["filter"] = {"cybersecurity": "none"}
        else:
            parameters["filter"].update({"cybersecurity": "none"})

        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        self.bot_api.api_url = parameters.get("BOT_ENDPOINT", Config.CYBERSEC_CLASSIFIER_API_ENDPOINT)

        num_news_items = 0
        for story in data:
            story_class_list = []
            for news_item in story.get("news_items", []):
                news_item_content = news_item.get("content", "")
                news_item_id = news_item.get("id", "")

                logger.debug(f"Classifying news item with id: {news_item_id} into cybersecurity/non-cybersecurity")

                class_result = self.classify_news_item(news_item_content)
                if not class_result:
                    continue

                news_item_cybersecurity_status = (
                    "yes" if class_result.get("cybersecurity", 0.0) > Config.CYBERSEC_CLASSIFIER_THRESHOLD else "no"
                )

                if self.core_api.update_news_item_attributes(
                    news_item_id,
                    [
                        {"key": "cybersecurity_bot", "value": news_item_cybersecurity_status},
                        {"key": "cybersecurity_bot_score", "value": str(class_result.get("cybersecurity", "N/A"))},
                    ],
                ):
                    logger.debug(f"Successfully updated news item {news_item_id} with cybersecurity attributes.")
                else:
                    logger.error(f"Failed to update news item {news_item_id} with cybersecurity attributes.")

                story_class_list.append(news_item_cybersecurity_status)

                num_news_items += 1

            if set(story_class_list) == {"yes"}:
                story_cybersecurity_status = "yes"
            elif set(story_class_list) == {"yes", "no"}:
                story_cybersecurity_status = "mixed"
            elif set(story_class_list) == {"no"}:
                story_cybersecurity_status = "no"
            else:
                story_cybersecurity_status = "none"
            self.core_api.add_or_update_story({"id": story.get("id", ""), "cybersecurity": story_cybersecurity_status})

        return {"message": f"Classified {num_news_items} news_items"}

    def classify_news_item(self, content: str) -> dict | None:
        class_result = self.bot_api.api_post("/", {"text": content})

        if not class_result:
            return None
        if "error" in class_result:
            logger.error(class_result["error"])
            return None

        logger.debug(f"Predicted class: {max(class_result, key=class_result.get)}")
        return class_result
