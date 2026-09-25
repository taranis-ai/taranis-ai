"""Apply a bot run's staged changes and task result in one database transaction."""

from datetime import UTC, datetime
from typing import Any

from models.task import Task as TaskResponseModel
from models.task import TaskSubmission
from sqlalchemy.exc import IntegrityError

from core.log import logger
from core.managers.db_manager import db
from core.model.bot import Bot
from core.model.ioc import IOC
from core.model.news_item import NewsItem
from core.model.news_item_attribute import NewsItemAttribute
from core.model.story import Story
from core.model.task import Task
from core.service.misp_auto_update import refresh_misp_auto_update_jobs


TAGGING_BOTS = {"WORDLIST_BOT", "IOC_BOT", "NLP_BOT", "TAGGING_BOT"}
CHANGE_KEYS = {"groups", "item_attributes", "story_attributes", "story_updates"}


class InvalidBotRun(ValueError):
    pass


class StaleBotRun(ValueError):
    pass


class BotPipelineService:
    @staticmethod
    def _attributes(value: list) -> list[NewsItemAttribute]:
        try:
            return NewsItemAttribute.load_multiple(value)
        except (TypeError, ValueError) as exc:
            raise InvalidBotRun from exc

    @classmethod
    def submit(cls, submission: TaskSubmission) -> tuple[dict[str, Any], int, bool]:
        if submission.task != "bot_pipeline" and not (submission.task or "").startswith("bot_"):
            return {"error": "Invalid bot run"}, 400, False
        data = submission.result.data
        if not isinstance(data, dict) or not isinstance(data.get("bot_stages"), list):
            return {"error": "Invalid bot run"}, 400, False
        stages = data["bot_stages"]
        revisions = data.get("story_revisions")
        if (
            not stages
            or not isinstance(revisions, dict)
            or any(not isinstance(story_id, str) or type(revision) is not int or revision < 0 for story_id, revision in revisions.items())
        ):
            return {"error": "Invalid bot run"}, 400, False
        try:
            existing = Task.get_by_job_id(submission.id)
            if existing and existing.status == "SUCCESS":
                return TaskResponseModel.model_validate(existing.to_dict()).model_dump(mode="json", exclude_none=False), 200, False

            stories = {
                story.id: story for story in db.session.execute(db.select(Story).where(Story.id.in_(revisions)).with_for_update()).scalars()
            }
            if len(stories) != len(revisions) or any(stories[story_id].revision != revision for story_id, revision in revisions.items()):
                raise StaleBotRun
            allowed_items = {item.id for story in stories.values() for item in story.news_items}
            affected_story_ids: set[str] = set()
            for stage in stages:
                cls._apply_stage(stage, set(revisions), allowed_items, affected_story_ids)

            result_payload = submission.result.model_dump(mode="json", exclude_none=False)
            task_data: dict[str, Any] = {
                "id": submission.id,
                "task": submission.task,
                "user_id": submission.user_id,
                "worker_id": submission.worker_id,
                "worker_type": submission.worker_type,
                "result": result_payload,
                "status": submission.status,
            }
            result, _ = Task.add_or_update(task_data, commit=False)
            db.session.commit()
        except StaleBotRun:
            db.session.rollback()
            return {"error": "Stories changed during bot run. Retry the run."}, 409, False
        except InvalidBotRun:
            db.session.rollback()
            return {"error": "Invalid bot run"}, 400, False
        except IntegrityError:
            db.session.rollback()
            if (existing := Task.get_by_job_id(submission.id)) and existing.status == "SUCCESS":
                return TaskResponseModel.model_validate(existing.to_dict()).model_dump(mode="json", exclude_none=False), 200, False
            logger.exception("Failed to commit bot run %s", submission.id)
            return {"error": "Bot run could not be saved"}, 500, False
        except Exception:
            db.session.rollback()
            logger.exception("Failed to apply bot run %s", submission.id)
            return {"error": "Bot run could not be saved"}, 500, False

        if affected_story_ids:
            try:
                refresh_misp_auto_update_jobs(affected_story_ids)
            except Exception:
                logger.exception("Bot run committed but MISP refresh failed")
        return TaskResponseModel.model_validate(result).model_dump(mode="json", exclude_none=False), 200, True

    @classmethod
    def _apply_stage(cls, stage: Any, allowed_stories: set[str], allowed_items: set[str], affected_story_ids: set[str]) -> None:
        if not isinstance(stage, dict):
            raise InvalidBotRun
        bot_id, bot_type, result = stage.get("bot_id"), stage.get("bot_type"), stage.get("result")
        bot = Bot.get(bot_id) if isinstance(bot_id, str) else None
        if not bot or bot.type.name != bot_type or not isinstance(result, dict):
            raise InvalidBotRun
        changes = result.get("changes") or {}
        if not isinstance(changes, dict) or set(changes) - CHANGE_KEYS:
            raise InvalidBotRun

        if bot_type in TAGGING_BOTS:
            tag_counts: dict[str, int] = {}
            for item_id, tags in result.items():
                if item_id in {"message", "changes"}:
                    continue
                if item_id not in allowed_items or not isinstance(tags, (dict, list)):
                    raise InvalidBotRun
                if not tags:
                    continue
                item = NewsItem.get(item_id)
                if not item:
                    raise InvalidBotRun
                _, status = item.set_tags(tags, actor="bot", replace=False, commit=False)
                if status != 200:
                    raise InvalidBotRun
                if item.story_id:
                    tag_counts[item.story_id] = tag_counts.get(item.story_id, 0) + len(tags)
                    affected_story_ids.add(item.story_id)
            now = datetime.now(UTC).isoformat()
            for story_id, count in tag_counts.items():
                story = Story.get(story_id)
                if story:
                    story.upsert_attribute(NewsItemAttribute(bot_type, f"worker_id={bot_id}|count={count}|{now}"))
                    story.record_revision(note="set_worker_execution_attribute")

        item_attributes = changes.get("item_attributes", {})
        if not isinstance(item_attributes, dict):
            raise InvalidBotRun
        for item_id, attributes in item_attributes.items():
            if item_id not in allowed_items or not isinstance(attributes, list):
                raise InvalidBotRun
            item = NewsItem.get(item_id)
            if not item:
                raise InvalidBotRun
            for attribute in cls._attributes(attributes):
                item.upsert_attribute(attribute)
            item._update_status("bot")
            if item.story:
                item.story.record_revision(note="update_news_item_attributes")
                affected_story_ids.add(item.story.id)

        story_attributes = changes.get("story_attributes", {})
        if not isinstance(story_attributes, dict):
            raise InvalidBotRun
        for story_id, attributes in story_attributes.items():
            if story_id not in allowed_stories or not isinstance(attributes, list):
                raise InvalidBotRun
            story = Story.get(story_id)
            if not story:
                raise InvalidBotRun
            story.patch_attributes(cls._attributes(attributes))
            story.update_status(change="bot")
            story.record_revision(note="update_story_attributes")
            affected_story_ids.add(story.id)

        updates = changes.get("story_updates", {})
        if not isinstance(updates, dict):
            raise InvalidBotRun
        for story_id, values in updates.items():
            if story_id not in allowed_stories or not isinstance(values, dict) or not values or set(values) - {"title", "summary"}:
                raise InvalidBotRun
            story = Story.get(story_id)
            if not story or any(not isinstance(value, str) for value in values.values()):
                raise InvalidBotRun
            for key, value in values.items():
                setattr(story, key, value)
            story.update_status(change="bot")
            story.record_revision(note="update")
            affected_story_ids.add(story_id)

        groups = changes.get("groups", [])
        if not isinstance(groups, list):
            raise InvalidBotRun
        for group in groups:
            if not isinstance(group, list) or len(group) < 2 or any(story_id not in allowed_stories for story_id in group):
                raise InvalidBotRun
            _, status = Story.group_stories(group, actor="bot", commit=False)
            if status != 200:
                raise InvalidBotRun
            affected_story_ids.update(group)

        if bot_type == "INTEL_OWL_BOT":
            enrichments = result.get("enrichments", [])
            if not isinstance(enrichments, list) or any(not isinstance(item, dict) for item in enrichments):
                raise InvalidBotRun
            IOC.upsert_many(enrichments, commit=False)
