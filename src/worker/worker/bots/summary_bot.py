from .base_bot import BaseBot
from worker.log import logger
import subprocess
import json

class SummaryBot(BaseBot):
    def __init__(self, language="en"):
        super().__init__()
        self.type = "SUMMARY_BOT"
        self.name = "Summary generation Bot"
        self.description = "Bot to generate summaries for stories"
        self.summary_threshold = 1000
        self.language = language

    def execute(self, parameters: dict | None = None) -> dict:
        if not parameters:
            parameters = {}
        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        for story in data:
            news_items = story.get("news_items", [])
            if not news_items:
                continue

            item_threshold: int = self.summary_threshold // len(news_items)
            content_to_summarize = "".join(news_item["content"][:item_threshold] + news_item["title"] for news_item in news_items)

            content_to_summarize = content_to_summarize[:self.summary_threshold]

            logger.debug(f"Summarizing {story['id']} with {len(content_to_summarize)} characters")
            try:
                summary = self.predict_summary(content_to_summarize)
                if summary:
                    self.core_api.update_story_summary(story["id"], summary)
                    logger.debug(f"Created summary for: {story['id']}")
            except Exception as e:
                logger.exception(f"Could not generate summary for {story['id']}: {str(e)}")
                continue

        return {"message": f"Summarized {len(data)} stories"}

    def predict_summary(self, text_to_summarize: str) -> str:
        """Call the external summarization service using cog predict."""
        try:
            result = subprocess.run(
                [
                    "cog",
                    "predict",
                    "-i", f"content={text_to_summarize}",
                    "-i", f"title=",  
                ],
                capture_output=True,
                text=True,
                cwd="cog"
            )

            if result.returncode != 0:
                logger.error(f"Cog predict failed: {result.stderr}")
                return ""

            prediction_output = json.loads(result.stdout)
            summary = prediction_output.get("output", "")
            return summary

        except Exception as e:
            logger.error(f"Error during prediction: {str(e)}")
            return ""
