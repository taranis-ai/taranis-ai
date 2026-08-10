import hashlib
from typing import Any

from models.hrag import HragSchema

from worker.bot_api import BotApi
from worker.config import Config
from worker.log import logger

from .base_bot import BaseBot


class HragBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "HRAG_BOT"
        self.name = "HRAG Bot"
        self.description = "Bot for maintaining HRAG embeddings and graph evidence"

    def execute(self, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        parameters = parameters or {}
        stories = self.get_stories(parameters)
        if not stories:
            logger.info("HRAG found no eligible stories to index")
            return {"message": "No new stories found", "indexed": 0}
        schema_payload = self.core_api.get_hrag_schema()
        schema = HragSchema.model_validate(schema_payload)
        client = BotApi(
            bot_endpoint=str(parameters.get("BOT_ENDPOINT") or "").rstrip("/"),
            bot_api_key=parameters.get("BOT_API_KEY") or Config.BOT_API_KEY,
            requests_timeout=parameters.get("REQUESTS_TIMEOUT"),
        )
        logger.info(f"HRAG indexing {sum(len(story.get('news_items', [])) for story in stories)} news items via {client.api_url}")
        indexed = 0
        errors: list[dict[str, str]] = []
        for story in stories:
            story_failed = False
            for news_item in story.get("news_items", []):
                try:
                    self._index_news_item(client, schema, news_item)
                    indexed += 1
                except Exception as exc:
                    story_failed = True
                    logger.error(f"Failed to index HRAG news item {news_item.get('id')}: {exc}")
                    errors.append({"news_item_id": str(news_item.get("id") or ""), "error": str(exc)})
            if not story_failed and not self.core_api.update_story_attributes(story.get("id", ""), [{"key": self.type, "value": 1}]):
                logger.error(f"Failed to mark story {story.get('id')} as indexed by HRAG")
        return {"message": f"Indexed {indexed} news items for HRAG", "indexed": indexed, "errors": errors}

    def _index_news_item(self, client: BotApi, schema: HragSchema, news_item: dict[str, Any]) -> None:
        news_item_id = str(news_item.get("id") or "")
        text = self._render_text(news_item)
        if not news_item_id or not text:
            raise ValueError("News item id and content are required")
        embedding_response = client.api_post("/embed", {"text": text})
        extraction_response = client.api_post("/entity-relation-extraction", {"text": text, "schema": schema.entity_relationship_payload()})
        if not isinstance(embedding_response, dict) or not isinstance(embedding_response.get("embedding"), list):
            raise RuntimeError("LLM bot returned no embedding")
        if not isinstance(extraction_response, dict):
            raise RuntimeError("LLM bot returned no entity-relation extraction")
        payload = {
            "news_item_id": news_item_id,
            "content_hash": hashlib.sha256(text.encode()).hexdigest(),
            "embedding": embedding_response["embedding"],
            "entities": extraction_response.get("entities", []),
            "relations": extraction_response.get("relations", []),
        }
        if self.core_api.index_hrag_document(payload) is None:
            raise RuntimeError("Core rejected HRAG index update")

    @staticmethod
    def _render_text(news_item: dict[str, Any]) -> str:
        return "\n\n".join(str(value).strip() for value in (news_item.get("title"), news_item.get("content")) if value).strip()
