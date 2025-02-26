from .base_bot import BaseBot
from worker.config import Config
from worker.bot_api import BotApi
from worker.log import logger


class NLPBot(BaseBot):
    def __init__(self, language="en"):
        super().__init__()
        self.type = "NLP_BOT"
        self.name = "NLP Bot"
        self.bot_api = BotApi(Config.NLP_API_ENDPOINT)

    def execute(self, parameters: dict | None = None) -> dict:
        if not parameters:
            parameters = {}
        if stories := self.get_stories(parameters):
            self.bot_api.update_parameters(parameters=parameters)
            return self.process_stories(stories)

        return {"message": "No new stories found"}

    def collect_keywords(self, stories: list) -> dict:
        return {k: v for story in stories for k, v in story["tags"].items()}

    def process_stories(self, stories: list) -> dict:
        update_result = {}

        for story in stories:
            story_content = "\n".join(news_item["content"] for news_item in story["news_items"])
            current_keywords = self.extract_ner(story_content)
            update_result[story["id"]] = current_keywords

        return self.update_tags(update_result)

    def update_tags(self, update_result: dict) -> dict:
        logger.debug(f"Extracted {len(update_result)} tags")
        self.core_api.update_tags(update_result, self.type)
        return update_result

    def extract_ner(self, text: str) -> dict:
        if keywords := self.bot_api.api_post("/", {"text": text}):
            return keywords
        return {}

    # def not_in_stopwords(self, keyword: str) -> bool:
    #    return keyword not in stopwords.words(self.language)
