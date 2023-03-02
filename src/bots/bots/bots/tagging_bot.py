from .base_bot import BaseBot
from bots.managers.log_manager import logger
import re


class TaggingBot(BaseBot):
    type = "TAGGING_BOT"
    name = "Tagging Bot"
    description = "Bot for tagging news items"

    def execute(self):
        try:
            source_group = self.parameters.get("SOURCE_GROUP", None)
            regexp = self.parameters.get("REGULAR_EXPRESSION", None)

            if not regexp or not source_group:
                return

            limit = self.history()

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

    def execute_on_event(self, event_type, data):
        try:
            # source_group = preset.parameter_values["SOURCE_GROUP"]
            # keywords = preset.parameter_values["KEYWORDS"]
            pass
        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
