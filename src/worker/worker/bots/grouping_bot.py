import re
from .base_bot import BaseBot
from worker.log import logger
from collections import defaultdict


class GroupingBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "GROUPING_BOT"
        self.name = "Grouping Bot"
        self.description = "Bot for grouping news items into stories"
        self.default_regex = r"CVE-\d{4}-\d{4,7}"

    def execute(self, parameters: dict | None = None):
        if not parameters:
            parameters = {}
        regexp = parameters.get("REGULAR_EXPRESSION")
        if not regexp:
            raise ValueError("GroupingBot requires REGULAR_EXPRESSION parameter")

        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        findings = defaultdict(list)
        for story in data:
            for news_item in story["news_items"]:
                content = news_item["content"]
                title = news_item["title"]

                analyzed_content = set((title + content).split())
                for element in analyzed_content:
                    if finding := re.search(f"({regexp})", element.strip(".,")):
                        findings[finding[1]].append(story["id"])
                        break

        if not findings:
            return {"message": "No Groups found"}

        for group, ids in findings.items():
            if len(ids) > 1:
                logger.debug(f"Grouping: {group} with: {ids}")
                self.core_api.news_items_grouping(ids)

        return {"message": f"Grouped {len(findings)} groups"}
