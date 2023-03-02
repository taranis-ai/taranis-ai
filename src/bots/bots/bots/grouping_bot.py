import re
from .base_bot import BaseBot
from bots.managers.log_manager import logger
from collections import defaultdict


class GroupingBot(BaseBot):
    type = "GROUPING_BOT"
    name = "Grouping Bot"
    description = "Bot for grouping news items into aggregates"

    def execute(self):
        try:
            source_group = self.parameters.get("SOURCE_GROUP", None) or "default"
            regexp = self.parameters.get("REGULAR_EXPRESSION", None)

            if not source_group or not regexp:
                return

            limit = self.history()
            import datetime

            limit = (datetime.datetime.now() - datetime.timedelta(days=30)).isoformat()
            data = self.core_api.get_news_items_aggregate(source_group, limit)
            if not data:
                return

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

    def execute_on_event(self, event_type, data):
        try:
            source_group = self.parameters["SOURCE_GROUP"]
            regexp = self.parameters["REGULAR_EXPRESSION"]
            logger.log_debug(source_group + regexp)

        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
