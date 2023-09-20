import re

from .base_bot import BaseBot
from worker.log import logger


class TaggingBot(BaseBot):
    type = "TAGGING_BOT"
    name = "Tagging Bot"
    description = "Bot for tagging news items based on regular expressions"

    def execute(self, parameters=None):
        if not parameters:
            return
        try:
            regexp = parameters.get("REGULAR_EXPRESSION", r"CVE-\d{4}-\d{4,7}")

            filter_dict = self.get_filter_dict(parameters)
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

                    for element in analyzed_content:
                        if finding := re.search(f"({regexp})", element.strip(".,")):
                            if finding[1] not in existing_tags:
                                findings.add(finding[1])
                self.core_api.update_news_item_tags(aggregate["id"], list(findings))

        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
