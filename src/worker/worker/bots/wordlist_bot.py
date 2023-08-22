import datetime

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

            word_list_entries = self.core_api.get_words_for_tagging_bot()

            data = self.core_api.get_news_items_aggregate(filter_dict=filter_dict)

            if not data or not word_list_entries:
                return "No data or word list entries found"

            for aggregate in data:
                if findings := self.find_tags(aggregate, word_list_entries):
                    logger.debug(f"Found tags: {findings}")
                    self.core_api.update_news_item_tags(aggregate["id"], findings)

        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
            return str(error)

    def find_tags(self, aggregate: dict, word_list_entries: list) -> list:
        findings = set()
        entry_set = {item["value"] for item in word_list_entries}
        existing_tags = aggregate["tags"] or []
        for news_item in aggregate["news_items"]:
            content = news_item["news_item_data"]["content"]
            title = news_item["news_item_data"]["title"]
            review = news_item["news_item_data"]["review"]

            analyzed_content = set((title + review + content).split())
            analyzed_content = analyzed_content.difference(existing_tags)
            findings.update(analyzed_content.intersection(entry_set))
        return list(findings)
