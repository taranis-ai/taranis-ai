import base64
import uuid
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import orm, and_, or_, func

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.managers.log_manager import logger
from core.model.user import User
from core.model.acl_entry import ACLEntry, ItemType
from core.model.osint_source import OSINTSourceGroup, OSINTSource


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
    collected = db.Column(db.DateTime)
    published = db.Column(db.DateTime, default=datetime.now())
    updated = db.Column(db.DateTime, default=datetime.now())

    attributes = db.relationship("NewsItemAttribute", secondary="news_item_data_news_item_attribute", cascade="all, delete")

    osint_source_id = db.Column(db.String, db.ForeignKey("osint_source.id"), nullable=True)
    osint_source = db.relationship("OSINTSource")
    remote_source = db.Column(db.String())

    def __init__(self, hash, title, review, source, link, published, author, collected, content, osint_source_id, attributes, id=None):
        self.id = id or str(uuid.uuid4())
        self.hash = hash
        self.title = title
        self.review = review
        self.author = author
        self.source = source
        self.link = link
        self.content = content
        self.collected = collected if type(collected) is datetime else datetime.fromisoformat(collected)
        self.published = published if type(published) is datetime else datetime.fromisoformat(published)
        self.attributes = attributes
        self.osint_source_id = osint_source_id

    @classmethod
    def count_all(cls):
        return cls.query.count()

    @classmethod
    def allowed_with_acl(cls, news_item_data_id, user, see, access, modify):
        news_item_data = cls.query.get(news_item_data_id)
        if news_item_data.remote_source:
            return True
        query = db.session.query(NewsItemData.id).distinct().group_by(NewsItemData.id).filter(NewsItemData.id == news_item_data_id)

        query = query.join(OSINTSource, NewsItemData.osint_source_id == OSINTSource.id)

        query = query.outerjoin(
            ACLEntry,
            or_(
                and_(
                    NewsItemData.osint_source_id == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.OSINT_SOURCE,
                ),
                and_(
                    OSINTSource.collector_id == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.COLLECTOR,
                ),
            ),
        )

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

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
            return "Invalid news item id", 400
        news_item.language = lang
        db.session.commit()
        return "Language updated", 200

    @classmethod
    def update_news_item_attributes(cls, news_item_id, attributes) -> tuple[str, int]:
        news_item = cls.get(news_item_id)
        if news_item is None:
            return "Invalid news item id", 400

        attributes = NewsItemAttribute.load_multiple(attributes)
        if attributes is None:
            return "Invalid attributes", 400

        for attribute in attributes:
            if not news_item.has_attribute_value(attribute.value):
                news_item.attributes.append(attribute)

        return "Attributes updated", 200

    @classmethod
    def get_for_sync(cls, last_synced, osint_sources):
        osint_source_ids = {osint_source.id for osint_source in osint_sources}
        last_sync_time = datetime.now()

        query = cls.query.filter(
            NewsItemData.updated >= last_synced,
            NewsItemData.updated <= last_sync_time,
            NewsItemData.osint_source_id.in_(osint_source_ids),
        )

        news_items = query.all()
        items = [news_item.to_dict() for news_item in news_items]
        return items, last_sync_time

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["tag"] = "mdi-file-table-outline"
        return data


class NewsItem(BaseModel):
    id = db.Column(db.Integer, primary_key=True)

    read = db.Column(db.Boolean, default=False)
    important = db.Column(db.Boolean, default=False)

    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    relevance = db.Column(db.Integer, default=0)

    news_item_data_id = db.Column(db.String, db.ForeignKey("news_item_data.id"))
    news_item_data = db.relationship("NewsItemData", cascade="all, delete")

    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"))

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
            or_(
                and_(
                    NewsItemData.osint_source_id == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.OSINT_SOURCE,
                ),
                and_(
                    OSINTSource.collector_id == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.COLLECTOR,
                ),
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

        return {"total_count": count, "items": items}

    @classmethod
    def get_all_by_group_and_source_query(cls, group_id, source_id, time_limit):
        query = cls.query.join(NewsItemData, NewsItemData.id == NewsItem.news_item_data_id)
        query = query.filter(
            NewsItemData.osint_source_id == source_id,
            NewsItemData.collected >= time_limit,
        )
        query = query.join(NewsItemAggregate, NewsItemAggregate.id == NewsItem.news_item_aggregate_id)
        query = query.filter(NewsItemAggregate.osint_source_group_id == group_id)
        return query

    @classmethod
    def allowed_with_acl(cls, news_item_id, user: User, see, access, modify):
        news_item = cls.query.get(news_item_id)
        if news_item.news_item_data.remote_source is not None:
            return True
        query = db.session.query(NewsItem.id).distinct().group_by(NewsItem.id).filter(NewsItem.id == news_item_id)

        query = query.join(NewsItemData, NewsItem.news_item_data_id == NewsItemData.id)
        query = query.join(OSINTSource, NewsItemData.osint_source_id == OSINTSource.id)

        query = query.outerjoin(
            ACLEntry,
            or_(
                and_(
                    NewsItemData.osint_source_id == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.OSINT_SOURCE,
                ),
                and_(
                    OSINTSource.collector_id == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.COLLECTOR,
                ),
            ),
        )

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    def vote(self, vote_data, user_id):
        vote = NewsItemVote.find_by_user(self.id, user_id)
        if vote is None:
            vote = self.create_new_vote(vote, user_id)

        if vote_data > 0:
            self.update_like_vote(vote)
        else:
            self.update_dislike_vote(vote)

        self.news_item_data.updated = datetime.now()

    def create_new_vote(self, vote, user_id):
        vote = NewsItemVote(self.id, user_id)
        db.session.add(vote)
        return vote

    def update_like_vote(self, vote):
        self.increment_likes()
        self.increment_relevance()
        vote.like = True
        vote.dislike = False

    def update_dislike_vote(self, vote):
        self.increment_dislikes()
        self.decrement_relevance()
        vote.dislike = True
        vote.like = False

    def increment_likes(self):
        self.likes += 1

    def decrement_likes(self):
        self.likes -= 1

    def increment_dislikes(self):
        self.dislikes += 1

    def decrement_dislikes(self):
        self.dislikes -= 1

    def increment_relevance(self):
        self.relevance += 1

    def decrement_relevance(self):
        self.relevance -= 1

    @classmethod
    def update(cls, id, data, user_id):
        news_item = cls.get(id)
        if not news_item:
            return "not_found", 404
        news_item.update_status(data, user_id)

        NewsItemAggregate.update_status(news_item.news_item_aggregate_id)
        db.session.commit()

        return "success", 200

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
            return "not_found", 404
        if NewsItemAggregate.is_assigned_to_report([{"type": "AGGREGATE", "id": news_item.news_item_aggregate_id}]) is False:
            return "aggregate_in_use", 500
        aggregate_id = news_item.news_item_aggregate_id
        aggregate = NewsItemAggregate.get(aggregate_id)
        if not aggregate:
            return "not_found", 404
        aggregate.news_items.remove(news_item)
        NewsItemVote.delete_all(news_item_id)
        db.session.delete(news_item)
        NewsItemAggregate.update_status(aggregate_id)
        db.session.commit()

        return "success", 200

    @classmethod
    def delete_only(cls, news_item):
        NewsItemVote.delete_all(news_item.id)
        db.session.delete(news_item)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["news_item_data"] = self.news_item_data.to_dict()
        return data


class NewsItemVote(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    like = db.Column(db.Boolean)
    dislike = db.Column(db.Boolean)
    news_item_id = db.Column(db.Integer, db.ForeignKey("news_item.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    remote_node_id = db.Column(db.Integer, db.ForeignKey("remote_node.id"), nullable=True)
    remote_user = db.Column(db.String())

    def __init__(self, news_item_id, user_id):
        self.id = None
        self.news_item_id = news_item_id
        self.user_id = user_id
        self.like = False
        self.dislike = False

    @classmethod
    def find_by_user(cls, news_item_id, user_id):
        return cls.query.filter_by(news_item_id=news_item_id, user_id=user_id).first()

    @classmethod
    def delete_all(cls, news_item_id):
        votes = cls.query.filter_by(news_item_id=news_item_id).all()
        for vote in votes:
            db.session.delete(vote)

    @classmethod
    def delete_for_remote_node(cls, news_item_id, remote_node_id):
        vote = cls.query.filter_by(news_item_id=news_item_id, remote_node_id=remote_node_id).first()
        if vote is None:
            return 0
        db.session.delete(vote)
        return 1 if vote.like else -1


class NewsItemAggregate(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    description = db.Column(db.String())

    created = db.Column(db.DateTime)

    read = db.Column(db.Boolean, default=False)
    important = db.Column(db.Boolean, default=False)

    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    relevance = db.Column(db.Integer, default=0)

    comments = db.Column(db.String(), default="")

    summary = db.Column(db.Text, default="")

    osint_source_group_id = db.Column(db.String, db.ForeignKey("osint_source_group.id"))

    news_items = db.relationship("NewsItem")

    news_item_attributes = db.relationship("NewsItemAttribute", secondary="news_item_aggregate_news_item_attribute")

    @classmethod
    def get_json(cls, aggregate_id):
        item = cls.get(aggregate_id)
        return item.to_dict() if item else ("not_found", 404)

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
        if group := filter_args.get("group"):
            query = query.filter(NewsItemAggregate.osint_source_group_id == group)

        if source := filter_args.get("source"):
            query = query.filter(OSINTSource.id == source)

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
            query = query.filter(NewsItemAggregate.read == False)

        if "important" in filter_args:
            query = query.filter(NewsItemAggregate.important)

        if "unimportant" in filter_args:
            query = query.filter(NewsItemAggregate.important == False)

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
                query = query.join(alias, NewsItemAggregate.id == alias.n_i_a_id).filter(alias.name == tag)

        filter_range = filter_args.get("range", "").lower()
        if filter_range and filter_range in ["day", "week", "month"]:
            date_limit = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            if filter_range == "day":
                date_limit -= timedelta(days=1)

            elif filter_range == "week":
                date_limit -= timedelta(days=date_limit.weekday())

            elif filter_range == "month":
                date_limit = date_limit.replace(day=1)

            query = query.filter(NewsItemAggregate.created >= date_limit)

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
        offset = filter_args.get("offset", 0)
        limit = filter_args.get("limit", 20)
        return query.offset(offset).limit(limit)

    @classmethod
    def _add_ACL_check(cls, query, user: User):
        if not ACLEntry.has_rows() or not user:
            return query

        query = query.join(NewsItem, NewsItem.news_item_aggregate_id == NewsItemAggregate.id)
        query = query.join(NewsItemData, NewsItem.news_item_data_id == NewsItemData.id)
        query = query.outerjoin(OSINTSource, NewsItemData.osint_source_id == OSINTSource.id)
        query = query.outerjoin(
            ACLEntry,
            or_(
                and_(
                    NewsItemData.osint_source_id == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.OSINT_SOURCE,
                ),
                and_(
                    OSINTSource.collector_id == ACLEntry.item_id,
                    ACLEntry.item_type == ItemType.COLLECTOR,
                ),
            ),
        )
        query = ACLEntry.apply_query(query, user, True, False, False)
        return query

    @classmethod
    def get_by_filter(cls, filter_args: dict, user: User | None = None):
        query = cls.query.distinct().group_by(NewsItemAggregate.id)

        if user:
            query = cls._add_ACL_check(query, user)

        query = cls._add_filters_to_query(filter_args, query)
        query = cls._add_sorting_to_query(filter_args, query)
        paged_query = cls._add_paging_to_query(filter_args, query)

        return paged_query.all(), query.count()

    @classmethod
    def get_by_timestamp(cls, filter_args: dict):
        logger.debug(f"Getting NewsItems Filtered: {filter_args}")
        query = cls.query.distinct().group_by(NewsItemAggregate.id)

        if group := filter_args.get("group"):
            query = query.filter(NewsItemAggregate.osint_source_group_id == group)

        if timestamp := filter_args.get("timestamp"):
            query = query.filter(NewsItemAggregate.created >= timestamp)

        return query.all()

    @classmethod
    def get_by_filter_json(cls, filter_args, user):
        news_item_aggregates, count = cls.get_by_filter(filter_args=filter_args, user=user)
        for news_item_aggregate in news_item_aggregates:
            news_item_aggregate.in_reports_count = ReportItemNewsItemAggregate.count(news_item_aggregate.id)

        items = [news_item_aggregate.to_dict() for news_item_aggregate in news_item_aggregates]
        return {"total_count": count, "items": items}

    @classmethod
    def get_by_timestamp_json(cls, filter_args):
        news_item_aggregates = cls.get_by_timestamp(filter_args=filter_args)
        return [news_item_aggregate.to_dict() for news_item_aggregate in news_item_aggregates]

    @classmethod
    def get_for_worker(cls, limit: str):
        news_item_aggregates, _ = cls.get_by_filter(filter_args={"limit": limit})
        return [news_item_aggregate.to_dict() for news_item_aggregate in news_item_aggregates]

    @classmethod
    def create_new_for_all_groups(cls, news_item_data):
        group = OSINTSourceGroup.get_for_osint_source(news_item_data.osint_source_id)[0]
        cls.create_new_for_group(news_item_data, group.id)

    @classmethod
    def create_new_for_group(cls, news_item_data, osint_source_group_id):
        news_item = NewsItem()
        news_item.news_item_data = news_item_data
        db.session.add(news_item)

        aggregate = NewsItemAggregate()
        aggregate.title = news_item_data.title
        aggregate.description = news_item_data.review
        aggregate.created = news_item_data.published
        aggregate.osint_source_group_id = osint_source_group_id
        aggregate.news_items.append(news_item)
        db.session.add(aggregate)

        NewsItemAggregateSearchIndex.prepare(aggregate)

        db.session.commit()

        return aggregate

    @classmethod
    def add_news_items(cls, news_items_data_list):
        news_items_data = NewsItemData.load_multiple(news_items_data_list)
        for news_item_data in news_items_data:
            if not NewsItemData.identical(news_item_data.hash):
                db.session.add(news_item_data)
                cls.create_new_for_all_groups(news_item_data)
        db.session.commit()

        return f"Added {len(news_items_data)} news items", 200

    @classmethod
    def add_news_item(cls, news_item_data) -> tuple[str, int]:
        news_item_data = NewsItemData.from_dict(news_item_data)
        if not news_item_data:
            return "Invalid news item data", 400
        if not news_item_data.id:
            news_item_data.id = str(uuid.uuid4())
        db.session.add(news_item_data)
        cls.create_new_for_all_groups(news_item_data)
        db.session.commit()

        return f"Added news item {news_item_data.id}", 201

    @classmethod
    def reassign_to_new_groups(cls, osint_source_id, default_group_id):
        time_limit = datetime.now() - timedelta(days=7)
        news_items_query = NewsItem.get_all_by_group_and_source_query(default_group_id, osint_source_id, time_limit)
        for news_item in news_items_query:
            news_item_data = news_item.news_item_data
            aggregate = NewsItemAggregate.get(news_item.news_item_aggregate_id)
            if not aggregate:
                continue
            aggregate.news_items.remove(news_item)
            NewsItemVote.delete_all(news_item.id)
            db.session.delete(news_item)
            NewsItemAggregate.update_status(aggregate.id)
            cls.create_new_for_all_groups(news_item_data)
            db.session.commit()

    @classmethod
    def add_remote_news_items(cls, news_items_data_list, remote_node, osint_source_group_id):
        news_items_data = cls.load_multiple(news_items_data_list)
        news_item_data_ids = set()
        if not news_items_data:
            return
        for news_item_data in news_items_data:
            news_item_data.remote_source = remote_node.name
            for attribute in news_item_data.attributes:
                attribute.remote_node_id = remote_node.id
                attribute.remote_user = remote_node.name

            db.session.add(news_item_data)
            cls.create_new_for_group(news_item_data, osint_source_group_id)
            news_item_data_ids.add(str(news_item_data.id))
        db.session.commit()

    @classmethod
    def update(cls, id, data, user):
        aggregate = cls.get(id)
        if not aggregate:
            return "Not found", 404

        logger.debug(f"Updating aggregate {id} with {data}")
        for news_item in aggregate.news_items:
            if NewsItem.allowed_with_acl(news_item.id, user, False, False, True):
                if "vote" in data:
                    news_item.vote(data["vote"], user.id)

                if "read" in data:
                    news_item.read = not aggregate.read

                if "important" in data:
                    all_important = all(news_item.important is not False for news_item in aggregate.news_items)
                    news_item.important = not all_important

        if "title" in data:
            aggregate.title = data["title"]

        if "description" in data:
            aggregate.description = data["description"]

        if "comments" in data:
            aggregate.comments = data["comments"]

        NewsItemAggregate.update_status(aggregate.id)
        NewsItemAggregateSearchIndex.prepare(aggregate)

        db.session.commit()

        return "success", 200

    @classmethod
    def delete_by_id(cls, id, user):
        if cls.is_assigned_to_report([id]):
            return "aggregate_in_use", 500

        aggregate = cls.get(id)
        if not aggregate:
            return "Not found", 404
        for news_item in aggregate.news_items:
            if NewsItem.allowed_with_acl(news_item.id, user, False, False, True):
                aggregate.news_items.remove(news_item)
                NewsItem.delete_only(news_item)

        NewsItemAggregate.update_status(aggregate.id)

        db.session.commit()

        return "success", 200

    def delete(self, user):
        return self.delete_by_id(self.id, user)

    @classmethod
    def is_assigned_to_report(cls, aggregate_ids: list) -> bool:
        return any(ReportItemNewsItemAggregate.assigned(aggregate_id) for aggregate_id in aggregate_ids)

    @classmethod
    def update_tags(cls, news_item_aggregate_id: int, tags: list) -> tuple[str, int]:
        try:
            n_i_a = cls.get(news_item_aggregate_id)
            if not n_i_a:
                return "not_found", 404
            for tag in tags:
                if type(tag) is dict:
                    tag_name = tag["name"]
                    tag_type = tag["type"]
                else:
                    tag_name = tag
                    tag_type = "misc"
                if tag_name not in [tag.name for tag in n_i_a.tags]:
                    n_i_a.tags.append(NewsItemTag(name=tag_name, tag_type=tag_type))
            db.session.commit()
            return "success", 200
        except Exception:
            logger.log_debug_trace("Update News Item Tags Failed")
            return "error", 500

    @classmethod
    def group_aggregate(cls, aggregate_ids: list, user: User | None = None):
        try:
            first_aggregate = NewsItemAggregate.get(aggregate_ids.pop(0))
            if not first_aggregate:
                return "not_found", 404
            processed_aggregates = {first_aggregate}
            for item in aggregate_ids:
                aggregate = NewsItemAggregate.get(item)
                if not aggregate:
                    continue
                for news_item in aggregate.news_items[:]:
                    if user is None or NewsItem.allowed_with_acl(news_item.id, user, False, False, True):
                        first_aggregate.news_items.append(news_item)
                        first_aggregate.relevance += news_item.relevance + 1
                        aggregate.news_items.remove(news_item)
                processed_aggregates.add(aggregate)

            db.session.commit()
            cls.update_aggregates(processed_aggregates)
            return "success", 200
        except Exception:
            logger.log_debug_trace("Grouping News Item Aggregates Failed")
            return "error", 500

    @classmethod
    def ungroup_aggregate(cls, newsitem_ids: list, user: User | None = None):
        try:
            processed_aggregates = set()
            for item in newsitem_ids:
                news_item = NewsItem.get(item)
                if not news_item:
                    continue
                if not NewsItem.allowed_with_acl(news_item.id, user, False, False, True):
                    continue
                aggregate = NewsItemAggregate.get(news_item.news_item_aggregate_id)
                if not aggregate:
                    continue
                group_id = aggregate.osint_source_group_id
                aggregate.news_items.remove(news_item)
                processed_aggregates.add(aggregate)
                cls.create_single_aggregate(news_item, group_id)
            db.session.commit()
            cls.update_aggregates(processed_aggregates)
            return "success", 200
        except Exception:
            logger.log_debug_trace("Grouping News Item Aggregates Failed")
            return "error", 500

    @classmethod
    def update_aggregates(cls, aggregates: set):
        try:
            logger.debug("UPDATE AGGREGATES")
            logger.debug(aggregates)
            for aggregate in aggregates:
                if len(aggregate.news_items) == 0:
                    NewsItemAggregateSearchIndex.remove(aggregate)
                    NewsItemTag.remove_by_aggregate(aggregate)
                    logger.debug(f"Trying to delete: {aggregate}")
                    db.session.delete(aggregate)
                else:
                    NewsItemAggregateSearchIndex.prepare(aggregate)
                    NewsItemAggregate.update_status(aggregate.id)
        except Exception:
            logger.warning("Update Aggregates Failed")
            logger.log_debug_trace("Update Aggregates Failed")

    @classmethod
    def create_single_aggregate(cls, news_item, group_id):
        new_aggregate = NewsItemAggregate()
        new_aggregate.title = news_item.news_item_data.title
        new_aggregate.description = news_item.news_item_data.review
        new_aggregate.created = news_item.news_item_data.collected
        new_aggregate.news_items.append(news_item)
        new_aggregate.osint_source_group_id = group_id
        db.session.add(new_aggregate)
        db.session.commit()

        NewsItemAggregateSearchIndex.prepare(new_aggregate)
        NewsItemAggregate.update_status(new_aggregate.id)

    @classmethod
    def update_status(cls, aggregate_id):
        aggregate = cls.get(aggregate_id)
        if aggregate is None:
            return

        news_items = aggregate.news_items
        if len(news_items) == 0:
            NewsItemAggregateSearchIndex.remove(aggregate)
            db.session.delete(aggregate)
            return

        aggregate.relevance = 0
        aggregate.read = True
        aggregate.important = False
        aggregate.likes = 0
        aggregate.dislikes = 0
        for news_item in news_items:
            aggregate.relevance += news_item.relevance
            aggregate.likes += news_item.likes
            aggregate.dislikes += news_item.dislikes
            aggregate.important |= news_item.important
            aggregate.read &= news_item.read

    @classmethod
    def update_news_items_aggregate_summary(cls, aggregate_id, summary):
        aggregate = cls.get(aggregate_id)
        if not aggregate:
            return "not_found", 404
        aggregate.summary = summary
        db.session.commit()
        return "success", 200

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["news_items"] = [news_item.to_dict() for news_item in self.news_items]
        data["tags"] = [tag.to_dict() for tag in self.tags]
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

    remote_node_id = db.Column(db.Integer, db.ForeignKey("remote_node.id"), nullable=True)
    remote_user = db.Column(db.String())

    def __init__(self, key, value, binary_mime_type, binary_value):
        self.id = None
        self.key = key
        self.value = value
        self.binary_mime_type = binary_mime_type

        if binary_value:
            self.binary_data = base64.b64decode(binary_value)


class NewsItemDataNewsItemAttribute(BaseModel):
    news_item_data_id = db.Column(db.String, db.ForeignKey("news_item_data.id"), primary_key=True)
    news_item_attribute_id = db.Column(db.Integer, db.ForeignKey("news_item_attribute.id"), primary_key=True)


class NewsItemAggregateNewsItemAttribute(BaseModel):
    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"), primary_key=True)
    news_item_attribute_id = db.Column(db.Integer, db.ForeignKey("news_item_attribute.id"), primary_key=True)


class ReportItemNewsItemAggregate(BaseModel):
    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id"), primary_key=True)
    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"), primary_key=True)

    @classmethod
    def assigned(cls, aggregate_id):
        return db.session.query(db.exists().where(ReportItemNewsItemAggregate.news_item_aggregate_id == aggregate_id)).scalar()

    @classmethod
    def count(cls, aggregate_id):
        return cls.query.filter_by(news_item_aggregate_id=aggregate_id).count()


class NewsItemTag(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    tag_type = db.Column(db.String(255))
    n_i_a_id = db.Column(db.ForeignKey(NewsItemAggregate.id))
    n_i_a = db.relationship(NewsItemAggregate, backref=orm.backref("tags", cascade="all, delete-orphan"))

    def __init__(self, name, tag_type):
        self.id = None
        self.name = name
        self.tag_type = tag_type

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
    def get_filtered_tags(cls, filter_args: dict) -> list["NewsItemTag"]:
        query = cls.query.with_entities(cls.name, cls.tag_type)

        if search := filter_args.get("search"):
            query = query.filter(cls.name.ilike(f"%{search}%"))

        if tag_type := filter_args.get("tag_type"):
            query = query.filter(cls.tag_type == tag_type)

        if min_size := filter_args.get("min_size", 2):
            # returns only tags where the name appears at least min_size times in the database
            query = query.group_by(cls.name, cls.tag_type).having(func.count(cls.name) >= min_size)

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
        return [tag.to_dict() for tag in tags]

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
        return {
            "name": self.name,
            "tag_type": self.tag_type,
        }
