from llm_bot.schemas import SummarizeRequest, TitleRequest
from llm_bot.tasks.summarize import summarize
from llm_bot.tasks.title import generate_title

from worker.bot_api import BotServiceUnavailableError
from worker.llm import get_llm_client, run_llm_task
from worker.log import logger

from .base_bot import BaseBot


class SummaryBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "SUMMARY_BOT"
        self.name = "Summary generation Bot"

    def execute(self, parameters: dict | None = None) -> dict[str, dict[str, str] | str]:
        if not parameters:
            parameters = {}

        if not (data := self.get_stories(parameters)):
            return {"message": "No new stories found"}

        client = get_llm_client(self.core_api, "summarization", parameters)

        for story in data:
            news_items = story.get("news_items", [])
            story_payload = {"news_items": [{"title": item.get("title", ""), "content": item.get("content", "")} for item in news_items]}

            logger.debug(f"Summarizing {story['id']} with {len(news_items)} news items")
            try:
                summary = run_llm_task(summarize(SummarizeRequest.model_validate(story_payload), client=client)).summary
                title = (
                    run_llm_task(generate_title(TitleRequest.model_validate(story_payload), client=client)).title
                    if len(news_items) > 1
                    else ""
                )

                story_update_data = {}
                if summary:
                    story_update_data["summary"] = summary
                if title:
                    story_update_data["title"] = title

                if story_update_data:
                    if self.core_api.update_story(story["id"], story_update_data):
                        self.core_api.update_story_attributes(
                            story["id"],
                            [{"key": self.type, "value": 1}],
                        )
                    else:
                        logger.warning(f"Failed to update story {story['id']}, skipping attribute update")
            except BotServiceUnavailableError:
                raise
            except Exception:
                logger.exception(f"Could not generate summary for {story['id']}")
                continue

            logger.debug(f"Created summary for : {story['id']}")
        return {"message": f"Summarized {len(data)} stories"}
