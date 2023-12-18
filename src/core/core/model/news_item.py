import uuid
import base64
import contextlib
from datetime import datetime, timedelta
from typing import Any, Optional
from sqlalchemy import orm, and_, or_, func
from enum import StrEnum, auto
from collections import Counter
import hashlib

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.managers.log_manager import logger
from core.model.user import User
from core.model.acl_entry import ACLEntry, ItemType
from core.model.osint_source import OSINTSourceGroup, OSINTSource, OSINTSourceGroupOSINTSource


class NewsItemData(BaseModel):
    id = db.Column(db.String(64), primary_key=True)
    hash = db.Column(db.String())

    title = db.Column(db.String())
    review = db.Column(db.String())
    author = db.Column(db.String())
    source = db.Column(db.String())
    link = db.Column(db.String())
    language = db.Column(db.String())
    content = db.Column(db.String())
    collected: Any = db.Column(db.DateTime)
    published: Any = db.Column(db.DateTime, default=datetime.now())
    updated = db.Column(db.DateTime, default=datetime.now())

    attributes = db.relationship("NewsItemAttribute", secondary="news_item_data_news_item_attribute", cascade="all, delete")

    osint_source_id = db.Column(db.String, db.ForeignKey("osint_source.id"), nullable=True)
    osint_source = db.relationship("OSINTSource")

    def __init__(
        self,
        title,
        review,
        source,
        content,
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

    @classmethod
    def update_news_item_lang(cls, news_item_id, lang):
        news_item = cls.get(news_item_id)
        if news_item is None:
            return {"error": "Invalid news item id"}, 400
        news_item.language = lang
        db.session.commit()
        return {"message": "Language updated"}, 200

    @classmethod
    def update_news_item_attributes(cls, news_item_id, attributes) -> tuple[dict, int]:
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


class NewsItem(BaseModel):
    id = db.Column(db.Integer, primary_key=True)

    read: Any = db.Column(db.Boolean, default=False)
    important: Any = db.Column(db.Boolean, default=False)

    likes: Any = db.Column(db.Integer, default=0)
    dislikes: Any = db.Column(db.Integer, default=0)
    relevance: Any = db.Column(db.Integer, default=0)

    news_item_data_id = db.Column(db.String, db.ForeignKey("news_item_data.id"))
    news_item_data: Any = db.relationship("NewsItemData", cascade="all, delete")

    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"))

    def __init__(self, read=False, important=False, news_item_data=None):
        self.read = read
        self.important = important
        self.news_item_data = news_item_data

    @classmethod
    def get_all_with_data(cls, news_item_data_id):
        return cls.query.filter_by(news_item_data_id=news_item_data_id).all()

    @classmethod
    def get_by_filter(cls, filter, user):
        query = cls.query.distinct().group_by(NewsItem.id)
        query = query.join(NewsItemData, NewsItem.news_item_data_id == NewsItemData.id)
        query = query.outerjoin(OSINTSource, NewsItemData.osint_source_id == OSINTSource.id)

        query = query.outerjoin(
            ACLEntry,
            and_(
                NewsItemData.osint_source_id == ACLEntry.item_id,
                ACLEntry.item_type == ItemType.OSINT_SOURCE,
            ),
        )

        query = ACLEntry.apply_query(query, user, True, False, False)

        if search := filter.get("search"):
            query = query.filter(
                db.or_(
                    NewsItemData.content.ilike(f"%{search}%"),
                    NewsItemData.review.ilike(f"%{search}%"),
                    NewsItemData.title.ilike(f"%{search}%"),
                )
            )

        if "read" in filter and filter["read"].lower() != "false":
            query = query.filter(NewsItem.read is False)

        if "important" in filter and filter["important"].lower() != "false":
            query = query.filter(NewsItem.important)

        if "relevant" in filter and filter["relevant"].lower() != "false":
            query = query.filter(NewsItem.likes > 0)

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

            query = query.filter(NewsItemData.collected >= date_limit)

        if "sort" in filter:
            if filter["sort"] == "DATE_DESC":
                query = query.order_by(db.desc(NewsItemData.collected), db.desc(NewsItemAggregate.id))

            elif filter["sort"] == "DATE_ASC":
                query = query.order_by(db.asc(NewsItemData.collected), db.asc(NewsItemAggregate.id))

            elif filter["sort"] == "RELEVANCE_DESC":
                query = query.order_by(db.desc(NewsItem.relevance), db.desc(NewsItem.id))

            elif filter["sort"] == "RELEVANCE_ASC":
                query = query.order_by(db.asc(NewsItem.relevance), db.asc(NewsItem.id))

        offset = filter.get("offset", 0)
        limit = filter.get("limit", 20)
        return query.offset(offset).limit(limit).all(), query.count()

    @classmethod
    def get_by_filter_json(cls, filter, user):
        news_items, count = cls.get_by_filter(filter, user)
        items = [news_item.to_dict() for news_item in news_items]
        return {"total_count": count, "items": items}, 200

    @classmethod
    def get_all_by_group_and_source_query(cls, group_id, source_id, time_limit):
        query = cls.query.join(NewsItemData, NewsItemData.id == NewsItem.news_item_data_id)
        query = query.filter(
            NewsItemData.osint_source_id == source_id,
            NewsItemData.collected >= time_limit,
        )
        query = query.join(NewsItemAggregate, NewsItemAggregate.id == NewsItem.news_item_aggregate_id)
        groups = OSINTSourceGroup.get_for_osint_source(NewsItemData.osint_source_id)
        if groups:
            group = groups[0]
            query = query.filter(group.id == group_id)
        return query

    def allowed_with_acl(self, user: User, see, access, modify):
        query = db.session.query(NewsItem.id).distinct().group_by(NewsItem.id).filter(NewsItem.id == self.id)

        query = query.join(NewsItemData, NewsItem.news_item_data_id == NewsItemData.id)
        query = query.join(OSINTSource, NewsItemData.osint_source_id == OSINTSource.id)

        query = query.outerjoin(
            ACLEntry,
            and_(
                NewsItemData.osint_source_id == ACLEntry.item_id,
                ACLEntry.item_type == ItemType.OSINT_SOURCE,
            ),
        )

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    def vote(self, vote_data, user_id) -> "NewsItemVote":
        if vote := NewsItemVote.get_by_filter(item_id=self.id, user_id=user_id, item_type="NEWS_ITEM"):
            if vote_data > 0:
                self.update_like_vote(vote)
            else:
                self.update_dislike_vote(vote)
        else:
            vote = self.create_new_vote(vote, user_id)

        self.news_item_data.updated = datetime.now()
        return vote

    def create_new_vote(self, vote, user_id):
        vote = NewsItemVote(item_id=self.id, user_id=user_id, item_type="NEWS_ITEM")
        db.session.add(vote)
        return vote

    def update_like_vote(self, vote):
        self.likes += 1
        self.relevance += 1
        vote.like = not vote.like

    def update_dislike_vote(self, vote):
        self.dislikes += 1
        self.relevance -= 1
        vote.dislike = not vote.dislike

    @classmethod
    def update(cls, news_item_id, data, user_id):
        news_item = cls.get(news_item_id)
        if not news_item:
            return {"error": f"NewsItem with id: {news_item_id} not found"}, 404
        news_item.update_status(data, user_id)

        NewsItemAggregate.update_status(news_item.news_item_aggregate_id)
        db.session.commit()

        return {"message": "success"}, 200

    def update_status(self, data, user_id):
        if "vote" in data:
            self.vote(data["vote"], user_id)

        if "read" in data:
            self.read = not self.read

        if "important" in data:
            self.important = not self.important

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
        NewsItemAggregate.update_status(aggregate_id)
        db.session.commit()

        return {"message": "success"}, 200

    @classmethod
    def delete_item(cls, news_item):
        NewsItemVote.delete_all(item_id=news_item.id, item_type="NEWS_ITEM")
        db.session.delete(news_item)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["news_item_data"] = self.news_item_data.to_dict()
        return data


class NewsItemTypes(StrEnum):
    AGGREGATE = auto()
    NEWS_ITEM = auto()


class NewsItemVote(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    like = db.Column(db.Boolean, default=False)
    dislike = db.Column(db.Boolean, default=False)
    item_id = db.Column(db.Integer)
    item_type = db.Column(db.Enum(NewsItemTypes))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=True)

    def __init__(self, item_id, user_id, item_type, like=False, dislike=False):
        self.id = None
        self.item_id = item_id
        self.user_id = user_id
        self.item_type = item_type
        self.like = like
        self.dislike = dislike

    @classmethod
    def get_by_filter(cls, item_id, user_id, item_type):
        return cls.query.filter_by(item_id=item_id, user_id=user_id, item_type=item_type).first()

    @classmethod
    def delete_all(cls, item_id, item_type):
        cls.query.filter_by(item_id=item_id, item_type=item_type).delete()
        db.session.commit()

    @classmethod
    def get_user_vote(cls, item_id, user_id, item_type):
        if vote := cls.get_by_filter(item_id, user_id, item_type):
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
    news_item_attributes: Any = db.relationship("NewsItemAttribute", secondary="news_item_aggregate_news_item_attribute")

    def __init__(self, title, description="", created=datetime.now(), read=False, important=False, summary="", comments="", news_items=None):
        self.title = title
        self.description = description
        self.created = created
        self.read = read
        self.important = important
        self.summary = summary
        self.comments = comments
        self.news_items = [NewsItem.get(item_id) for item_id in news_items] if news_items else []

    @classmethod
    def get_json(cls, aggregate_id: int, user: User):
        item = cls.get(aggregate_id)

        if not item:
            return {"error": f"NewsItemAggregate with id: {aggregate_id} not found"}, 404

        data = item.to_dict()
        data["in_reports_count"] = ReportItemNewsItemAggregate.count(item.id)
        data["user_vote"] = NewsItemVote.get_user_vote(item.id, user.id, "AGGREGATE")

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
        if filter_args.get("source") or filter_args.get("group"):
            query = query.join(NewsItem, NewsItem.news_item_aggregate_id == NewsItemAggregate.id)
            query = query.join(NewsItemData, NewsItem.news_item_data_id == NewsItemData.id)
            query = query.outerjoin(OSINTSource, NewsItemData.osint_source_id == OSINTSource.id)
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

        if "read" in filter_args:
            query = query.filter(NewsItemAggregate.read)

        if "unread" in filter_args:
            query = query.filter(NewsItemAggregate.read is False)

        if "important" in filter_args:
            query = query.filter(NewsItemAggregate.important)

        if "unimportant" in filter_args:
            query = query.filter(NewsItemAggregate.important is False)

        if "relevant" in filter_args:
            query = query.filter(NewsItemAggregate.relevance > 0)

        if "in_report" in filter_args:
            query = query.join(
                ReportItemNewsItemAggregate,
                NewsItemAggregate.id == ReportItemNewsItemAggregate.news_item_aggregate_id,
            )

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

            query = query.filter(NewsItemAggregate.created >= date_limit)

        if timestamp := filter_args.get("timestamp"):
            query = query.filter(NewsItemAggregate.created >= datetime.fromisoformat(timestamp))

        return query

    @classmethod
    def _add_sorting_to_query(cls, filter_args: dict, query):
        if sort := filter_args.get("sort", "date_desc").lower():
            if sort == "date_desc":
                query = query.order_by(db.desc(cls.created), db.desc(cls.id))

            elif sort == "date_asc":
                query = query.order_by(db.asc(cls.created), db.asc(cls.id))

            elif sort == "relevance_desc":
                query = query.order_by(db.desc(cls.relevance), db.desc(cls.id))

            elif sort == "relevance_asc":
                query = query.order_by(db.asc(cls.relevance), db.asc(cls.id))

            elif sort == "source":
                query = query.order_by(db.desc(OSINTSource.name), db.desc(cls.created), db.desc(cls.id))

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
        if not ACLEntry.has_rows() or not user:
            return query

        query = query.outerjoin(
            ACLEntry,
            and_(
                NewsItemData.osint_source_id == ACLEntry.item_id,
                ACLEntry.item_type == ItemType.OSINT_SOURCE,
            ),
        )
        query = ACLEntry.apply_query(query, user, True, False, False)
        return query

    @classmethod
    def get_by_filter(cls, filter_args: dict, user: User | None = None):
        query = cls.query.distinct().group_by(NewsItemAggregate.id)
        query = cls._add_filters_to_query(filter_args, query)

        if user:
            query = cls._add_ACL_check(query, user)

        query = cls._add_sorting_to_query(filter_args, query)
        paged_query = cls._add_paging_to_query(filter_args, query)

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
        item["user_vote"] = NewsItemVote.get_user_vote(news_item_aggregate.id, user.id, "AGGREGATE")
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

        return {"total_count": count, "items": items, "max_item": max_item_count}

    @classmethod
    def get_for_worker(cls, filter_args: dict) -> list[dict[str, Any]]:
        news_item_aggregates, _ = cls.get_by_filter(filter_args=filter_args)
        return [news_item_aggregate.to_worker_dict() for news_item_aggregate in news_item_aggregates]

    @classmethod
    def create_new(cls, news_item_data):
        news_item = NewsItem()
        news_item.news_item_data = news_item_data
        db.session.add(news_item)

        aggregate = NewsItemAggregate(title=news_item_data.title, created=news_item_data.published)
        aggregate.title = news_item_data.title
        aggregate.description = news_item_data.review
        aggregate.created = news_item_data.published
        aggregate.news_items.append(news_item)
        db.session.add(aggregate)

        NewsItemAggregateSearchIndex.prepare(aggregate)

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

        return {"message": f"Added {len(news_items_data)} news items", "ids": ids}, 200

    @classmethod
    def update(cls, id, data, user):
        aggregate = cls.get(id)
        if not aggregate:
            return {"error": f"Aggregate with id: {id} not found"}, 404

        logger.debug(f"Updating aggregate {id} with {data}")
        if "vote" in data:
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

        NewsItemAggregate.update_status(aggregate.id)
        db.session.commit()
        return {"message": "success"}, 200

    def vote(self, vote_data, user_id):
        if not (vote := NewsItemVote.get_by_filter(item_id=self.id, user_id=user_id, item_type="AGGREGATE")):
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
        vote = NewsItemVote(item_id=self.id, user_id=user_id, item_type="AGGREGATE")
        db.session.add(vote)
        return vote

    @classmethod
    def delete_by_id(cls, aggregate_id, user):
        if cls.is_assigned_to_report([aggregate_id]):
            return {"error": f"aggregate with: {aggregate_id} assigned to a report"}, 500

        aggregate = cls.get(aggregate_id)
        if not aggregate:
            return {"error": f"Aggregate with id: {aggregate_id} not found"}, 404
        for news_item in aggregate.news_items:
            if news_item.allowed_with_acl(user, False, False, True):
                aggregate.news_items.remove(news_item)
                NewsItem.delete_item(news_item)

        NewsItemAggregate.update_status(aggregate.id)

        db.session.commit()

        return {"message": "success"}, 200

    def delete(self, user):
        return self.delete_by_id(self.id, user)

    @classmethod
    def is_assigned_to_report(cls, aggregate_ids: list) -> bool:
        return any(ReportItemNewsItemAggregate.assigned(aggregate_id) for aggregate_id in aggregate_ids)

    @classmethod
    def update_tags(cls, news_item_aggregate_id: int, tags: list | dict, bot_type: str = "") -> tuple[dict, int]:
        try:
            n_i_a = cls.get(news_item_aggregate_id)
            if not n_i_a:
                logger.error(f"News Item Aggregate {news_item_aggregate_id} not found")
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
                n_i_a.news_item_attributes.append(NewsItemAttribute(key=bot_type, value=f"{len(new_tags)}"))
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
                if user is None or news_item.allowed_with_acl(user, False, False, True):
                    aggregate.news_items.append(news_item)
                    aggregate.relevance += news_item.relevance + 1
                    aggregate.add(aggregate)
                    NewsItemAggregate.update_status(aggregate.id)
            cls.update_aggregates(aggregate)
            db.session.commit()
            return {"message": "success"}, 200
        except Exception:
            logger.log_debug_trace("Grouping News Item Aggregates Failed")
            return {"error": "grouping failed"}, 500

    @classmethod
    def group_aggregate(cls, aggregate_ids: list[int], user: User | None = None):
        try:
            logger.debug(f"grouping: {aggregate_ids}")
            if len(aggregate_ids) < 2 or any(type(a_id) is not int for a_id in aggregate_ids):
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
                    if user is None or news_item.allowed_with_acl(user, False, False, True):
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
            return {"error": "grouping failed"}, 500
        return {"message": "success"}, 200

    @classmethod
    def ungroup_story(cls, story_id: int, user: User | None = None):
        try:
            story = NewsItemAggregate.get(story_id)
            if not story:
                return {"error": "not_found"}, 404
            for news_item in story.news_items[:]:
                if user is None or news_item.allowed_with_acl(user, False, False, True):
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
                if not news_item.allowed_with_acl(user, False, False, True):
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
        try:
            for aggregate in aggregates:
                if len(aggregate.news_items) == 0:
                    NewsItemAggregateSearchIndex.remove(aggregate)
                    NewsItemTag.remove_by_aggregate(aggregate)
                    db.session.delete(aggregate)
                else:
                    NewsItemAggregateSearchIndex.prepare(aggregate)
                    NewsItemAggregate.update_status(aggregate.id)
        except Exception:
            logger.warning("Update Aggregates Failed")
            logger.log_debug_trace("Update Aggregates Failed")

    @classmethod
    def create_single_aggregate(cls, news_item):
        new_aggregate = NewsItemAggregate(
            title=news_item.news_item_data.title,
            created=news_item.news_item_data.published,
            description=news_item.news_item_data.review,
            news_items=[news_item.id],
        )
        db.session.add(new_aggregate)
        db.session.commit()

        NewsItemAggregateSearchIndex.prepare(new_aggregate)
        NewsItemAggregate.update_status(new_aggregate.id)

    @classmethod
    def update_status(cls, aggregate_id):
        aggregate = cls.get(aggregate_id)
        if aggregate is None:
            return

        if len(aggregate.news_items) == 0:
            NewsItemAggregateSearchIndex.remove(aggregate)
            db.session.delete(aggregate)
            return

    @classmethod
    def update_news_items_aggregate_summary(cls, aggregate_id, summary):
        aggregate = cls.get(aggregate_id)
        if not aggregate:
            return "not_found", 404
        aggregate.summary = summary
        db.session.commit()
        return {"message": "success"}, 200

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["news_items"] = [news_item.to_dict() for news_item in self.news_items]
        data["tags"] = [tag.to_small_dict() for tag in self.tags]
        if news_item_attributes := self.news_item_attributes:
            data["news_item_attributes"] = [news_item_attribute.to_dict() for news_item_attribute in news_item_attributes]
        return data

    def to_worker_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["news_items"] = [news_item.to_dict() for news_item in self.news_items]
        data["tags"] = {tag.name: tag.to_dict() for tag in self.tags}
        if news_item_attributes := self.news_item_attributes:
            data["news_item_attributes"] = [news_item_attribute.to_dict() for news_item_attribute in news_item_attributes]
        return data


class NewsItemAggregateSearchIndex(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String)
    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"))

    @classmethod
    def remove(cls, aggregate):
        search_index = cls.query.filter_by(news_item_aggregate_id=aggregate.id).first()
        if search_index is not None:
            db.session.delete(search_index)
            db.session.commit()

    @classmethod
    def prepare(cls, aggregate):
        search_index = cls.query.filter_by(news_item_aggregate_id=aggregate.id).first()
        if search_index is None:
            search_index = NewsItemAggregateSearchIndex()
            search_index.news_item_aggregate_id = aggregate.id
            db.session.add(search_index)

        data = aggregate.title
        data += f" {aggregate.description}"
        data += f" {aggregate.comments}"
        data += f" {aggregate.summary}"

        for news_item in aggregate.news_items:
            data += f" {news_item.news_item_data.title}"
            data += f" {news_item.news_item_data.review}"
            data += f" {news_item.news_item_data.content}"
            data += f" {news_item.news_item_data.author}"
            data += f" {news_item.news_item_data.link}"

            for attribute in news_item.news_item_data.attributes:
                data += f" {attribute.value}"

        search_index.data = data.lower()
        db.session.commit()


class NewsItemAttribute(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(), nullable=False)
    value = db.Column(db.String(), nullable=False)
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


class NewsItemDataNewsItemAttribute(BaseModel):
    news_item_data_id = db.Column(db.String, db.ForeignKey("news_item_data.id"), primary_key=True)
    news_item_attribute_id = db.Column(db.Integer, db.ForeignKey("news_item_attribute.id"), primary_key=True)


class NewsItemAggregateNewsItemAttribute(BaseModel):
    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"), primary_key=True)
    news_item_attribute_id = db.Column(db.Integer, db.ForeignKey("news_item_attribute.id"), primary_key=True)


class ReportItemNewsItemAggregate(BaseModel):
    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id", ondelete="CASCADE"), primary_key=True)
    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"), primary_key=True)

    @classmethod
    def assigned(cls, aggregate_id):
        return db.session.query(db.exists().where(ReportItemNewsItemAggregate.news_item_aggregate_id == aggregate_id)).scalar()

    @classmethod
    def count(cls, aggregate_id):
        return cls.query.filter_by(news_item_aggregate_id=aggregate_id).count()


class NewsItemTag(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name: Any = db.Column(db.String(255))
    tag_type: Any = db.Column(db.String(255))
    n_i_a_id = db.Column(db.ForeignKey(NewsItemAggregate.id))
    n_i_a = db.relationship(NewsItemAggregate, backref=orm.backref("tags", cascade="all, delete-orphan"))

    def __init__(self, name, tag_type):
        self.id = None
        self.name = name
        self.tag_type = tag_type

    @classmethod
    def delete_all_tags(cls):
        tags = cls.query.all()
        for tag in tags:
            db.session.delete(tag)
        db.session.commit()

    @classmethod
    def get_filtered_tags(cls, filter_args: dict) -> list["NewsItemTag"]:
        query = cls.query.with_entities(cls.name, cls.tag_type)

        if search := filter_args.get("search"):
            query = query.filter(cls.name.ilike(f"%{search}%"))

        if tag_type := filter_args.get("tag_type"):
            query = query.filter(cls.tag_type == tag_type)

        if min_size := filter_args.get("min_size", 4):
            # returns only tags where the name appears at least min_size times in the database
            query = query.group_by(cls.name, cls.tag_type).having(func.count(cls.name) >= min_size)
            # order by size
            query = query.order_by(func.count(cls.name).desc())

        rows = cls.get_rows(query, filter_args)
        return [cls(name=row[0], tag_type=row[1]) for row in rows]

    @classmethod
    def get_rows(cls, query, filter_args: dict) -> list["NewsItemTag"]:
        offset = filter_args.get("offset", 0)
        limit = filter_args.get("limit", 20)

        return query.offset(offset).limit(limit).all()

    @classmethod
    def get_json(cls, filter_args: dict) -> list[dict[str, Any]]:
        tags = cls.get_filtered_tags(filter_args)
        return [tag.to_small_dict() for tag in tags]

    @classmethod
    def get_list(cls, filter_args: dict) -> list[str]:
        tags = cls.get_filtered_tags(filter_args)
        return [tag.name for tag in tags]

    @classmethod
    def remove_by_aggregate(cls, aggregate):
        tags = cls.query.filter_by(n_i_a_id=aggregate.id).all()
        for tag in tags:
            db.session.delete(tag)
        db.session.commit()

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "tag_type": self.tag_type}

    def to_small_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tag_type": self.tag_type,
        }

    @classmethod
    def find_by_name(cls, tag_name: str) -> "NewsItemTag | None":
        return cls.query.filter(cls.name.ilike(tag_name)).first()

    @classmethod
    def find_largest_tag_clusters(cls, days: int = 7, limit: int = 12, min_count: int = 2):
        start_date = datetime.now() - timedelta(days=days)
        subquery = (
            db.session.query(cls.name, cls.tag_type, NewsItemAggregate.id, NewsItemAggregate.created)
            .join(cls.n_i_a)
            .filter(NewsItemAggregate.created >= start_date)
            .subquery()
        )

        if db.session.get_bind().dialect.name == "sqlite":
            group_concat_fn = func.group_concat(subquery.c.created)
        else:
            group_concat_fn = func.array_agg(subquery.c.created)

        clusters = (
            db.session.query(subquery.c.name, subquery.c.tag_type, group_concat_fn, func.count(subquery.c.name).label("count"))
            .select_from(subquery.join(NewsItemAggregate, subquery.c.id == NewsItemAggregate.id))
            .group_by(subquery.c.name, subquery.c.tag_type)
            .having(func.count(subquery.c.name) >= min_count)
            .order_by(func.count(subquery.c.name).desc())
            .limit(limit)
            .all()
        )
        if not clusters:
            return []
        results = []
        for cluster in clusters:
            if db.session.get_bind().dialect.name == "sqlite":
                published = list(cluster[2].split(","))
            else:
                published = [dt.isoformat() for dt in cluster[2]]

            results.append(
                {
                    "name": cluster[0],
                    "tag_type": cluster[1],
                    "published": published,
                    "size": cluster[3],
                }
            )
        return results

    @classmethod
    def get_n_biggest_tags_by_type(cls, tag_type: str, n: int, offset: int = 0) -> dict[str, dict]:
        query = (
            cls.query.with_entities(cls.name, func.count(cls.name).label("name_count"))
            .filter(cls.tag_type == tag_type)
            .group_by(cls.name)
            .order_by(db.desc("name_count"))
            .offset(offset)
            .limit(n)
            .all()
        )
        return {row[0]: {"name": row[0], "size": row[1]} for row in query}

    @classmethod
    def get_cluster_by_filter(cls, filter):
        query = cls.query.with_entities(cls.name, func.count(cls.name).label("name_count"))
        if tag_type := filter.get("tag_type"):
            query = query.filter(cls.tag_type == tag_type).group_by(cls.name).order_by(db.desc("name_count"))

        count = query.count()

        if search := filter.get("search"):
            query = query.filter(cls.name.ilike(f"%{search}%"))
        if offset := filter.get("offset"):
            query = query.offset(offset)
        if limit := filter.get("limit"):
            query = query.limit(limit)

        items = {row[0]: {"name": row[0], "size": row[1]} for row in query.all()}

        return {"total_count": count, "items": list(items.values())}

    @classmethod
    def get_tag_types(cls) -> list[tuple[str, int]]:
        query = (
            cls.query.with_entities(cls.tag_type, func.count(cls.name).label("type_count"))
            .group_by(cls.tag_type)
            .order_by(db.desc("type_count"))
            .all()
        )
        return [(row[0], row[1]) for row in query]

    @classmethod
    def get_largest_tag_types(cls) -> dict:
        tag_types_with_count = cls.get_tag_types()
        return {
            tag_type: {"size": count, "name": tag_type, "tags": cls.get_n_biggest_tags_by_type(tag_type, 5)}
            for tag_type, count in tag_types_with_count
        }

    @classmethod
    def parse_tags(cls, tags: list | dict) -> dict[str, "NewsItemTag"]:
        new_tags = {}
        if type(tags) is dict:
            for name, tag in tags.items():
                tag_name = name
                tag_type = tag.get("tag_type", "misc")
                new_tags[tag_name] = NewsItemTag(name=tag_name, tag_type=tag_type)
        else:
            for tag_name in tags:
                new_tags[tag_name] = NewsItemTag(name=tag_name, tag_type="misc")
        return new_tags
