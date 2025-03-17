from core.model.story import Story
from core.model.news_item import NewsItem
from core.managers.db_manager import db
from core.model.user import User
from core.log import logger


class NewsItemService:
    @classmethod
    def update(cls, news_item_id: str, data, user: User):
        news_item = NewsItem.get(news_item_id)
        if not news_item:
            return {"error": f"NewsItem with id: {news_item_id} not found"}, 404
        if not news_item.allowed_with_acl(user, require_write_access=True):
            return {"error": "User does not have write access to this news item"}, 403
        news_item.update_item(data)

        if story := Story.get(news_item.story_id):
            story.update_status()
        db.session.commit()

        return {"message": "success"}, 200

    @classmethod
    def delete(cls, news_item_id: str, user: User):
        news_item = NewsItem.get(news_item_id)
        if not news_item:
            logger.debug(f"NewsItem with id: {news_item_id} not found")
            return {"error": f"NewsItem with id: {news_item_id} not found"}, 404
        if not news_item.allowed_with_acl(user, require_write_access=True):
            logger.debug("User does not have write access to this news item")
            return {"error": "User does not have write access to this news item"}, 403
        story_id = news_item.story_id
        story = Story.get(story_id)
        if not story:
            logger.debug(f"Story with id: {story_id} not found")
            return {"error": f"Story with id: {id} not found"}, 404

        if Story.is_assigned_to_report([story_id]):
            logger.debug(f"Story with: {story_id} assigned to a report")
            return {"error": f"Story with: {story_id} assigned to a report"}, 400

        story.last_change = "internal"
        story.news_items.remove(news_item)
        news_item.delete_item()
        story.update_status()
        logger.debug(f"NewsItem with id: {news_item_id} deleted")
        return {"message": "News Item deleted", "id": news_item_id}, 200

    @classmethod
    def has_related_news_items(cls, osint_source_id: str) -> bool:
        return db.session.execute(db.select(db.exists().where(NewsItem.osint_source_id == osint_source_id))).scalar_one()
