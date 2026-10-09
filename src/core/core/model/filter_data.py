from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import undefer

from core.managers.db_manager import db


class FilterData:
    LIST_LIMIT = 1000

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
            query = query.where(Story.visible_query(user).where(Story.id == NewsItem.story_id).exists())
        return query

    @classmethod
    def _build_tags(cls, user=None) -> list[str]:
        from core.model.news_item import NewsItem
        from core.model.news_item_tag import NewsItemTag, NewsItemTagCluster

        names = (
            db.select(NewsItemTagCluster.name)
            .where(or_(NewsItemTagCluster.tag_type_key == "", NewsItemTagCluster.tag_type_key.not_ilike("report_%")))
            .distinct()
            .subquery()
        )
        visible_item = cls.visible_news_items(user).where(NewsItem.id == NewsItemTag.news_item_id).offset(0).exists()
        # OFFSET 0 keeps PostgreSQL from joining all tag occurrences instead of probing each candidate name.
        visible_tag = (
            db.select(NewsItemTag.news_item_id)
            .where(NewsItemTag.name == names.c.name, visible_item)
            .where(or_(NewsItemTag.tag_type.is_(None), NewsItemTag.tag_type == "", NewsItemTag.tag_type.not_ilike("report_%")))
            .offset(0)
            .exists()
        )
        rows = db.session.scalars(db.select(names.c.name).where(visible_tag).order_by(names.c.name).limit(cls.LIST_LIMIT)).all()

        return [name for name in rows if name]

    @classmethod
    def _build_sources(cls, user=None) -> list[dict[str, Any]]:
        from core.model.news_item import NewsItem
        from core.model.osint_source import OSINTSource

        query = OSINTSource.get_filter_query_with_acl({}, user) if user else OSINTSource.get_filter_query({})
        if user:
            query = query.where(cls.visible_news_items(user).where(NewsItem.osint_source_id == OSINTSource.id).exists())
        query = query.order_by(OSINTSource.name).limit(cls.LIST_LIMIT).options(undefer(OSINTSource.icon))
        sources = OSINTSource.get_filtered(query) or []
        return [source.to_assess_dict() for source in sources if source]

    @classmethod
    def _build_groups(cls, user=None) -> list[dict[str, Any]]:
        from core.model.news_item import NewsItem
        from core.model.osint_source import OSINTSourceGroup, OSINTSourceGroupOSINTSource

        query = OSINTSourceGroup.get_filter_query_with_acl({}, user) if user else OSINTSourceGroup.get_filter_query({})
        if user:
            query = query.where(
                db.select(OSINTSourceGroupOSINTSource.osint_source_group_id)
                .where(
                    OSINTSourceGroupOSINTSource.osint_source_group_id == OSINTSourceGroup.id,
                    cls.visible_news_items(user).where(NewsItem.osint_source_id == OSINTSourceGroupOSINTSource.osint_source_id).exists(),
                )
                .exists()
            )
        query = query.limit(cls.LIST_LIMIT)
        groups = OSINTSourceGroup.get_filtered(query) or []
        return [group.to_assess_dict() for group in groups if getattr(group, "id", None)]

    @classmethod
    def _build_languages(cls, user=None) -> list[str]:
        from core.model.news_item import NewsItem

        normalized_language = func.lower(func.trim(NewsItem.language)).label("language")
        query = (
            cls.visible_news_items(user)
            .with_only_columns(normalized_language)
            .where(
                NewsItem.language.is_not(None),
                func.trim(NewsItem.language) != "",
            )
            .distinct()
            .order_by(normalized_language)
            .limit(cls.LIST_LIMIT)
        )
        languages = db.session.scalars(query).all()

        return [language for language in languages if language]
