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
            regexp = self.parameters["REGULAR_EXPRESSION"]

            limit = self.history()

            data = self.core_api.get_news_items_aggregate(source_group, limit)
            if not data:
                return
            for aggregate in data:

                findings = []

                for news_item in aggregate["news_items"]:

                    content = news_item["news_item_data"]["content"]

                    analyzed_content = "".join(content).split()
                    analyzed_content = [item.replace(".", "") if item.endswith(".") else item for item in analyzed_content]
                    analyzed_content = [item.replace(",", "") if item.endswith(",") else item for item in analyzed_content]

                    analyzed_content = set(analyzed_content)

                    for element in analyzed_content:

                        finding = re.search("(" + regexp + ")", element)

                        if finding:
                            finding = [news_item["id"], finding.group(1)]
                            findings.append(finding)

                # NEXT PART OF CODE IS FOR FINDINGS IN ONE AGGREGATE
                # IT WILL GROUP NEWS_ITEMS TOGETHER FROM ONE AGGREGATE

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

        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def execute_on_event(self, event_type, data):
        try:
            source_group = self.parameters["SOURCE_GROUP"]
            regexp = self.parameters["REGULAR_EXPRESSION"]
            logger.log_debug(source_group + regexp)

        except Exception as error:
            logger.log_debug_trace(f"Error running Bot: {self.type}")
