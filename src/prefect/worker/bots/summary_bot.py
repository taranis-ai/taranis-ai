from .base_bot import BaseBot
from worker.log import logger
from worker.bot_api import BotApi
from worker.config import Config


class SummaryBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "SUMMARY_BOT"
        self.name = "Summary generation Bot"
        self.bot_api = BotApi(Config.SUMMARY_API_ENDPOINT)

    def execute(self, parameters: dict | None = None) -> dict:
        if not parameters:
            parameters = {}

        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        self.bot_api.api_url = parameters.get("BOT_ENDPOINT", Config.SUMMARY_API_ENDPOINT)

        for story in data:
            news_items = story.get("news_items", [])
            content_to_summarize = "".join(news_item["content"] for news_item in news_items)

            logger.debug(f"Summarizing {story['id']} with {len(content_to_summarize)} characters")
            try:
                if summary := self.predict_summary(content_to_summarize):
                    self.core_api.update_story_summary(story["id"], summary)
            except Exception:
                logger.exception(f"Could not generate summary for {story['id']}")
                continue

            logger.debug(f"Created summary for : {story['id']}")
        return {"message": f"Summarized {len(data)} stories"}

    def predict_summary(self, text_to_summarize: str) -> str:
        if summary := self.bot_api.api_post("/", {"text": text_to_summarize}):
            return summary.get("summary", "")
        return ""
