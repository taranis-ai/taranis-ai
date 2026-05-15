from datetime import datetime
from typing import Any

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Mapped
from sqlalchemy.sql import Select

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.role_based_access import ItemType, RoleBasedAccess
from core.service.role_based_access import RBACQuery, RoleBasedAccessService


class FilterData(BaseModel):
    __tablename__ = "filterdata"

    ASSESS_FILTERLISTS_ID = "assess_filterlists"

    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    tags: Mapped[list[str]] = db.Column(db.JSON, nullable=False, default=list)
    sources: Mapped[list[dict[str, Any]]] = db.Column(db.JSON, nullable=False, default=list)
    groups: Mapped[list[dict[str, Any]]] = db.Column(db.JSON, nullable=False, default=list)
    languages: Mapped[list[str]] = db.Column(db.JSON, nullable=False, default=list)
    updated: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow, onupdate=BaseModel.utcnow, nullable=False)

    def __init__(
        self,
        id: str = ASSESS_FILTERLISTS_ID,
        tags: list[str] | None = None,
        sources: list[dict[str, Any]] | None = None,
        groups: list[dict[str, Any]] | None = None,
        languages: list[str] | None = None,
    ):
        self.id = id
        self.tags = tags or []
        self.sources = sources or []
        self.groups = groups or []
        self.languages = languages or []

    @classmethod
    def get_filter_query(cls, filter_args: dict[str, Any]) -> Select:
        query = db.select(cls)
        if item_id := filter_args.get("id"):
            query = query.where(cls.id == item_id)
        return query

    @classmethod
    def get_assess_filterlists(cls, user=None) -> dict[str, Any]:
        filter_data = cls.get(cls.ASSESS_FILTERLISTS_ID)
        if filter_data is None:
            try:
                filter_data = cls.rebuild_filter_data()
            except OperationalError:
                db.session.rollback()
                payload = {
                    "tags": cls._build_tags(),
                    "sources": cls._build_sources(),
                    "groups": cls._build_groups(),
                    "languages": cls._build_languages(),
                }
                return cls(**payload).to_filterlists_dict(user=user)

        if not cls._is_cached_filter_data_valid(filter_data):
            try:
                filter_data = cls.rebuild_filter_data()
            except OperationalError:
                db.session.rollback()
                payload = {
                    "tags": cls._build_tags(),
                    "sources": cls._build_sources(),
                    "groups": cls._build_groups(),
                    "languages": cls._build_languages(),
                }
                return cls(**payload).to_filterlists_dict(user=user)

        return filter_data.to_filterlists_dict(user=user)

    def to_filterlists_dict(self, user=None) -> dict[str, Any]:
        sources = self._filter_acl_items(self.sources, user, ItemType.OSINT_SOURCE)
        groups = self._filter_acl_items(self.groups, user, ItemType.OSINT_SOURCE_GROUP)
        return {
            "tags": self.tags,
            "sources": sources,
            "groups": groups,
            "languages": self.languages,
        }

    @staticmethod
    def _filter_acl_items(items: list[dict[str, Any]], user, item_type: ItemType) -> list[dict[str, Any]]:
        if not user or not RoleBasedAccess.is_enabled_for_type(item_type):
            return items

        filtered_items = []
        for item in items:
            item_id = item.get("id")
            if not item_id:
                continue
            query = RBACQuery(user=user, resource_id=str(item_id), resource_type=item_type)
            if RoleBasedAccessService.user_has_access_to_resource(query):
                filtered_items.append(item)
        return filtered_items

    @classmethod
    def rebuild_filter_data(cls) -> "FilterData":
        payload = {
            "tags": cls._build_tags(),
            "sources": cls._build_sources(),
            "groups": cls._build_groups(),
            "languages": cls._build_languages(),
        }

        filter_data = cls.get(cls.ASSESS_FILTERLISTS_ID) or cls()
        filter_data.tags = payload["tags"]
        filter_data.sources = payload["sources"]
        filter_data.groups = payload["groups"]
        filter_data.languages = payload["languages"]
        filter_data.updated = cls.utcnow()
        db.session.add(filter_data)
        db.session.commit()
        return filter_data

    @classmethod
    def _is_cached_filter_data_valid(cls, filter_data: "FilterData") -> bool:
        return bool(filter_data)

    @classmethod
    def _build_tags(cls) -> list[str]:
        from core.model.news_item_tag import NewsItemTag

        rows = db.session.scalars(
            db.select(NewsItemTag.name).where(NewsItemTag.tag_type.not_ilike("report_%")).distinct().order_by(NewsItemTag.name)
        ).all()

        return [name for name in rows if name]

    @classmethod
    def _build_sources(cls) -> list[dict[str, Any]]:
        from core.model.osint_source import OSINTSource

        sources = OSINTSource.get_filtered(db.select(OSINTSource)) or []
        return [source.to_assess_dict() for source in sources if source]

    @classmethod
    def _build_groups(cls) -> list[dict[str, Any]]:
        from core.model.osint_source import OSINTSourceGroup

        groups = OSINTSourceGroup.get_filtered(db.select(OSINTSourceGroup)) or []
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
