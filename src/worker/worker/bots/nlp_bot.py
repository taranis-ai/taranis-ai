from worker.bot_api import BotApi
from worker.config import Config

from .base_bot import BaseBot


def batched(stories: list, batch_size=10):
    for i in range(0, len(stories), batch_size):
        yield stories[i : i + batch_size]


class NLPBot(BaseBot):
    def __init__(self, language="en"):
        super().__init__()
        self.type = "NLP_BOT"
        self.name = "NLP Bot"

    def execute(self, parameters: dict | None = None) -> dict[str, dict[str, str] | str]:
        update_result = {}

        if not parameters:
            parameters = {}
        if stories := self.get_stories(parameters):
            self.bot_api = BotApi(
                bot_endpoint=parameters.get("BOT_ENDPOINT", Config.NLP_API_ENDPOINT),
                bot_api_key=parameters.get("BOT_API_KEY", Config.BOT_API_KEY),
                requests_timeout=parameters.get("REQUESTS_TIMEOUT"),
            )

            for story_batch in batched(stories):
                update_result |= self._process_stories(story_batch)
            return update_result
        return {"message": "No new stories found"}

    def _process_stories(self, stories: list) -> dict:
        update_result = {}

        for story in stories:
            if "attributes" in story and story.get("attributes", {}):
                is_cybersecurity = story["attributes"].get("cybersecurity", {}).get("value", "no") == "yes"
            else:
                is_cybersecurity = False
            for news_item in story["news_items"]:
                news_item_content = "\n".join([news_item.get("title", ""), news_item.get("review", ""), news_item.get("content", "")])
                current_keywords = self._extract_ner(news_item_content, is_cybersecurity)
                update_result[news_item["id"]] = current_keywords

        return update_result

    def _extract_ner(self, text: str, is_cybersecurity: bool = False) -> dict:
        if keywords := self.bot_api.api_post("/", {"text": text, "cybersecurity": is_cybersecurity}):
            return keywords
        return {}

    # def not_in_stopwords(self, keyword: str) -> bool:
    #    return keyword not in stopwords.words(self.language)
