from .base_bot import BaseBot
from worker.log import logger
import py3langid
import torch
from flair.data import Sentence
from flair.nn import Classifier


class NLPBot(BaseBot):
    def __init__(self, language="en"):
        super().__init__()
        self.type = "NLP_BOT"
        self.name = "NLP Bot"
        self.description = "Bot for naturale language processing of news items"
        self.language = language
        self.set_language(self.language)

        logger.debug("Setup NER Model...")
        self.set_ner_model()
        torch.set_num_threads(1)  # https://github.com/pytorch/pytorch/issues/36191
        self.extraction_line_limit = 20

    def set_ner_model(self):
        self.ner_multi = self.models[self.language]["NLP_BOT"]

    def execute(self, parameters=None):
        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        all_keywords = {k: v for news_item in data for k, v in news_item["tags"].items()}

        update_result = {}
        tag_count = 0

        for i, story in enumerate(data):
            if attributes := story.get("news_item_attributes", {}):
                if self.type in [d["key"] for d in attributes if "key" in d]:
                    logger.debug(f"Skipping {story['id']} because it has attributes: {attributes}")
                    continue
            if i % max(len(data) // 4, 1) == 0:
                logger.debug(f"Extracting NER from {story['id']}: {i}/{len(data)}")
                self.core_api.update_tags(update_result, self.type)
                tag_count += len(update_result)
                update_result = {}

            current_keywords = self.extract_keywords(story, all_keywords)
            all_keywords |= current_keywords
            update_result[story["id"]] = current_keywords
        self.core_api.update_tags(update_result, self.type)
        tag_count += len(update_result)
        return {"message": f"Extracted {tag_count} tags"}

    def extract_keywords(self, story: dict, all_keywords: dict) -> dict:
        current_keywords = story.get("tags", {})
        # drop "name" from current_keywords
        current_keywords = {k: v for k, v in current_keywords.items() if k != "name"}
        story_content = "\n".join(news_item["content"] for news_item in story["news_items"])
        lines = self.get_first_and_last_n_lines(story_content)
        for line in lines:
            current_keywords |= self.extract_ner(line, all_keywords, self.ner_multi)
        return current_keywords

    def get_first_and_last_n_lines(self, content: str) -> list:
        ll = self.extraction_line_limit
        lines = [line for line in content.split("\n") if line]
        if len(lines) <= (ll * 2):
            return lines[:ll] + lines[ll:]
        return lines[:ll] + lines[-ll:]

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
