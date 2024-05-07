from .base_bot import BaseBot
from worker.log import logger

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
)


class SummaryBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "SUMMARY_BOT"
        self.name = "Summary generation Bot"
        self.description = "Bot to generate summaries for stories"
        self.summary_threshold = 1000
        self.language = "en"
        logger.debug("Setup Summarization Model...")
        torch.set_num_threads(1)  # https://github.com/pytorch/pytorch/issues/36191
        self.set_summarization_model()

    def set_summarization_model(self) -> None:
        self.model_names = {"en": "facebook/bart-large-cnn", "de": "T-Systems-onsite/mt5-small-sum-de-en-v2"}
        self.models = {}
        self.tokenizers = {}
        for lang, model_name in self.model_names.items():
            self.models[lang] = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            self.tokenizers[lang] = AutoTokenizer.from_pretrained(model_name, use_fast=True)

    def execute(self, parameters=None):
        try:
            if not (data := self.get_stories(parameters)):
                return "Error getting news items"

            for story in data:
                news_items = story.get("news_items", [])
                item_threshold: int = self.summary_threshold // len(news_items)
                content_to_summarize = "".join(news_item["content"][:item_threshold] + news_item["title"] for news_item in news_items)

                logger.debug(f"Summarizing {story['id']} with {len(content_to_summarize)} characters")
                try:
                    if summary := self.predict_summary(content_to_summarize[: self.summary_threshold]):
                        self.core_api.update_story_summary(story["id"], summary)
                except Exception:
                    logger.log_debug_trace(f"Could not generate summary for {story['id']}")
                    continue

                logger.debug(f"Created summary for : {story['id']}")

        except Exception as e:
            logger.log_debug_trace(f"Error running Bot: {self.type} - {str(e)}")
            return f"Error running Bot - {str(e)}"

    def predict_summary(self, text_to_summarize: str) -> str:
        min_length = int(len(text_to_summarize.split()) * 0.2)
        max_length = len(text_to_summarize.split())
        model = self.models.get(self.language)
        tokenizer = self.tokenizers.get(self.language)

        if not model or not tokenizer:
            logger.error(f"Model or Tokenizer not found for language {self.language}")
            return ""

        input_ids = tokenizer(text_to_summarize, return_tensors="pt", padding=True, truncation=True, max_length=1024)["input_ids"]
        summary_ids = model.generate(input_ids, min_length=min_length, max_length=max_length, no_repeat_ngram_size=2, num_beams=4)

        return tokenizer.decode(summary_ids[0], skip_special_tokens=True)
