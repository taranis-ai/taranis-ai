import base64
import uuid
from datetime import datetime, timedelta
import dateutil.parser as dateparser

from marshmallow import post_load, fields, ValidationError
from sqlalchemy import orm, and_, or_, func

from core.managers.db_manager import db
from core.managers.log_manager import logger
from core.model.user import User
from core.model.acl_entry import ACLEntry
from core.model.osint_source import OSINTSourceGroup, OSINTSource
from shared.schema.acl_entry import ItemType
from shared.schema.news_item import NewsItemDataSchema, NewsItemAggregateSchema, NewsItemAttributeSchema, NewsItemSchema, \
    NewsItemRemoteSchema


class NewNewsItemAttributeSchema(NewsItemAttributeSchema):
    @post_load
    def make(self, data, **kwargs):
        return NewsItemAttribute(**data)


class NewNewsItemDataSchema(NewsItemDataSchema):
    attributes = fields.Nested(NewNewsItemAttributeSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return NewsItemData(**data)


class NewsItemData(db.Model):
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

    attributes = db.relationship("NewsItemAttribute", secondary="news_item_data_news_item_attribute")

    osint_source_id = db.Column(db.String, db.ForeignKey("osint_source.id"), nullable=True)
    osint_source = db.relationship("OSINTSource")
    remote_source = db.Column(db.String())

    def __init__(
        self,
        id,
        hash,
        title,
        review,
        source,
        link,
        published,
        author,
        collected,
        content,
        osint_source_id,
        attributes,
    ):
        self.id = id or str(uuid.uuid4())
        self.hash = hash
        self.title = title
        self.review = review
        self.source = source
        self.link = link
        self.published = published
        self.author = author
        self.collected = collected
        self.content = content
        self.attributes = attributes
        self.osint_source_id = osint_source_id

    @classmethod
    def allowed_with_acl(cls, news_item_data_id, user, see, access, modify):

        news_item_data = cls.query.get(news_item_data_id)
        if news_item_data.remote_source is not None:
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
    def identical(cls, hash):
        return db.session.query(db.exists().where(NewsItemData.hash == hash)).scalar()

    @classmethod
    def find(cls, id):
        return cls.query.get(id)

    @classmethod
    def find_by_hash(cls, hash):
        return cls.query.filter(NewsItemData.hash == hash).all()

    @classmethod
    def count_all(cls):
        return cls.query.count()

    @classmethod
    def latest_collected(cls):
        news_item_data = cls.query.order_by(db.desc(NewsItemData.collected)).first()
        return news_item_data.collected.isoformat() if news_item_data else ""

    @classmethod
    def get_all_news_items_data(cls, limit: str):
        limit_date = datetime.fromisoformat(limit)

        news_items_data = cls.query.filter(cls.collected > limit_date).all()
        news_items_data_schema = NewsItemDataSchema(many=True)
        return news_items_data_schema.dump(news_items_data)

    @classmethod
    def attribute_value_identical(cls, id, value):
        return (
            NewsItemAttribute.query.join(NewsItemDataNewsItemAttribute)
            .join(NewsItemData)
            .filter(NewsItemData.id == id)
            .filter(NewsItemAttribute.value == value)
            .scalar()
        )

    @classmethod
    def update_news_item_lang(cls, news_item_id, lang):
        news_item = cls.find(news_item_id)

        news_item.language = lang
        db.session.commit()

    @classmethod
    def update_news_item_attributes(cls, news_item_id, attributes):
        news_item = cls.query.filter_by(id=news_item_id).first()

        attributes_schema = NewNewsItemAttributeSchema(many=True)
        attributes = attributes_schema.load(attributes)
        if attributes is None:
            return

        for attribute in attributes:
            if not cls.attribute_value_identical(news_item_id, attribute.value):
                news_item.attributes.append(attribute)
                db.session.commit()

    @classmethod
    def get_news_item_data(cls, news_item_id):
        query = cls.query.join(NewsItem, NewsItemData.id == NewsItem.news_item_data_id)
        query = query.filter(NewsItem.id == news_item_id)
        return query

    @classmethod
    def get_for_sync(cls, last_synced, osint_sources):
        osint_source_ids = set()
        for osint_source in osint_sources:
            osint_source_ids.add(osint_source.id)

        last_sync_time = datetime.now()

        query = cls.query.filter(
            NewsItemData.updated >= last_synced,
            NewsItemData.updated <= last_sync_time,
            NewsItemData.osint_source_id.in_(osint_source_ids),
        )

        news_items = query.all()
        news_item_remote_schema = NewsItemRemoteSchema(many=True)
        for news_item in news_items:
            total_relevance = NewsItem.get_total_relevance(news_item.id)
            if total_relevance > 0:
                news_item.relevance = 1
            elif total_relevance < 0:
                news_item.relevance = -1
            else:
                news_item.relevance = 0

        items = news_item_remote_schema.dump(news_items)

        return items, last_sync_time


class NewsItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    read = db.Column(db.Boolean, default=False)
    important = db.Column(db.Boolean, default=False)

    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    relevance = db.Column(db.Integer, default=0)

    news_item_data_id = db.Column(db.String, db.ForeignKey("news_item_data.id"))
    news_item_data = db.relationship("NewsItemData")

    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"))

    @classmethod
    def find(cls, news_item_id):
        return cls.query.get(news_item_id)

    @classmethod
    def get_all_with_data(cls, news_item_data_id):
        return cls.query.filter_by(news_item_data_id=news_item_data_id).all()

    @classmethod
    def get_total_count(cls):
        return {"total_count": cls.query.get.count()}

    @classmethod
    def get_detail_json(cls, id):
        news_item = cls.query.get(id)
        news_item_schema = NewsItemSchema()
        return news_item_schema.dump(news_item)

    @classmethod
    def get_by_group(cls, group_id, filter, user):
        query = cls.query.distinct().group_by(NewsItem.id)
        query = query.join(NewsItemData, NewsItem.news_item_data_id == NewsItemData.id)
        query = query.outerjoin(OSINTSource, NewsItemData.osint_source_id == OSINTSource.id)
        query = query.filter(OSINTSource.id == group_id)

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

        if "search" in filter and filter["search"] != "":
            search_string = f"%{filter['search'].lower()}%"
            query = query.filter(NewsItemData.content.like(search_string))

        if "read" in filter and filter["read"].lower() == "true":
            query = query.filter(NewsItem.read is False)

        if "important" in filter and filter["important"].lower() == "true":
            query = query.filter(NewsItem.important is True)

        if "relevant" in filter and filter["relevant"].lower() == "true":
            query = query.filter(NewsItem.likes > 0)

        if "range" in filter and filter["range"] != "ALL":
            date_limit = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            if filter["range"] == "WEEK":
                date_limit -= timedelta(days=date_limit.weekday())

            elif filter["range"] == "MONTH":
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
    def get_by_group_json(cls, group_id, filter, user):
        news_items, count = cls.get_by_group(group_id, filter, user)

        for news_item in news_items:
            see, access, modify = NewsItem.get_acl_status(news_item.id, user)
            news_item.see = see
            news_item.access = access
            news_item.modify = modify
            vote = NewsItemVote.find(news_item.id, user.id)
            if vote is not None:
                news_item.me_like = vote.like
                news_item.me_dislike = vote.dislike
            else:
                news_item.me_like = False
                news_item.me_dislike = False

        news_item_schema = NewsItemSchema(many=True)
        items = news_item_schema.dump(news_items)

        return {"total_count": count, "items": items}

    @classmethod
    def get_total_relevance(cls, news_item_data_id):
        query = db.session.query(NewsItem.relevance).filter(NewsItem.news_item_data_id == news_item_data_id)
        result = query.all()
        return sum(int(row[0]) for row in result)

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

    @classmethod
    def get_acl_status(cls, news_item_id: int, user) -> tuple[bool, bool, bool]:

        news_item = cls.query.get(news_item_id)
        if news_item.news_item_data.remote_source is not None:
            return True, True, True
        query = (
            db.session.query(
                NewsItem.id,
                func.count().filter(ACLEntry.id != None).label("acls"),
                func.count().filter(ACLEntry.see).label("see"),
                func.count().filter(ACLEntry.access).label("access"),
                func.count().filter(ACLEntry.modify).label("modify"),
            )
            .distinct()
            .group_by(NewsItem.id)
            .filter(NewsItem.id == news_item_id)
        )

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

        query = ACLEntry.apply_query(query, user, False, False, False)

        result = query.all()
        see = result[0].see > 0 or result[0].acls == 0
        access = result[0].access > 0 or result[0].acls == 0
        modify = result[0].modify > 0 or result[0].acls == 0

        return see, access, modify

    def vote(self, data, user_id):
        if "vote" not in data:
            return

        vote = NewsItemVote.find(self.id, user_id)
        if vote is None:
            vote = self.create_new_vote(vote, user_id)

        if data["vote"] > 0:
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
        news_item = cls.find(id)

        news_item.update_status(data, user_id)

        NewsItemAggregate.update_status(news_item.news_item_aggregate_id)
        db.session.commit()

        return "success", 200

    def update_status(self, data, user_id):
        self.vote(data, user_id)

        if "read" in data:
            self.read = not self.read

        if "important" in data:
            self.important = not self.important

    @classmethod
    def delete(cls, news_item_id):
        news_item = cls.find(news_item_id)
        if NewsItemAggregate.is_assigned_to_report([{"type": "AGGREGATE", "id": news_item.news_item_aggregate_id}]) is False:
            return "aggregate_in_use", 500
        aggregate_id = news_item.news_item_aggregate_id
        aggregate = NewsItemAggregate.find(aggregate_id)
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


class NewsItemVote(db.Model):
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
    def find(cls, news_item_id, user_id):
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


class NewsItemAggregate(db.Model):
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
    def find(cls, aggregate_id):
        return cls.query.get(aggregate_id)

    @classmethod
    def get_by_id(cls, aggregate_id):
        aggregate = cls.find(aggregate_id)
        return NewsItemAggregateSchema().dump(aggregate)

    @classmethod
    def get_by_group(cls, group_id, filter: dict, user: User):
        logger.debug(f"Getting NewsItems Filtered: {filter}")
        query = cls.query.distinct().group_by(NewsItemAggregate.id)

        query = query.filter(NewsItemAggregate.osint_source_group_id == group_id)

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

        if "source" in filter and filter["source"] != "":
            query = query.filter(OSINTSource.id == filter["source"])

        if "search" in filter and filter["search"] != "":
            search_string = f"%{filter['search']}%"
            query = query.join(
                NewsItemAggregateSearchIndex,
                NewsItemAggregate.id == NewsItemAggregateSearchIndex.news_item_aggregate_id,
            ).filter(NewsItemAggregateSearchIndex.data.ilike(search_string))

        if "read" in filter and filter["read"].lower() == "true":
            query = query.filter(NewsItemAggregate.read is False)

        if "important" in filter and filter["important"].lower() == "true":
            query = query.filter(NewsItemAggregate.important is True)

        if "relevant" in filter and filter["relevant"].lower() == "true":
            query = query.filter(NewsItemAggregate.relevance > 0)

        if "in_report" in filter and filter["in_report"].lower() == "true":
            query = query.join(
                ReportItemNewsItemAggregate,
                NewsItemAggregate.id == ReportItemNewsItemAggregate.news_item_aggregate_id,
            )
        if "tags" in filter and filter["tags"] != "":
            query = query.join(
                NewsItemTag,
                NewsItemAggregate.id == NewsItemTag.n_i_a_id,
            )
            query = query.filter(NewsItemTag.name.in_(filter["tags"].split(",")))

        if "range" in filter and filter["range"] != "ALL":
            date_limit = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            if filter["range"] == "WEEK":
                date_limit -= timedelta(days=date_limit.weekday())

            elif filter["range"] == "MONTH":
                date_limit = date_limit.replace(day=1)

            query = query.filter(NewsItemAggregate.created >= date_limit)

        if "sort" in filter:
            if filter["sort"] == "DATE_DESC":
                query = query.order_by(db.desc(NewsItemAggregate.created), db.desc(NewsItemAggregate.id))

            elif filter["sort"] == "DATE_ASC":
                query = query.order_by(db.asc(NewsItemAggregate.created), db.asc(NewsItemAggregate.id))

            elif filter["sort"] == "RELEVANCE_DESC":
                query = query.order_by(db.desc(NewsItemAggregate.relevance), db.desc(NewsItemAggregate.id))

            elif filter["sort"] == "RELEVANCE_ASC":
                query = query.order_by(db.asc(NewsItemAggregate.relevance), db.asc(NewsItemAggregate.id))

        offset = filter.get("offset", 0)
        limit = filter.get("limit", 20)
        return query.offset(offset).limit(limit).all(), query.count()

    @classmethod
    def get_by_group_json(cls, group_id, filter, user):
        news_item_aggregates, count = cls.get_by_group(group_id, filter, user)
        for news_item_aggregate in news_item_aggregates:
            news_item_aggregate.me_like = False
            news_item_aggregate.me_dislike = False
            for news_item in news_item_aggregate.news_items:
                see, access, modify = NewsItem.get_acl_status(news_item.id, user)
                if not see:
                    news_item_aggregate.news_items.remove(news_item)
                    continue
                news_item.see = see
                news_item.access = access
                news_item.modify = modify
                vote = NewsItemVote.find(news_item.id, user.id)
                news_item.me_like = vote.like if vote is not None else False
                news_item_aggregate.me_like = vote.like if vote is not None else False
                news_item.me_dislike = vote.dislike if vote is not None else False
                news_item_aggregate.me_dislike = vote.dislike if vote is not None else False

            news_item_aggregate.in_reports_count = ReportItemNewsItemAggregate.count(news_item_aggregate.id)

        items = NewsItemAggregateSchema(many=True).dump(news_item_aggregates)

        return {"total_count": count, "items": items}

    @classmethod
    def create_new_for_all_groups(cls, news_item_data):
        groups = OSINTSourceGroup.get_all_with_source(news_item_data.osint_source_id)
        for group in groups:
            news_item = NewsItem()
            news_item.news_item_data = news_item_data
            db.session.add(news_item)

            aggregate = NewsItemAggregate()
            aggregate.title = news_item_data.title
            aggregate.description = news_item_data.review
            aggregate.created = news_item_data.published
            aggregate.osint_source_group_id = group.id
            aggregate.news_items.append(news_item)
            db.session.add(aggregate)

            NewsItemAggregateSearchIndex.prepare(aggregate)

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

    @classmethod
    def add_news_items(cls, news_items_data_list):
        try:
            news_items_data = NewNewsItemDataSchema(many=True).load(news_items_data_list)
        except ValidationError:
            logger.exception("Error while parsing news items")
            return
        osint_source_ids = set()
        if not news_items_data:
            return

        for news_item_data in news_items_data:
            if not NewsItemData.identical(news_item_data.hash):
                db.session.add(news_item_data)
                cls.create_new_for_all_groups(news_item_data)
                osint_source_ids.add(news_item_data.osint_source_id)

        db.session.commit()

        return osint_source_ids

    @classmethod
    def add_news_item(cls, news_item_data):
        news_item_data = NewNewsItemDataSchema().load(news_item_data)
        if not news_item_data:
            return
        if not news_item_data.id:  # type: ignore
            news_item_data.id = str(uuid.uuid4())  # type: ignore
        db.session.add(news_item_data)
        cls.create_new_for_all_groups(news_item_data)
        db.session.commit()

        return {news_item_data.osint_source_id}  # type: ignore

    @classmethod
    def reassign_to_new_groups(cls, osint_source_id, default_group_id):
        time_limit = datetime.now() - timedelta(days=7)
        news_items_query = NewsItem.get_all_by_group_and_source_query(default_group_id, osint_source_id, time_limit)
        for news_item in news_items_query:
            news_item_data = news_item.news_item_data
            aggregate = NewsItemAggregate.find(news_item.news_item_aggregate_id)
            aggregate.news_items.remove(news_item)
            NewsItemVote.delete_all(news_item.id)
            db.session.delete(news_item)
            NewsItemAggregate.update_status(aggregate.id)
            cls.create_new_for_all_groups(news_item_data)
            db.session.commit()

    @classmethod
    def add_remote_news_items(cls, news_items_data_list, remote_node, osint_source_group_id):
        news_items_data = NewNewsItemDataSchema(many=True).load(news_items_data_list)
        news_item_data_ids = set()
        if not news_items_data:
            return
        for news_item_data in news_items_data:
            news_item_data.remote_source = remote_node.name
            for attribute in news_item_data.attributes:
                attribute.remote_node_id = remote_node.id
                attribute.remote_user = remote_node.name

            original_news_item = NewsItemData.find_by_hash(news_item_data.hash)

            if original_news_item is None:
                db.session.add(news_item_data)
                cls.create_new_for_group(news_item_data, osint_source_group_id)
                news_item_data_ids.add(str(news_item_data.id))
            else:
                original_news_item.updated = datetime.now()
                for attribute in original_news_item.attributes[:]:
                    if attribute.remote_node_id == remote_node.id:
                        original_news_item.attributes.remove(attribute)
                        db.session.delete(attribute)

                original_news_item.attributes.extend(news_item_data.attributes)
                news_item_data_ids.add(str(original_news_item.id))

        db.session.commit()

        aggregate_ids = set()
        current_index = 0
        for news_item_data_id in news_item_data_ids:
            news_items = NewsItem.get_all_with_data(news_item_data_id)
            for news_item in news_items:
                had_relevance = NewsItemVote.delete_for_remote_node(news_item.id, remote_node.id)
                news_item.relevance -= had_relevance
                if had_relevance > 0:
                    news_item.likes -= 1
                elif had_relevance < 0:
                    news_item.dislikes -= 1

                if news_items_data_list[current_index]["relevance"] != 0:
                    vote = NewsItemVote(news_item.id, None)
                    vote.remote_node_id = remote_node.id
                    vote.remote_user = remote_node.name
                    if news_items_data_list[current_index]["relevance"] > 0:
                        vote.like = True
                        news_item.relevance += 1
                        news_item.likes += 1
                    else:
                        vote.dislike = True
                        news_item.relevance -= 1
                        news_item.dislikes += 1

                    db.session.add(vote)

                aggregate_ids.add(news_item.news_item_aggregate_id)

            current_index += 1

        db.session.commit()

        for aggregate_id in aggregate_ids:
            cls.update_status(aggregate_id)

        db.session.commit()

    @classmethod
    def update(cls, id, data, user):
        aggregate = cls.find(id)
        logger.debug(f"Updating news item aggregate {id} with data {data}")

        all_important = all(news_item.important is not False for news_item in aggregate.news_items)

        for news_item in aggregate.news_items:
            if NewsItem.allowed_with_acl(news_item.id, user, False, False, True):
                if "vote" in data:
                    news_item.vote(data, user.id)

                if "read" in data:
                    news_item.read = not aggregate.read

                if "important" in data:
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
    def delete(cls, id, user):
        if cls.is_assigned_to_report({id}):
            return "aggregate_in_use", 500

        aggregate = cls.find(id)
        for news_item in aggregate.news_items:
            if NewsItem.allowed_with_acl(news_item.id, user, False, False, True):
                aggregate.news_items.remove(news_item)
                NewsItem.delete_only(news_item)

        NewsItemAggregate.update_status(aggregate.id)

        db.session.commit()

        return "success", 200

    @classmethod
    def is_assigned_to_report(cls, aggregate_ids: list) -> bool:
        return any(ReportItemNewsItemAggregate.assigned(aggregate_id) for aggregate_id in aggregate_ids)

    @classmethod
    def update_tags(cls, news_item_aggregate_id, tags):
        try:
            n_i_a = cls.find(news_item_aggregate_id)
            if type(tags) is list:
                for tag in tags:
                    if tag not in n_i_a.tags:
                        n_i_a.tags.append(NewsItemTag(name=tag, tag_type="undef"))
            elif tags not in n_i_a.tags:
                n_i_a.tags.append(NewsItemTag(name=tags, tag_type="undef"))
            db.session.commit()
        except Exception:
            logger.log_debug_trace("Update News Item Tags Failed")

    @classmethod
    def group_aggregate(cls, aggregate_ids: list, user: User | None = None):
        try:
            first_aggregate = NewsItemAggregate.find(aggregate_ids.pop(0))
            processed_aggregates = {first_aggregate}
            for item in aggregate_ids:
                aggregate = NewsItemAggregate.find(item)
                for news_item in aggregate.news_items[:]:
                    if user is None or NewsItem.allowed_with_acl(news_item.id, user, False, False, True):
                        first_aggregate.news_items.append(news_item)
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
                news_item = NewsItem.find(item)
                if not NewsItem.allowed_with_acl(news_item.id, user, False, False, True):
                    continue
                aggregate = NewsItemAggregate.find(news_item.news_item_aggregate_id)
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
        aggregate = cls.find(aggregate_id)

        if len(aggregate.news_items) == 0:
            NewsItemAggregateSearchIndex.remove(aggregate)
            db.session.delete(aggregate)
            return

        aggregate.relevance = 0
        aggregate.read = True
        aggregate.important = False
        aggregate.likes = 0
        aggregate.dislikes = 0
        for news_item in aggregate.news_items:
            aggregate.relevance += news_item.relevance
            aggregate.likes += news_item.likes
            aggregate.dislikes += news_item.dislikes
            aggregate.important |= news_item.important
            aggregate.read &= news_item.read

    @classmethod
    def update_news_items_aggregate_summary(cls, aggregate_id, summary):
        try:
            aggregate = cls.find(aggregate_id)
            aggregate.summary = summary
            db.session.commit()
        except Exception:
            logger.log_debug_trace(f"Update News Aggregate Summary Failed for {aggregate_id}")

    @classmethod
    def get_news_items_aggregate(cls, source_group, limit: str):
        filter_date = cls.get_filter_date(limit)
        # TODO: Change condition in query to >
        news_item_aggregates = cls.query.filter(cls.osint_source_group_id == source_group).filter(cls.created > filter_date).all()
        news_item_aggregate_schema = NewsItemAggregateSchema(many=True)
        return news_item_aggregate_schema.dumps(news_item_aggregates)

    @classmethod
    def get_filter_date(cls, limit: str) -> datetime | None:
        try:
            return dateparser.parse(limit)
        except Exception:
            return None

    @classmethod
    def get_default_news_items_aggregate(cls, limit: str):
        source_group = OSINTSourceGroup.get_default().id
        query = cls.query.filter(cls.osint_source_group_id == source_group)

        filter_date = cls.get_filter_date(limit)
        query = query.filter(cls.created > filter_date)
        news_item_aggregates = query.all()
        return NewsItemAggregateSchema(many=True).dumps(news_item_aggregates)


class NewsItemAggregateSearchIndex(db.Model):
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
        data += f" {aggregate.tags}"

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


class NewsItemAttribute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(), nullable=False)
    value = db.Column(db.String(), nullable=False)
    binary_mime_type = db.Column(db.String())
    binary_data = orm.deferred(db.Column(db.LargeBinary))
    created = db.Column(db.DateTime, default=datetime.now)

    remote_node_id = db.Column(db.Integer, db.ForeignKey("remote_node.id"), nullable=True)
    remote_user = db.Column(db.String())

    def __init__(self, key, value, binary_mime_type, binary_value):
        # self.id = id
        self.id = None
        self.key = key
        self.value = value
        self.binary_mime_type = binary_mime_type

        if binary_value:
            self.binary_data = base64.b64decode(binary_value)

    @classmethod
    def find(cls, attribute_id):
        return cls.query.get(attribute_id)


class NewsItemDataNewsItemAttribute(db.Model):
    news_item_data_id = db.Column(db.String, db.ForeignKey("news_item_data.id"), primary_key=True)
    news_item_attribute_id = db.Column(db.Integer, db.ForeignKey("news_item_attribute.id"), primary_key=True)

    @classmethod
    def find(cls, attribute_id):
        return cls.query.filter(NewsItemDataNewsItemAttribute.news_item_attribute_id == attribute_id).scalar()


class NewsItemAggregateNewsItemAttribute(db.Model):
    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"), primary_key=True)
    news_item_attribute_id = db.Column(db.Integer, db.ForeignKey("news_item_attribute.id"), primary_key=True)


class ReportItemNewsItemAggregate(db.Model):
    report_item_id = db.Column(db.Integer, db.ForeignKey("report_item.id"), primary_key=True)
    news_item_aggregate_id = db.Column(db.Integer, db.ForeignKey("news_item_aggregate.id"), primary_key=True)

    @classmethod
    def assigned(cls, aggregate_id):
        return db.session.query(db.exists().where(ReportItemNewsItemAggregate.news_item_aggregate_id == aggregate_id)).scalar()

    @classmethod
    def count(cls, aggregate_id):
        return cls.query.filter_by(news_item_aggregate_id=aggregate_id).count()


class NewsItemTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    tag_type = db.Column(db.String(255))
    n_i_a_id = db.Column(db.ForeignKey(NewsItemAggregate.id, ondelete="CASCADE"), nullable=False)
    n_i_a = db.relationship(NewsItemAggregate, backref="tags")

    def __init__(self, name, tag_type):
        self.id = None
        self.name = name
        self.tag_type = tag_type

    @classmethod
    def find(cls, tag_id):
        return cls.query.get(tag_id)

    @classmethod
    def search(cls, tag_name=""):
        return cls.query.filter(cls.name.ilike(f"%{tag_name}%"))

    @classmethod
    def get_json(cls, tag_name=""):
        rows = cls.search(tag_name).all()
        return [row.name for row in rows]

    @classmethod
    def remove(cls, tag):
        if tag := cls.find(tag.id):
            db.session.delete(tag)
            db.session.commit()

    @classmethod
    def remove_by_aggregate(cls, aggregate):
        tags = cls.query.filter_by(n_i_a_id=aggregate.id).all()
        for tag in tags:
            db.session.delete(tag)
        db.session.commit()
