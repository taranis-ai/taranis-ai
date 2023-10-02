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

            if not (data := self.get_stories(parameters)):
                return "Error getting news items"

            found_tags = {}
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
                found_tags[aggregate["id"]] = findings

            self.core_api.update_tags(found_tags, self.type)

        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
