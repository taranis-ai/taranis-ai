from .base_bot import BaseBot
from worker.log import logger
from sentiment_analysis_bot import analyze_sentiment, categorize_text


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
        sentiment_results = self.analyze_stories(data)
        self.update_news_items(sentiment_results)

        logger.info(f"Sentiment analysis complete with results: {sentiment_results}")

        return sentiment_results
    
    def analyze_stories(self, stories: list) -> dict:
        results = {}
        for story in stories:
            text_content = self.extract_content_from_story(story)
            logger.info(f"Extracted text for sentiment analysis: {text_content}")

            sentiment = analyze_sentiment(text_content)
            category = categorize_text(text_content)

            results[story["id"]] = {
                "sentiment": sentiment,
                "category": category,
            }

        return results

    def extract_content_from_story(self, story: dict) -> str:#
        content = [item.get("content", "") for item in story.get("news_items", [])]
        return " ".join(content)

    def update_news_items(self, sentiment_results: dict):
        for news_item_id, sentiment_data in sentiment_results.items():
            attributes = [
                {"key": "sentiment_score", "value": str(sentiment_data["sentiment_score"])},
                {"key": "sentiment_category", "value": sentiment_data["sentiment_category"]},
            ]

            if self.core_api.update_news_item_attributes(news_item_id, attributes):
                logger.info(f"Updated news item {news_item_id} with sentiment attributes.")
            else:
                logger.error(f"Failed to update news item {news_item_id} with sentiment attributes.")