from .base_bot import BaseBot
from shared.schema.parameter import Parameter, ParameterType
from bots.managers.log_manager import logger
import datetime
from keybert import KeyBERT
from nltk.corpus import stopwords

from transformers import (
    BartTokenizer,
    BartForConditionalGeneration,
    MBartTokenizer,
    TFMBartForConditionalGeneration,
    MBartConfig,
)

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from bs4 import BeautifulSoup

def clean_html(text):
    return BeautifulSoup(markup=text, features="html.parser").get_text()

class NLPBot(BaseBot):
    type = "NLP_BOT"
    name = "NLP Bot"
    description = "Bot for naturale language processing of news items"

    parameters = [
        Parameter(
            0,
            "SOURCE_GROUP",
            "Source Group",
            "OSINT Source group to inspect",
            ParameterType.STRING,
        ),
        Parameter(
            0,
            "LANGUAGE",
            "language",
            "language','",
            ParameterType.STRING,
        ),
    ]
    parameters.extend(BaseBot.parameters)
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
            self.sum_tokenizer = AutoTokenizer.from_pretrained(
                    self.sum_model_name, use_fast=False
            )

    def execute(self, preset):
        try:
            source_group = preset.parameter_values["SOURCE_GROUP"]
            interval = preset.parameter_values["REFRESH_INTERVAL"]
            language = preset.parameter_values["LANGUAGE"].lower()

            if language == "en":
                kw_model = KeyBERT("all-MiniLM-L6-v2")
            elif language == "de":
                kw_model = KeyBERT("paraphrase-mpnet-base-v2")

            limit = BaseBot.history(interval)
            limit = datetime.datetime.now() - datetime.timedelta(weeks=12)
            logger.log_debug(f"LIMIT: {limit}")

            data, status = self.core_api.get_news_items_aggregate(source_group, limit)
            if status != 200:
                logger.log_error(f"Error getting news items: {status}")
                return

            if not data:
                logger.log_info("No news items returend")
                return

            for aggregate in data:
                findings = {}
                content_list = []

                for news_item in aggregate["news_items"]:
                    content = news_item["news_item_data"]["content"]
                    content_list.append(content)

                    findings[news_item["id"]] = self.generateKeywords(language, kw_model, content)

                summary = self.predict_summary(content_list)
                self.core_api.update_news_items_aggregate_summary(aggregate["id"],summary)

                for news_id, keywords in findings.items():
                    keyword = [i[0] for i in keywords]
                    logger.log_debug(f"news_id: {news_id}, keyword: {keyword}")
                    self.core_api.update_news_item_tags(news_id, keyword)

        except Exception as error:
            BaseBot.print_exception(preset, error)

    def execute_on_event(self, preset, event_type, data):
        try:
            # source_group = preset.parameter_values["SOURCE_GROUP"]
            # keywords = preset.parameter_values["KEYWORDS"]
            pass
        except Exception as error:
            BaseBot.print_exception(preset, error)

    def generateSummary(self, text: str) -> str:
        # TODO: Implement
        return text

    def generateKeywords(self, language, kw_model, text):
        if language == "en":
            keywords = kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),
                stop_words="english",
                use_mmr=True,
                diversity=0.8,
                top_n=15,
            )
        elif language == "de":
            german_stop_words = stopwords.words("german")
            keywords = kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),
                stop_words=german_stop_words,
                use_mmr=True,
                diversity=0.8,
                top_n=15,
            )

        return keywords

    def predict_summary(self, texts, preprocess=[clean_html], pct_min_length=0.2):
        r"""
        Generates summary for a list of texts.

        Parameters
        -------------
        texts: list
            List of strings denoting the documents that need to be summarized.

        preprocess: list
            List of functions to be applied for pre-processing each text.
            By default it cleans the text from HTML tags and whitespaces.

        pct_min_length: int
            Percentage of number of words from the input documents as minimum length for the summary.
        Returns
        -------------
        summary: str
            String denoting the summary of the input documents.
        """
        text_to_summarize = ""
        for t in texts:
            for f in preprocess:
                t = f(t)
            text_to_summarize += f" {t}"
#        print(text_to_summarize)
        nb_tokens = len(text_to_summarize.split(" "))
        min_length = int(nb_tokens * pct_min_length)
        max_length = nb_tokens
        summary = ""
        if (
            self.sum_model_name == "T-Systems-onsite/mt5-small-sum-de-en-v2"
            or self.sum_model_name == "deutsche-telekom/mt5-small-sum-de-en-v1"
        ):
            input_ids = self.sum_tokenizer(
                [text_to_summarize],
                return_tensors="pt",
                padding="max_length",
                truncation=True,
                max_length=1024,
            )["input_ids"]
            output_ids = self.sum_model.generate(
                input_ids=input_ids,
                min_length=min_length,
                max_length=max_length,
                no_repeat_ngram_size=2,
                num_beams=6,
            )[0]
            summary = self.sum_tokenizer.decode(
                output_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )
        if self.sum_model_name == "facebook/bart-large-cnn":
            inputs = self.sum_tokenizer(
                text_to_summarize,
                max_length=1024,
                padding=True,
                truncation=True,
                return_tensors="pt",
            )
            summary_ids = self.sum_model.generate(
                inputs["input_ids"],
                num_beams=6,
                min_length=min_length,
                max_length=max_length,
                no_repeat_ngram_size=2,
            )
            summary = self.sum_tokenizer.batch_decode(
                summary_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0]

        return summary
