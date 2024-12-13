from .base_bot import BaseBot
from worker.config import Config
from worker.bot_api import BotApi


class NLPBot(BaseBot):
    def __init__(self, language="en"):
        super().__init__()
        self.type = "NLP_BOT"
        self.name = "NLP Bot"
        self.bot_api = BotApi(Config.NLP_API_ENDPOINT)

    def execute(self, parameters: dict | None = None) -> dict:
        if not parameters:
            parameters = {}
        stories = self.get_stories(parameters)
        if not stories:
            return {"message": "No new stories found"}

        all_keywords = self.collect_keywords(stories)
        tag_count = self.process_stories(stories, all_keywords)
        return {"message": f"Extracted {tag_count} tags"}

    def collect_keywords(self, stories: list) -> dict:
        return {k: v for story in stories for k, v in story["tags"].items()}

    def process_stories(self, stories: list, all_keywords: dict) -> int:
        update_result = {}
        tag_count = 0

        for story in stories:
            story_content = "\n".join(news_item["content"] for news_item in story["news_items"])
            current_keywords = self.extract_ner(story_content, all_keywords)
            all_keywords |= current_keywords
            update_result[story["id"]] = current_keywords

        tag_count += self.update_tags(update_result)
        return tag_count

    def update_tags(self, update_result: dict) -> int:
        self.core_api.update_tags(update_result, self.type)
        return len(update_result)

    def extract_ner(self, text: str, all_keywords) -> dict:
        if keywords := self.bot_api.api_post("/ner", {"text": text, "all_keywords": all_keywords}):
            return keywords
        return {}

    # def not_in_stopwords(self, keyword: str) -> bool:
    #    return keyword not in stopwords.words(self.language)
