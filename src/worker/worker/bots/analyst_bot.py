import re
import datetime

from .base_bot import BaseBot
from worker.log import logger


class AnalystBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "ANALYST_BOT"
        self.name = "Analyst Bot"
        self.description = "Bot for news items analysis"
        self.regexp = []
        self.attr_name = []

    def execute(self, parameters=None):
        regex = parameters.get("REGULAR_EXPRESSION", "")
        attr = parameters.get("ATTRIBUTE_NAME", "")
        if not regex or not attr:
            raise ValueError("AnalystBot requires REGULAR_EXPRESSION and ATTRIBUTE_NAME parameters")

        self.regexp = regex.replace(" ", "").split(",")
        self.attr_name = attr.replace(" ", "").split(",")

        bots_params = dict(zip(self.regexp, self.attr_name))
        limit = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()

        if not (data := self.core_api.get_news_items(limit)):
            logger.debug(f"No News Items for filter: {limit}")
            return None
        for item in data:
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

                        news_attribute = {
                            "key": key,
                            "value": value,
                        }

                        attributes.append(news_attribute)

                        self.core_api.update_news_item_attributes(
                            news_item_id,
                            attributes,
                        )
