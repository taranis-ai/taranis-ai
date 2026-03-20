import hashlib
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Sequence

from models.assess import NewsItem as AssessNewsItem
from models.assess import Story as AssessStory
from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import Select

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.news_item_attribute import NewsItemAttribute
from core.model.osint_source import OSINTSource
from core.model.role import TLPLevel
from core.model.role_based_access import ItemType, RoleBasedAccess
from core.model.user import User
from core.service.role_based_access import RBACQuery, RoleBasedAccessService


if TYPE_CHECKING:
    from core.model.story import Story


class NewsItem(BaseModel):
    __tablename__ = "news_item"

    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    hash: Mapped[str] = db.Column(db.String(), index=True, unique=True, nullable=False)

    title: Mapped[str] = db.Column(db.String())
    review: Mapped[str] = db.Column(db.String())
    author: Mapped[str] = db.Column(db.String())
    source: Mapped[str] = db.Column(db.String())
    link: Mapped[str] = db.Column(db.String())
    language: Mapped[str] = db.Column(db.String())
    content: Mapped[str] = db.Column(db.String())
    collected: Mapped[datetime] = db.Column(
        db.DateTime,
        default=BaseModel.utcnow,
    )
    last_change: Mapped[str] = db.Column(db.String())
    published: Mapped[datetime] = db.Column(
        db.DateTime,
        default=BaseModel.utcnow,
    )
    updated: Mapped[datetime] = db.Column(
        db.DateTime,
        default=BaseModel.utcnow,
        onupdate=BaseModel.utcnow,
    )
    attributes: Mapped[list["NewsItemAttribute"]] = relationship(
        "NewsItemAttribute", secondary="news_item_news_item_attribute", cascade="all, delete"
    )

    osint_source_id: Mapped[str] = db.Column(db.String, db.ForeignKey("osint_source.id"), nullable=True, index=True)
    osint_source: Mapped["OSINTSource"] = relationship("OSINTSource", back_populates="news_items")

    story_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("story.id", ondelete="SET NULL"), nullable=True, index=True)
    story: Mapped["Story"] = relationship("Story", back_populates="news_items")

    def __init__(
        self,
        title: str = "",
        source: str = "",
        content: str = "",
        osint_source_id: str = "manual",
        review: str = "",
        author: str = "",
        link: str = "",
        language: str = "",
        hash: str | None = None,
        attributes=None,
        id=None,
        last_change="external",
        published: datetime | str | None = None,
        collected: datetime | str | None = None,
        story_id: str = "",
    ):
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.review = review
        self.content = content
        if osint_source := OSINTSource.get(osint_source_id):
            with db.session.no_autoflush:
                self.osint_source = osint_source
        else:
            raise ValueError(f"OSINT Source {osint_source_id} not found")
        self.source = source
        self.link = link
        self.author = author
        self.language = language
        self.last_change = last_change
        self.hash = hash or self.get_hash(title, link, content)
        self.collected = self.get_date_field(collected)
        self.published = self.get_date_field(published)
        self.story_id = story_id
        self.attributes = NewsItemAttribute.load_multiple(attributes or [])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NewsItem":
        return cls.from_payload(AssessNewsItem.from_input(data))

    @classmethod
    def from_payload(cls, payload: AssessNewsItem) -> "NewsItem":
        return cls(**payload.to_core_dict())

    @staticmethod
    def get_date_field(date_field: str | datetime | None) -> datetime:
        return AssessNewsItem.normalize_datetime(date_field, default_to_now=True) or BaseModel.utcnow()

    @classmethod
    def get_hash(cls, title: str = "", link: str = "", content: str = "") -> str:
        if not title and not link and not content:
            raise ValueError("At least one of the following parameters must be provided: title, link, content")
        combined_str = f"{title}{link}" if title or link else content
        return hashlib.sha256(combined_str.encode()).hexdigest()

    @classmethod
    def identical(cls, hash) -> bool:
        return db.session.execute(db.select(db.exists().where(cls.hash == hash))).scalar_one()

    @classmethod
    def find_by_hash(cls, hash):
        return cls.get_filtered(db.select(cls).where(cls.hash == hash))

    @classmethod
    def get_by_hash(cls, hash: str | None) -> "NewsItem | None":
        if not hash:
            return None
        return cls.get_first(db.select(cls).where(cls.hash == hash))

    @classmethod
    def latest_collected(cls) -> str | None:
        if news_item := cls.get_first(db.select(cls).order_by(db.desc(cls.collected)).limit(1)):
            return cls.serialize_datetime(news_item.collected)
        return None

    def has_attribute(self, key) -> bool:
        return any(attribute.key == key for attribute in self.attributes)

    def has_attribute_key(self, key) -> bool:
        return any(attribute.key == key for attribute in self.attributes)

    @classmethod
    def get_for_api(cls, item_id: str, user: User | None = None) -> tuple[dict[str, Any], int]:
        logger.debug(f"Getting {cls.__name__} {item_id}")
        if item := cls.get(item_id):
            return item.to_detail_dict(), 200
        return {"error": f"{cls.__name__} {item_id} not found"}, 404

    def to_detail_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        if attributes := self.attributes:
            data["attributes"] = [attribute.to_small_dict() for attribute in attributes]
        return data

    def get_sentiment(self) -> str:
        return next((attr.value for attr in self.attributes if attr.key == "sentiment_category"), "")

    def get_cybersecurity_status(self) -> str:
        return next((attr.value for attr in self.attributes if attr.key == "cybersecurity_human"), None) or next(
            (attr.value for attr in self.attributes if attr.key == "cybersecurity_bot"), "none"
        )

    def upsert(self):
        """Insert a NewsItem into the database or skip if hash exists."""
        if db.engine.dialect.name == "postgresql":
            insert_stmt = pg_insert(NewsItem)
        else:
            insert_stmt = sqlite_insert(NewsItem)

        stmt = insert_stmt.values(self.to_upsert_dict()).on_conflict_do_nothing(index_elements=["hash"]).returning(NewsItem)

        result = db.session.execute(stmt)
        return result.scalar_one()

    @classmethod
    def upsert_from_dict(cls, news_item: dict) -> "NewsItem":
        item = cls.from_dict(news_item)
        return item.upsert()

    @classmethod
    def upsert_multiple(cls, news_items: Sequence["NewsItem | None"]) -> list["NewsItem"]:
        updated_news_items = []
        for news_item in news_items:
            if news_item is not None:
                news_item.upsert()
                updated_news_items.append(news_item)
        return updated_news_items

    def to_upsert_dict(self) -> dict[str, Any]:
        table = getattr(self, "__table__", None)
        if table is None:
            return {}
        return {c.name: getattr(self, c.name) for c in table.columns}

    def _update_status(self, change: str = "internal"):
        self.last_change = change
        self.story.update_status(change=change)

    @classmethod
    def update_news_item_lang(cls, news_item_id, lang):
        news_item = cls.get(news_item_id)
        if news_item is None:
            return {"error": "Invalid news item id"}, 400
        news_item.language = lang
        news_item._update_status()
        if story := news_item.story:
            story.record_revision(note="update_news_item_lang")
        db.session.commit()
        return {"message": "Language updated"}, 200

    @classmethod
    def update_attributes(cls, news_item_id, attributes) -> tuple[dict, int]:
        news_item = cls.get(news_item_id)
        if news_item is None:
            return {"error": "Invalid news item id"}, 400

        attributes = NewsItemAttribute.load_multiple(attributes)
        if attributes is None:
            return {"error": "Invalid attributes"}, 400

        for attribute in attributes:
            news_item.upsert_attribute(attribute)
        news_item._update_status()
        if story := news_item.story:
            story.record_revision(note="update_news_item_attributes")
        db.session.commit()
        return {"message": f"Attributes of news item with id '{news_item_id}' updated"}, 200

    def add_attribute(self, attribute: NewsItemAttribute) -> None:
        if not self.has_attribute(attribute.key):
            self.attributes.append(attribute)

    def find_attribute_by_key(self, key: str) -> NewsItemAttribute | None:
        return next((attribute for attribute in self.attributes if attribute.key == key), None)

    def upsert_attribute(self, attribute: NewsItemAttribute) -> None:
        if existing_attribute := self.find_attribute_by_key(attribute.key):
            existing_attribute.value = attribute.value
        else:
            self.attributes.append(attribute)

    @property
    def tlp_level(self) -> TLPLevel:
        return next((TLPLevel(attr.value) for attr in self.attributes if attr.key == "TLP"), self.osint_source.tlp_level)

    def update_item(self, data) -> tuple[dict, int]:
        if self.osint_source_id != "manual":
            return {"error": "Only manual news items can be updated"}, 400

        try:
            payload = AssessNewsItem.from_input(self.to_detail_dict() | data | {"osint_source_id": self.osint_source_id})
        except ValidationError as exc:
            return AssessNewsItem.validation_error_response(exc, prefix="Invalid news item data"), 400

        if duplicate_item := self.get_by_hash(payload.hash):
            if duplicate_item.id != self.id:
                return {
                    "error": "Identical news item found. Skipping...",
                    "conflicting_news_item_id": duplicate_item.id,
                    "story_id": duplicate_item.story_id,
                }, 409

        self.title = payload.title or ""
        self.review = payload.review or ""
        self.author = payload.author or ""
        self.link = payload.link or ""
        self.content = payload.content or ""
        self.language = str(payload.language or "")
        self.published = payload.published or self.published
        self.hash = payload.hash or self.hash

        self._update_status("internal")

        self.updated = self.utcnow()

        return {"message": f"News Item {self.id} updated", "id": self.id}, 200

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls).distinct()
        query = query.join(OSINTSource, OSINTSource.id == cls.osint_source_id)

        if search := filter_args.get("search"):
            query = query.filter(
                db.or_(
                    cls.content.ilike(f"%{search}%"),
                    cls.review.ilike(f"%{search}%"),
                    cls.title.ilike(f"%{search}%"),
                )
            )

        if "range" in filter_args and filter_args["range"].upper() != "ALL":
            filter_range = filter_args["range"].upper()
            date_limit = cls.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            if filter_range == "DAY":
                date_limit -= timedelta(days=1)

            if filter_range == "WEEK":
                date_limit -= timedelta(days=date_limit.weekday())

            elif filter_range == "MONTH":
                date_limit = date_limit.replace(day=1)

            query = query.filter(cls.published >= date_limit)

        if "sort" in filter_args:
            if filter_args["sort"] == "DATE_DESC":
                query = query.order_by(db.desc(cls.published))

            elif filter_args["sort"] == "DATE_ASC":
                query = query.order_by(db.asc(cls.published))

        if timefrom := filter_args.get("timefrom"):
            normalized_timefrom = AssessStory.model_validate({"created": timefrom}).created
            query = query.filter(cls.published >= normalized_timefrom)

        if timeto := filter_args.get("timeto"):
            normalized_timeto = AssessStory.model_validate({"created": timeto}).created
            query = query.filter(cls.published <= normalized_timeto)

        offset = filter_args.get("offset", 0)
        limit = filter_args.get("limit", 20)
        return query.offset(offset).limit(limit)

    def allowed_with_acl(self, user: User, require_write_access: bool) -> bool:
        if not RoleBasedAccess.is_enabled():
            return True

        query = RBACQuery(
            user=user,
            resource_id=self.osint_source_id,
            resource_type=ItemType.OSINT_SOURCE,
            require_write_access=require_write_access,
        )

        access = RoleBasedAccessService.user_has_access_to_resource(query)
        if not access:
            logger.warning(f"User {user.id} has no access to resource {self.osint_source_id}")
        return access

    @classmethod
    def get_filter_query_with_acl(cls, filter_args: dict, user: User) -> Select:
        query = cls.get_filter_query(filter_args)
        rbac = RBACQuery(user=user, resource_type=ItemType.OSINT_SOURCE)
        query = RoleBasedAccessService.filter_query_with_acl(query, rbac)
        return query

    def delete_item(self):
        db.session.delete(self)


class NewsItemNewsItemAttribute(BaseModel):
    news_item_id: Mapped[str] = db.Column(db.String, db.ForeignKey("news_item.id", ondelete="CASCADE"), primary_key=True)
    news_item_attribute_id: Mapped[str] = db.Column(db.String, db.ForeignKey("news_item_attribute.id", ondelete="CASCADE"), primary_key=True)
