import re
import datetime

from .base_bot import BaseBot
from worker.log import logger


class TaggingBot(BaseBot):
    type = "WORDLIST_BOT"
    name = "Wordlist Bot"
    description = "Bot for tagging news items by wordlist"

    def execute(self, parameters=None):
        if not parameters:
            return
        try:
            source_group = parameters.get("SOURCE_GROUP", None)

            if not source_group:
                return

            limit = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()

            filter_dict = {"timestamp": limit, "source_group": source_group}

            word_list_entries = self.core_api.get_words_by_source_group(source_group)

            data = self.core_api.get_news_items_aggregate(filter_dict=filter_dict)
            if not data:
                return

            for aggregate in data:
                findings = set()
                existing_tags = aggregate["tags"] or []
                for news_item in aggregate["news_items"]:
                    content = news_item["news_item_data"]["content"]
                    title = news_item["news_item_data"]["title"]
                    review = news_item["news_item_data"]["review"]

                    analyzed_content = set((title + review + content).split())
                    analyzed_content = analyzed_content.difference(existing_tags)
                    findings.add(analyzed_content.intersection(word_list_entries))
                self.core_api.update_news_item_tags(aggregate["id"], list(findings))

        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
