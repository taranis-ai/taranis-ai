from worker.log import logger
from worker.core_api import CoreApi
from urllib.parse import parse_qs
import datetime


class BaseBot:
    def __init__(self):
        self.core_api = CoreApi()
        self.type = "BASE_BOT"
        self.name = "Base Bot"
        self.description = "Base abstract type for all bots"

    def execute(self):
        pass

    def get_filter_dict(self, parameters) -> dict:
        filter_dict = {}
        if item_filter := parameters.pop("ITEM_FILTER", None):
            filter_dict = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(item_filter).items()}

        if param_filter := parameters.get("filter"):
            filter_dict |= {k.lower(): v for k, v in param_filter.items()}

        if "story_id" in filter_dict:
            return filter_dict

        if "timefrom" not in filter_dict:
            limit = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
            filter_dict["timefrom"] = limit

        filter_dict["no_count"] = True
        filter_dict["exclude_attr"] = self.type

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
        data = self.core_api.get_stories(filter_dict)
        if not data:
            logger.debug(f"No Stories for filter: {filter_dict}")
        return data

    def refresh(self):
        logger.info(f"Refreshing Bot: {self.type} ...")
        self.execute()
