from worker.bot_api import BotApi
from worker.config import Config
from worker.log import logger

from .base_bot import BaseBot


class SentimentAnalysisBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "SENTIMENT_ANALYSIS_BOT"
        self.name = "Sentiment Analysis Bot"
        self.description = "Bot to analyze the sentiment of news items' content"

    def execute(self, parameters: dict | None = None) -> dict:
        if not parameters:
            parameters = {}
        if not (data := self.get_stories(parameters)):
            return {"message": "No stories found for sentiment analysis"}

        self.bot_api = BotApi(
            bot_endpoint=parameters.get("BOT_ENDPOINT", Config.SENTIMENT_ANALYSIS_API_ENDPOINT),
            bot_api_key=parameters.get("BOT_API_KEY", Config.BOT_API_KEY),
            requests_timeout=parameters.get("REQUESTS_TIMEOUT"),
        )

        logger.debug(f"Analyzing sentiment for {len(data)} news items")

        # Process each story
        if sentiment_results := self._analyze_news_items(data):
            self.update_news_items(sentiment_results)
            return {
                "message": "Sentiment analysis complete",
            }

        return {"message": "No sentiment analysis results"}

    def _analyze_news_items(self, stories: list) -> dict:
        results = {}

        for story in stories:
            for news_item in story.get("news_items", []):
                text_content = news_item.get("content", "")
                response = self.bot_api.api_post("/", {"text": text_content})

                if not response:
                    continue
                if "error" in response:
                    logger.error(response["error"])
                    continue

                sentiment = response.get("sentiment") if isinstance(response, dict) else None
                sentiment_payload = sentiment if isinstance(sentiment, dict) else response if isinstance(response, dict) else None
                if not sentiment_payload:
                    continue

                label = sentiment_payload.get("label")
                score = sentiment_payload.get("score")
                logger.debug(f"Received sentiment label: {label} with score: {score}")

                news_item_id = news_item.get("id")
                normalized_label = str(label).lower() if label not in (None, "") else ""
                if news_item_id is not None and normalized_label:
                    results[news_item_id] = {"sentiment": score, "category": normalized_label}

        return results

    def update_news_items(self, sentiment_results: dict):
        for news_item_id, sentiment_data in sentiment_results.items():
            attributes = [
                {"key": "sentiment_score", "value": str(sentiment_data.get("sentiment", "N/A"))},
                {"key": "sentiment_category", "value": sentiment_data.get("category", "N/A")},
            ]

            if self.core_api.update_news_item_attributes(news_item_id, attributes):
                logger.debug(f"Successfully updated news item {news_item_id} with sentiment attributes.")
            else:
                logger.error(f"Failed to update news item {news_item_id} with sentiment attributes.")
