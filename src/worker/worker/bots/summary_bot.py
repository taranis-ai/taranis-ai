from .base_bot import BaseBot
from worker.log import logger

import torch
from transformers import (
    BartTokenizer,
    BartForConditionalGeneration,
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
)


class SummaryBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "SUMMARY_BOT"
        self.name = "Summary generation Bot"
        self.description = "Bot to generate summaries for stories"
        self.summary_threshold = 750
        logger.debug("Setup Summarization Model...")
        torch.set_num_threads(1)  # https://github.com/pytorch/pytorch/issues/36191
        self.set_summarization_model()

    def set_summarization_model(self) -> None:
        self.sum_model_name_en = "facebook/bart-large-cnn"
        self.sum_model_en = BartForConditionalGeneration.from_pretrained(self.sum_model_name_en)
        self.sum_tokenizer_en = BartTokenizer.from_pretrained(self.sum_model_name_en)
        self.sum_model_name_de = "T-Systems-onsite/mt5-small-sum-de-en-v2"
        self.sum_model_de = AutoModelForSeq2SeqLM.from_pretrained(self.sum_model_name_de)
        self.sum_tokenizer_de = AutoTokenizer.from_pretrained(self.sum_model_name_de, use_fast=False)

    def execute(self, parameters=None):
        if not parameters:
            return
        try:
            if not (data := self.get_stories(parameters)):
                return "Error getting news items"

            for story in data:
                content_to_summarize = ""

                for news_item in story["news_items"]:
                    content = news_item["content"] + news_item["review"] + news_item["title"]
                    content_to_summarize += content

                if not story.get("summary"):
                    try:
                        if summary := self.predict_summary(content_to_summarize[: self.summary_threshold]):
                            logger.debug(f"Generated summary for {story['id']}: {summary}")
                            self.core_api.update_story_summary(story["id"], summary)
                    except Exception:
                        logger.log_debug_trace(f"Could not generate summary for {story['id']}")

                logger.debug(f"Created summary for : {story['id']}")

        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def predict_summary(self, text_to_summarize: str, pct_min_length: float = 0.2) -> str:
        return "SUMMARY NOT IMPLEMENTED"
        # nb_tokens = len(text_to_summarize.split(" "))
        # min_length = int(nb_tokens * pct_min_length)
        # max_length = nb_tokens
        # sum_model = None
        # sum_tokenizer = None

        # if self.language == "de":
        #     sum_model = self.sum_model_de
        #     sum_tokenizer = self.sum_tokenizer_de

        # elif self.language == "en":
        #     sum_model = self.sum_model_en
        #     sum_tokenizer = self.sum_tokenizer_en

        # if not sum_model or not sum_tokenizer:
        #     return ""

        # logger.debug(
        #     f"Summarizing {max_length} tokens with min_length={min_length} and max_length={max_length}"
        # )

        # input_ids = sum_tokenizer(
        #     text_to_summarize,
        #     max_length=1024,
        #     padding=True,
        #     truncation=True,
        #     return_tensors="pt",
        # )["input_ids"]

        # if input_ids is None:
        #     return ""

        # summary_ids = sum_model.generate(  # type: ignore
        #     input_ids=input_ids,
        #     min_length=min_length,
        #     max_length=max_length,
        #     no_repeat_ngram_size=2,
        #     num_beams=6,
        # )

        # return sum_tokenizer.batch_decode(
        #     summary_ids,
        #     skip_special_tokens=True,
        #     clean_up_tokenization_spaces=False,
        # )[0]
