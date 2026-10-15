from llm_bot.schemas import NerRequest, NerResponse
from llm_bot.tasks.ner import prepare_ner
from niquests.exceptions import RequestException
from rq import Retry

from worker.llm import LLMTaskError, get_llm_client, run_llm_tasks
from worker.log import logger

from .base_bot import BaseBot
from .tagging_content import _news_item_content_for_tagging


class NLPBot(BaseBot):
    def __init__(self, language="en"):
        super().__init__()
        self.type = "NLP_BOT"
        self.name = "NLP Bot"

    def execute(self, parameters: dict | None = None) -> dict | Retry:
        if not parameters:
            parameters = {}
        if stories := self.get_stories(parameters):
            self.llm_client = get_llm_client(parameters)

            return self._process_stories(stories, parameters)
        return {"message": "No new stories found"}

    def _process_stories(self, stories: list, parameters: dict) -> dict | Retry:
        items = []
        tasks = []

        for story in stories:
            if "attributes" in story and story.get("attributes", {}):
                is_cybersecurity = story["attributes"].get("cybersecurity", {}).get("value", "no") == "yes"
            else:
                is_cybersecurity = False
            for news_item in story["news_items"]:
                news_item_content = _news_item_content_for_tagging(news_item, separator="\n")
                items.append((news_item["id"], news_item.get("story_id", story["id"])))
                tasks.append(prepare_ner(NerRequest(text=news_item_content, cybersecurity=is_cybersecurity)))

        def upload_tags(index: int, result: NerResponse) -> None:
            item_id, story_id = items[index]
            logger.info(f"Saving NER for news item {item_id} ({index + 1}/{len(items)})")
            if result.root:
                try:
                    response = self.core_api.api_put("/worker/tags?replace=false", {item_id: result.root})
                except RequestException:
                    logger.exception(f"Failed to upload NER tags for news item {item_id}")
                    response = None
                if not response or response.get("errors"):
                    raise LLMTaskError("Could not save extracted NER tags. Check Core connectivity and worker logs.", "ner_save_failed")
                if story_id in self.story_revisions:
                    # Each successful tag update records one story revision.
                    self.story_revisions[story_id] += 1

        results = run_llm_tasks(tasks, self.llm_client, parameters, on_result=upload_tags)
        if isinstance(results, Retry):
            return results
        return {item_id: result.root for (item_id, _), result in zip(items, results, strict=True)}
