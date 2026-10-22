import json

from llm_bot.schemas import ClassifyRequest
from llm_bot.tasks.classify import prepare_classify
from models.classification import story_classification

from worker.llm import get_decisions_client, run_decisions_tasks

from .base_bot import BaseBot


class CyberSecClassifierBot(BaseBot):
    def __init__(self):
        super().__init__()
        # Keep the persisted worker type so existing schedules and dependencies still resolve.
        self.type = "CYBERSEC_CLASSIFIER_BOT"
        self.name = "Topic classification bot"

    def execute(self, parameters: dict | None = None) -> dict:
        parameters = parameters or {}
        if not (stories := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        client = get_decisions_client(parameters)
        items = [item for story in stories for item in story.get("news_items", []) if item.get("content", "").strip()]
        tasks = [prepare_classify(ClassifyRequest(text=item["content"])) for item in items]
        results = run_decisions_tasks(tasks, client, parameters)
        categories = {}
        item_attributes = {
            item["id"]: [{"key": "classification", "value": "none"}, {"key": "classification_scores", "value": "{}"}]
            for story in stories
            for item in story.get("news_items", [])
            if not item.get("content", "").strip()
        }
        for item, result in zip(items, results, strict=True):
            scores = result.model_dump()
            category = max(scores, key=lambda category: scores[category])
            categories[item["id"]] = category
            item_attributes[item["id"]] = [
                {"key": "classification", "value": category},
                {"key": "classification_scores", "value": json.dumps(scores)},
            ]
        return {
            "message": f"Classified {len(items)} news items",
            "changes": {
                "item_attributes": item_attributes,
                "story_attributes": {
                    story["id"]: [
                        {
                            "key": "classification",
                            "value": story_classification(categories.get(item["id"], "none") for item in story.get("news_items", [])),
                        }
                    ]
                    for story in stories
                },
            },
        }
