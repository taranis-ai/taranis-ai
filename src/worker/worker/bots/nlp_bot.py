from .base_bot import BaseBot
from worker.log import logger
import py3langid
from flair.data import Sentence


class NLPBot(BaseBot):
    def __init__(self, language="en"):
        super().__init__()
        self.type = "NLP_BOT"
        self.name = "NLP Bot"
        self.description = "Bot for naturale language processing of news items"
        self.language = language
        self.extraction_line_limit = 50
        self.initialize_models()

    def execute(self, parameters: dict | None = None) -> dict:
        if not parameters:
            parameters = {}
        stories = self.get_stories(parameters)
        if not stories:
            return {"message": "No new stories found"}

        all_keywords = self.collect_keywords(stories)
        batch_mode = parameters.get("batch_mode", len(stories) > 10)
        tag_count = self.process_stories(stories, all_keywords, batch_mode)
        return {"message": f"Extracted {tag_count} tags"}

    def collect_keywords(self, stories: list) -> dict:
        return {k: v for story in stories for k, v in story["tags"].items()}

    def process_stories(self, stories: list, all_keywords: dict, batch_mode: bool) -> int:
        update_result = {}
        tag_count = 0

        for i, story in enumerate(stories):
            if batch_mode and i % max(len(stories) // 4, 1) == 0:
                self.log_progress(story["id"], i, len(stories))
                tag_count += self.update_tags(update_result)
                update_result = {}

            current_keywords = self.extract_keywords(story, all_keywords)
            all_keywords |= current_keywords
            update_result[story["id"]] = current_keywords

        tag_count += self.update_tags(update_result)
        return tag_count

    def update_tags(self, update_result: dict) -> int:
        self.core_api.update_tags(update_result, self.type)
        return len(update_result)

    def log_progress(self, story_id: str, current_index: int, total: int) -> None:
        logger.debug(f"Extracting NER from {story_id}: {current_index}/{total}")

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
