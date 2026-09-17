from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import undefer

from core.managers.db_manager import db


class FilterData:
    @classmethod
    def get_assess_filterlists(cls, user=None) -> dict[str, Any]:
        return {
            "tags": cls._build_tags(user=user),
            "sources": cls._build_sources(user=user),
            "groups": cls._build_groups(user=user),
            "languages": cls._build_languages(user=user),
        }

    @classmethod
    def visible_news_items(cls, user):
        from core.model.news_item import NewsItem
        from core.model.story import Story

        query = db.select(NewsItem)
        if user:
            query = query.where(NewsItem.story_id.in_(Story.visible_query(user).with_only_columns(Story.id)))
        return query

    @classmethod
    def _build_tags(cls, user=None) -> list[str]:
        from core.model.news_item import NewsItem
        from core.model.news_item_tag import NewsItemTag

        rows = db.session.scalars(
            db.select(NewsItemTag.name)
            .where(NewsItemTag.news_item_id.in_(cls.visible_news_items(user).with_only_columns(NewsItem.id)))
            .where(or_(NewsItemTag.tag_type.is_(None), NewsItemTag.tag_type == "", NewsItemTag.tag_type.not_ilike("report_%")))
            .distinct()
            .order_by(NewsItemTag.name)
        ).all()

        return [name for name in rows if name]

    @classmethod
    def _build_sources(cls, user=None) -> list[dict[str, Any]]:
        from core.model.news_item import NewsItem
        from core.model.osint_source import OSINTSource

        query = OSINTSource.get_filter_query_with_acl({}, user) if user else OSINTSource.get_filter_query({})
        if user:
            query = query.where(OSINTSource.id.in_(cls.visible_news_items(user).with_only_columns(NewsItem.osint_source_id)))
        query = query.options(undefer(OSINTSource.icon))
        sources = OSINTSource.get_filtered(query) or []
        return [source.to_assess_dict() for source in sources if source]

    @classmethod
    def _build_groups(cls, user=None) -> list[dict[str, Any]]:
        from core.model.news_item import NewsItem
        from core.model.osint_source import OSINTSourceGroup, OSINTSourceGroupOSINTSource

        query = OSINTSourceGroup.get_filter_query_with_acl({}, user) if user else OSINTSourceGroup.get_filter_query({})
        if user:
            visible_sources = cls.visible_news_items(user).with_only_columns(NewsItem.osint_source_id)
            query = query.where(
                OSINTSourceGroup.id.in_(
                    db.select(OSINTSourceGroupOSINTSource.osint_source_group_id).where(
                        OSINTSourceGroupOSINTSource.osint_source_id.in_(visible_sources)
                    )
                )
            )
        groups = OSINTSourceGroup.get_filtered(query) or []
        return [group.to_assess_dict() for group in groups if getattr(group, "id", None)]

    @classmethod
    def _build_languages(cls, user=None) -> list[str]:
        from core.model.news_item import NewsItem

        normalized_language = func.lower(func.trim(NewsItem.language)).label("language")
        query = (
            db.select(normalized_language)
            .where(NewsItem.id.in_(cls.visible_news_items(user).with_only_columns(NewsItem.id)))
            .where(
                NewsItem.language.is_not(None),
                func.trim(NewsItem.language) != "",
            )
            .distinct()
            .order_by(normalized_language)
        )
        languages = db.session.scalars(query).all()

        return [language for language in languages if language]
