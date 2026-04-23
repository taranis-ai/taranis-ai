import re

from worker.log import logger

from .base_bot import BaseBot


class TaggingBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "TAGGING_BOT"
        self.name = "Tagging Bot"
        self.description = "Bot for tagging news items based on regular expressions"

    def execute(self, parameters: dict | None = None) -> dict[str, dict[str, str] | str]:
        if not parameters:
            parameters = {}
        regexp = parameters.get("REGULAR_EXPRESSION")
        if not regexp:
            raise ValueError("TaggingBot requires REGULAR_EXPRESSION parameter")

        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        found_tags = {}
        for story in data:
            for news_item in story["news_items"]:
                findings = set()
                existing_tags = self._tag_names(news_item.get("tags") or {})
                content = news_item["content"]
                title = news_item["title"]
                review = news_item["review"]

                analyzed_content = set((title + review + content).split())

                for element in analyzed_content:
                    if finding := re.search(f"({regexp})", element.strip(".,")):
                        if finding[1] not in existing_tags:
                            findings.add(finding[1])
                found_tags[news_item["id"]] = sorted(findings)

        logger.info({"message": f"Extracted {len(found_tags)} tags"})
        return found_tags

    @staticmethod
    def _tag_names(tags) -> set[str]:
        if isinstance(tags, dict):
            return set(tags)
        if isinstance(tags, list):
            return {tag["name"] for tag in tags if isinstance(tag, dict) and isinstance(tag.get("name"), str)}
        return set()
