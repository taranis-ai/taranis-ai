from .base_bot import BaseBot
from worker.log import logger
import py3langid
from flair.data import Sentence
from flair.models import SequenceTagger


class NLPBot(BaseBot):
    def __init__(self, language="en"):
        super().__init__()
        self.type = "NLP_BOT"
        self.name = "NLP Bot"
        self.description = "Bot for naturale language processing of news items"
        self.language = language
        self.extraction_line_limit = 50
        self.initialize_models()

        logger.debug("Setup NER Model...")
        self.ner_multi = SequenceTagger.load("flair/ner-multi")

    def execute(self, parameters=None):
        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        all_keywords = {k: v for story in data for k, v in story["tags"].items()}

        update_result = {}
        tag_count = 0

        for i, story in enumerate(data):
            if attributes := story.get("news_item_attributes", {}):
                if self.type in [d["key"] for d in attributes if "key" in d]:
                    logger.debug(f"Skipping {story['id']} because it has attributes: {attributes}")
                    continue
            if i % max(len(data) // 4, 1) == 0:
                logger.debug(f"Extracting NER from {story['id']}: {i}/{len(data)}")
                logger.debug(f"{update_result=}")
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
        story_content = self.get_first_and_last_n_lines(story_content, self.extraction_line_limit)
        current_keywords |= self.extract_ner(story_content, all_keywords)
        return current_keywords

    def get_first_and_last_n_lines(self, content: str, line_limit: int = 50) -> str:
        lines = [line for line in content.split("\n") if line]
        if len(lines) <= (line_limit * 2):
            return "\n".join(lines[:line_limit] + lines[line_limit:])
        return "\n".join(lines[:line_limit] + lines[-line_limit:])

    def extract_ner(self, text: str, all_keywords) -> dict:
        sentence = Sentence(text, use_tokenizer=False)
        self.model.predict(sentence)
        current_keywords = {}
        for ent in sentence.get_labels():
            tag = ent.data_point.text
            if len(tag) > 2 and ent.score > 0.97:
                tag_type = all_keywords[tag] if tag in all_keywords else ent.value
                current_keywords[tag] = tag_type

        return current_keywords

    def detect_language(self, text) -> str:
        return py3langid.classify(text)[0]

    # def not_in_stopwords(self, keyword: str) -> bool:
    #    return keyword not in stopwords.words(self.language)
