"""Source-scoped URL identity and non-destructive collection updates."""

import hashlib
import json
from datetime import timedelta

from models.assess import NewsItem as AssessNewsItem
from pydantic import ValidationError

from core.log import logger
from core.managers.db_manager import db
from core.model.news_item import NewsItem
from core.model.osint_source import OSINTSource
from core.model.story import Story
from core.service.misp_auto_update import refresh_misp_auto_update_jobs


class CollectionService:
    @staticmethod
    def ingest(data: list[dict]) -> tuple[dict, int]:
        # Validate the batch before committing any items. Invalid input is not "unchanged".
        try:
            payloads = [AssessNewsItem.from_input(item) for item in data]
        except ValidationError as exc:
            return AssessNewsItem.validation_error_response(exc, prefix="Invalid news item data"), 400

        counts = dict.fromkeys(("created", "updated", "grouped", "unchanged", "stale"), 0)
        story_ids: list[str] = []
        item_ids: list[str] = []
        try:
            for payload in payloads:
                result, status = CollectionService.ingest_item(payload)
                if status >= 300:
                    db.session.rollback()
                    return result, status
                db.session.commit()
                action = result["action"]
                counts[action] += 1
                if action in ("created", "updated", "grouped"):
                    story_ids.append(result["story_id"])
                    item_ids.extend(result["news_item_ids"])
                    refresh_misp_auto_update_jobs([result["story_id"]])
        except Exception:
            db.session.rollback()
            logger.exception("Failed to ingest collected news items")
            return {"error": "Failed to ingest collected news items"}, 500

        message = (
            f"{counts['created']} created, {counts['updated']} updated, {counts['grouped']} grouped, "
            f"{counts['unchanged']} unchanged, {counts['stale']} stale"
            if item_ids
            else "All news items were skipped"
        )
        return {
            "message": message,
            "counts": counts,
            "story_ids": list(dict.fromkeys(story_ids)),
            "news_item_ids": list(dict.fromkeys(item_ids)),
        }, 200

    @staticmethod
    def ingest_item(payload: AssessNewsItem) -> tuple[dict, int]:
        source = db.session.execute(
            db.select(OSINTSource).where(OSINTSource.id == payload.osint_source_id).with_for_update()
        ).scalar_one_or_none()
        if source is None:
            return {"error": "OSINT source not found"}, 400
        if source.key == "manual":
            result, status = Story.add_from_news_item(payload)
            if status == 409:
                return {"action": "unchanged"}, 200
            return {**result, "action": "created"}, status

        now = NewsItem.utcnow()
        observed = payload.collected or now
        if observed > now + timedelta(minutes=5):
            return {"error": "Collection timestamp is in the future"}, 400
        # Keep the legacy title/URL hash contract outside this ingestion boundary.
        identity = [source.id, payload.link] if payload.link else [source.id, payload.title, payload.content]
        collection_hash = hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()
        item = NewsItem.get_by_hash(collection_hash)
        if item is None and payload.link:
            item = db.session.execute(
                db.select(NewsItem)
                .where(NewsItem.osint_source_id == source.id, NewsItem.link == payload.link)
                .order_by(NewsItem.collected.desc(), NewsItem.id.desc())
                .limit(1)
            ).scalar_one_or_none()

        if item:
            if item.collection_seen_at and observed <= item.collection_seen_at:
                return {"action": "stale"}, 200
            if not payload.content and item.content:
                return {"error": "Collected article content is empty; existing content was preserved"}, 400
            incoming = {
                "content": payload.content or "",
                "title": payload.title or item.title,
                "author": payload.author or item.author,
                "language": payload.language or item.language,
            }
            changed = any(
                NewsItem.normalized_content(getattr(item, field)) != NewsItem.normalized_content(value) for field, value in incoming.items()
            )
            if not changed:
                db.session.execute(
                    db.update(NewsItem).where(NewsItem.id == item.id).values(collection_seen_at=observed, updated=item.updated)
                )
                return {"action": "unchanged"}, 200
            story = db.session.execute(db.select(Story).where(Story.id == item.story_id).with_for_update()).scalar_one_or_none()
            if story is None or any(attribute.key == "rt_id" for attribute in story.attributes):
                return {"error": "Collected article belongs to a story that cannot be updated"}, 409
            # Preserve the actual pre-change state, including items moved into this story.
            story.record_revision(note="before_collection_update")
            for field, value in incoming.items():
                setattr(item, field, value)
            item.fuzzy_hash = NewsItem.get_fuzzy_hash(item.content)
            item.collection_seen_at = observed
            item.updated = now
            # The story title and all analyst-owned fields remain untouched.
            action = "updated"
        else:
            match = NewsItem.find_collection_match(payload)
            story = None
            if match:
                story = db.session.execute(db.select(Story).where(Story.id == match[1]).with_for_update()).scalar_one_or_none()
                if story and any(attribute.key == "rt_id" for attribute in story.attributes):
                    story = None
            order = [entry.id for entry in story.ordered_news_items] if story else []
            item = NewsItem.from_payload(payload)
            item.hash = collection_hash
            item.collection_seen_at = observed
            if story:
                story.news_items.append(item)
                db.session.flush()
                story.news_item_order = [*order, item.id]
                action = "grouped"
            else:
                story = Story(title=payload.title or "", news_items=[])
                story.news_items.append(item)
                db.session.add(story)
                action = "created"

        actor = Story.last_change_for_source(source)
        item.last_change = actor or "external"
        story.read = False
        story.collection_updated_at = now
        db.session.flush()
        Story.refresh_tag_summaries_for_news_items([item])
        story.update_status(change=actor)
        story.record_revision(note=f"collection_{action}")
        return {"action": action, "story_id": story.id, "news_item_ids": [item.id]}, 200
