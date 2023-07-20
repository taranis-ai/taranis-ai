from .base_bot import BaseBot
from worker.log import logger
import spacy, spacy.cli
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
    """
    summary_threshold: int
        if content is larger than summary_threshold it will be summarized
    """
    summary_threshold = 750

    def set_summarization_model(self) -> None:
        self.sum_model_name_en = "facebook/bart-large-cnn"
        self.sum_model_en = BartForConditionalGeneration.from_pretrained(self.sum_model_name_en)
        self.sum_tokenizer_en = BartTokenizer.from_pretrained(self.sum_model_name_en)
        self.sum_model_name_de = "T-Systems-onsite/mt5-small-sum-de-en-v2"
        self.sum_model_de = AutoModelForSeq2SeqLM.from_pretrained(self.sum_model_name_de)
        self.sum_tokenizer_de = AutoTokenizer.from_pretrained(self.sum_model_name_de, use_fast=False)

    def bot_setup(self):
        logger.debug("Setup Summarization Model...")
        self.set_summarization_model()
        logger.debug("Setup NER Model...")
        self.ner_model = spacy.load("xx_ent_wiki_sm")

        # logger.debug("Setup KeyWord Model...")
        # self.kw_model_en = KeyBERT("all-MiniLM-L6-v2")
        # self.kw_model_de = KeyBERT("paraphrase-mpnet-base-v2")

    def execute(self, parameters=None):
        if not parameters:
            return
        try:
            source_group = parameters.get("SOURCE_GROUP", None)

            limit = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()

            data = self.core_api.get_news_items_aggregate(source_group, limit)
            if not data:
                logger.critical("Error getting news items")
                return

            for aggregate in data:
                existing_tags = aggregate.get("tags", [])
                keywords = []
                content_list = []

                if aggregate.get("summary", None) and aggregate.get("tags", None):
                    logger.debug(f"Skipping aggregate: {aggregate['id']}")
                    continue

                logger.debug(f"NLP processing aggregate: {aggregate['id']}")

                for news_item in aggregate["news_items"]:
                    content = (
                        news_item["news_item_data"]["content"] + news_item["news_item_data"]["review"] + news_item["news_item_data"]["title"]
                    )
                    if len(content) > self.summary_threshold:
                        content_list.append(content)

                    if "language" in news_item["news_item_data"] and news_item["news_item_data"]["language"] != "":
                        self.language = self.detect_language(content)
                        self.core_api.update_news_item_data(news_item["news_item_data"]["id"], {"language": self.language})

                    if len(existing_tags) == 0:
                        current_keywords = self.extract_ner(content)
                        keywords.extend([keyword for keyword in current_keywords[:10] if keyword["name"] not in existing_tags])

                    # Disabled for now, as it is not working well
                    # current_keywords = self.generateKeywords(content)
                    # keywords.extend(keyword[0] for keyword in current_keywords[:10])

                if not aggregate.get("summary"):
                    try:
                        if summary := self.predict_summary(content_list):
                            self.core_api.update_news_items_aggregate_summary(aggregate["id"], summary)
                    except Exception:
                        logger.log_debug_trace(f"Could not generate summary for {aggregate['id']}")
                if keywords:
                    self.core_api.update_news_item_tags(aggregate["id"], keywords)

        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def extract_ner(self, text):
        ner_model = self.ner_model
        doc = ner_model(text)
        return [{"name": ent.text, "type": ent.label_} for ent in doc.ents if len(ent.text) > 2]

    def generateKeywords(self, text):
        stop_words = "german" if self.language == "de" else "english"
        kw_model = self.kw_model_de if self.language == "de" else self.kw_model_en
        return kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 1),
            stop_words=stop_words,
            top_n=10,
        )

    def detect_language(self, text) -> str:
        return py3langid.classify(text)[0]

    def predict_summary(self, texts: list, pct_min_length: float = 0.2) -> str:
        text_to_summarize = "".join(f" {t}" for t in texts)
        if not text_to_summarize:
            return ""
        nb_tokens = len(text_to_summarize.split(" "))
        min_length = int(nb_tokens * pct_min_length)
        max_length = nb_tokens
        sum_model = None
        sum_tokenizer = None

        if self.language == "de":
            sum_model = self.sum_model_de
            sum_tokenizer = self.sum_tokenizer_de

        elif self.language == "en":
            sum_model = self.sum_model_en
            sum_tokenizer = self.sum_tokenizer_en

        if not sum_model or not sum_tokenizer:
            return ""

        input_ids = sum_tokenizer(
            text_to_summarize,
            max_length=1024,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )["input_ids"]
        if input_ids is None:
            return ""

        summary_ids = sum_model.generate(  # type: ignore
            input_ids=input_ids,
            min_length=min_length,
            max_length=max_length,
            no_repeat_ngram_size=2,
            num_beams=6,
        )
        return sum_tokenizer.batch_decode(
            summary_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
