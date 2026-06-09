from worker.bot_api import BotApi
from worker.config import Config
from worker.log import logger

from .base_bot import BaseBot


class SummaryBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "SUMMARY_BOT"
        self.name = "Summary generation Bot"

    def execute(self, parameters: dict | None = None) -> dict[str, dict[str, str] | str]:
        if not parameters:
            parameters = {}

        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        summary_api = self._build_bot_api(parameters, "SUMMARY_ENDPOINT", Config.SUMMARY_API_ENDPOINT)
        title_api = self._build_bot_api(parameters, "TITLE_ENDPOINT", None)

        for story in data:
            news_items = story.get("news_items", [])
            story_payload = self._build_story_payload(news_items)

            logger.debug(f"Summarizing {story['id']} with {len(news_items)} news items")
            try:
                summary = self.predict_summary(summary_api, story_payload)
                if len(news_items) > 1:
                    title = self.predict_title(title_api, story_payload)
                else:
                    title = ""

                story_update_data = {}
                if summary:
                    story_update_data["summary"] = summary
                if title:
                    story_update_data["title"] = title

                if story_update_data:
                    if self.core_api.update_story(story["id"], story_update_data):
                        self.core_api.update_story_attributes(
                            story["id"],
                            [{"key": self.type, "value": 1}],
                        )
                    else:
                        logger.warning(f"Failed to update story {story['id']}, skipping attribute update")
            except Exception:
                logger.exception(f"Could not generate summary for {story['id']}")
                continue

            logger.debug(f"Created summary for : {story['id']}")
        return {"message": f"Summarized {len(data)} stories"}

    @staticmethod
    def _build_story_payload(news_items: list[dict]) -> dict[str, list[dict[str, str]]]:
        return {
            "news_items": [
                {
                    "title": news_item.get("title", ""),
                    "content": news_item.get("content", ""),
                }
                for news_item in news_items
            ]
        }

    @staticmethod
    def _build_bot_api(parameters: dict, endpoint_parameter: str, default_endpoint: str | None) -> BotApi | None:
        endpoint = parameters.get(endpoint_parameter) or default_endpoint
        if not endpoint:
            return None

        return BotApi(
            bot_endpoint=endpoint,
            bot_api_key=parameters.get("BOT_API_KEY", Config.BOT_API_KEY),
            requests_timeout=parameters.get("REQUESTS_TIMEOUT"),
        )

    def predict_summary(self, bot_api: BotApi | None, story_payload: dict[str, list[dict[str, str]]]) -> str:
        if not bot_api:
            return ""

        if response := bot_api.api_post("", story_payload):
            return response.get("summary", "")
        return ""

    def predict_title(self, bot_api: BotApi | None, story_payload: dict[str, list[dict[str, str]]]) -> str:
        if not bot_api:
            return ""

        if response := bot_api.api_post("", story_payload):
            return response.get("title", "")
        return ""
