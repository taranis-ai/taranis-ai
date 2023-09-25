from worker.log import logger
from worker.core_api import CoreApi
from urllib.parse import parse_qs
import datetime


class BaseBot:
    type = "BASE_BOT"
    name = "Base Bot"
    description = "Base abstract type for all bots"

    def __init__(self):
        self.core_api = CoreApi()

    def execute(self):
        pass

    def get_filter_dict(self, parameters) -> dict:
        filter_dict = {}
        if item_filter := parameters.pop("ITEM_FILTER", None):
            filter_dict = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(item_filter).items()}

        filter_dict |= {k.lower(): v for k, v in parameters.items()}
        if "timestamp" not in filter_dict:
            limit = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
            filter_dict["timestamp"] = limit

        return filter_dict

    def update_filter_for_pagination(self, filter_dict, limit=100):
        filter_dict["limit"] = limit
        if "offset" in filter_dict:
            filter_dict["offset"] += limit
        else:
            filter_dict["offset"] = limit
        return filter_dict

    def get_stories(self, parameters) -> list:
        filter_dict = self.get_filter_dict(parameters)
        data = self.core_api.get_news_items_aggregate(filter_dict)
        if not data:
            logger.error("Error getting news items")
        return data

    def refresh(self):
        logger.info(f"Refreshing Bot: {self.type} ...")

        try:
            self.execute()
        except Exception:
            logger.log_debug_trace(f"Refresh Bots Failed: {self.type}")
