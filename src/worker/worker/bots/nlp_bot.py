from .base_bot import BaseBot
from worker.log import logger
import py3langid
import torch
from flair.data import Sentence
from flair.nn import Classifier


class NLPBot(BaseBot):
    type = "NLP_BOT"
    name = "NLP Bot"
    description = "Bot for naturale language processing of news items"

    def __init__(self):
        super().__init__()
        logger.debug("Setup NER Model...")
        # self.ner_english = Classifier.load("flair/ner-english-fast")
        # self.ner_german = Classifier.load("flair/ner-german")
        self.ner_multi = Classifier.load("flair/ner-multi")
        torch.set_num_threads(1)  # https://github.com/pytorch/pytorch/issues/36191
        self.extraction_text_limit = 5000

    def execute(self, parameters=None):
        if not parameters:
            return
        try:
            filter_dict = self.get_filter_dict(parameters)

            data = self.core_api.get_news_items_aggregate(filter_dict)
            if not data:
                logger.critical("Error getting news items")
                return

            all_keywords = {k: v for news_item in data for k, v in news_item["tags"].items()}

            update_result = {}

            for i, aggregate in enumerate(data):
                if i % max(len(data) // 10, 1) == 0:
                    logger.debug(f"Extracting NER from {aggregate['id']}: {i}/{len(data)}")
                    self.core_api.update_tags(update_result)
                    update_result = {}

                current_keywords = self.extract_keywords(aggregate, all_keywords)
                all_keywords |= current_keywords
                update_result[aggregate["id"]] = current_keywords
            self.core_api.update_tags(update_result)

        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def extract_keywords(self, aggregate: dict, all_keywords: dict) -> dict:
        current_keywords = aggregate.get("tags", {})
        # drop "name" from current_keywords
        current_keywords = {k: v for k, v in current_keywords.items() if k != "name"}
        aggregate_content = "\n".join(news_item["news_item_data"]["content"] for news_item in aggregate["news_items"])
        lines = self.get_first_and_last_20_lines(aggregate_content)
        ner_model = self.get_ner_model(aggregate_content)
        for line in lines:
            current_keywords |= self.extract_ner(line, all_keywords, ner_model)
        return current_keywords

    def get_ner_model(self, text: str) -> Classifier:
        return self.ner_multi
        # language = self.detect_language(text)
        # if language == "en":
        #     return self.ner_english
        # elif language == "de":
        #     return self.ner_german
        # else:
        #     return self.ner_multi

    def get_first_and_last_20_lines(self, content: str) -> list:
        lines = [line for line in content.split("\n") if line]
        if len(lines) <= 40:
            return lines[:20] + lines[20:]
        return lines[:20] + lines[-20:]

    def extract_ner(self, text: str, all_keywords, ner_model) -> dict:
        sentence = Sentence(text)
        ner_model.predict(sentence)
        current_keywords = {}
        for ent in sentence.get_labels():
            tag = ent.data_point.text
            if len(tag) > 2 and ent.score > 0.97:
                tag_type = all_keywords[tag]["tag_type"] if tag in all_keywords else ent.value
                current_keywords[tag] = {"tag_type": tag_type}

        return current_keywords

    def detect_language(self, text) -> str:
        return py3langid.classify(text)[0]

    # def not_in_stopwords(self, keyword: str) -> bool:
    #    return keyword not in stopwords.words(self.language)
