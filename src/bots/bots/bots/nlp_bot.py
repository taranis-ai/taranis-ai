from .base_bot import BaseBot
from shared.schema.parameter import Parameter, ParameterType
from bots.managers.log_manager import logger
import datetime
from keybert import KeyBERT
from nltk.corpus import stopwords


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
                for news_item in aggregate["news_items"]:
                    content = news_item["news_item_data"]["content"]

                    findings[news_item["id"]] = self.generateKeywords(language, kw_model, content)

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
