from .base_bot import BaseBot
from worker.log import logger
import datetime
from ioc_finder import find_iocs
import ioc_fanger


class IOCBot(BaseBot):
    type = "IOC_BOT"
    name = "IOC Bot"
    description = "Bot for finding indicators of compromise in news items"

    def __init__(self):
        super().__init__()

    def execute(self, parameters=None):
        if not parameters:
            return
        try:
            source_group = parameters.get("SOURCE_GROUP")
            source = parameters.get("SOURCE")

            limit = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
            filter_dict = {"timestamp": limit}
            if source_group:
                filter_dict["source_group"] = source_group
            if source:
                filter_dict["source"] = source

            data = self.core_api.get_news_items_aggregate(filter_dict)
            if not data:
                logger.critical("Error getting news items")
                return

            for aggregate in data:
                aggregate_content = "".join(news_item["news_item_data"]["content"] for news_item in aggregate["news_items"])
                current_keywords = self.extract_ioc(aggregate_content)
                self.core_api.update_news_item_tags(aggregate["id"], current_keywords)

        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def extract_ioc(self, text: str):
        iocs = find_iocs(text)
        result = {}
        extract_keys = [
            "bitcoin_addresses",
            "cves",
            "domains",
            "email_addresses",
            "file_paths",
            "ipv4s",
            "ipv6s",
            "md5s",
            "sha1s",
            "sha256s",
            "sha512s",
            "ssdeeps",
            "registry_key_paths",
            "tlp_labels",
        ]
        for key in extract_keys:
            if key in iocs:
                for ioc in iocs[key]:
                    result[ioc_fanger.fang(str(ioc))] = {"tag_type": key}
        logger.debug(result)
        return result
