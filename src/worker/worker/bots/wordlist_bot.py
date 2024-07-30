import re
from .base_bot import BaseBot
from worker.log import logger


class WordlistBot(BaseBot):
    def __init__(self):
        super().__init__()

        self.type = "WORDLIST_BOT"
        self.name = "Wordlist Bot"
        self.description = "Bot for tagging news items by wordlist"

    def execute(self, parameters: dict | None = None):
        if not parameters:
            parameters = {}
        ignore_case = self._set_ignore_case_flag(parameters)
        override_existing_tags = parameters.get("OVERRIDE_EXISTING_TAGS", True)

        word_list_entries = self._get_word_list_entries()
        if not word_list_entries:
            return {"message": "No word list entries found"}

        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        found_tags = self._find_tags_for_stories(data, word_list_entries, override_existing_tags, ignore_case)
        if not found_tags:
            return {"message": "No tags found"}

        self.core_api.update_tags(found_tags, self.type)
        return {"message": f"Extracted {len(found_tags)} tags"}

    @staticmethod
    def _set_ignore_case_flag(parameters):
        return re.IGNORECASE if parameters.get("IGNORECASE", "true").lower() == "true" else re.NOFLAG

    def _get_word_list_entries(self):
        if word_lists := self.core_api.get_words_for_tagging_bot():
            return [entry for word_list in word_lists["items"] for entry in word_list["entries"]]
        return

    def _find_tags_for_stories(self, data, word_list_entries, override_existing_tags, ignore_case):
        found_tags = {}
        logger.info(f"Extracting tags from news items: {len(data)}")
        for i, story in enumerate(data):
            if i % max(len(data) // 10, 1) == 0:
                logger.debug(f"Extracting words from {story['id']}: {i}/{len(data)}")
            if findings := self._find_tags(story, word_list_entries, override_existing_tags, ignore_case):
                found_tags[story["id"]] = findings
        return found_tags

    def _find_tags(self, stord, word_list_entries, override_existing_tags, ignore_case):
        findings = {}
        entry_set = {item["value"]: item["category"] for item in word_list_entries}
        existing_tags = stord["tags"] or {}

        all_content = self._story_content(stord)

        for entry, category in entry_set.items():
            if re.search(r"\b" + re.escape(entry) + r"\b", all_content, ignore_case):
                if entry in existing_tags and not override_existing_tags:
                    continue
                findings[entry] = category

        return findings

    @staticmethod
    def _story_content(story):
        return " ".join([news_item["title"] + news_item["review"] + news_item["content"] for news_item in story["news_items"]])
