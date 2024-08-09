from .base_bot import BaseBot
from worker.log import logger

import torch


class SummaryBot(BaseBot):
    def __init__(self, language="en"):
        super().__init__()
        self.type = "SUMMARY_BOT"
        self.name = "Summary generation Bot"
        self.description = "Bot to generate summaries for stories"
        self.summary_threshold = 1000
        self.language = language
        self.initialize_models()
        torch.set_num_threads(1)  # https://github.com/pytorch/pytorch/issues/36191

    def execute(self, parameters: dict | None = None) -> dict:
        if not parameters:
            parameters = {}
        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        for story in data:
            news_items = story.get("news_items", [])
            item_threshold: int = self.summary_threshold // len(news_items)
            content_to_summarize = "".join(news_item["content"][:item_threshold] + news_item["title"] for news_item in news_items)

            logger.debug(f"Summarizing {story['id']} with {len(content_to_summarize)} characters")
            try:
                if summary := self.predict_summary(content_to_summarize[: self.summary_threshold]):
                    self.core_api.update_story_summary(story["id"], summary)
            except Exception:
                logger.exception(f"Could not generate summary for {story['id']}")
                continue

            logger.debug(f"Created summary for : {story['id']}")
        return "Summarized stories"

    def predict_summary(self, text_to_summarize: str) -> str:
        min_length = int(len(text_to_summarize.split()) * 0.2)
        max_length = len(text_to_summarize.split())
        model = self.model
        tokenizer = self.tokenizer

        if not model or not tokenizer:
            logger.error(f"Model or Tokenizer not found for language {self.language}")
            return ""

        input_ids = tokenizer(text_to_summarize, return_tensors="pt", padding=True, truncation=True, max_length=1024)["input_ids"]
        summary_ids = model.generate(input_ids, min_length=min_length, max_length=max_length, no_repeat_ngram_size=2, num_beams=4)

        return tokenizer.decode(summary_ids[0], skip_special_tokens=True)
