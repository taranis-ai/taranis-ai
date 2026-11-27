"""Source-scoped URL identity and non-destructive collection updates."""

import hashlib
import json
from datetime import datetime
from typing import Literal

from models.assess import CollectedNewsItem
from models.assess import NewsItem as AssessNewsItem
from models.news_image import MAX_IMAGE_COUNT, CapturedImage
from PIL import Image
from pydantic import ValidationError

from core.log import logger
from core.managers.db_manager import db
from core.model.news_item import NewsItem
from core.model.news_item_image import NewsItemImage
from core.model.osint_source import OSINTSource
from core.model.story import Story
from core.service.misp_auto_update import refresh_misp_auto_update_jobs


class CollectionService:
    @staticmethod
    def ingest(data: list[dict]) -> tuple[dict, int]:
        # Validate the batch before committing any items. Invalid input is not "unchanged".
        try:
            payloads = [CollectedNewsItem.from_input(item) for item in data]
        except ValidationError as exc:
            return AssessNewsItem.validation_error_response(exc, prefix="Invalid news item data"), 400

        counts = dict.fromkeys(("created", "updated", "grouped", "unchanged", "stale"), 0)
        story_ids: list[str] = []
        item_ids: list[str] = []
        error = {}
        status = 200
        skipped_images = 0
        try:
            for payload in payloads:
                images: dict[str, NewsItemImage] = {}
                for capture in payload.captured_images:
                    try:
                        image = NewsItemImage.from_capture(CapturedImage.model_validate(capture))
                    except (ValueError, OSError, EOFError, SyntaxError, IndexError, Image.DecompressionBombError):
                        skipped_images += 1
                        continue
                    stored = images.setdefault(image.digest, image)
                    stored.description = stored.description or image.description
                result, status = CollectionService.ingest_item(payload, list(images.values()))
                if status >= 300:
                    db.session.rollback()
                    error = result
                    break
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
            error = {"error": "Failed to ingest collected news items"}
            status = 500

        message = (
            f"{counts['created']} created, {counts['updated']} updated, {counts['grouped']} grouped, "
            f"{counts['unchanged']} unchanged, {counts['stale']} stale"
            if item_ids
            else "All news items were skipped"
        )
        return {
            **(error or {"message": message}),
            **({"skipped_images": skipped_images} if skipped_images else {}),
            "counts": counts,
            "story_ids": list(dict.fromkeys(story_ids)),
            "news_item_ids": list(dict.fromkeys(item_ids)),
        }, status

    @classmethod
    def ingest_item(cls, payload: CollectedNewsItem, images: list[NewsItemImage]) -> tuple[dict, int]:
        """Resolve collection identity while holding the source lock until the caller commits."""
        source = db.session.execute(
            db.select(OSINTSource).where(OSINTSource.id == payload.osint_source_id).with_for_update()
        ).scalar_one_or_none()
        if source is None:
            return {"error": "OSINT source not found"}, 400
        if source.key == "manual":
            result, status = Story.add_from_news_item(payload, captured_images=images)
            if status == 409:
                return {"action": "unchanged"}, 200
            return {**result, "action": "created"}, status

        now = NewsItem.utcnow()
        payload.published = payload.published or now
        collection_hash = cls._collection_hash(payload)
        if item := cls._find_existing_item(payload, collection_hash):
            return cls._update_item(item, payload, now, images)
        return cls._create_item(payload, collection_hash, images)

    @staticmethod
    def _collection_hash(payload: AssessNewsItem) -> str:
        identity = [payload.osint_source_id, payload.link] if payload.link else [payload.osint_source_id, payload.title, payload.content]
        return hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()

    @classmethod
    def known_images(cls, payload: AssessNewsItem) -> dict[str, str]:
        source = db.session.get(OSINTSource, payload.osint_source_id)
        if source is None:
            return {}
        if source.key == "manual":
            item = NewsItem.get_by_payload_identity(payload)
        else:
            item = cls._find_existing_item(payload, cls._collection_hash(payload))
        if item is None or item.osint_source_id != source.id:
            return {}
        return {image.source_url: image.id for image in item.images}

    @staticmethod
    def _find_existing_item(payload: AssessNewsItem, collection_hash: str) -> NewsItem | None:
        item = NewsItem.get_by_hash(collection_hash)
        if item is not None or not payload.link:
            return item
        return db.session.execute(
            db.select(NewsItem)
            .where(NewsItem.osint_source_id == payload.osint_source_id, NewsItem.link == payload.link)
            .order_by(NewsItem.collected.desc(), NewsItem.id.desc())
            .limit(1)
        ).scalar_one_or_none()

    @classmethod
    def _update_item(cls, item: NewsItem, payload: CollectedNewsItem, now: datetime, images: list[NewsItemImage]) -> tuple[dict, int]:
        published = payload.published or now
        if item.published and published < item.published:
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
        story = None
        has_image_input = "captured_images" in payload.model_fields_set or bool(payload.known_image_descriptions)
        if changed or has_image_input:
            story = db.session.execute(db.select(Story).where(Story.id == item.story_id).with_for_update()).scalar_one_or_none()
        new_images = []
        descriptions = {}
        evict_count = 0
        if has_image_input:
            existing = {image.digest: image for image in item.images}
            for image in item.images:
                if image.description is None and (alt := payload.known_image_descriptions.get(image.id)):
                    descriptions[image] = alt
            for image in images:
                stored = existing.get(image.digest)
                if stored is None:
                    new_images.append(image)
                elif stored.description is None and image.description:
                    descriptions[stored] = image.description
            evict_count = max(0, len(item.images) + len(new_images) - MAX_IMAGE_COUNT)

        if not changed and not new_images and not descriptions and not evict_count:
            if published != item.published:
                db.session.execute(db.update(NewsItem).where(NewsItem.id == item.id).values(published=published, updated=item.updated))
            return {"action": "unchanged"}, 200

        if story is None or any(attribute.key == "rt_id" for attribute in story.attributes):
            return {"error": "Collected article belongs to a story that cannot be updated"}, 409
        # Preserve the actual pre-change state, including items moved into this story.
        story.record_revision(note="before_collection_update")
        if evict_count:
            del item.images[:evict_count]
        if new_images:
            item.images.extend(new_images)
        for stored, description in descriptions.items():
            stored.description = description
        for field, value in incoming.items():
            setattr(item, field, value)
        item.fuzzy_hash = NewsItem.get_fuzzy_hash(item.content)
        item.published = published
        item.updated = now
        return cls._record_change(item, story, "updated", images_only=not changed)

    @classmethod
    def _create_item(cls, payload: AssessNewsItem, collection_hash: str, images: list[NewsItemImage]) -> tuple[dict, int]:
        match = NewsItem.find_collection_match(payload)
        story = None
        if match:
            story = db.session.execute(db.select(Story).where(Story.id == match[1]).with_for_update()).scalar_one_or_none()
            if story and any(attribute.key == "rt_id" for attribute in story.attributes):
                story = None

        order = [entry.id for entry in story.ordered_news_items] if story else []
        item = NewsItem.from_payload(payload)
        item.images.extend(images)
        item.hash = collection_hash
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
        return cls._record_change(item, story, action)

    @staticmethod
    def _record_change(
        item: NewsItem, story: Story, action: Literal["created", "updated", "grouped"], *, images_only: bool = False
    ) -> tuple[dict, int]:
        actor = Story.last_change_for_source(item.osint_source)
        item.last_change = actor or "external"
        if images_only:
            story.remove_attributes(["IMAGE2TEXT_BOT"])
        else:
            story.read = False
            story.clear_bot_execution_attributes()
        db.session.flush()
        Story.refresh_tag_summaries_for_news_items([item])
        story.update_status(change=actor)
        story.record_revision(note=f"collection_{action}")
        return {"action": action, "story_id": story.id, "news_item_ids": [item.id]}, 200
