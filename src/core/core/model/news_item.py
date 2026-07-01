import hashlib
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Sequence

from models.assess import NewsItem as AssessNewsItem
from models.assess import Story as AssessStory
from models.assess import validate_bcp47
from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import Select

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel
from core.model.news_item_attribute import NewsItemAttribute
from core.model.news_item_tag import NewsItemTag
from core.model.osint_source import OSINTSource
from core.model.role import TLPLevel
from core.model.role_based_access import ItemType, RoleBasedAccess
from core.model.user import User
from core.service.role_based_access import RBACQuery, RoleBasedAccessService


if TYPE_CHECKING:
    from core.model.story import Story


class NewsItem(BaseModel):
    __tablename__ = "news_item"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
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
    tags: Mapped[list["NewsItemTag"]] = relationship("NewsItemTag", back_populates="news_item", cascade="all, delete")

    osint_source_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("osint_source.id"), nullable=True, index=True)
    osint_source: Mapped["OSINTSource | None"] = relationship("OSINTSource", back_populates="news_items")

    story_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("story.id", ondelete="SET NULL"), nullable=True, index=True)
    story: Mapped["Story | None"] = relationship("Story", back_populates="news_items")

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
        tags: list | dict | None = None,
    ):
        normalized_published = self.get_date_field(published)
        normalized_collected = self.get_date_field(collected)
        normalized_id = self.normalize_uuid_id(id)

        payload = AssessNewsItem.from_input(
            {
                "title": title,
                "source": source,
                "content": content,
                "osint_source_id": osint_source_id,
                "review": review,
                "author": author,
                "link": link,
                "language": language,
                "hash": hash,
                "id": normalized_id,
                "attributes": attributes,
                "last_change": last_change,
                "published": normalized_published,
                "collected": normalized_collected,
                "story_id": story_id,
                "tags": tags,
            }
        )

        self.id = payload.id or normalized_id
        self.title = payload.title or ""
        self.review = payload.review or ""
        self.content = payload.content or ""
        if osint_source := OSINTSource.get(payload.osint_source_id):
            with db.session.no_autoflush:
                self.osint_source = osint_source
        else:
            logger.warning(f"OSINT Source {payload.osint_source_id} not found. Setting osint_source_id to manual.")
            self.osint_source = OSINTSource.get_manual()
        self.source = payload.source or ""
        self.link = payload.link or ""
        self.author = payload.author or ""
        self.language = payload.language or ""
        self.last_change = payload.last_change or last_change
        self.hash = payload.hash or self.get_hash(title=self.title, link=self.link, content=self.content)
        self.collected = payload.collected or normalized_collected
        self.published = payload.published or normalized_published
        self.story_id = payload.story_id or story_id
        self.attributes = NewsItemAttribute.load_multiple(
            [attribute for attribute in payload.attributes or [] if isinstance(attribute, dict)]
        )
        self.tags = list(NewsItemTag.parse_tags(payload.tags or {}).values())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NewsItem":
        return cls.from_payload(AssessNewsItem.from_input(data))

    @classmethod
    def _sanitize_import_payload(cls, payload: AssessNewsItem) -> dict[str, Any]:
        return payload.to_core_dict()

    @classmethod
    def from_payload(cls, payload: AssessNewsItem) -> "NewsItem":
        return cls(**cls._sanitize_import_payload(payload))

    @staticmethod
    def get_date_field(date_field: str | datetime | None) -> datetime:
        return AssessNewsItem.normalize_datetime(date_field, default_to_now=True) or BaseModel.utcnow()

    @classmethod
    def get_hash(cls, title: str = "", link: str = "", content: str = "") -> str:
        if not title and not link and not content:
            raise ValueError("At least one of the following parameters must be provided: title, link, content")
        combined_str = f"{title}{link}"
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
        return {"error": f"{cls.__name__} not found"}, 404

    def to_detail_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        if self.osint_source and self.osint_source.key:
            data["osint_source_key"] = self.osint_source.key
        if attributes := self.attributes:
            data["attributes"] = [attribute.to_small_dict() for attribute in attributes]
        return data

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["tags"] = [tag.to_dict() for tag in self.tags]
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

    @classmethod
    def delete_all(cls) -> tuple[dict[str, Any], int]:
        from core.model.news_item_tag import NewsItemTag, NewsItemTagCluster

        db.session.execute(db.delete(NewsItemTagCluster))
        db.session.execute(db.delete(NewsItemTag))
        db.session.execute(db.delete(cls))
        db.session.commit()
        logger.debug(f"All {cls.__name__} deleted")
        return {"message": f"All {cls.__name__} deleted"}, 200

    def to_upsert_dict(self) -> dict[str, Any]:
        table = getattr(self, "__table__", None)
        if table is None:
            return {}
        return {c.name: getattr(self, c.name) for c in table.columns}

    def _update_status(self, change: str = "internal"):
        self.last_change = change
        if self.story:
            self.story.update_status(change=change)

    @staticmethod
    def _normalize_language(lang: Any) -> str:
        return validate_bcp47(lang) or ""

    @classmethod
    def update_news_item_lang(cls, news_item_id, lang, actor: str | None = None):
        news_item = cls.get(news_item_id)
        if news_item is None:
            return {"error": "Invalid news item id"}, 400
        try:
            news_item.language = cls._normalize_language(lang)
        except (TypeError, ValueError):
            return {"error": "Invalid news item data: Invalid BCP 47 language tag"}, 400
        news_item._update_status(actor or "internal")
        if story := news_item.story:
            story.record_revision(note="update_news_item_lang")
        db.session.commit()
        return {"message": "Language updated"}, 200

    @classmethod
    def update_attributes(cls, news_item_id, attributes, actor: str | None = None) -> tuple[dict, int]:
        news_item = cls.get(news_item_id)
        if news_item is None:
            return {"error": "Invalid news item id"}, 400

        if isinstance(attributes, dict):
            attributes = attributes.get("attributes", attributes)

        attributes = NewsItemAttribute.load_multiple(attributes)
        if attributes is None:
            return {"error": "Invalid attributes"}, 400

        for attribute in attributes:
            news_item.upsert_attribute(attribute)
        news_item._update_status(actor or "internal")
        if story := news_item.story:
            story.record_revision(note="update_news_item_attributes")
        db.session.commit()
        return {"message": "News item attributes updated"}, 200

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

    def get_tags_to_remove(self, tags: dict[str, NewsItemTag]) -> set[str]:
        incoming_tag_names = set(tags.keys())
        existing_tag_names = {tag.name for tag in self.tags}
        return existing_tag_names - incoming_tag_names

    def set_tags(
        self,
        incoming_tags: list | dict,
        user: User | None = None,
        actor: str | None = None,
        replace: bool = True,
        update_story: bool = True,
        commit: bool = True,
    ) -> tuple[dict, int]:
        try:
            return self._update_tags(
                incoming_tags,
                user=user,
                actor=actor,
                replace=replace,
                update_story=update_story,
                commit=commit,
            )
        except Exception:
            logger.exception("Update News Item Tags Failed")
            db.session.rollback()
            return {"error": "Update News Item Tags Failed"}, 500

    def _update_tags(
        self,
        incoming_tags: list | dict,
        user: User | None = None,
        actor: str | None = None,
        replace: bool = True,
        update_story: bool = True,
        commit: bool = True,
    ) -> tuple[dict, int]:
        try:
            parsed_tags = NewsItemTag.parse_tags(incoming_tags)
        except (TypeError, ValueError):
            return {"error": "Invalid tags"}, 400

        if incoming_tags and not parsed_tags:
            return {"error": "No valid tags provided"}, 400

        summary_keys = self.get_tag_summary_keys()
        for tag in parsed_tags.values():
            summary_keys.update(NewsItemTag.get_summary_keys_for_tag_types(tag.name, tag.tag_type))

        if not parsed_tags:
            if replace:
                self.remove_tags({tag.name for tag in self.tags})
            else:
                return {"error": "No valid tags provided"}, 400
        else:
            self.patch_tags(parsed_tags)
            if replace:
                self.remove_tags(self.get_tags_to_remove(parsed_tags))

        if update_story and (story := self.story):
            from core.model.story import Story

            actor = Story.resolve_actor(user=user, actor=actor)
            story.update_status(change=actor)
            story.record_revision(user or Story.user_for_actor(actor), note="set_news_item_tags")

        db.session.flush()
        self.refresh_tag_summaries(summary_keys)
        if commit:
            db.session.commit()
        return {"message": "News item tags updated"}, 200

    def get_tag_summary_keys(self) -> set[tuple[str, str]]:
        summary_keys = set()
        for tag in self.tags:
            summary_keys.update(NewsItemTag.get_summary_keys_for_tag_types(tag.name, tag.tag_type))
        return summary_keys

    def refresh_tag_summaries(self, summary_keys: set[tuple[str, str]]) -> None:
        from core.model.news_item_tag import NewsItemTagCluster

        if summary_keys:
            NewsItemTagCluster.refresh_for_keys(summary_keys)

    def patch_tags(self, tags: dict[str, NewsItemTag]):
        for tag in tags.values():
            self.upsert_tag(tag)

    def remove_tags(self, keys: set[str]):
        for key in keys:
            if tag := self.find_tag_by_name(key):
                self.tags.remove(tag)
                db.session.delete(tag)

    def upsert_tag(self, tag: NewsItemTag) -> None:
        if existing_tag := self.find_tag_by_name(tag.name):
            existing_tag.tag_type = tag.tag_type
        else:
            self.tags.append(tag)

    def find_tag_by_name(self, name: str) -> NewsItemTag | None:
        return next((tag for tag in self.tags if tag.name == name), None)

    @property
    def tlp_level(self) -> TLPLevel:
        source_tlp = self.osint_source.tlp_level if self.osint_source else TLPLevel.CLEAR
        return next((TLPLevel(attr.value) for attr in self.attributes if attr.key == "TLP"), source_tlp)

    def update_item(self, data, actor: str | None = None) -> tuple[dict, int]:
        if not self.osint_source or self.osint_source.key != "manual":
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
        self.language = payload.language or ""
        self.published = payload.published or self.published
        self.hash = payload.hash or self.hash

        self._update_status(actor or "internal")

        self.updated = self.utcnow()

        return {"message": "News item updated", "id": self.id}, 200

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
    news_item_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("news_item.id", ondelete="CASCADE"), primary_key=True)
    news_item_attribute_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("news_item_attribute.id", ondelete="CASCADE"), primary_key=True
    )
