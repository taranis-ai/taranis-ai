import re

from .base_bot import BaseBot


class TaggingBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "TAGGING_BOT"
        self.name = "Tagging Bot"
        self.description = "Bot for tagging news items based on regular expressions"

    def execute(self, parameters: dict | None = None):
        if not parameters:
            parameters = {}
        regexp = parameters.get("REGULAR_EXPRESSION")
        if not regexp:
            raise ValueError("TaggingBot requires REGULAR_EXPRESSION parameter")

        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        found_tags = {}
        for story in data:
            findings = set()
            existing_tags = story["tags"] or []
            for news_item in story["news_items"]:
                content = news_item["content"]
                title = news_item["title"]
                review = news_item["review"]

                analyzed_content = set((title + review + content).split())

                for element in analyzed_content:
                    if finding := re.search(f"({regexp})", element.strip(".,")):
                        if finding[1] not in existing_tags:
                            findings.add(finding[1])
            found_tags[story["id"]] = findings

        if not found_tags:
            return {"message": "No tags found"}

        self.core_api.update_tags(found_tags, self.type)
        return {"message": f"Extracted {len(found_tags)} tags"}
