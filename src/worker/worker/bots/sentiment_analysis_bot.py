from .base_bot import BaseBot
from worker.log import logger
from worker.bot_api import BotApi
from worker.config import Config


class SentimentAnalysisBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "SENTIMENT_ANALYSIS_BOT"
        self.name = "Sentiment Analysis Bot"
        self.description = "Bot to analyze the sentiment of news items' content"
        self.bot_api = BotApi(Config.SENTIMENT_ANALYSIS_API_ENDPOINT)

    def execute(self, parameters: dict | None = None) -> dict:
        if not parameters:
            parameters = {}
        if not (data := self.get_stories(parameters)):
            return {"message": "No stories found for sentiment analysis"}

        self.bot_api.api_url = parameters.get("BOT_ENDPOINT", Config.SENTIMENT_ANALYSIS_API_ENDPOINT)

        logger.debug(f"Analyzing sentiment for {len(data)} news items")

        # Process each story
        if sentiment_results := self.analyze_news_items(data):
            self.update_news_items(sentiment_results)
            return {
                "message": "Sentiment analysis complete",
            }

        return {"message": "No sentiment analysis results"}

    def analyze_news_items(self, stories: list) -> dict:
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

                sentiment = response.get("sentiment")
                if not sentiment:
                    continue

                label = sentiment.get("label")
                score = sentiment.get("score")
                logger.debug(f"Received sentiment label: {label} with score: {score}")

                news_item_id = news_item.get("id")
                if news_item_id is not None:
                    results[news_item_id] = {"sentiment": score, "category": label}

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
