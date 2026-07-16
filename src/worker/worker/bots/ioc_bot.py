# pyright: reportMissingTypeStubs=false

from typing import Any

import ioc_fanger
from ioc_finder import find_iocs
from models.cti import IOC_FINDER_TYPES

from worker.log import logger

from .base_bot import BaseBot
from .tagging_content import _news_item_content_for_tagging


class IOCBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "IOC_BOT"
        self.name = "IOC Bot"
        self.description = "Bot for finding indicators of compromise in news items"
        self.included_ioc_types = list(
            dict.fromkeys(
                IOC_FINDER_TYPES
                + [
                    "bitcoin_addresses",
                    "ssdeeps",
                    "registry_key_paths",
                ]
            )
        )

    def execute(self, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        if not parameters:
            parameters = {}
        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        extracted_keywords: dict[str, dict[str, str]] = {}

        for i, story in enumerate(data):
            if i % max(len(data) // 10, 1) == 0:
                logger.debug(f"Extracting IOCs from {story['id']}: {i}/{len(data)}")
            for news_item in story["news_items"]:
                news_item_content = _news_item_content_for_tagging(news_item)
                iocs = self.extract_ioc(news_item_content)
                extracted_keywords[news_item["id"]] = iocs
        logger.info({"message": f"Extracted {len(extracted_keywords)} IOCs"})
        return extracted_keywords

    def extract_ioc(self, text: str) -> dict[str, str]:
        ioc_data = find_iocs(text=text, included_ioc_types=self.included_ioc_types)
        result = {}
        for key, iocs in ioc_data.items():
            for ioc in iocs:
                result[ioc_fanger.fang(str(ioc))] = key

        return result
