from core.log import logger
from core.managers.db_manager import db
from core.model.news_item import NewsItem
from core.model.story import Story
from core.model.user import User
from core.service.misp_auto_update import refresh_misp_auto_update_jobs


class NewsItemService:
    @classmethod
    def update(cls, news_item_id: str, data, user: User):
        news_item = NewsItem.get(news_item_id)
        if not news_item:
            return {"error": "NewsItem not found"}, 404
        if not news_item.allowed_with_acl(user, require_write_access=True):
            return {"error": "User does not have write access to this news item"}, 403
        response, status = news_item.update_item(data, actor=Story.last_change_for_user(user))
        if status != 200:
            db.session.rollback()
            return response, status

        if story := Story.get(news_item.story_id):
            story.record_revision(user, note="update_news_item")
            db.session.commit()
            refresh_misp_auto_update_jobs([story.id])
            return {"message": "Successfully updated News Item", "story_id": story.id, "news_item_id": news_item.id}, 200

        db.session.rollback()
        return {"error": "Unable to update News Itemm"}, 500

    @classmethod
    def delete(cls, news_item_id: str, user: User):
        news_item = NewsItem.get(news_item_id)
        if not news_item:
            logger.debug(f"NewsItem with id: {news_item_id} not found")
            return {"error": "NewsItem not found"}, 404
        if not news_item.allowed_with_acl(user, require_write_access=True):
            logger.debug("User does not have write access to this news item")
            return {"error": "User does not have write access to this news item"}, 403
        story_id = news_item.story_id
        story = Story.get(story_id)
        if not story:
            logger.debug(f"Story with id: {story_id} not found")
            return {"error": "Story not found"}, 404

        if Story.is_assigned_to_report([story_id]):
            logger.debug(f"Story with: {story_id} assigned to a report")
            return {"error": "Story is assigned to a report"}, 400

        story_actor = Story.last_change_for_user(user) or "internal"
        story.last_change = story_actor
        deleted_title = news_item.title
        story.news_items.remove(news_item)
        news_item.delete_item()
        if story.news_items and story.title == deleted_title:
            story.title = story.news_items[0].title
        story.update_status(change=story_actor)
        story.record_revision(user, note="delete_news_item")
        db.session.commit()
        refresh_misp_auto_update_jobs([story.id])
        logger.debug(f"NewsItem with id: {news_item_id} deleted")
        return {"message": "News Item deleted", "id": news_item.id, "story_id": story.id}, 200

    @staticmethod
    def update_language(news_item_id: str, language, actor: str | None = None) -> tuple[dict, int]:
        item = NewsItem.get(news_item_id)
        response, status = NewsItem.update_news_item_lang(news_item_id, language, actor=actor)
        if status == 200 and item:
            refresh_misp_auto_update_jobs([item.story_id])
        return response, status

    @staticmethod
    def update_attributes(news_item_id: str, attributes, actor: str | None = None) -> tuple[dict, int]:
        item = NewsItem.get(news_item_id)
        response, status = NewsItem.update_attributes(news_item_id, attributes, actor=actor)
        if status == 200 and item:
            refresh_misp_auto_update_jobs([item.story_id])
        return response, status

    @staticmethod
    def update_tags(
        news_item: NewsItem,
        tags: list | dict,
        user: User | None = None,
        actor: str | None = None,
    ) -> tuple[dict, int]:
        response, status = news_item.set_tags(tags, user=user, actor=actor)
        if status == 200:
            refresh_misp_auto_update_jobs([news_item.story_id])
        return response, status

    @classmethod
    def has_related_news_items(cls, osint_source_id: str) -> bool:
        return db.session.execute(db.select(db.exists().where(NewsItem.osint_source_id == osint_source_id))).scalar_one()
