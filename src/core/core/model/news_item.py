import uuid
import base64
import contextlib
from datetime import datetime, timedelta
from typing import Any, Optional
from sqlalchemy import orm, or_, func
from sqlalchemy.sql.expression import false, null

from collections import Counter
import hashlib

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.log import logger
from core.model.user import User
from core.model.role import TLPLevel
from core.model.news_item_tag import NewsItemTag
from core.model.role_based_access import ItemType, RoleBasedAccess
from core.model.osint_source import OSINTSourceGroup, OSINTSource, OSINTSourceGroupOSINTSource
from core.service.role_based_access import RBACQuery, RoleBasedAccessService


class NewsItemData(BaseModel):
    id = db.Column(db.String(64), primary_key=True)
    hash = db.Column(db.String())

    title: Any = db.Column(db.String())
    review: Any = db.Column(db.String())
    author: Any = db.Column(db.String())
    source: Any = db.Column(db.String())
    link: Any = db.Column(db.String())
    language: Any = db.Column(db.String())
    content: Any = db.Column(db.String())
    collected: Any = db.Column(db.DateTime)
    published: Any = db.Column(db.DateTime, default=datetime.now())
    updated = db.Column(db.DateTime, default=datetime.now())

    attributes: Any = db.relationship("NewsItemAttribute", secondary="news_item_data_news_item_attribute", cascade="all, delete")

    osint_source_id = db.Column(db.String, db.ForeignKey("osint_source.id"), nullable=True, index=True)
    osint_source = db.relationship("OSINTSource")

    def __init__(
        self,
        title,
        source,
        content,
        review=None,
        osint_source_id=None,
        author=None,
        link=None,
        published=datetime.now(),
        collected=datetime.now(),
        hash=None,
        attributes=None,
        id=None,
    ):
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.review = review
        self.source = source
        self.content = content
        self.link = link
        self.author = author
        self.hash = hash or self.get_hash(author, title, link, content)
        self.collected = collected if type(collected) is datetime else datetime.fromisoformat(str(collected))
        self.published = published if type(published) is datetime else datetime.fromisoformat(str(published))
        self.osint_source_id = osint_source_id if OSINTSource.get(osint_source_id) else None
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
    def count_all(cls):
        return cls.query.count()

    @classmethod
    def identical(cls, hash) -> bool:
        return db.session.query(db.exists().where(NewsItemData.hash == hash)).scalar()

    @classmethod
    def find_by_hash(cls, hash):
        return cls.query.filter(NewsItemData.hash == hash).all()

    @classmethod
    def latest_collected(cls):
        news_item_data = cls.query.order_by(db.desc(NewsItemData.collected)).first()
        return news_item_data.collected.isoformat() if news_item_data else ""

    @classmethod
    def get_all_news_items_data(cls, limit: str):
        limit_date = datetime.fromisoformat(limit)
        news_items_data = cls.query.filter(cls.collected > limit_date).all()
        return [news_item_data.to_dict() for news_item_data in news_items_data]

    @classmethod
    def attribute_value_identical(cls, id, value) -> bool:
        return (
            NewsItemAttribute.query.join(NewsItemDataNewsItemAttribute)
            .join(cls)
            .filter(cls.id == id)
            .filter(NewsItemAttribute.value == value)
            .scalar()
        )

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

    def update(self, data) -> tuple[dict, int]:
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


class NewsItem(BaseModel):
    id = db.Column(db.Integer, primary_key=True)

    news_item_data_id = db.Column(db.String, db.ForeignKey("news_item_data.id"), index=True)
    news_item_data: Any = db.relationship("NewsItemData", cascade="all, delete")

    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"), index=True)

    def __init__(self, news_item_data=None):
        self.news_item_data = news_item_data

    @classmethod
    def get_all_with_data(cls, news_item_data_id):
        return cls.query.filter_by(news_item_data_id=news_item_data_id).all()

    @classmethod
    def get_by_filter(cls, filter, user):
        query = cls.query.distinct().group_by(NewsItem.id)
        query = query.join(NewsItemData, NewsItem.news_item_data_id == NewsItemData.id)
        query = query.outerjoin(OSINTSource, NewsItemData.osint_source_id == OSINTSource.id)

        if search := filter.get("search"):
            query = query.filter(
                db.or_(
                    NewsItemData.content.ilike(f"%{search}%"),
                    NewsItemData.review.ilike(f"%{search}%"),
                    NewsItemData.title.ilike(f"%{search}%"),
                )
            )

        if "in_report" in filter and filter["in_report"].lower() != "false":
            query = query.join(
                ReportItemNewsItemAggregate,
                NewsItemAggregate.id == ReportItemNewsItemAggregate.news_item_aggregate_id,
            )

        if "range" in filter and filter["range"].upper() != "ALL":
            filter_range = filter["range"].upper()
            date_limit = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            if filter_range == "DAY":
                date_limit -= timedelta(days=1)

            if filter_range == "WEEK":
                date_limit -= timedelta(days=date_limit.weekday())

            elif filter_range == "MONTH":
                date_limit = date_limit.replace(day=1)

            query = query.filter(NewsItemData.published >= date_limit)

        if "sort" in filter:
            if filter["sort"] == "DATE_DESC":
                query = query.order_by(db.desc(NewsItemData.published), db.desc(NewsItemAggregate.id))

            elif filter["sort"] == "DATE_ASC":
                query = query.order_by(db.asc(NewsItemData.published), db.asc(NewsItemAggregate.id))

        offset = filter.get("offset", 0)
        limit = filter.get("limit", 20)
        return query.offset(offset).limit(limit).all(), query.count()

    @classmethod
    def get_by_filter_json(cls, filter, user):
        news_items, count = cls.get_by_filter(filter, user)
        items = [news_item.to_dict() for news_item in news_items]
        return {"total_count": count, "items": items}, 200

    def allowed_with_acl(self, user: User, require_write_access: bool) -> bool:
        if not RoleBasedAccess.is_enabled():
            return True

        query = RBACQuery(
            user=user,
            resource_id=self.news_item_data.osint_source_id,
            resource_type=ItemType.OSINT_SOURCE,
            require_write_access=require_write_access,
        )

        access = RoleBasedAccessService.user_has_access_to_resource(query)
        if not access:
            logger.warning(f"User {user.id} has no access to resource {self.news_item_data.osint_source_id}")
        return access

    @classmethod
    def update(cls, news_item_id, data, user_id):
        news_item = cls.get(news_item_id)
        if not news_item:
            return {"error": f"NewsItem with id: {news_item_id} not found"}, 404
        news_item.news_item_data.update(data)

        if story := NewsItemAggregate.get(news_item.news_item_aggregate_id):
            story.update_status()
        db.session.commit()

        return {"message": "success"}, 200

    @classmethod
    def delete(cls, news_item_id):
        news_item = cls.get(news_item_id)
        if not news_item:
            return {"error": f"NewsItem with id: {news_item_id} not found"}, 404
        aggregate_id = news_item.news_item_aggregate_id
        aggregate = NewsItemAggregate.get(aggregate_id)
        if not aggregate:
            return {"error": f"Aggregate with id: {id} not found"}, 404

        if NewsItemAggregate.is_assigned_to_report([aggregate_id]):
            return {"error": f"aggregate with: {aggregate_id} assigned to a report"}, 400

        aggregate.news_items.remove(news_item)
        cls.delete_item(news_item)
        aggregate.update_status()
        db.session.commit()

        return {"message": "success"}, 200

    @classmethod
    def delete_item(cls, news_item):
        db.session.delete(news_item)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["news_item_data"] = self.news_item_data.to_dict()
        return data


class NewsItemVote(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    like = db.Column(db.Boolean, default=False)
    dislike = db.Column(db.Boolean, default=False)
    item_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=True)

    def __init__(self, item_id, user_id, like=False, dislike=False):
        self.id = None
        self.item_id = item_id
        self.user_id = user_id
        self.like = like
        self.dislike = dislike

    @classmethod
    def get_by_filter(cls, item_id, user_id):
        return cls.query.filter_by(item_id=item_id, user_id=user_id).first()

    @classmethod
    def get_user_vote(cls, item_id, user_id):
        if vote := cls.get_by_filter(item_id, user_id):
            return {"like": vote.like, "dislike": vote.dislike}
        return {"like": False, "dislike": False}


class NewsItemAggregate(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    title: Any = db.Column(db.String())
    description: Any = db.Column(db.String())
    created: Any = db.Column(db.DateTime)

    read: Any = db.Column(db.Boolean, default=False)
    important: Any = db.Column(db.Boolean, default=False)

    likes: Any = db.Column(db.Integer, default=0)
    dislikes: Any = db.Column(db.Integer, default=0)
    relevance: Any = db.Column(db.Integer, default=0)

    comments: Any = db.Column(db.String(), default="")
    summary: Any = db.Column(db.Text, default="")
    news_items: Any = db.relationship("NewsItem")
    attributes: Any = db.relationship("NewsItemAttribute", secondary="news_item_aggregate_news_item_attribute")

    def __init__(
        self,
        title,
        description="",
        created=datetime.now(),
        read=False,
        important=False,
        summary="",
        comments="",
        attributes=None,
        news_items=None,
    ):
        self.title = title
        self.description = description
        self.created = created
        self.read = read
        self.important = important
        self.summary = summary
        self.comments = comments
        self.news_items = self.load_news_items(news_items)
        if attributes:
            self.attributes = NewsItemAttribute.load_multiple(attributes)

    def load_news_items(self, news_items):
        if all(isinstance(item, int) for item in news_items):
            return [NewsItem.get(item_id) for item_id in news_items]
        elif all(isinstance(item, NewsItem) for item in news_items):
            return news_items
        return []

    @classmethod
    def get_json(cls, aggregate_id: int, user: User):
        item = cls.get(aggregate_id)

        if not item:
            return {"error": f"NewsItemAggregate with id: {aggregate_id} not found"}, 404

        data = item.to_dict()
        data["in_reports_count"] = ReportItemNewsItemAggregate.count(item.id)
        data["user_vote"] = NewsItemVote.get_user_vote(item.id, user.id)

        return data

    @classmethod
    def get_story_clusters(cls, days: int = 7, limit: int = 10):
        start_date = datetime.now() - timedelta(days=days)
        clusters = (
            cls.query.join(NewsItem)
            .join(NewsItemData)
            .filter(NewsItemData.published >= start_date)
            .group_by(cls.title, cls.id)
            .order_by(func.count().desc())
            .having(func.count() > 1)
            .limit(limit)
            .all()
        )
        return [
            {
                "name": cluster.title,
                "size": len(cluster.news_items),
                "published": [ni.news_item_data.published.isoformat() for ni in cluster.news_items],
            }
            for cluster in clusters
        ]

    @classmethod
    def _add_filters_to_query(cls, filter_args: dict, query):
        query = query.join(NewsItem, NewsItem.news_item_aggregate_id == NewsItemAggregate.id)
        query = query.join(NewsItemData, NewsItem.news_item_data_id == NewsItemData.id)
        query = query.join(OSINTSource, NewsItemData.osint_source_id == OSINTSource.id)

        if filter_args.get("group"):
            query = query.outerjoin(OSINTSourceGroupOSINTSource, OSINTSource.id == OSINTSourceGroupOSINTSource.osint_source_id)
            query = query.outerjoin(OSINTSourceGroup, OSINTSourceGroupOSINTSource.osint_source_group_id == OSINTSourceGroup.id)

        if group := filter_args.get("group"):
            query = query.filter(OSINTSourceGroup.id.in_(group))

        if source := filter_args.get("source"):
            query = query.filter(OSINTSource.id.in_(source))

        if search := filter_args.get("search"):
            search = search.strip()
            if search.startswith('"') and search.endswith('"'):
                words = [search[1:-1]]
            else:
                words = search.split()
            query = query.join(
                NewsItemAggregateSearchIndex,
                NewsItemAggregate.id == NewsItemAggregateSearchIndex.news_item_aggregate_id,
            )
            for word in words:
                query = query.filter(NewsItemAggregateSearchIndex.data.ilike(f"%{word}%"))

        read = filter_args.get("read", "").lower()
        if read == "true":
            query = query.filter(NewsItemAggregate.read)
        if read == "false":
            query = query.filter(NewsItemAggregate.read == false())

        important = filter_args.get("important", "").lower()
        if important == "true":
            query = query.filter(NewsItemAggregate.important)
        if important == "false":
            query = query.filter(NewsItemAggregate.important == false())

        relevant = filter_args.get("relevant", "").lower()
        if relevant == "true":
            query = query.filter(NewsItemAggregate.relevance > 0)
        if relevant == "false":
            query = query.filter(NewsItemAggregate.relevance <= 0)

        in_report = filter_args.get("in_report", "").lower()
        if in_report == "true":
            query = query.join(
                ReportItemNewsItemAggregate,
                NewsItemAggregate.id == ReportItemNewsItemAggregate.news_item_aggregate_id,
            )
        if in_report == "false":
            query = query.outerjoin(
                ReportItemNewsItemAggregate,
                NewsItemAggregate.id == ReportItemNewsItemAggregate.news_item_aggregate_id,
            )
            query = query.filter(ReportItemNewsItemAggregate.news_item_aggregate_id == null())

        if tags := filter_args.get("tags"):
            for tag in tags:
                alias = orm.aliased(NewsItemTag)
                query = query.join(alias, NewsItemAggregate.id == alias.n_i_a_id).filter(or_(alias.name == tag, alias.tag_type == tag))

        if filter_range := filter_args.get("range", "").lower():
            date_limit = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if filter_range in ["day", "week", "month"]:
                if filter_range == "day":
                    date_limit -= timedelta(days=1)

                elif filter_range == "week":
                    date_limit -= timedelta(days=date_limit.weekday())

                elif filter_range == "month":
                    date_limit = date_limit.replace(day=1)

            elif filter_range.startswith("last") and filter_range[4:].isdigit():
                days = int(filter_range[4:])
                date_limit -= timedelta(days=days)

            query = query.filter(NewsItemData.published >= date_limit)

        if timefrom := filter_args.get("timefrom"):
            query = query.filter(NewsItemData.published >= datetime.fromisoformat(timefrom))

        if timeto := filter_args.get("timeto"):
            query = query.filter(NewsItemData.published <= datetime.fromisoformat(timeto))

        return query

    @classmethod
    def _add_sorting_to_query(cls, filter_args: dict, query):
        if sort := filter_args.get("sort", "date_desc").lower():
            if sort == "date_desc":
                query = query.group_by(NewsItemData.published).order_by(db.desc(NewsItemData.published), db.desc(cls.id))

            elif sort == "date_asc":
                query = query.group_by(NewsItemData.published).order_by(db.asc(NewsItemData.published), db.asc(cls.id))

            elif sort == "relevance_desc":
                query = query.order_by(db.desc(cls.relevance), db.desc(cls.id))

            elif sort == "relevance_asc":
                query = query.order_by(db.asc(cls.relevance), db.asc(cls.id))

            elif sort == "source":
                query = query.order_by(db.desc(OSINTSource.name), db.desc(cls.id))

        return query

    @classmethod
    def _add_paging_to_query(cls, filter_args: dict, query):
        if offset := filter_args.get("offset"):
            query = query.offset(offset)
        if limit := filter_args.get("limit"):
            query = query.limit(limit)
        return query

    @classmethod
    def _add_ACL_check(cls, query, user: User):
        rbac = RBACQuery(user=user, resource_type=ItemType.OSINT_SOURCE)
        return RoleBasedAccessService.filter_query_with_acl(query, rbac)

    @classmethod
    def _add_TLP_check(cls, query, user: User):
        return RoleBasedAccessService.filter_query_with_tlp(query, user)

    @classmethod
    def get_by_filter(cls, filter_args: dict, user: User | None = None):
        query = cls.query.distinct().group_by(NewsItemAggregate.id)
        query = cls._add_filters_to_query(filter_args, query)

        if user:
            query = cls._add_ACL_check(query, user)
            query = cls._add_TLP_check(query, user)

        query = cls._add_sorting_to_query(filter_args, query)
        paged_query = cls._add_paging_to_query(filter_args, query)

        if filter_args.get("no_count", False):
            return paged_query.all(), 0
        return paged_query.all(), query.count()

    @classmethod
    def get_date_counts(cls, news_items: list[dict[str, Any]]) -> Counter:
        return Counter(datetime.fromisoformat(news_item["news_item_data"]["published"]).strftime("%d-%m") for news_item in news_items)

    @classmethod
    def get_max_item_count(cls, news_items: list[dict[str, Any]]) -> int:
        date_counts = cls.get_date_counts(news_items)
        return max(date_counts.values(), default=0)

    @classmethod
    def get_item_dict(cls, news_item_aggregate: Any, user: Any) -> dict[str, Any]:
        item = news_item_aggregate.to_dict()
        item["in_reports_count"] = ReportItemNewsItemAggregate.count(news_item_aggregate.id)
        item["user_vote"] = NewsItemVote.get_user_vote(news_item_aggregate.id, user.id)
        return item

    @classmethod
    def get_by_filter_json(cls, filter_args, user):
        news_item_aggregates, count = cls.get_by_filter(filter_args=filter_args, user=user)
        items = []
        max_item_count = 0

        for news_item_aggregate in news_item_aggregates:
            item = cls.get_item_dict(news_item_aggregate, user)

            current_max_item = cls.get_max_item_count(item["news_items"])
            max_item_count = max(max_item_count, current_max_item)

            items.append(item)

        if filter_args.get("no_count", False):
            return {"items": items, "max_item": max_item_count}, 200

        return {"total_count": count, "items": items, "max_item": max_item_count}

    @classmethod
    def get_for_worker(cls, filter_args: dict) -> list[dict[str, Any]]:
        news_item_aggregates, _ = cls.get_by_filter(filter_args=filter_args)
        return [news_item_aggregate.to_worker_dict() for news_item_aggregate in news_item_aggregates]

    @classmethod
    def create_new(cls, news_item_data: NewsItemData):
        news_item = NewsItem.add({"news_item_data": news_item_data})

        aggregate = NewsItemAggregate.add(
            {
                "title": news_item_data.title,
                "description": news_item_data.review or news_item_data.content,
                "created": news_item_data.published,
                "news_items": [news_item],
            }
        )
        NewsItemAggregateSearchIndex.prepare(aggregate)
        aggregate.update_tlp()

        db.session.commit()

        return aggregate

    @classmethod
    def add_news_items(cls, news_items_data_list):
        news_items_data = NewsItemData.load_multiple(news_items_data_list)
        ids = []
        try:
            for news_item_data in news_items_data:
                if not NewsItemData.identical(news_item_data.hash):
                    db.session.add(news_item_data)
                    ids.append(cls.create_new(news_item_data).id)
            db.session.commit()
        except Exception as e:
            return {"error": f"Failed to add news items: {e}"}, 400

        return {"message": f"Added {len(ids)} news items", "ids": ids}, 200

    @classmethod
    def update(cls, id, data, user=None):
        aggregate = cls.get(id)
        if not aggregate:
            return {"error": "Story not found", "id": f"{id}"}, 404

        if "vote" in data and user:
            aggregate.vote(data["vote"], user.id)

        if "important" in data:
            aggregate.important = data["important"]

        if "read" in data:
            aggregate.read = data["read"]

        if "title" in data:
            aggregate.title = data["title"]

        if "description" in data:
            aggregate.description = data["description"]

        if "comments" in data:
            aggregate.comments = data["comments"]

        if "tags" in data:
            cls.reset_tags(id)
            cls.update_tags(id, data["tags"])

        if "summary" in data:
            cls.summary = data["summary"]

        if "attributes" in data:
            aggregate.update_attributes(data["attributes"])

        aggregate.update_status()
        db.session.commit()
        return {"message": "Story updated Successful", "id": f"{id}"}, 200

    def update_attributes(self, attributes):
        self.attributes = []
        for attribute in attributes:
            self.set_atrribute_by_key(key=attribute["key"], value=attribute["value"])

    def set_atrribute_by_key(self, key, value):
        if not (attribute := NewsItemAttribute.get_by_key(self.attributes, key)):
            attribute = NewsItemAttribute(key=key, value=value)
            self.attributes.append(attribute)
        else:
            attribute.value = value

    def vote(self, vote_data, user_id):
        if not (vote := NewsItemVote.get_by_filter(item_id=self.id, user_id=user_id)):
            vote = self.create_new_vote(vote, user_id, vote_data)

        if vote.like and vote_data == "like":
            vote = self.remove_like_vote(vote)
        elif vote.dislike and vote_data == "dislike":
            vote = self.remove_dislike_vote(vote)
        elif vote.like and vote_data == "dislike":
            vote = self.change_like_to_dislike(vote)
        elif vote.dislike and vote_data == "like":
            vote = self.change_dislike_to_like(vote)
        elif vote_data == "like":
            self.likes = self.likes + 1
            self.relevance = self.relevance + 1
            vote.like = True
        elif vote_data == "dislike":
            self.dislikes = self.dislikes + 1
            self.relevance = self.relevance - 1
            vote.dislike = True

        db.session.commit()
        return vote

    def remove_like_vote(self, vote):
        self.likes = self.likes - 1
        self.relevance = self.relevance - 1
        vote.like = False
        return vote

    def remove_dislike_vote(self, vote):
        self.dislikes = self.dislikes - 1
        self.relevance = self.relevance + 1
        vote.dislike = False
        return vote

    def change_like_to_dislike(self, vote):
        self.likes = self.likes - 1
        self.dislikes = self.dislikes + 1
        self.relevance = self.relevance - 2
        vote.like = False
        vote.dislike = True
        return vote

    def change_dislike_to_like(self, vote):
        self.likes = self.likes + 1
        self.dislikes = self.dislikes - 1
        self.relevance = self.relevance + 2
        vote.like = True
        vote.dislike = False
        return vote

    def create_new_vote(self, vote, user_id, vote_data):
        vote = NewsItemVote(item_id=self.id, user_id=user_id)
        db.session.add(vote)
        return vote

    @classmethod
    def delete_by_id(cls, aggregate_id, user):
        aggregate = cls.get(aggregate_id)
        if not aggregate:
            return {"error": f"Aggregate with id: {aggregate_id} not found"}, 404

        if cls.is_assigned_to_report([aggregate_id]):
            return {"error": f"aggregate with: {aggregate_id} assigned to a report"}, 500

        for news_item in aggregate.news_items:
            if news_item.allowed_with_acl(user, True):
                aggregate.news_items.remove(news_item)
                NewsItem.delete_item(news_item)
            else:
                logger.debug(f"User {user.id} not allowed to remove news item {news_item.id}")
                return {"error": f"User {user.id} not allowed to remove news item {news_item.id}"}, 403

        aggregate.update_status()

        db.session.commit()

        return {"message": "success"}, 200

    def delete(self, user):
        return self.delete_by_id(self.id, user)

    @classmethod
    def is_assigned_to_report(cls, aggregate_ids: list) -> bool:
        return any(ReportItemNewsItemAggregate.assigned(aggregate_id) for aggregate_id in aggregate_ids)

    @classmethod
    def reset_tags(cls, news_item_aggregate_id: int) -> tuple[dict, int]:
        try:
            n_i_a = cls.get(news_item_aggregate_id)
            if not n_i_a:
                logger.error(f"Story {news_item_aggregate_id} not found")
                return {"error": "not_found"}, 404

            n_i_a.tags = []
            db.session.commit()
            return {"message": "success"}, 200
        except Exception as e:
            logger.log_debug_trace("Reset News Item Tags Failed")
            return {"error": str(e)}, 500

    @classmethod
    def update_tags(cls, news_item_aggregate_id: int, tags: list | dict, bot_type: str = "") -> tuple[dict, int]:
        try:
            n_i_a = cls.get(news_item_aggregate_id)
            if not n_i_a:
                logger.error(f"Story {news_item_aggregate_id} not found")
                return {"error": "not_found"}, 404

            new_tags = NewsItemTag.parse_tags(tags)
            for tag_name, new_tag in new_tags.items():
                if tag_name in [tag.name for tag in n_i_a.tags]:
                    continue
                if existing_tag := NewsItemTag.find_by_name(tag_name):
                    new_tag.name = existing_tag.name
                    new_tag.tag_type = existing_tag.tag_type
                n_i_a.tags.append(new_tag)
            if bot_type:
                n_i_a.attributes.append(NewsItemAttribute(key=bot_type, value=f"{len(new_tags)}"))
            db.session.commit()
            return {"message": "success"}, 200
        except Exception as e:
            logger.log_debug_trace("Update News Item Tags Failed")
            return {"error": str(e)}, 500

    @classmethod
    def check_tags_by_source(cls, source_id: int) -> tuple[dict, int]:
        try:
            query = cls._add_filters_to_query({"source": source_id}, cls.query)
            items = query.all()

            if not items:
                return {"error": "no items found"}, 404

            common_tags = {tag.name for tag in items[0].tags}

            for item in items[1:]:
                item_tags = {tag.name for tag in item.tags}
                common_tags.intersection_update(item_tags)

                if not common_tags:
                    break

            return {"common_tags": list(common_tags)}, 200

        except Exception:
            logger.log_debug_trace("Get News Item Tags Failed")
            return {"error": "get failed"}, 500

    @classmethod
    def group_multiple_aggregate(cls, aggregate_id_list: list[list[int]]):
        results = [cls.group_aggregate(aggregate_ids) for aggregate_ids in aggregate_id_list]
        if any(result[1] == 500 for result in results):
            return {"error": "grouping failed"}, 500
        return {"message": "success"}, 200

    @classmethod
    def move_items_to_aggregate(cls, aggregate_id: int, news_item_ids: list[int], user: User | None = None):
        try:
            aggregate = cls.get(aggregate_id)
            if not aggregate:
                return {"error": "not_found"}, 404
            for item in news_item_ids:
                news_item = NewsItem.get(item)
                if not news_item:
                    continue
                if user is None or news_item.allowed_with_acl(user, True):
                    aggregate.news_items.append(news_item)
                    aggregate.relevance += news_item.relevance + 1
                    aggregate.add(aggregate)
                    aggregate.update_status()
            cls.update_aggregates(aggregate)
            db.session.commit()
            return {"message": "success"}, 200
        except Exception:
            logger.log_debug_trace("Grouping News Item Aggregates Failed")
            return {"error": "grouping failed"}, 500

    @classmethod
    def group_aggregate(cls, aggregate_ids: list[int], user: User | None = None):
        try:
            if len(aggregate_ids) < 2 or any(not isinstance(a_id, int) for a_id in aggregate_ids):
                return {"error": "at least two aggregate ids needed"}, 404
            first_aggregate = NewsItemAggregate.get(aggregate_ids.pop(0))
            if not first_aggregate:
                return {"error": "not_found"}, 404
            processed_aggregates = {first_aggregate}
            for item in aggregate_ids:
                aggregate = NewsItemAggregate.get(item)
                if not aggregate:
                    continue

                first_aggregate.tags = list({tag.name: tag for tag in first_aggregate.tags + aggregate.tags}.values())
                for news_item in aggregate.news_items[:]:
                    if user is None or news_item.allowed_with_acl(user, True):
                        first_aggregate.news_items.append(news_item)
                        first_aggregate.relevance += 1
                        aggregate.news_items.remove(news_item)
                processed_aggregates.add(aggregate)

            cls.update_aggregates(processed_aggregates)
            db.session.commit()
            return {"message": "success"}, 200
        except Exception:
            logger.log_debug_trace("Grouping News Item Aggregates Failed")
            return {"error": "grouping failed"}, 500

    @classmethod
    def ungroup_multiple_stories(cls, story_ids: list[int], user: User | None = None):
        results = [cls.ungroup_story(story_id, user) for story_id in story_ids]
        if any(result[1] == 500 for result in results):
            return {"error": "grouping failed"}, 400
        return {"message": "success"}, 200

    @classmethod
    def ungroup_story(cls, story_id: int, user: User | None = None):
        try:
            story = NewsItemAggregate.get(story_id)
            if not story:
                return {"error": "not_found"}, 404
            for news_item in story.news_items[:]:
                if user is None or news_item.allowed_with_acl(user, True):
                    cls.create_single_aggregate(news_item)
            cls.update_aggregates({story})
            db.session.commit()
            return {"message": "success"}, 200
        except Exception:
            logger.log_debug_trace("Grouping News Item Aggregates Failed")
            return {"error": "ungroup failed"}, 500

    @classmethod
    def remove_news_items_from_story(cls, newsitem_ids: list, user: User | None = None):
        try:
            processed_aggregates = set()
            for item in newsitem_ids:
                news_item = NewsItem.get(item)
                if not news_item:
                    continue
                if not news_item.allowed_with_acl(user, True):
                    continue
                aggregate = NewsItemAggregate.get(news_item.news_item_aggregate_id)
                if not aggregate:
                    continue
                aggregate.news_items.remove(news_item)
                processed_aggregates.add(aggregate)
                cls.create_single_aggregate(news_item)
            db.session.commit()
            cls.update_aggregates(processed_aggregates)
            return {"message": "success"}, 200
        except Exception:
            logger.log_debug_trace("Grouping News Item Aggregates Failed")
            return {"error": "ungroup failed"}, 500

    @classmethod
    def update_aggregates(cls, aggregates: set):
        for aggregate in aggregates:
            try:
                aggregate.update_status()
            except Exception:
                logger.exception("Update Aggregates Failed")

    @classmethod
    def create_single_aggregate(cls, news_item):
        new_aggregate = NewsItemAggregate(
            title=news_item.news_item_data.title,
            created=news_item.news_item_data.published,
            description=news_item.news_item_data.review or news_item.news_item_data.content,
            news_items=[news_item.id],
        )
        db.session.add(new_aggregate)
        db.session.commit()

        NewsItemAggregateSearchIndex.prepare(new_aggregate)
        new_aggregate.update_status()

    def update_status(self):
        if len(self.news_items) == 0:
            NewsItemAggregateSearchIndex.remove(self)
            NewsItemTag.remove_by_aggregate(self)
            db.session.delete(self)
            logger.info(f"Deleting empty aggregate - 'ID': {self.id}")
            return

        self.update_tlp()

    def update_tlp(self):
        highest_tlp = None
        for news_item in self.news_items:
            if tlp_level := news_item.news_item_data.get_tlp():
                tlp_level_enum = TLPLevel(tlp_level)
                if highest_tlp is None or tlp_level_enum > highest_tlp:
                    highest_tlp = tlp_level_enum

        if highest_tlp:
            logger.debug(f"Setting TLP level {highest_tlp} for aggregate {self.id}")
            NewsItemAttribute.set_or_update(self.attributes, "TLP", highest_tlp.value)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["news_items"] = [news_item.to_dict() for news_item in self.news_items]
        data["tags"] = [tag.to_small_dict() for tag in self.tags]
        if attributes := self.attributes:
            data["attributes"] = [news_item_attribute.to_dict() for news_item_attribute in attributes]
        return data

    def to_worker_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["news_items"] = [news_item.to_dict() for news_item in self.news_items]
        data["tags"] = {tag.name: tag.to_dict() for tag in self.tags}
        if attributes := self.attributes:
            data["attributes"] = [news_item_attribute.to_dict() for news_item_attribute in attributes]
        return data


class NewsItemAggregateSearchIndex(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    data: Any = db.Column(db.String)
    news_item_aggregate_id: Any = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"), index=True)

    def __init__(self, story_id, data=None):
        self.news_item_aggregate_id = story_id
        self.data = data or ""

    @classmethod
    def remove(cls, aggregate: "NewsItemAggregate"):
        search_index = db.session.execute(db.select(cls).filter_by(news_item_aggregate_id=aggregate.id)).scalar_one_or_none()
        if search_index is not None:
            db.session.delete(search_index)
            db.session.commit()

    @classmethod
    def prepare(cls, aggregate: "NewsItemAggregate"):
        search_index = db.session.execute(db.select(cls).filter_by(news_item_aggregate_id=aggregate.id)).scalar_one_or_none()
        if search_index is None:
            search_index = NewsItemAggregateSearchIndex(aggregate.id)
            db.session.add(search_index)

        data_components = [
            aggregate.title,
            aggregate.description,
            aggregate.comments,
            aggregate.summary,
        ]

        for news_item in aggregate.news_items:
            data_components.extend(
                [
                    news_item.news_item_data.title,
                    news_item.news_item_data.review,
                    news_item.news_item_data.content,
                    news_item.news_item_data.author,
                    news_item.news_item_data.link,
                ]
            )

            data_components.extend([attribute.value for attribute in news_item.news_item_data.attributes])

        search_index.data = " ".join(data_components).lower()
        db.session.commit()


class NewsItemAttribute(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    key: Any = db.Column(db.String(), nullable=False)
    value: Any = db.Column(db.String(), nullable=False)
    binary_mime_type = db.Column(db.String())
    binary_data = orm.deferred(db.Column(db.LargeBinary))
    created = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, key, value, binary_mime_type=None, binary_value=None, id=None):
        self.id = id
        self.key = key
        self.value = value
        self.binary_mime_type = binary_mime_type

        with contextlib.suppress(Exception):
            if binary_value:
                self.binary_data = base64.b64decode(binary_value)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data.pop("binary_mime_type", None)
        data.pop("binary_data", None)
        return data

    @classmethod
    def get_by_key(cls, attributes: list["NewsItemAttribute"], key: str) -> "NewsItemAttribute | None":
        return next((attribute for attribute in attributes if attribute.key == key), None)

    @classmethod
    def set_or_update(cls, attributes: list["NewsItemAttribute"], key: str, value: str) -> list["NewsItemAttribute"]:
        if not (attribute := cls.get_by_key(attributes, key)):
            attributes.append(cls(key=key, value=value))
        else:
            attribute.value = value
        return attributes

    @classmethod
    def get_tlp_level(cls, attributes: list["NewsItemAttribute"]) -> TLPLevel | None:
        return TLPLevel(cls.get_by_key(attributes, "TLP"))


class NewsItemDataNewsItemAttribute(BaseModel):
    news_item_data_id = db.Column(db.String, db.ForeignKey("news_item_data.id"), primary_key=True)
    news_item_attribute_id = db.Column(db.Integer, db.ForeignKey("news_item_attribute.id", ondelete="CASCADE"), primary_key=True)


class NewsItemAggregateNewsItemAttribute(BaseModel):
    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"), primary_key=True)
    news_item_attribute_id = db.Column(db.Integer, db.ForeignKey("news_item_attribute.id", ondelete="CASCADE"), primary_key=True)


class ReportItemNewsItemAggregate(BaseModel):
    report_item_id = db.Column(db.String(64), db.ForeignKey("report_item.id", ondelete="CASCADE"), primary_key=True)
    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"), primary_key=True)

    @classmethod
    def assigned(cls, aggregate_id):
        return db.session.query(db.exists().where(ReportItemNewsItemAggregate.news_item_aggregate_id == aggregate_id)).scalar()

    @classmethod
    def count(cls, aggregate_id):
        return cls.query.filter_by(news_item_aggregate_id=aggregate_id).count()
