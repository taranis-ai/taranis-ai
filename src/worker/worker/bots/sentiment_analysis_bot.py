from llm_bot.schemas import SentimentRequest
from llm_bot.tasks.sentiment import prepare_sentiment
from rq import Retry

from worker.llm import get_llm_client, run_llm_tasks
from worker.log import logger

from .base_bot import BaseBot


class SentimentAnalysisBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "SENTIMENT_ANALYSIS_BOT"
        self.name = "Sentiment Analysis Bot"
        self.description = "Bot to analyze the sentiment of news items' content"

    def execute(self, parameters: dict | None = None) -> dict | Retry:
        if not parameters:
            parameters = {}
        if not (data := self.get_stories(parameters)):
            return {"message": "No stories found for sentiment analysis"}

        self.llm_client = get_llm_client(parameters)

        logger.debug(f"Analyzing sentiment for {len(data)} news items")

        sentiment_results = self._analyze_news_items(data, parameters)
        if isinstance(sentiment_results, Retry):
            return sentiment_results
        if sentiment_results:
            self.update_news_items(sentiment_results)
            return {
                "message": "Sentiment analysis complete",
            }

        return {"message": "No sentiment analysis results"}

    def _analyze_news_items(self, stories: list, parameters: dict) -> dict | Retry:
        items = [item for story in stories for item in story.get("news_items", []) if item.get("content", "").strip()]
        tasks = [prepare_sentiment(SentimentRequest(text=item["content"])) for item in items]
        results = run_llm_tasks(tasks, self.llm_client, parameters)
        if isinstance(results, Retry):
            return results
        return {
            item["id"]: {"sentiment": result.sentiment.score, "category": result.sentiment.label.value}
            for item, result in zip(items, results, strict=True)
        }

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
