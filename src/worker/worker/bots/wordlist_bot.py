import datetime
import re

from .base_bot import BaseBot
from worker.log import logger


class WordlistBot(BaseBot):
    type = "WORDLIST_BOT"
    name = "Wordlist Bot"
    description = "Bot for tagging news items by wordlist"

    def execute(self, parameters=None):
        if not parameters:
            return
        try:
            limit = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat(timespec="seconds")

            filter_dict = {"timestamp": limit}

            if source_group := parameters.get("SOURCE_GROUP"):
                filter_dict["group"] = source_group

            if source := parameters.get("SOURCE"):
                filter_dict["source"] = source

            override_existing_tags = parameters.get("OVERRIDE_EXISTING_TAGS", True)

            word_lists = self.core_api.get_words_for_tagging_bot()
            if not word_lists:
                return "No word lists found"

            word_list_entries = [entry for word_list in word_lists["items"] for entry in word_list["entries"]]

            data = self.core_api.get_news_items_aggregate(filter_dict=filter_dict)

            if not data or not word_list_entries:
                return "No data or word list entries found"

            for aggregate in data:
                if findings := self.find_tags(aggregate, word_list_entries, override_existing_tags):
                    logger.debug(f"Found tags: {findings}")
                    self.core_api.update_news_item_tags(aggregate["id"], findings)

        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
            return str(error)

    def find_tags(self, aggregate: dict, word_list_entries: list, override_existing_tags: bool) -> dict:
        findings = {}
        entry_set = {item["value"]: item["category"] for item in word_list_entries}
        existing_tags = aggregate["tags"] or {}

        all_content = " ".join(
            [
                news_item["news_item_data"]["title"] + news_item["news_item_data"]["review"] + news_item["news_item_data"]["content"]
                for news_item in aggregate["news_items"]
            ]
        )

        for entry, category in entry_set.items():
            if re.search(r"\b" + re.escape(entry) + r"\b", all_content, re.IGNORECASE):
                if entry in existing_tags and not override_existing_tags:
                    continue
                findings[entry] = {"tag_type": category}
        return findings
