import re

from .base_bot import BaseBot
from worker.log import logger


class TaggingBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "TAGGING_BOT"
        self.name = "Tagging Bot"
        self.description = "Bot for tagging news items based on regular expressions"

    def execute(self, parameters=None):
        regexp = parameters.get("REGULAR_EXPRESSION", None)
        if not regexp:
            raise ValueError("TaggingBot requires REGULAR_EXPRESSION parameter")

        if not (data := self.get_stories(parameters)):
            return None

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

        if not found_tags:
            logger.debug("No tags found")
            return

        self.core_api.update_tags(found_tags, self.type)
