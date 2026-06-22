from typing import Any

from sqlalchemy import func, or_

from core.managers.db_manager import db


class FilterData:
    @classmethod
    def get_assess_filterlists(cls, user=None) -> dict[str, Any]:
        return {
            "tags": cls._build_tags(),
            "sources": cls._build_sources(user=user),
            "groups": cls._build_groups(user=user),
            "languages": cls._build_languages(user=user),
        }

    @classmethod
    def _build_tags(cls) -> list[str]:
        from core.model.news_item_tag import NewsItemTagCluster

        rows = db.session.scalars(
            db.select(NewsItemTagCluster.name)
            .where(or_(NewsItemTagCluster.tag_type_key == "", NewsItemTagCluster.tag_type_key.not_ilike("report_%")))
            .distinct()
            .order_by(NewsItemTagCluster.name)
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
    def _build_languages(cls, user=None) -> list[str]:
        from core.model.news_item import NewsItem
        from core.model.osint_source import OSINTSource
        from core.model.role_based_access import ItemType
        from core.service.role_based_access import RBACQuery, RoleBasedAccessService

        normalized_language = func.lower(func.trim(NewsItem.language)).label("language")
        query = (
            db.select(normalized_language)
            .join(OSINTSource, NewsItem.osint_source_id == OSINTSource.id)
            .where(
                NewsItem.language.is_not(None),
                func.trim(NewsItem.language) != "",
            )
            .distinct()
            .order_by(normalized_language)
        )
        if user:
            rbac = RBACQuery(user=user, resource_type=ItemType.OSINT_SOURCE)
            query = RoleBasedAccessService.filter_query_with_acl(query, rbac)
        languages = db.session.scalars(query).all()

        return [language for language in languages if language]
