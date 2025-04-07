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
        self.language = None
        self.model = None

    def execute(self, parameters: dict | None = None) -> dict:
        if not parameters:
            parameters = {}
        return {"message": "No action defined for this bot"}

    def get_filter_dict(self, parameters: dict) -> dict:
        filter_dict = {}
        if item_filter := parameters.pop("ITEM_FILTER", None):
            filter_dict = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(item_filter).items()}

        if param_filter := parameters.get("filter"):
            filter_dict |= {k.lower(): v for k, v in param_filter.items()}

        if "story_id" in filter_dict:
            return filter_dict

        if timefrom := parameters.get("timefrom"):
            filter_dict["timefrom"] = timefrom
        else:
            filter_dict["timefrom"] = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()

        filter_dict["worker"] = True
        filter_dict["exclude_attr"] = self.type

        return filter_dict

    def update_filter_for_pagination(self, filter_dict, limit=100):
        filter_dict["limit"] = limit
        if "offset" in filter_dict:
            filter_dict["offset"] += limit
        else:
            filter_dict["offset"] = limit
        return filter_dict

    def get_stories(self, parameters: dict) -> list:
        filter_dict = self.get_filter_dict(parameters)
        data = self.core_api.get_stories(filter_dict)
        if data is None:
            logger.debug(f"No Stories for filter: {filter_dict}")
            return []
        return data

    def refresh(self):
        logger.info(f"Refreshing Bot: {self.type} ...")
        self.execute()
