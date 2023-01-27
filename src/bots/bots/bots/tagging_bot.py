from .base_bot import BaseBot
from bots.managers.log_manager import logger
import datetime


class TaggingBot(BaseBot):
    type = "TAGGING_BOT"
    name = "Tagging Bot"
    description = "Bot for tagging news items"

    def execute(self):
        try:
            source_group = self.parameters.get("SOURCE_GROUP", None)
            keywords = self.parameters["KEYWORDS"].split(",")

            limit = self.history()
            logger.log_debug(f"LIMIT: {limit}")
            logger.log_debug(f"KEYWORDKS: {keywords}")

            data = self.core_api.get_news_items_aggregate(source_group, limit)
            if not data:
                return

            for aggregate in data:
                findings = {}
                for news_item in aggregate["news_items"]:
                    content = news_item["news_item_data"]["content"]
                    existing_tags = news_item["news_item_data"]["tags"] if news_item["news_item_data"]["tags"] is not None else []

                    for keyword in keywords:
                        if keyword in content and keyword not in existing_tags:
                            if news_item["id"] in findings:
                                findings[news_item["id"]] = findings[news_item["id"]].add(keyword)
                            else:
                                findings[news_item["id"]] = {keyword}
                for news_id, keyword in findings.items():
                    logger.log_debug(f"news_id: {news_id}, keyword: {keyword}")
                    if keyword is None:
                        continue
                    self.core_api.update_news_item_tags(news_id, list(keyword))

        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def execute_on_event(self, event_type, data):
        try:
            # source_group = preset.parameter_values["SOURCE_GROUP"]
            # keywords = preset.parameter_values["KEYWORDS"]
            pass
        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
