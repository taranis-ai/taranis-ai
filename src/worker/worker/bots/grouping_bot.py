import re
from .base_bot import BaseBot
from worker.log import logger
from collections import defaultdict


class GroupingBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "GROUPING_BOT"
        self.name = "Grouping Bot"
        self.description = "Bot for grouping news items into aggregates"
        self.default_regex = r"CVE-\d{4}-\d{4,7}"

    def execute(self, parameters=None):
        regexp = parameters.get("REGULAR_EXPRESSION", None)
        if not regexp:
            raise ValueError("GroupingBot requires REGULAR_EXPRESSION parameter")

        if not (data := self.get_stories(parameters)):
            return None

        findings = defaultdict(list)
        for aggregate in data:
            for news_item in aggregate["news_items"]:
                content = news_item["news_item_data"]["content"]
                title = news_item["news_item_data"]["title"]

                analyzed_content = set((title + content).split())
                for element in analyzed_content:
                    if finding := re.search(f"({regexp})", element.strip(".,")):
                        findings[finding[1]].append(aggregate["id"])
                        break

        if not findings:
            return

        for group, ids in findings.items():
            if len(ids) > 1:
                logger.debug(f"Grouping: {group} with: {ids}")
                self.core_api.news_items_grouping(ids)
