import re

from .base_bot import BaseBot
from shared.schema import news_item
from bots.managers.log_manager import logger


class AnalystBot(BaseBot):
    type = "ANALYST_BOT"
    name = "Analyst Bot"
    description = "Bot for news items analysis"

    regexp = []
    attr_name = []
    news_items = []
    news_items_data = []

    def execute(self):
        try:
            regex = self.parameters.get("REGULAR_EXPRESSION", "")
            attr = self.parameters.get("ATTRIBUTE_NAME", "")
            if not regex or not attr:
                return

            self.regexp = regex.replace(" ", "").split(",")
            self.attr_name = attr.replace(" ", "").split(",")

            bots_params = dict(zip(self.regexp, self.attr_name))
            limit = self.history()

            if news_items_data := self.core_api.get_news_items_data(limit):
                for item in news_items_data:
                    if not item:
                        continue
                    news_item_id = item["id"]
                    title = item["title"]
                    review = item["review"]
                    content = item["content"]

                    analyzed_text = set((title + review + content).split())

                    for element in analyzed_text:
                        attributes = []
                        for key, value in bots_params.items():
                            if finding := re.search(f"({value})", element.strip(".,")):
                                value = finding[1]
                                binary_mime_type = ""
                                binary_value = ""

                                news_attribute = news_item.NewsItemAttribute(key, value, binary_mime_type, binary_value)

                                attributes.append(news_attribute)

                                news_item_attributes_schema = news_item.NewsItemAttributeSchema(many=True)
                                self.core_api.update_news_item_attributes(
                                    news_item_id,
                                    news_item_attributes_schema.dump(attributes),
                                )

        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def execute_on_event(self, event_type, data):
        try:
            source_group = self.parameters["SOURCE_GROUP"]
            regexp = self.parameters["REGULAR_EXPRESSION"]
            attr_name = self.parameters["ATTRIBUTE_NAME"]
            logger.log_debug(source_group + regexp + attr_name)

        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
