from llm_bot.schemas import NerRequest
from llm_bot.tasks.ner import prepare_ner
from rq import Retry

from worker.llm import get_llm_client, run_llm_tasks

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
                items.append(news_item["id"])
                tasks.append(prepare_ner(NerRequest(text=news_item_content, cybersecurity=is_cybersecurity)))

        results = run_llm_tasks(tasks, self.llm_client, parameters)
        if isinstance(results, Retry):
            return results
        return {item_id: result.root for item_id, result in zip(items, results, strict=True)}
