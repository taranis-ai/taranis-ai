from typing import Any

from core.managers.db_manager import db


class FilterData:
    @classmethod
    def get_assess_filterlists(cls, user=None) -> dict[str, Any]:
        return {
            "tags": cls._build_tags(),
            "sources": cls._build_sources(user=user),
            "groups": cls._build_groups(user=user),
            "languages": cls._build_languages(),
        }

    @classmethod
    def _build_tags(cls) -> list[str]:
        from core.model.news_item_tag import NewsItemTag

        rows = db.session.scalars(
            db.select(NewsItemTag.name).where(NewsItemTag.tag_type.not_ilike("report_%")).distinct().order_by(NewsItemTag.name)
        ).all()

        return [name for name in rows if name]

    @classmethod
    def _build_sources(cls, user=None) -> list[dict[str, Any]]:
        from core.model.osint_source import OSINTSource

        query = OSINTSource.get_filter_query_with_acl({}, user) if user else OSINTSource.get_filter_query({})
        sources = OSINTSource.get_filtered(query) or []
        return [source.to_assess_dict() for source in sources if source]

    @classmethod
    def _build_groups(cls, user=None) -> list[dict[str, Any]]:
        from core.model.osint_source import OSINTSourceGroup

        query = OSINTSourceGroup.get_filter_query_with_acl({}, user) if user else OSINTSourceGroup.get_filter_query({})
        groups = OSINTSourceGroup.get_filtered(query) or []
        return [group.to_assess_dict() for group in groups if getattr(group, "id", None)]

    @classmethod
    def _build_languages(cls) -> list[str]:
        from core.model.news_item import NewsItem

        languages = db.session.scalars(
            db.select(NewsItem.language)
            .where(
                NewsItem.language.is_not(None),
                NewsItem.language != "",
            )
            .distinct()
            .order_by(NewsItem.language)
        ).all()

        return [language for language in languages if language]
