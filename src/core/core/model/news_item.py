import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional
from sqlalchemy.sql import Select
from sqlalchemy.orm import Mapped, relationship


from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.log import logger
from core.model.user import User
from core.model.role_based_access import ItemType, RoleBasedAccess
from core.model.osint_source import OSINTSource
from core.model.news_item_attribute import NewsItemAttribute
from core.service.role_based_access import RBACQuery, RoleBasedAccessService


class NewsItem(BaseModel):
    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    hash: Mapped[str] = db.Column(db.String())

    title: Mapped[str] = db.Column(db.String())
    review: Mapped[str] = db.Column(db.String())
    author: Mapped[str] = db.Column(db.String())
    source: Mapped[str] = db.Column(db.String())
    link: Mapped[str] = db.Column(db.String())
    language: Mapped[str] = db.Column(db.String())
    content: Mapped[str] = db.Column(db.String())
    collected: Mapped[datetime] = db.Column(db.DateTime)
    published: Mapped[datetime] = db.Column(db.DateTime, default=datetime.now())
    updated: Mapped[datetime] = db.Column(db.DateTime, default=datetime.now())

    attributes: Mapped[list["NewsItemAttribute"]] = relationship(
        "NewsItemAttribute", secondary="news_item_news_item_attribute", cascade="all, delete"
    )

    osint_source_id: Mapped[str] = db.Column(db.String, db.ForeignKey("osint_source.id"), nullable=True, index=True)
    osint_source: Mapped["OSINTSource"] = relationship("OSINTSource")

    story_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("story.id"), index=True)

    def __init__(
        self,
        title: str,
        source: str,
        content: str,
        osint_source_id: str,
        review="",
        author="",
        link="",
        published=datetime.now(),
        collected=datetime.now(),
        hash=None,
        attributes=None,
        id=None,
    ):
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.review = review
        self.content = content
        self.osint_source = OSINTSource.get(osint_source_id)
        self.source = source
        self.link = link
        self.author = author
        self.hash = hash or self.get_hash(author, title, link, content)
        self.collected = collected if type(collected) is datetime else datetime.fromisoformat(str(collected))
        self.published = published if type(published) is datetime else datetime.fromisoformat(str(published))
        if attributes:
            self.attributes = NewsItemAttribute.load_multiple(attributes)

    @classmethod
    def get_hash(
        cls, author: Optional[str] = None, title: Optional[str] = None, link: Optional[str] = None, content: Optional[str] = None
    ) -> str:
        strauthor = author or ""
        strtitle = title or ""
        strlink = link or ""
        strcontent = content or ""
        combined_str = f"{strauthor}{strtitle}{strlink}{strcontent}"
        return hashlib.sha256(combined_str.encode()).hexdigest()

    @classmethod
    def identical(cls, hash) -> bool:
        return db.session.execute(db.select(db.exists().where(cls.hash == hash))).scalar_one()

    @classmethod
    def find_by_hash(cls, hash):
        return cls.get_filtered(db.select(cls).where(cls.hash == hash))

    @classmethod
    def latest_collected(cls):
        news_item = cls.get_first(db.select(cls).order_by(db.desc(cls.collected)).limit(1))
        return news_item.collected.isoformat() if news_item else ""

    def has_attribute_value(self, value) -> bool:
        return any(attribute.value == value for attribute in self.attributes)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["attributes"] = [attribute.to_dict() for attribute in self.attributes]
        return data

    @classmethod
    def update_news_item_lang(cls, news_item_id, lang):
        news_item = cls.get(news_item_id)
        if news_item is None:
            return {"error": "Invalid news item id"}, 400
        news_item.language = lang
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
            if not news_item.has_attribute_value(attribute.value):
                news_item.attributes.append(attribute)

        return {"message": "Attributes updated"}, 200

    def get_tlp(self) -> str | None:
        return next((attr.value for attr in self.attributes if attr.key == "TLP"), None)

    def update_item(self, data) -> tuple[dict, int]:
        if self.source != "manual":
            return {"error": "Only manual news items can be updated"}, 400

        if title := data.get("title"):
            self.title = title

        if review := data.get("review"):
            self.review = review

        if author := data.get("author"):
            self.author = author

        if link := data.get("link"):
            self.link = link

        if content := data.get("content"):
            self.content = content

        if published := data.get("published"):
            self.published = published

        self.updated = datetime.now()
        self.hash = self.get_hash(self.author, self.title, self.link, self.content)

        db.session.commit()
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
            date_limit = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

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
            query = query.filter(NewsItem.published >= datetime.fromisoformat(timefrom))

        if timeto := filter_args.get("timeto"):
            query = query.filter(NewsItem.published <= datetime.fromisoformat(timeto))

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
        db.session.commit()


class NewsItemNewsItemAttribute(BaseModel):
    news_item_id: Mapped[str] = db.Column(db.String, db.ForeignKey("news_item.id"), primary_key=True)
    news_item_attribute_id: Mapped[str] = db.Column(db.String, db.ForeignKey("news_item_attribute.id", ondelete="CASCADE"), primary_key=True)
