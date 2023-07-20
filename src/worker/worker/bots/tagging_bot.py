import re
import datetime

from .base_bot import BaseBot
from worker.log import logger


class TaggingBot(BaseBot):
    type = "TAGGING_BOT"
    name = "Tagging Bot"
    description = "Bot for tagging news items"

    def execute(self, parameters=None):
        if not parameters:
            return
        try:
            source_group = parameters.get("SOURCE_GROUP", None)
            regexp = parameters.get("REGULAR_EXPRESSION", None)

            if not regexp or not source_group:
                return

            limit = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()

            data = self.core_api.get_news_items_aggregate(source_group, limit)
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

        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
