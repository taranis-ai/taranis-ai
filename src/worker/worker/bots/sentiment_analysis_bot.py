from llm_bot.schemas import SentimentRequest
from llm_bot.tasks.sentiment import analyze_sentiment

from worker.llm import get_llm_client, run_llm_task
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

        self.llm_client = get_llm_client(parameters)

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
                if not text_content.strip():
                    continue
                sentiment = run_llm_task(analyze_sentiment(SentimentRequest(text=text_content), client=self.llm_client)).sentiment
                results[news_item["id"]] = {"sentiment": sentiment.score, "category": sentiment.label.value}

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
