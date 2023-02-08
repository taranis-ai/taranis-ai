from .base_bot import BaseBot
from bots.managers.log_manager import logger
from keybert import KeyBERT
import py3langid

from transformers import (
    BartTokenizer,
    BartForConditionalGeneration,
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
)


class NLPBot(BaseBot):
    type = "NLP_BOT"
    name = "NLP Bot"
    description = "Bot for naturale language processing of news items"

    r"""
    Parameters
    ------------
    model_name: str
        the pre-trained transformers model to be used;
        currently supported: facebook/bart-large-cnn (default), T-Systems-onsite/mt5-small-sum-de-en-v2, deutsche-telekom/mt5-small-sum-de-en-v1
    """

    def set_summarization_model(self, model_name="facebook/bart-large-cnn") -> None:

        self.sum_model_name = model_name
        if self.sum_model_name == "facebook/bart-large-cnn":
            self.sum_model = BartForConditionalGeneration.from_pretrained(self.sum_model_name)
            self.sum_tokenizer = BartTokenizer.from_pretrained(self.sum_model_name)
        elif self.sum_model_name in [
            "T-Systems-onsite/mt5-small-sum-de-en-v2",
            "deutsche-telekom/mt5-small-sum-de-en-v1",
        ]:
            self.sum_model = AutoModelForSeq2SeqLM.from_pretrained(self.sum_model_name)
            self.sum_tokenizer = AutoTokenizer.from_pretrained(self.sum_model_name, use_fast=False)

    def bot_setup(self):
        self.language = self.parameters.get("LANGUAGE", "de").lower()
        sum_model = "facebook/bart-large-cnn" if self.language == "en" else "T-Systems-onsite/mt5-small-sum-de-en-v2"
        logger.debug("Setup Summarization Model...")
        self.set_summarization_model(sum_model)
        logger.debug("Setup KeyWord Model...")
        self.kw_model = KeyBERT("all-MiniLM-L6-v2") if self.language == "en" else KeyBERT("paraphrase-mpnet-base-v2")

    def execute(self):
        try:
            source_group = self.parameters.get("SOURCE_GROUP", None)

            limit = self.history()
            logger.log_debug(f"LIMIT: {limit}")

            data = self.core_api.get_news_items_aggregate(source_group, limit)
            if not data:
                logger.critical("Error getting news items")
                return

            for aggregate in data:
                keywords = []

                if aggregate.get("summary", None) and aggregate.get("tags", None):
                    logger.debug(f"Skipping aggregate: {aggregate['id']}")
                    continue

                keywords = []
                content_list = []

                logger.debug(f"NLP processing aggregate: {aggregate['id']}")

                for news_item in aggregate["news_items"]:
                    content = (
                        news_item["news_item_data"]["content"] + news_item["news_item_data"]["review"] + news_item["news_item_data"]["title"]
                    )
                    content_list.append(content)

                    self.core_api.update_news_item_data(news_item["news_item_data"]["id"], {"language": self.detect_language(content)})

                    current_keywords = self.generateKeywords(content)
                    keywords.extend(keyword[0] for keyword in current_keywords[:10])

                if summary := self.predict_summary(content_list):
                    self.core_api.update_news_items_aggregate_summary(aggregate["id"], summary)
                if keywords:
                    self.core_api.update_news_item_tags(aggregate["id"], keywords)

        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def execute_on_event(self, event_type, data):
        try:
            # source_group = preset.parameter_values["SOURCE_GROUP"]
            # keywords = preset.parameter_values["KEYWORDS"]
            pass
        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def generateKeywords(self, text):
        stop_words = "german" if self.language == "de" else "english"
        return self.kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words=stop_words,
            use_mmr=True,
            diversity=0.8,
            top_n=15,
        )

    def detect_language(self, text) -> str:
        return py3langid.classify(text)[0]

    def predict_summary(self, texts, pct_min_length=0.2):
        r"""
        Generates summary for a list of texts.

        Parameters
        -------------
        texts: list
            List of strings denoting the documents that need to be summarized.

        pct_min_length: int
            Percentage of number of words from the input documents as minimum length for the summary.
        Returns
        -------------
        summary: str
            String denoting the summary of the input documents.
        """

        text_to_summarize = "".join(f" {t}" for t in texts)
        nb_tokens = len(text_to_summarize.split(" "))
        min_length = int(nb_tokens * pct_min_length)
        max_length = nb_tokens
        if not self.sum_model:
            return ""

        input_ids = self.sum_tokenizer(
            text_to_summarize,
            max_length=1024,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )["input_ids"]
        if input_ids is None:
            return ""

        if self.sum_model_name == "facebook/bart-large-cnn":
            summary_ids = self.sum_model.generate(
                input_ids=input_ids,
                min_length=min_length,
                max_length=max_length,
                no_repeat_ngram_size=2,
                num_beams=6,
            )
            return self.sum_tokenizer.batch_decode(
                summary_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0]

        output_ids = self.sum_model.generate(
            input_ids=input_ids,
            min_length=min_length,
            max_length=max_length,
            no_repeat_ngram_size=2,
            num_beams=6,
        )[0]
        return self.sum_tokenizer.decode(output_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
