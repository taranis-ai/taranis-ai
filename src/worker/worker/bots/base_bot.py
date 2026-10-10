from urllib.parse import parse_qs

from rq import Retry

from worker.core_api import CoreApi
from worker.log import logger


class BaseBot:
    def __init__(self):
        self.core_api = CoreApi()
        self.type = "BASE_BOT"
        self.name = "Base Bot"
        self.description = "Base abstract type for all bots"
        self.language: str | None = None
        self.model: str | None = None

    def execute(self, parameters: dict | None = None) -> dict | Retry:
        if not parameters:
            parameters = {}
        return {"message": "No action defined for this bot"}

    def get_filter_dict(self, parameters: dict) -> dict:
        filter_dict = {}
        if item_filter := parameters.pop("ITEM_FILTER", None):
            filter_dict = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(item_filter).items()}

        if param_filter := parameters.get("filter"):
            filter_dict |= {k.lower(): v for k, v in param_filter.items()}

        skip_processed = filter_dict.pop("skip_processed", False)
        if "story_id" in filter_dict or "story_ids" in filter_dict:
            if not skip_processed:
                return filter_dict
            # Collection IDs define the scope even when updated articles have old publication dates.
            filter_dict = {k: v for k, v in filter_dict.items() if k in {"story_id", "story_ids", "source"}}

        if not skip_processed and (timefrom := parameters.get("timefrom")):
            filter_dict["timefrom"] = timefrom

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
        if hasattr(self, "pipeline_stories"):
            data = self.pipeline_stories
        elif "_stories" in parameters:
            data = parameters["_stories"]
        else:
            filter_dict = self.get_filter_dict(parameters)
            data = self.core_api.get_stories(filter_dict)
        if not data:
            logger.debug("No stories found")
            return []
        self.story_revisions = {story["id"]: story["revision"] for story in data if "revision" in story}
        return data

    def refresh(self):
        logger.info(f"Refreshing Bot: {self.type} ...")
        self.execute()
