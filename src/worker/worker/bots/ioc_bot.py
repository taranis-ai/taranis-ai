from .base_bot import BaseBot
from worker.log import logger
from ioc_finder import find_iocs
import ioc_fanger


class IOCBot(BaseBot):
    type = "IOC_BOT"
    name = "IOC Bot"
    description = "Bot for finding indicators of compromise in news items"
    included_ioc_types = ["bitcoin_addresses", "cves", "md5s", "sha1s", "sha256s", "sha512s", "ssdeeps", "registry_key_paths", "ipv4_cidrs"]

    def __init__(self):
        super().__init__()

    def execute(self, parameters=None):
        if not parameters:
            return
        try:
            if not (data := self.get_stories(parameters)):
                return "Error getting news items"

            extracted_keywords = {}

            for i, aggregate in enumerate(data):
                if attributes := aggregate.get("news_item_attributes", {}):
                    if self.type in [d["key"] for d in attributes if "key" in d]:
                        continue
                if i % max(len(data) // 10, 1) == 0:
                    logger.debug(f"Extracting IOCs from {aggregate['id']}: {i}/{len(data)}")
                aggregate_content = " ".join(news_item["news_item_data"]["content"] for news_item in aggregate["news_items"])
                if iocs := self.extract_ioc(aggregate_content):
                    extracted_keywords[aggregate["id"]] = iocs

            logger.debug(extracted_keywords)
            self.core_api.update_tags(extracted_keywords, self.type)

        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def extract_ioc(self, text: str):
        ioc_data = find_iocs(text=text, included_ioc_types=self.included_ioc_types)
        result = {}
        for key, iocs in ioc_data.items():
            for ioc in iocs:
                result[ioc_fanger.fang(str(ioc))] = {"tag_type": key}

        return result
