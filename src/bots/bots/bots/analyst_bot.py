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
            # source_group = preset.parameter_values["SOURCE_GROUP"]
            regexp = self.parameters["REGULAR_EXPRESSION"].replace(" ", "")
            attr_name = self.parameters["ATTRIBUTE_NAME"].replace(" ", "")

            regexp = regexp.split(",")
            attr_name = attr_name.split(",")

            bots_params = dict(zip(attr_name, regexp))
            limit = self.history()

            if news_items_data := self.core_api.get_news_items_data(limit):
                for item in news_items_data:
                    if item is not type(dict):
                        continue
                    news_item_id = item["id"]
                    title = item["title"]
                    preview = item["review"]
                    content = item["content"]

                    analyzed_text = "".join([title, preview, content]).split()
                    analyzed_text = [item.replace(".", "") if item.endswith(".") else item for item in analyzed_text]
                    analyzed_text = [item.replace(",", "") if item.endswith(",") else item for item in analyzed_text]

                    for element in analyzed_text:

                        attributes = []

                        for key, value in bots_params.items():

                            finding = re.search("(" + value + ")", element)
                            if finding:
                                found_value = finding.group(1)

                                value = found_value
                                binary_mime_type = ""
                                binary_value = ""

                                news_attribute = news_item.NewsItemAttribute(key, value, binary_mime_type, binary_value)

                                attributes.append(news_attribute)

                                news_item_attributes_schema = news_item.NewsItemAttributeSchema(many=True)
                                self.core_api.update_news_item_attributes(
                                    news_item_id,
                                    news_item_attributes_schema.dump(attributes),
                                )

        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def execute_on_event(self, event_type, data):
        try:
            source_group = self.parameters["SOURCE_GROUP"]
            regexp = self.parameters["REGULAR_EXPRESSION"]
            attr_name = self.parameters["ATTRIBUTE_NAME"]
            logger.log_debug(source_group + regexp + attr_name)

        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
