from .base_bot import BaseBot
from worker.log import logger
from sentiment_analysis.sentiment_analysis_multimodel import analyze_sentiment


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

        logger.info(f"Analyzing sentiment for {len(data)} news items")

        # Process each story
        sentiment_results = self.analyze_news_items(data)
        self.update_news_items(sentiment_results)

        logger.info(f"Sentiment analysis complete with results: {sentiment_results}")

        return {
            "sentiment_score": sentiment_results.get(list(sentiment_results.keys())[0])["sentiment"],
            "message": "Sentiment analysis complete",
        }

    def analyze_news_items(self, stories: list) -> dict:
        results = {}
        for story in stories:
            news_items = story.get("news_items", [])
            for news_item in news_items:
                text_content = news_item.get("content", "")
                sentiment = analyze_sentiment(text_content)
                logger.info(f"Sentiment analysis result for news item {news_item['id']}: {sentiment}")
                if "score" not in sentiment:
                    logger.error(f"Sentiment analysis failed for news item {news_item['id']}")
                    continue

                logger.info(f"Received sentiment label: {sentiment['label']} with score: {sentiment['score']}")
                news_item_id = news_item["id"]
                results[news_item_id] = {
                    "sentiment": sentiment["score"],
                    "category": sentiment["label"],  
                }

        return results

    def update_news_items(self, sentiment_results: dict):
        for news_item_id, sentiment_data in sentiment_results.items():
            attributes = [
                {"key": "sentiment_score", "value": str(sentiment_data.get("sentiment", "N/A"))},
                {"key": "sentiment_category", "value": sentiment_data.get("category", "N/A")},
            ]
            logger.info(f"Updating news item {news_item_id} with attributes: {attributes}")

            if success := self.core_api.update_news_item_attributes(news_item_id, attributes):  # noqa: F841
                logger.info(f"Successfully updated news item {news_item_id} with sentiment attributes.")
            else:
                logger.error(f"Failed to update news item {news_item_id} with sentiment attributes.")
