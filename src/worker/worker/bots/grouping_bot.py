import re
from .base_bot import BaseBot
from worker.log import logger
from collections import defaultdict


class GroupingBot(BaseBot):
    type = "GROUPING_BOT"
    name = "Grouping Bot"
    description = "Bot for grouping news items into aggregates"
    default_regex = r"CVE-\d{4}-\d{4,7}"

    def execute(self, parameters=None):
        if not parameters:
            return
        try:
            regexp = parameters.get("REGULAR_EXPRESSION", None)
            if not regexp:
                return

            if not (data := self.get_stories(parameters)):
                return "Error getting news items"

            findings = defaultdict(list)
            for aggregate in data:
                for news_item in aggregate["news_items"]:
                    content = news_item["news_item_data"]["content"]
                    title = news_item["news_item_data"]["title"]
                    review = news_item["news_item_data"]["review"]

                    analyzed_content = set((title + review + content).split())
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

        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
