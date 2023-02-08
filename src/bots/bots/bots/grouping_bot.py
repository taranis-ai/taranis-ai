import json
import re

from .base_bot import BaseBot
from bots.managers.log_manager import logger


class GroupingBot(BaseBot):
    type = "GROUPING_BOT"
    name = "Grouping Bot"
    description = "Bot for grouping news items into aggregates"

    def execute(self):
        try:
            source_group = self.parameters.get("SOURCE_GROUP", None)
            regexp = self.parameters.get("REGULAR_EXPRESSION", None)

            if not source_group or not regexp:
                return

            data = self.core_api.get_news_items_aggregate(source_group, self.history())
            if not data:
                return

            for aggregate in data:

                findings = []

                for news_item in aggregate["news_items"]:
                    content = news_item["news_item_data"]["content"]
                    title = news_item["news_item_data"]["title"]
                    review = news_item["news_item_data"]["review"]

                    analyzed_content = set((title + review + content).split())

                    for element in analyzed_content:
                        if finding := re.search(f"({regexp})", element.strip(".,")):
                            finding = [news_item["id"], finding[1]]
                            findings.append(finding)

                if findings:

                    grouped_ids = []
                    values = {}

                    for k, val in findings:
                        if val in values:
                            grouped = [x for x in grouped_ids if len(x) != 1]
                            x_flat = [k for sublist in grouped for k in sublist]

                            if str(k) not in x_flat:
                                grouped_ids[values[val]].extend(str(k))
                        else:
                            grouped_ids.append([str(k)])
                            values[val] = len(values)

                    grouped_ids = [x for x in grouped_ids if len(x) != 1]

                    marker_set = set()
                    corrected_grouped_ids = []

                    for sublist in grouped_ids:
                        for element in sublist:
                            if element not in marker_set:
                                marker_set.add(element)
                            else:
                                break
                        else:
                            corrected_grouped_ids.append(sublist)

                    for sublist in corrected_grouped_ids:

                        items = []

                        for element in sublist:
                            item = {"type": "ITEM", "id": int(element)}
                            items.append(item)

                        data = {"action": "GROUP", "items": items}
                        self.core_api.news_items_grouping(data)

        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def execute_on_event(self, event_type, data):
        try:
            source_group = self.parameters["SOURCE_GROUP"]
            regexp = self.parameters["REGULAR_EXPRESSION"]
            logger.log_debug(source_group + regexp)

        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
