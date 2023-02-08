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
            keyword_param = self.parameters.get("KEYWORDS", None)

            if keyword_param is None or source_group is None or keyword_param == "":
                return

            keywords = keyword_param.split(",")

            limit = self.history()

            data = self.core_api.get_news_items_aggregate(source_group, limit)
            if not data:
                return

            for aggregate in data:
                findings = set()
                existing_tags = aggregate["tags"] if aggregate["tags"] is not None else []
                for news_item in aggregate["news_items"]:
                    content = news_item["news_item_data"]["content"]

                    for keyword in keywords:
                        if keyword in content and keyword not in existing_tags:
                            findings.add(keyword)
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
