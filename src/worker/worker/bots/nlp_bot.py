from llm_bot.schemas import NerRequest
from llm_bot.tasks.ner import extract_entities

from worker.llm import get_llm_client, run_llm_task

from .base_bot import BaseBot
from .tagging_content import _news_item_content_for_tagging


def batched(stories: list, batch_size=10):
    for i in range(0, len(stories), batch_size):
        yield stories[i : i + batch_size]


class NLPBot(BaseBot):
    def __init__(self, language="en"):
        super().__init__()
        self.type = "NLP_BOT"
        self.name = "NLP Bot"

    def execute(self, parameters: dict | None = None) -> dict[str, dict[str, str] | str]:
        update_result = {}

        if not parameters:
            parameters = {}
        if stories := self.get_stories(parameters):
            self.llm_client = get_llm_client(parameters)

            for story_batch in batched(stories):
                update_result |= self._process_stories(story_batch)
            return update_result
        return {"message": "No new stories found"}

    def _process_stories(self, stories: list) -> dict:
        update_result = {}

        for story in stories:
            if "attributes" in story and story.get("attributes", {}):
                is_cybersecurity = story["attributes"].get("cybersecurity", {}).get("value", "no") == "yes"
            else:
                is_cybersecurity = False
            for news_item in story["news_items"]:
                news_item_content = _news_item_content_for_tagging(news_item, separator="\n")
                current_keywords = self._extract_ner(news_item_content, is_cybersecurity)
                update_result[news_item["id"]] = current_keywords

        return update_result

    def _extract_ner(self, text: str, is_cybersecurity: bool = False) -> dict:
        request = NerRequest(text=text, cybersecurity=is_cybersecurity)
        return run_llm_task(extract_entities(request, client=self.llm_client)).root
