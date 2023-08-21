import re
import datetime

from .base_bot import BaseBot
from worker.log import logger


class AnalystBot(BaseBot):
    type = "ANALYST_BOT"
    name = "Analyst Bot"
    description = "Bot for news items analysis"

    regexp = []
    attr_name = []
    news_items = []
    news_items_data = []

    def execute(self, parameters=None):
        if not parameters:
            return
        try:
            regex = parameters.get("REGULAR_EXPRESSION", "")
            attr = parameters.get("ATTRIBUTE_NAME", "")
            if not regex or not attr:
                return

            self.regexp = regex.replace(" ", "").split(",")
            self.attr_name = attr.replace(" ", "").split(",")

            bots_params = dict(zip(self.regexp, self.attr_name))
            limit = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()

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

                                news_attribute = {
                                    "key": key,
                                    "value": value,
                                    "binary_mime_type": binary_mime_type,
                                    "binary_value": binary_value,
                                }

                                attributes.append(news_attribute)

                                self.core_api.update_news_item_attributes(
                                    news_item_id,
                                    attributes,
                                )

        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
