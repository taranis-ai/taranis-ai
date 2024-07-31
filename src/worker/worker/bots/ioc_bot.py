from .base_bot import BaseBot
from worker.log import logger
from ioc_finder import find_iocs
import ioc_fanger


class IOCBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "IOC_BOT"
        self.name = "IOC Bot"
        self.description = "Bot for finding indicators of compromise in news items"
        self.included_ioc_types = [
            "bitcoin_addresses",
            "cves",
            "md5s",
            "sha1s",
            "sha256s",
            "sha512s",
            "ssdeeps",
            "registry_key_paths",
            "ipv4_cidrs",
        ]

    def execute(self, parameters: dict | None = None):
        if not parameters:
            parameters = {}
        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        extracted_keywords = {}

        for i, story in enumerate(data):
            if i % max(len(data) // 10, 1) == 0:
                logger.debug(f"Extracting IOCs from {story['id']}: {i}/{len(data)}")
            story_content = " ".join(news_item["content"] for news_item in story["news_items"])
            if iocs := self.extract_ioc(story_content):
                extracted_keywords[story["id"]] = iocs

        self.core_api.update_tags(extracted_keywords, self.type)
        return {"message": f"Extracted {len(extracted_keywords)} IOCs"}

    def extract_ioc(self, text: str):
        ioc_data = find_iocs(text=text, included_ioc_types=self.included_ioc_types)
        result = {}
        for key, iocs in ioc_data.items():
            for ioc in iocs:
                result[ioc_fanger.fang(str(ioc))] = key

        return result
