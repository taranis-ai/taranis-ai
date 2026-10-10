from llm_bot.schemas import SummarizeRequest, TitleRequest
from llm_bot.tasks.summarize import prepare_summary
from llm_bot.tasks.title import prepare_title
from rq import Retry

from worker.bot_api import BotServiceUnavailableError
from worker.llm import get_llm_client, run_llm_tasks
from worker.log import logger

from .base_bot import BaseBot


class SummaryBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "SUMMARY_BOT"
        self.name = "Summary generation Bot"

    def execute(self, parameters: dict | None = None) -> dict | Retry:
        if not parameters:
            parameters = {}

        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        client = get_llm_client(parameters)
        tasks = []
        for story in data:
            news_items = story.get("news_items", [])
            story_payload = {"news_items": [{"title": item.get("title", ""), "content": item.get("content", "")} for item in news_items]}
            tasks.append(prepare_summary(SummarizeRequest.model_validate(story_payload)))
            if len(news_items) > 1:
                tasks.append(prepare_title(TitleRequest.model_validate(story_payload)))
        results = run_llm_tasks(tasks, client, parameters)
        if isinstance(results, Retry):
            return results
        results = iter(results)

        story_updates = {}
        for story in data:
            news_items = story.get("news_items", [])
            logger.debug(f"Summarizing {story['id']} with {len(news_items)} news items")
            try:
                summary = next(results).summary
                title = next(results).title if len(news_items) > 1 else ""

                story_update_data = {}
                if summary:
                    story_update_data["summary"] = summary
                if title:
                    story_update_data["title"] = title

                if story_update_data:
                    story_updates[story["id"]] = story_update_data
            except BotServiceUnavailableError:
                raise
            except Exception:
                logger.exception(f"Could not generate summary for {story['id']}")
                raise RuntimeError("Story summarization failed") from None

            logger.debug(f"Created summary for : {story['id']}")
        return {
            "message": f"Summarized {len(data)} stories",
            "changes": {"story_updates": story_updates},
        }
