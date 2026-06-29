import re
from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any, cast

from models.assess import NewsItem as AssessNewsItem
from models.assess import Story as StoryPayload
from pydantic import ValidationError
from sqlalchemy import func, inspect, or_
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, aliased, relationship
from sqlalchemy.sql import Select
from sqlalchemy.sql.expression import false, null, true

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel
from core.model.news_item import NewsItem
from core.model.news_item_attribute import NewsItemAttribute
from core.model.news_item_conflict import NewsItemConflict
from core.model.news_item_tag import NewsItemTag
from core.model.osint_source import OSINTSource, OSINTSourceGroup, OSINTSourceGroupOSINTSource
from core.model.revision import StoryRevision
from core.model.role import TLPLevel
from core.model.role_based_access import ItemType
from core.model.story_conflict import StoryConflict
from core.model.user import User
from core.service.role_based_access import RBACQuery, RoleBasedAccessService
from core.service.story_operations import StoryOperationsService


class Story(BaseModel):
    __tablename__ = "story"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    title: Mapped[str] = db.Column(db.String())
    description: Mapped[str] = db.Column(db.String())
    created: Mapped[datetime] = db.Column(db.DateTime)
    updated: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow)

    read: Mapped[bool] = db.Column(db.Boolean, default=False)
    important: Mapped[bool] = db.Column(db.Boolean, default=False)

    likes: Mapped[int] = db.Column(db.Integer, default=0)
    dislikes: Mapped[int] = db.Column(db.Integer, default=0)
    relevance: Mapped[int] = db.Column(db.Integer, default=0)
    relevance_override: Mapped[int] = db.Column(db.Integer, default=0)

    comments: Mapped[str] = db.Column(db.String(), default="")
    summary: Mapped[str] = db.Column(db.Text, default="")
    revision: Mapped[int] = db.Column(db.Integer, nullable=False, default=0)
    news_items: Mapped[list["NewsItem"]] = relationship("NewsItem")
    last_change: Mapped[str] = db.Column(db.String())
    attributes: Mapped[list["NewsItemAttribute"]] = relationship(
        "NewsItemAttribute", secondary="story_news_item_attribute", cascade="all, delete"
    )
    search_vector = db.Column(db.Text().with_variant(TSVECTOR(), "postgresql"), server_default="")

    def __init__(
        self,
        title: str,
        description: str = "",
        created: datetime | str | None = None,
        id: str | None = None,
        likes: int = 0,
        dislikes: int = 0,
        relevance: int = 0,
        relevance_override: int | None = None,
        read: bool = False,
        important: bool = False,
        summary: str = "",
        comments: str = "",
        revision: int = 0,
        attributes: list[dict[str, Any]] | None = None,
        news_items: list[dict[str, Any]] | list[str] | list[NewsItem] | None = None,
        last_change: str | None = None,
        updated: datetime | str | None = None,
    ):
        self.id = self.normalize_uuid_id(id)
        self.likes = likes
        self.dislikes = dislikes
        self.relevance = 0
        self.title = title
        self.description = description
        self.read = read
        self.important = important
        self.summary = summary
        self.comments = comments
        self.revision = revision
        self.news_items = self.load_news_items(news_items)
        self.last_change = last_change or "internal"
        self.relevance_override = relevance if relevance_override is None else relevance_override
        if attributes:
            self.attributes = NewsItemAttribute.load_multiple(attributes)
        self.created, self.updated = self.get_story_dates(created, updated)
        self.recompute_relevance(in_reports_count=0)

    @classmethod
    def _is_actor_change(cls, last_change: str | None) -> bool:
        return isinstance(last_change, str) and last_change.startswith(("user_", "collector_", "bot", "connector_", "system_"))

    @classmethod
    def last_change_for_user(cls, user: User | None) -> str | None:
        if not user:
            return None
        return f"user_{user.username}_{user.id}"

    @classmethod
    def user_for_actor(cls, actor: str | None) -> User | None:
        if not isinstance(actor, str) or not actor.startswith("user_"):
            return None

        _, _, user_id = actor.rpartition("_")
        if not (user := User.get(user_id)):
            return None

        return user if cls.last_change_for_user(user) == actor else None

    @classmethod
    def last_change_for_connector(cls, connector_id: str | None) -> str | None:
        if not connector_id:
            return None
        return f"connector_{connector_id}"

    @classmethod
    def last_change_for_worker(cls, worker_kind: str, worker_type: str | None, worker_id: str | None) -> str | None:
        if not worker_type or not worker_id:
            return None
        normalized_kind = worker_kind.strip().lower()
        normalized_type = worker_type.strip().lower()
        return f"{normalized_kind}_{normalized_type}_{worker_id}"

    @classmethod
    def last_change_for_collector(cls, collector_type: str | None, collector_id: str | None) -> str | None:
        return cls.last_change_for_worker("collector", collector_type, collector_id)

    @classmethod
    def resolve_actor(cls, user: User | None = None, actor: str | None = None) -> str | None:
        if actor and cls._is_actor_change(actor):
            return actor
        return cls.last_change_for_user(user)

    @classmethod
    def last_change_for_source(cls, source: OSINTSource | None) -> str | None:
        if not source:
            return None
        source_type = getattr(source.type, "value", source.type)
        return cls.last_change_for_collector(str(source_type) if source_type is not None else None, source.id)

    @staticmethod
    def _is_manual_source(source: OSINTSource | None) -> bool:
        if not source:
            return False
        source_type = getattr(source.type, "value", source.type)
        return "manual" in str(source_type).lower()

    @classmethod
    def _resolve_actor(
        cls,
        *,
        user: User | None = None,
        actor: str | None = None,
        source: OSINTSource | None = None,
        connector_id: str | None = None,
    ) -> str | None:
        if resolved_actor := cls.resolve_actor(user=user, actor=actor):
            return resolved_actor
        if connector_id is not None:
            return cls.last_change_for_connector(connector_id)
        if source is not None and not cls._is_manual_source(source):
            return cls.last_change_for_source(source)
        return None

    @classmethod
    def _determine_actor_for_update(
        cls,
        *,
        story: "Story",
        user: User | None = None,
        external: bool = False,
        actor: str | None = None,
    ) -> str | None:
        if user is not None:
            return cls.last_change_for_user(user)
        if external and not cls._is_actor_change(actor):
            return story.last_change if cls._is_actor_change(story.last_change) else "external"
        if not cls._is_actor_change(actor) and cls._is_actor_change(story.last_change):
            return story.last_change
        return actor

    @staticmethod
    def _first_news_item_source(news_items: list[dict[str, Any]] | list[str] | list[NewsItem] | None) -> OSINTSource | None:
        if not news_items:
            return None
        first_item = news_items[0]
        news_item_id = None
        if isinstance(first_item, dict):
            news_item_id = first_item.get("id")
            source_id = first_item.get("osint_source_id")
            if source_id and (source := OSINTSource.get(source_id)):
                return source
            if news_item_id and (news_item := NewsItem.get(news_item_id)) and news_item.osint_source:
                return news_item.osint_source
        elif isinstance(first_item, str):
            if news_item := NewsItem.get(first_item):
                return news_item.osint_source
        elif isinstance(first_item, NewsItem):
            return first_item.osint_source
        return None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Story":
        return cls(**StoryPayload.model_validate(data).to_core_dict())

    def get_story_dates(self, created: datetime | str | None, updated: datetime | str | None) -> tuple[datetime, datetime]:
        payload = StoryPayload.model_validate({"created": created, "updated": updated})
        if payload.created:
            created_date = payload.created
            return created_date, payload.updated or created_date

        published_dates = self._published_dates()
        if not published_dates:
            created_date = self.utcnow()
            return created_date, payload.updated or created_date

        created_date = min(published_dates, key=self._comparison_timestamp)
        updated_date = payload.updated or max(published_dates, key=self._comparison_timestamp)
        return created_date, updated_date

    def _published_dates(self) -> list[datetime]:
        return [news_item.published for news_item in self.news_items if news_item.published]

    def load_news_items(self, news_items: list[dict[str, Any]] | list[str] | list[NewsItem] | None) -> list["NewsItem"]:
        if not news_items:
            return []
        if isinstance(news_items[0], dict):
            return NewsItem.load_multiple([item for item in news_items if isinstance(item, dict)])
        if isinstance(news_items[0], str):
            loaded_news_items = [NewsItem.get(item_id) for item_id in news_items if isinstance(item_id, str)]
            return [news_item for news_item in loaded_news_items if news_item]
        if isinstance(news_items[0], NewsItem):
            return [item for item in news_items if isinstance(item, NewsItem)]
        return []

    @property
    def links(self) -> list[str]:
        return [item.link for item in self.news_items if getattr(item, "link", None)]

    @property
    def tags(self) -> list["NewsItemTag"]:
        tags_by_identity: dict[tuple[str, str], NewsItemTag] = {}
        for news_item in self.news_items:
            for tag in news_item.tags:
                if tag.name:
                    tags_by_identity[(tag.name, tag.tag_type or "misc")] = tag
        return [tags_by_identity[identity] for identity in sorted(tags_by_identity)]

    @staticmethod
    def refresh_tag_summaries_for_news_items(news_items: list["NewsItem"]) -> None:
        summary_keys = set()
        for news_item in news_items:
            summary_keys.update(news_item.get_tag_summary_keys())

        if not summary_keys:
            return

        from core.model.news_item_tag import NewsItemTagCluster

        db.session.flush()
        NewsItemTagCluster.refresh_for_keys(summary_keys)

    @classmethod
    def refresh_tag_summaries_for_stories(cls, stories: list["Story"] | set["Story"]) -> None:
        news_items_by_id = {}
        for story in stories:
            for news_item in story.news_items:
                news_items_by_id[news_item.id] = news_item

        cls.refresh_tag_summaries_for_news_items(list(news_items_by_id.values()))

    @property
    def relevance_source(self) -> int:
        return StoryOperationsService.calculate_source_relevance(self)

    @property
    def relevance_feedback(self) -> int:
        return StoryOperationsService.calculate_relevance_feedback(self)

    def recompute_relevance(self, in_reports_count: int | None = None) -> int:
        return StoryOperationsService.recompute_relevance(self, in_reports_count)

    @classmethod
    def get_for_api(cls, item_id: str, user: User | None = None) -> tuple[dict[str, Any], int]:
        logger.debug(f"Getting {cls.__name__} {item_id}")
        query = db.select(cls).filter(cls.id == item_id)
        if user:
            query = cls._add_ACL_check(query, user)
            query = cls._add_TLP_check(query, user)
            query = cls.enhance_with_user_votes(query, user.id)

            if result := db.session.execute(query).first():
                story, user_vote = result
                story_data = story.to_detail_dict()
                story_data["user_vote"] = user_vote
                return story_data, 200

        if item := db.session.execute(query).scalar():
            return item.to_detail_dict(), 200
        return {"error": f"{cls.__name__} not found"}, 404

    @classmethod
    def get_additional_counts(cls, filter_query):
        subquery = filter_query.subquery()
        total_count_subquery = db.select(func.count()).select_from(subquery).scalar_subquery()
        read_count_subquery = db.select(func.count()).select_from(subquery).where(subquery.c.read == true()).scalar_subquery()
        important_count_subquery = db.select(func.count()).select_from(subquery).where(subquery.c.important == true()).scalar_subquery()
        in_reports_count_subquery = (
            db.select(func.count())
            .select_from(subquery)
            .join(ReportItemStory, ReportItemStory.story_id == subquery.c.id)
            .distinct()
            .scalar_subquery()
        )

        count_query = db.select(
            read_count_subquery.label("read_count"),
            important_count_subquery.label("important_count"),
            total_count_subquery.label("total_count"),
            in_reports_count_subquery.label("in_reports_count"),
        )

        return db.session.execute(count_query).one()

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls).group_by(cls.id).join(NewsItem, NewsItem.story_id == cls.id)
        query = query.join(OSINTSource, NewsItem.osint_source_id == OSINTSource.id)

        if item_id := filter_args.get("story_id"):
            return query.filter(cls.id == item_id)

        if item_ids := filter_args.get("story_ids"):
            return query.filter(cls.id.in_(item_ids))

        source_group_filters = []

        if filter_args.get("group"):
            query = query.outerjoin(OSINTSourceGroupOSINTSource, OSINTSource.id == OSINTSourceGroupOSINTSource.osint_source_id)
            query = query.outerjoin(OSINTSourceGroup, OSINTSourceGroupOSINTSource.osint_source_group_id == OSINTSourceGroup.id)

        if group := filter_args.get("group"):
            source_group_filters.append(OSINTSourceGroup.id.in_(group))

        if source := filter_args.get("source"):
            source_group_filters.append(OSINTSource.id.in_(source))

        if source_group_filters:
            query = query.filter(or_(*source_group_filters))

        if language := filter_args.get("language"):
            languages = language if isinstance(language, list) else [language]
            languages = [str(lang).strip().lower() for lang in languages if lang is not None and str(lang).strip()]
            if languages:
                query = query.filter(func.lower(NewsItem.language).in_(languages))
            else:
                query = query.filter(false())

        if search := filter_args.get("search"):
            sort: bool = "relevance" in filter_args.get("sort", "").lower()
            query = cls._add_search_to_query(search, query, sort=sort)

        if exclude_attr := filter_args.get("exclude_attr"):
            query = cls._add_attribute_filter_to_query(query, exclude_attr, exclude=True)

        if include_attr := filter_args.get("include_attr"):
            query = cls._add_attribute_filter_to_query(query, include_attr, exclude=False)

        read = filter_args.get("read", "").lower()
        if read == "true":
            query = query.filter(Story.read)
        if read == "false":
            query = query.filter(Story.read == false())

        important = filter_args.get("important", "").lower()
        if important == "true":
            query = query.filter(Story.important)
        if important == "false":
            query = query.filter(Story.important == false())

        if cybersecurity_status := filter_args.get("cybersecurity", "").lower():
            query = cls._add_key_value_filter_to_query(query, "cybersecurity", cybersecurity_status)

        relevant = filter_args.get("relevant", "").lower()
        if relevant == "true":
            query = query.filter(Story.relevance > 0)
        if relevant == "false":
            query = query.filter(Story.relevance <= 0)

        in_report = filter_args.get("in_report", "").lower()
        if in_report == "true":
            query = query.join(
                ReportItemStory,
                Story.id == ReportItemStory.story_id,
            )
        if in_report == "false":
            query = query.outerjoin(
                ReportItemStory,
                Story.id == ReportItemStory.story_id,
            ).filter(ReportItemStory.story_id == null())

        if tags := filter_args.get("tags"):
            for tag in tags:
                item_alias = aliased(NewsItem)
                tag_alias = aliased(NewsItemTag)
                query = (
                    query.join(item_alias, item_alias.story_id == Story.id)
                    .join(tag_alias, item_alias.id == tag_alias.news_item_id)
                    .filter(or_(tag_alias.name == tag, tag_alias.tag_type == tag))
                )

        if changed_by := filter_args.get("changed_by"):
            if changed_by == "me" and (user := filter_args.get("_user")):
                actor = cls.last_change_for_user(user)
                if actor:
                    query = query.filter(cls.last_change == actor)
            elif changed_by:
                query = query.filter(cls.last_change == changed_by)

        if filter_range := filter_args.get("range", "").lower():
            date_limit = cls.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            if filter_range in ["day", "week", "month", "24h"]:
                if filter_range == "day":
                    date_limit -= timedelta(days=1)

                elif filter_range == "24h":
                    date_limit -= timedelta(hours=24)

                elif filter_range == "week":
                    date_limit -= timedelta(days=date_limit.weekday())

                elif filter_range == "month":
                    date_limit = date_limit.replace(day=1)

            elif filter_range.startswith("last") and filter_range[4:].isdigit():
                days = int(filter_range[4:])
                date_limit -= timedelta(days=days)

            query = query.filter(cls.created >= date_limit)

        if timefrom := filter_args.get("timefrom"):
            normalized_timefrom = StoryPayload.model_validate({"created": timefrom}).created
            query = query.filter(cls.created >= normalized_timefrom)

        if timeto := filter_args.get("timeto"):
            normalized_timeto = StoryPayload.model_validate({"updated": timeto}).updated
            query = query.filter(cls.updated <= normalized_timeto)

        return query

    @classmethod
    def _add_search_to_query(cls, search: str, query: Select, sort: bool = False) -> Select:
        if db.engine.dialect.name == "postgresql":
            search_term = search.strip()
            if not search_term:
                return query

            ts_query = None
            if search_term.endswith("*"):
                prefix_body = search_term[:-1].strip()
                prefix_tokens = [cleaned for token in prefix_body.split() if (cleaned := re.sub(r"[^\w]", "", token))]
                if prefix_tokens:
                    prefix_query = " & ".join(f"{token}:*" for token in prefix_tokens)
                    ts_query = func.to_tsquery("simple", func.unaccent(prefix_query))

            if ts_query is None:
                ts_query = func.websearch_to_tsquery("simple", func.unaccent(search_term))

            logger.debug(f"FTS with: {search=} {sort=}")
            q = query.where(cls.search_vector.op("@@")(ts_query))
            if sort:
                q = q.order_by(db.desc(func.ts_rank_cd(cls.search_vector, ts_query, 32)))
            return q

        return cls._add_sqlite_search_query(search, query)

    @classmethod
    def _add_sqlite_search_query(cls, search: str, query: Select) -> Select:
        pattern = f"%{search}%"

        news_exists = cls.news_items.any(or_(NewsItem.title.ilike(pattern), NewsItem.content.ilike(pattern)))

        return query.where(
            or_(
                cls.title.ilike(pattern),
                cls.summary.ilike(pattern),
                news_exists,
            )
        )

    @classmethod
    def _add_sorting_to_query(cls, filter_args: dict[str, str], query: Select) -> Select:
        if sort := filter_args.get("sort", "date_desc").lower():
            if sort == "date_desc":
                query = query.order_by(db.desc(cls.created), db.desc(cls.title))

            elif sort == "date_asc":
                query = query.order_by(db.asc(cls.created), db.asc(cls.title))

            elif sort == "relevance":
                query = query.order_by(db.desc(cls.relevance), db.desc(cls.created))

            elif sort == "updated_desc":
                query = query.order_by(db.desc(cls.updated), db.desc(cls.title))

            elif sort == "updated_asc":
                query = query.order_by(db.asc(cls.updated), db.asc(cls.title))

        return query

    @classmethod
    def _add_key_value_filter_to_query(cls, query: Select, filter_key: str, filter_value: str) -> Select:
        nia1 = aliased(NewsItemAttribute)
        snia1 = aliased(StoryNewsItemAttribute)

        subquery = (
            db.select(snia1.story_id)
            .join(nia1, nia1.id == snia1.news_item_attribute_id)
            .filter((nia1.key == filter_key) & (nia1.value == filter_value))
            .distinct()
        )
        return query.filter(Story.id.in_(subquery))

    @classmethod
    def _add_attribute_filter_to_query(cls, query: Select, filter_key: str, exclude: bool = False) -> Select:
        nia2 = aliased(NewsItemAttribute)
        snia2 = aliased(StoryNewsItemAttribute)

        subquery = db.select(snia2.story_id).join(nia2, nia2.id == snia2.news_item_attribute_id).filter(nia2.key == filter_key).distinct()

        query = query.outerjoin(StoryNewsItemAttribute, StoryNewsItemAttribute.story_id == Story.id).outerjoin(
            NewsItemAttribute, NewsItemAttribute.id == StoryNewsItemAttribute.news_item_attribute_id
        )

        if exclude:
            return query.filter(Story.id.notin_(subquery))
        return query.filter(Story.id.in_(subquery))

    @classmethod
    def _add_paging_to_query(cls, filter_args: dict[str, Any], query: Select) -> Select:
        if offset := filter_args.get("offset"):
            query = query.offset(offset)
        if limit := filter_args.get("limit"):
            query = query.limit(limit)
        return query

    @classmethod
    def _add_ACL_check(cls, query: Select, user: User) -> Select:
        rbac = RBACQuery(user=user, resource_type=ItemType.OSINT_SOURCE)
        return RoleBasedAccessService.filter_query_with_acl(query, rbac)

    @classmethod
    def _add_TLP_check(cls, query: Select, user: User) -> Select:
        return RoleBasedAccessService.filter_query_with_tlp(query, user)

    @classmethod
    def enhance_with_user_votes(cls, query: Select, user_id: str) -> Select:
        vote_subquery = (
            db.select(NewsItemVote.item_id, NewsItemVote.user_vote_expr.label("user_vote")).filter(NewsItemVote.user_id == user_id).subquery()
        )

        query = query.outerjoin(vote_subquery, Story.id == vote_subquery.c.item_id)
        query = query.add_columns(func.coalesce(vote_subquery.c.user_vote, "").label("user_vote"))
        query = query.group_by(Story.id, vote_subquery.c.user_vote)

        return query

    @classmethod
    def enhance_with_report_count(cls, query: Select) -> Select:
        report_subquery = (
            db.select(ReportItemStory.story_id, func.count().label("report_count"))
            .group_by(ReportItemStory.story_id)
            .correlate(None)
            .subquery()
        )
        query = query.outerjoin(report_subquery, Story.id == report_subquery.c.story_id)
        query = query.add_columns(func.coalesce(report_subquery.c.report_count, 0).label("report_count"))
        query = query.group_by(Story.id, report_subquery.c.report_count)
        return query

    @classmethod
    def get_by_filter(cls, filter_args: dict[str, Any], user: User | None = None) -> tuple[list[dict[str, Any]], dict[str, int] | None]:
        if user:
            filter_args = {**filter_args, "_user": user}
        base_query = cls.get_filter_query(filter_args)
        if user:
            base_query = cls._add_ACL_check(base_query, user)
            base_query = cls._add_TLP_check(base_query, user)

        query = cls._add_sorting_to_query(filter_args, base_query)
        query = cls._add_paging_to_query(filter_args, query)

        if filter_args.get("worker", False) or not user:
            return [s.to_worker_dict() for s in cls.get_filtered(query) or []], None

        if filter_args.get("no_count", False):
            stories = []
            for story in cls.get_filtered(query) or []:
                story_data = story.to_dict()
                story_data["revision_count"] = story.get_revision_count()
                stories.append(story_data)
            return stories, None

        stories = []
        biggest_story = 0
        query = cls.enhance_with_user_votes(query, user.id)
        query = cls.enhance_with_report_count(query)

        for story, user_vote, report_count in db.session.execute(query):
            story_data = story.to_dict()
            story_data["revision_count"] = story.get_revision_count()
            story_data["user_vote"] = user_vote
            story_data["in_reports_count"] = report_count
            biggest_story = max(biggest_story, len(story_data["news_items"]))
            stories.append(story_data)

        additional_counts = cls.get_additional_counts(base_query)

        count_dict = {
            "total_count": additional_counts.total_count,
            "read_count": additional_counts.read_count,
            "important_count": additional_counts.important_count,
            "in_reports_count": additional_counts.in_reports_count,
            "biggest_story": biggest_story,
        }

        return stories, count_dict

    @classmethod
    def get_by_filter_json(cls, filter_args: dict[str, Any], user: User | None):
        stories, count = cls.get_by_filter(filter_args=filter_args, user=user)

        if count:
            return {"items": stories, "counts": count}, 200

        return {"items": stories}, 200

    @classmethod
    def get_for_worker(cls, filter_args: dict[str, Any]) -> list[dict[str, Any]]:
        filter_args["worker"] = True
        stories, _ = cls.get_by_filter(filter_args=filter_args)
        return stories

    @classmethod
    def delete_news_items(cls, news_items_to_delete: list[str]):
        for news_item_id in news_items_to_delete:
            if news_item := NewsItem.get(news_item_id):
                news_item.delete_item()

    @classmethod
    def add_or_update(cls, data) -> "tuple[dict, int]":
        if "id" not in data:
            return cls.add(data)

        story_id = data.get("id")
        if Story.get(story_id) is None:
            return cls._handle_new_story_add(data)

        if data.pop("conflict", None):
            return cls.update_with_conflicts(story_id, data)
        else:
            return cls._handle_existing_story_update(data)

    @classmethod
    def _handle_new_story_add(cls, data) -> "tuple[dict, int]":
        message, code = cls.add(data)
        if code != 200 and message.get("error") == "Story already exists":
            logger.warning(f"Story being added {data['id']} contains existing content. A news item conflict is raised.")
            cls.handle_conflicting_news_items(data)
            return {"error": "Story contains existing content. A news item conflict is raised."}, 409
        return message, code

    @classmethod
    def _handle_existing_story_update(cls, data) -> "tuple[dict, int]":
        story_ids = [data["id"]]
        news_item_to_delete = data.pop("news_items_to_delete", None)

        skipped_story_ids, added_story_ids = cls._process_news_items(data)
        story_ids += added_story_ids

        if cls._has_cross_story_conflict(data["id"], skipped_story_ids):
            cls._remove_conflicting_stories(data["id"], story_ids[1:])
            return cls.handle_conflicting_news_items(data)

        if news_item_to_delete:
            cls.delete_news_items(news_item_to_delete)

        cls.group_stories(story_ids)
        return cls.update(data["id"], data, external=True)

    @classmethod
    def _process_news_items(cls, data: dict[str, Any]) -> "tuple[list[str], list[str]]":
        skipped = []
        added = []
        for news_item in data.get("news_items", []):
            result, code = cls.add_single_news_item(news_item)
            if skipped_id := result.get("skipped_news_item_story_id"):
                skipped.append(skipped_id)
            if story_id := result.get("story_id"):
                added.append(story_id)
            logger.debug(f"News item {news_item.get('id')} added with result: {result}")
        return skipped, added

    @classmethod
    def _has_cross_story_conflict(cls, target_id: str, skipped_story_ids: list[str]) -> bool:
        return any(sid != target_id for sid in skipped_story_ids)

    @classmethod
    def _remove_conflicting_stories(cls, target_id: str, story_ids: list[str]) -> None:
        for story_id in story_ids:
            if story := cls.get(story_id):
                logger.debug(f"Deleting story {story_id} due to incoming conflict with target story {target_id}.")
                story.delete(story_id)

    @classmethod
    def add(cls, data, user: User | None = None, actor: str | None = None) -> "tuple[dict[str, Any], int]":
        try:
            if attributes := data.get("attributes"):
                data["attributes"] = NewsItemAttribute.unify_attributes_to_old_format(attributes)
            source = cls._first_news_item_source(data.get("news_items"))
            resolved_actor = cls._resolve_actor(user=user, actor=actor, source=source)
            if resolved_actor is None and cls._is_actor_change(data.get("last_change")):
                resolved_actor = data.get("last_change")
            if resolved_actor is not None:
                data = {**data, "last_change": resolved_actor}
            story = cls.from_dict(data)
            for news_item in story.news_items:
                source = news_item.osint_source or OSINTSource.get(news_item.osint_source_id)
                if source and cls._is_manual_source(source):
                    news_item.last_change = "internal"
                    continue
                if source and (actor := cls.last_change_for_source(source)):
                    news_item.last_change = actor
            db.session.add(story)
            db.session.flush()
            cls.refresh_tag_summaries_for_news_items(story.news_items)
            story.update_status(change=resolved_actor, refresh_timestamps=False)
            story.record_revision(note="created")
            db.session.commit()

            logger.info(f"Story added successfully: {story.id}")
            return {
                "message": "Story added successfully",
                "story_id": story.id,
                "news_item_ids": [news_item.id for news_item in story.news_items],
            }, 200
        except IntegrityError:
            logger.exception()
            db.session.rollback()
            return {"error": "Story already exists"}, 400

        except Exception:
            logger.exception(f"Failed to add story: {data}")
            db.session.rollback()
            return {"error": "Failed to add story"}, 400

    @classmethod
    def add_from_news_item(cls, news_item: AssessNewsItem, user: User | None = None) -> "tuple[dict, int]":
        if news_item_obj := NewsItem.get_by_hash(news_item.hash):
            logger.warning("Identical news item found. Skipping...")
            return {
                "error": "Identical news item found. Skipping...",
                "skipped_news_item_story_id": news_item_obj.story_id if news_item_obj else None,
            }, 409

        data = {
            "title": news_item.title,
            "created": news_item.published,
            "news_items": [news_item.to_core_dict()],
        }

        return cls.add(data, user=user)

    @classmethod
    def add_or_update_for_misp(cls, data: list[dict[str, Any]], force: bool = False) -> "tuple[dict[str, Any], int]":
        if not data:
            return {"error": "No data provided"}, 400
        prepared_stories = cls.prepare_misp_stories(data, force=force)
        results = []
        story_ids = []
        status = 200
        for story in prepared_stories:
            result, status = cls.add_or_update(story)
            if status != 200:
                results.append(result)
            elif status == 200:
                story_ids.append(result.get("story_id", result.get("id", result)))
        StoryConflict.enforce_quota()
        NewsItemConflict.enforce_quota()
        if results:
            return {"error": "Some stories could not be added", "details": {"errors": results}}, status
        return {"message": "Stories added or updated successfully", "details": {"story_ids": story_ids}}, 200

    @classmethod
    def check_news_item_data(cls, news_item: dict[str, Any]) -> tuple[AssessNewsItem | None, dict[str, str] | None]:
        try:
            return AssessNewsItem.from_input(news_item), None
        except ValidationError as exc:
            return None, AssessNewsItem.validation_error_response(cast(Any, exc), prefix="Invalid news item data")

    @classmethod
    def add_single_news_item(cls, news_item: dict, user: User | None = None) -> tuple[dict, int]:
        normalized_news_item, err = cls.check_news_item_data(news_item)
        if err:
            logger.error(err)
            return err, 400
        if normalized_news_item is None:
            return {"error": "Invalid news item data"}, 400
        try:
            return cls.add_from_news_item(normalized_news_item, user=user)
        except Exception:
            logger.exception("Failed to add news items")
            return {"error": "Failed to add news items"}, 400

    @classmethod
    def add_news_items(cls, news_items_list: list[dict], user: User | None = None):
        story_ids = []
        news_item_ids = []
        skipped_items = []
        try:
            for news_item in news_items_list:
                normalized_news_item, err = cls.check_news_item_data(news_item)
                if err:
                    logger.warning(err)
                    skipped_items.append(err)
                    continue
                if normalized_news_item is None:
                    skipped_items.append(news_item.get("title", "Unknown Title"))
                    continue
                message, status = cls.add_from_news_item(normalized_news_item, user=user)
                if status > 299:
                    skipped_items.append(normalized_news_item.title or news_item.get("title", "Unknown Title"))
                    continue
                story_ids.append(message["story_id"])
                news_item_ids += message["news_item_ids"]
            db.session.commit()
        except Exception:
            logger.exception("Failed to add news items")
            return {"error": "Failed to add news items"}, 400

        result = {"story_ids": story_ids, "news_item_ids": news_item_ids, "message": f"{len(news_item_ids)} News items added successfully"}
        if len(skipped_items) == len(news_items_list):
            result["message"] = "All news items were skipped"
            logger.warning(result)
            return result, 200
        if skipped_items:
            result["warning"] = f"{len(skipped_items)} items were skipped"
            logger.warning(result)
        logger.info(f"News items added successfully: {result}")
        return result, 200

    @classmethod
    def update(cls, story_id: str, data, user=None, external: bool = False, actor: str | None = None) -> tuple[dict, int]:
        story: "Story | None" = cls.get(story_id)
        logger.debug(f"Updating story {story_id} with data: {data}")
        if not story:
            return {"error": "Story not found"}, 404

        if "vote" in data and user:
            story.vote(data["vote"], user.id)

        if "important" in data:
            story.important = data["important"]

        if "read" in data:
            story.read = data["read"]

        if "title" in data:
            story.title = data["title"]

        if "description" in data:
            story.description = data["description"]

        if "comments" in data:
            story.comments = data["comments"]

        if "summary" in data:
            story.summary = data["summary"]

        if "attributes" in data:
            story.set_attributes(data["attributes"])

        if "relevance_override" in data:
            story.relevance_override = data["relevance_override"] or 0
        elif "relevance" in data:
            story.relevance_override = data["relevance"] or 0

        actor = cls._determine_actor_for_update(story=story, user=user, external=external, actor=actor)

        if actor is not None:
            story.last_change = actor

        story.update_timestamps()
        story.recompute_relevance()
        story.record_revision(user, note="update")
        db.session.commit()
        return {"message": "Story updated successfully", "id": story.id, "story": story.to_detail_dict()}, 200

    @classmethod
    def update_with_conflicts(cls, story_id: str, upstream_data: dict[str, Any]) -> tuple[dict[str, Any], int]:
        current_story = Story.get(story_id)
        if not current_story:
            return {
                "message": f"Conflicts were detected, but the internal story with ID {story_id} was not found. This should not happen, raise an issue"
            }, 400

        has_proposals_value: str | None = None
        if attributes_map := upstream_data.get("attributes", {}):
            attributes_map = NewsItemAttribute.parse_attributes(attributes_map)
            if proposals_attr := attributes_map.get("has_proposals"):
                has_proposals_value = proposals_attr.value

        current_full = current_story.to_worker_dict()

        original_str, updated_str = StoryConflict.normalize_data(current_full, upstream_data)

        if existing_conflict := StoryConflict.conflict_store.get(story_id):
            existing_conflict.existing_story = original_str
            existing_conflict.incoming_story = updated_str
            existing_conflict.has_proposals = has_proposals_value
            logger.debug(f"Updated existing conflict for story {story_id}")
        else:
            StoryConflict.conflict_store[story_id] = StoryConflict(
                story_id=story_id,
                existing_story=original_str,
                incoming_story=updated_str,
                has_proposals=has_proposals_value,
            )
            logger.warning(f"Story Conflict detected for story {story_id}")

        return {
            "warning": "Story Conflict detected",
            "conflict": {"local": current_full, "new": upstream_data},
        }, 409

    @classmethod
    def handle_conflicting_news_items(cls, data: dict) -> tuple[dict, int]:
        news_items: list[dict] = data.get("news_items", [])
        if not news_items:
            return {"error": "No news items provided"}, 400

        incoming_story_id = data.get("id")
        if not incoming_story_id:
            return {"error": "Missing story ID"}, 400

        entries: list[dict] = []
        for news_item in news_items:
            if news_item_id := news_item.get("id"):
                if existing_item := NewsItem.get(news_item_id):
                    existing_story_id = existing_item.story_id

                    entries.append(
                        {
                            "news_item_id": news_item_id,
                            "existing_story_id": existing_story_id,
                            "incoming_story_data": data,
                        }
                    )

        count = NewsItemConflict.set_for_story(incoming_story_id, entries)

        if count:
            return {"error": {"conflicts_number": count}}, 409
        return {"message": "Update successful"}, 200

    def set_attributes(self, attributes: list[dict]):
        """
        Synchronize story attributes to match the provided list.
        Calls patch_attributes() for add/update,
        remove_attributes() for deletions.
        """
        parsed_attributes = NewsItemAttribute.parse_attributes(attributes)
        if len(parsed_attributes) == 0:
            return
        input_keys = set(parsed_attributes.keys())
        existing_keys = {attr.key for attr in self.attributes}

        self.patch_attributes(list(parsed_attributes.values()))

        keys_to_remove = existing_keys - input_keys
        self.remove_attributes(list(keys_to_remove))

    def patch_attributes(self, attributes: list[NewsItemAttribute] | dict[str, dict]):
        if isinstance(attributes, dict) or not isinstance(attributes[0], NewsItemAttribute):
            attributes = list(NewsItemAttribute.parse_attributes(attributes).values())
        for attribute in attributes:
            if isinstance(attribute, NewsItemAttribute):
                if attribute.key == "TLP":
                    attribute.value = self.get_story_tlp(TLPLevel.get_tlp_level(attribute.value))
                self.upsert_attribute(attribute)
            else:
                logger.warning(f"Expected NewsItemAttribute, got {type(attribute)}")

    def remove_attributes(self, keys: list[str]):
        """
        Remove attributes from the story whose keys are in the provided list.
        """
        for key in keys:
            if (attr := self.find_attribute_by_key(key)) and key != "TLP":
                self.attributes.remove(attr)
                db.session.delete(attr)

    def upsert_attribute(self, attribute: NewsItemAttribute) -> None:
        if existing_attribute := self.find_attribute_by_key(attribute.key):
            existing_attribute.value = attribute.value
        else:
            self.attributes.append(attribute)

    def find_attribute_by_key(self, key: str) -> NewsItemAttribute | None:
        return next((attribute for attribute in self.attributes if attribute.key == key), None)

    def vote(self, vote_data, user_id):
        vote = NewsItemVote.get_by_filter(item_id=self.id, user_id=user_id)
        if vote is None:
            vote = self.create_new_vote(user_id)

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
            vote.like = True
        elif vote_data == "dislike":
            self.dislikes = self.dislikes + 1
            vote.dislike = True
        self.recompute_relevance()
        return vote

    def remove_like_vote(self, vote):
        self.likes = self.likes - 1
        vote.like = False
        return vote

    def remove_dislike_vote(self, vote):
        self.dislikes = self.dislikes - 1
        vote.dislike = False
        return vote

    def change_like_to_dislike(self, vote):
        self.likes = self.likes - 1
        self.dislikes = self.dislikes + 1
        vote.like = False
        vote.dislike = True
        return vote

    def change_dislike_to_like(self, vote):
        self.likes = self.likes + 1
        self.dislikes = self.dislikes - 1
        vote.like = True
        vote.dislike = False
        return vote

    def create_new_vote(self, user_id):
        vote = NewsItemVote(item_id=self.id, user_id=user_id)
        db.session.add(vote)
        return vote

    @classmethod
    def delete_by_id(cls, story_id, user):
        story = cls.get(story_id)
        if not story:
            logger.debug(f"Story with id: {story_id} not found")
            return {"error": "Story not found"}, 404

        if cls.is_assigned_to_report([story_id]):
            logger.debug(f"Story with: {story_id} assigned to a report")
            return {"error": "Story is assigned to a report"}, 500

        for news_item in story.news_items[:]:
            if news_item.allowed_with_acl(user, True):
                story.news_items.remove(news_item)
                news_item.delete_item()
            else:
                logger.debug(f"User {user.id} not allowed to remove news item {news_item.id}")
                return {"error": "User is not allowed to remove news item"}, 403

        story.update_status()

        db.session.commit()

        return {"message": "Successfully deleted story"}, 200

    def delete(self, user):
        return self.delete_by_id(self.id, user)

    @classmethod
    def is_assigned_to_report(cls, story_ids: list) -> bool:
        return any(ReportItemStory.is_assigned(story_id) for story_id in story_ids)

    @classmethod
    def group_multiple_stories(cls, story_mappings: list[list[str]], user: User | None = None, actor: str | None = None):
        results = [cls.group_stories(story_ids, user=user, actor=actor) for story_ids in story_mappings]
        if any(result[1] == 500 for result in results):
            return {"error": "grouping failed"}, 500
        return {"message": "success"}, 200

    @classmethod
    def move_items_to_story(
        cls,
        story_id: str,
        news_item_ids: list[str],
        user: User | None = None,
        actor: str | None = None,
    ):
        actor = cls.resolve_actor(user=user, actor=actor)
        try:
            story = cls.get(story_id)
            if not story:
                return {"error": "not_found"}, 404
            source_stories_by_id: dict[str, Story] = {}
            for news_item in [NewsItem.get(item_id) for item_id in news_item_ids]:
                StoryOperationsService.transfer_news_item_to_story(story, news_item, source_stories_by_id, user)
            processed_stories = StoryOperationsService.finalize_story_merge(
                story,
                list(source_stories_by_id.values()),
                actor=actor,
            )
            for processed_story in processed_stories:
                processed_story.record_revision(user, note="move_items_to_story")
            cls.refresh_tag_summaries_for_stories(processed_stories)
            db.session.commit()
            return {"message": "success"}, 200
        except Exception:
            logger.exception("Grouping Stories Failed")
            return {"error": "grouping failed"}, 500

    @classmethod
    def group_stories(cls, story_ids: Sequence[str], user: User | None = None, actor: str | None = None):
        actor = cls.resolve_actor(user=user, actor=actor)
        try:
            if not isinstance(story_ids, list):
                return {"error": "story_ids must be a list"}, 400

            if len(story_ids) < 2 or any(not isinstance(a_id, str) or len(a_id) == 0 for a_id in story_ids):
                return {"error": "at least two valid Story ids needed"}, 404

            ordered_story_ids = list(story_ids)
            first_story = cls.get(ordered_story_ids[0])
            if not first_story:
                return {"error": "Story not found"}, 404
            source_stories_by_id: dict[str, Story] = {}
            for source_story_id in ordered_story_ids[1:]:
                source_story = Story.get(source_story_id)
                if not source_story:
                    continue

                for news_item in source_story.news_items[:]:
                    StoryOperationsService.transfer_news_item_to_story(first_story, news_item, source_stories_by_id, user)

            processed_stories = StoryOperationsService.finalize_story_merge(
                first_story,
                list(source_stories_by_id.values()),
                actor=actor,
            )
            for story in processed_stories:
                story.record_revision(user, note="group_stories")
            cls.refresh_tag_summaries_for_stories(processed_stories)
            db.session.commit()
            return {"message": "Clustering Stories successful", "id": first_story.id}, 200
        except Exception:
            logger.exception("Grouping Stories Failed")
            return {"error": "Grouping Stories Failed"}, 500

    @classmethod
    def ungroup_multiple_stories(cls, story_ids: list[str], user: User | None = None):
        results = [cls.ungroup_story(story_id, user) for story_id in story_ids]
        if errors := [res[0].get("error") for res in results if res[1] != 200 and res[0].get("error") is not None]:
            error_message = "; ".join(filter(None, errors))
            logger.error(f"Errors ungrouping stories: {error_message}")
            return {"error": error_message}, 400
        return {"message": "Ungrouping Stories successful"}, 200

    @classmethod
    def ungroup_story(cls, story_id: str, user: User | None = None, actor: str | None = None):
        actor = cls.resolve_actor(user=user, actor=actor)
        try:
            if ReportItemStory.is_assigned(story_id):
                return {"error": "Story is assigned to a report"}, 400
            story = cls.get(story_id)
            if not story:
                return {"error": "Story not found"}, 404
            for news_item in story.news_items[:]:
                if user is None or news_item.allowed_with_acl(user, True):
                    cls.create_from_item(news_item, commit=False, actor=actor)
            story.update_status(change=actor)
            story.record_revision(user, note="ungroup_story")
            db.session.commit()
            return {"message": "Ungrouping Stories successful"}, 200
        except Exception:
            logger.exception("Ungrouping Stories Failed")
            return {"error": "Ungrouping Stories failed"}, 500

    @classmethod
    def ungroup_news_items_from_story(
        cls,
        newsitem_ids: list,
        user: User | None = None,
        actor: str | None = None,
    ):
        actor = cls.resolve_actor(user=user, actor=actor)
        try:
            processed_stories = set()
            new_stories_ids = []
            removed_titles_by_story: dict[Story, set[str]] = {}
            for item in newsitem_ids:
                news_item = NewsItem.get(item)
                if not news_item or not user:
                    continue
                if not news_item.allowed_with_acl(user, True):
                    continue
                story = Story.get(news_item.story_id)
                if not story:
                    continue
                removed_titles_by_story.setdefault(story, set()).add(news_item.title)
                story.news_items.remove(news_item)
                processed_stories.add(story)
                new_stories_ids.append(cls.create_from_item(news_item, commit=False, actor=actor))
            for story in processed_stories:
                if story.news_items and story.title in removed_titles_by_story.get(story, set()):
                    story.title = story.news_items[0].title
                story.update_status(change=actor)
            for story in processed_stories:
                story.record_revision(user, note="ungroup_news_items")
            db.session.commit()
            return {"message": f"Successfully ungrouped {len(newsitem_ids)} items from their story", "new_stories_ids": new_stories_ids}, 200
        except Exception:
            logger.exception("Ungrouping News Item stories Failed")
            return {"error": "ungroup failed"}, 500

    @classmethod
    def update_stories(cls, stories: set["Story"], actor: str | None = None):
        for story in stories:
            try:
                story.update_status(change=actor)
            except Exception:
                logger.exception(f"Update Story: {story.id} Failed")

    @classmethod
    def prepare_misp_stories(cls, story_lists: list[dict], force: bool) -> list[dict]:
        stories = []
        for story in story_lists:
            if story_id := story.get("id"):
                if existing_story := cls.get(story_id):
                    existing_story_data = existing_story.to_detail_dict()
                    if not force and cls.check_internal_changes(existing_story_data):
                        logger.info(f"Internal changes detected in story {existing_story.id}, story conflict raised.")
                        story["conflict"] = True
                    else:
                        if news_items_to_delete := cls.get_news_items_to_delete(story, existing_story_data):
                            story["news_items_to_delete"] = news_items_to_delete
            else:
                logger.debug(f"Story does not have an ID: {story}")
                continue

            stories.append(story)
        return stories

    @classmethod
    def check_internal_changes(cls, existing_story: dict) -> bool:
        last_change = existing_story.get("last_change")
        if last_change is None:
            return False
        if last_change in {"internal", "external"}:
            return last_change == "internal"
        return not last_change.startswith(("collector_", "connector_"))

    @classmethod
    def get_news_items_to_delete(cls, new_story: dict, existing_story: dict) -> list[str]:
        existing_news_items = existing_story.get("news_items", [])
        new_news_items = new_story.get("news_items", [])

        existing_ids = {item.get("id") for item in existing_news_items if item.get("id") is not None}
        new_ids = {item.get("id") for item in new_news_items if item.get("id") is not None}

        return list(existing_ids - new_ids)

    @classmethod
    def create_from_item(cls, news_item: NewsItem, commit: bool = True, actor: str | None = None) -> str | None:
        change = actor or news_item.last_change or "internal"
        if source_story := cls.get(news_item.story_id):
            if news_item in source_story.news_items:
                source_story.news_items.remove(news_item)

        new_story = Story(
            title=news_item.title,
            created=news_item.published,
            description=news_item.review or news_item.content,
            news_items=[news_item],
            last_change=change,
        )
        db.session.add(new_story)
        db.session.flush()

        new_story.update_status(change=change, refresh_timestamps=False)
        new_story.record_revision(note="created")
        if commit:
            db.session.commit()
        return new_story.id or None

    def get_cybersecurity_status(self) -> str:
        status_list = [news_item.get_cybersecurity_status() for news_item in self.news_items]
        status_set = frozenset(status_list)

        if "none" in status_set and len(status_set) > 1:
            return "incomplete"
        status_map = {
            frozenset(["yes"]): "yes",
            frozenset(["no"]): "no",
            frozenset(["yes", "no"]): "mixed",
            frozenset(["none"]): "none",
        }
        return status_map.get(status_set, "none")

    def get_story_sentiment(self) -> str:
        counts = Counter(item.get_sentiment() for item in self.news_items)

        pos = counts.get("positive", 0)
        neg = counts.get("negative", 0)
        neu = counts.get("neutral", 0)

        if pos == 0 and neg == 0 and neu == 0:
            return "none"

        max_count = max(pos, neg, neu)
        leaders = [label for label, count in (("positive", pos), ("negative", neg), ("neutral", neu)) if count == max_count]

        return leaders[0] if len(leaders) == 1 else "mixed"

    def remove_empty_story(self) -> bool:
        if len(self.news_items) == 0:
            StoryOperationsService.delete_votes_for_story_ids([self.id])
            NewsItemTag.remove_by_story(self)
            db.session.delete(self)
            logger.debug(f"Deleting empty Story - 'ID': {self.id}")
            return True
        return False

    def update_status(self, change: str | None = None, refresh_timestamps: bool = True):
        if self.remove_empty_story():
            return
        if refresh_timestamps:
            self.update_timestamps()
        self.update_status_attributes()
        self.recompute_relevance()
        if change is not None:
            self.last_change = change
        elif not self._is_actor_change(self.last_change):
            if self.news_items:
                source = self.news_items[0].osint_source if self.news_items[0] else None
                if self._is_manual_source(source):
                    self.last_change = self.last_change or "internal"
                else:
                    self.last_change = self.last_change_for_source(source) or self.last_change or "external"
            else:
                self.last_change = self.last_change or "internal"

    def update_status_attributes(self):
        attributes = [
            NewsItemAttribute(key="TLP", value=self.get_story_tlp()),
            NewsItemAttribute(key="cybersecurity", value=self.get_cybersecurity_status()),
            NewsItemAttribute(key="sentiment", value=self.get_story_sentiment()),
        ]
        for attribute in attributes:
            if attribute.value != "none":
                self.upsert_attribute(attribute)

    @staticmethod
    def _comparison_timestamp(value: datetime) -> datetime:
        return BaseModel.as_utc_aware(value)

    def update_timestamps(self):
        self.updated = self.utcnow()
        published_dates = [news_item.published for news_item in self.news_items if news_item.published]
        if published_dates:
            self.created = min(published_dates, key=self._comparison_timestamp)

    def get_story_tlp(self, input_tlp: TLPLevel | None = None) -> TLPLevel:
        most_restrictive_tlp = input_tlp or TLPLevel.CLEAR

        tlp_levels: list[TLPLevel] = []
        for news_item in self.news_items:
            if not news_item.tlp_level:
                source_tlp = news_item.osint_source.tlp_level if news_item.osint_source else TLPLevel.CLEAR
                news_item.add_attribute(NewsItemAttribute("TLP", source_tlp))
            logger.debug(f"News item {news_item.id} has TLP level")
            tlp_levels.append(news_item.tlp_level)
        tlp_levels += [input_tlp] if input_tlp else []

        most_restrictive_tlp = TLPLevel.get_most_restrictive_tlp(tlp_levels)

        logger.debug(f"Updating TLP for Story {self.id} to {most_restrictive_tlp}")
        return most_restrictive_tlp

    @property
    def tlp_level(self) -> TLPLevel:
        return next((TLPLevel(attr.value) for attr in self.attributes if attr.key == "TLP"), TLPLevel.CLEAR)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["news_items"] = [news_item.to_detail_dict() for news_item in self.news_items]
        data["tags"] = [tag.to_dict() for tag in self.tags]
        data["links"] = self.links
        del data["search_vector"]
        return data

    def to_detail_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        data["tags"] = [tag.to_dict() for tag in self.tags]
        data["attributes"] = [attribute.to_small_dict() for attribute in self.attributes]
        data["detail_view"] = True
        data["in_reports_count"] = ReportItemStory.count(self.id)
        data["links"] = self.links
        data["revision_count"] = self.get_revision_count()
        return data

    def to_worker_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["news_items"] = [news_item.to_dict() for news_item in self.news_items]
        data["tags"] = {tag.name: tag.to_dict() for tag in self.tags}
        if attributes := self.attributes:
            data["attributes"] = {attribute.key: attribute.to_small_dict() for attribute in attributes}
        del data["search_vector"]

        return data

    def record_revision(self, user: User | None = None, note: str | None = None) -> StoryRevision | None:
        if not self.id:
            return None

        state = inspect(self)
        if not state:
            return None
        if state.deleted or state.detached or self in db.session.deleted:
            return None

        created_by_id = user.id if isinstance(user, User) else getattr(user, "id", None)
        return StoryRevision.create_from_story(self, created_by_id=created_by_id, note=note)

    def get_revision_count(self) -> int:
        """Get the number of revisions for this story"""
        return self.revision or 0


class NewsItemVote(BaseModel):
    __tablename__ = "news_item_vote"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    like: Mapped[bool] = db.Column(db.Boolean, default=False)
    dislike: Mapped[bool] = db.Column(db.Boolean, default=False)
    item_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH))
    user_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("user.id", ondelete="CASCADE"), nullable=True)

    @hybrid_property
    def user_vote(self):
        if self.like:
            return "like"
        elif self.dislike:
            return "dislike"
        return ""

    @user_vote.expression
    def user_vote_expr(cls):
        return db.case(
            (cls.like == true(), "like"),
            (cls.dislike == true(), "dislike"),
            else_="",
        )

    def __init__(self, item_id, user_id, like=False, dislike=False):
        self.id = self.uuid7_str()
        self.item_id = item_id
        self.user_id = user_id
        self.like = like
        self.dislike = dislike

    @classmethod
    def get_by_filter(cls, item_id: str, user_id: str):
        return cls.get_first(db.select(cls).filter_by(item_id=item_id, user_id=user_id))

    @classmethod
    def get_user_vote(cls, item_id: str, user_id: str):
        if vote := cls.get_by_filter(item_id, user_id):
            return {"like": vote.like, "dislike": vote.dislike}
        return {"like": False, "dislike": False}


class StoryNewsItemAttribute(BaseModel):
    __tablename__ = "story_news_item_attribute"

    story_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("story.id", ondelete="CASCADE"), primary_key=True)
    news_item_attribute_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("news_item_attribute.id", ondelete="CASCADE"), primary_key=True
    )


class ReportItemStory(BaseModel):
    __tablename__ = "report_item_story"

    report_item_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("report_item.id", ondelete="CASCADE"), primary_key=True)
    story_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("story.id", ondelete="CASCADE"), primary_key=True)

    @classmethod
    def is_assigned(cls, story_id: str) -> bool:
        return db.session.query(db.exists().where(cls.story_id == story_id)).scalar()

    @classmethod
    def count(cls, story_id: str) -> int:
        return cls.get_filtered_count(db.select(cls).where(cls.story_id == story_id))


class StoryBookmark(BaseModel):
    __tablename__ = "story_bookmark"
    __table_args__ = (db.UniqueConstraint("user_id", "name", name="ux_story_bookmark_user_name"),)

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    name: Mapped[str] = db.Column(db.String(120), nullable=False)
    position: Mapped[int] = db.Column(db.Integer, default=0, nullable=False)
    created: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow, nullable=False)
    updated: Mapped[datetime] = db.Column(db.DateTime, default=BaseModel.utcnow, nullable=False)

    user_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    user: Mapped["User"] = relationship("User")
    stories: Mapped[list["Story"]] = relationship(
        "Story", secondary="story_bookmark_story", cascade="save-update, merge", passive_deletes=True, single_parent=False, lazy="selectin"
    )

    def __init__(self, name: str, user_id: str, bookmark_id: str | None = None, stories: list[str] | None = None, position: int = 0):
        self.id = self.normalize_uuid_id(bookmark_id)
        self.name = self._clean_name(name)
        self.position = position
        self.user_id = user_id
        self.created = self.utcnow()
        self.updated = self.created
        self.stories = Story.get_bulk(stories) if stories else []

    @staticmethod
    def _clean_name(raw_name: Any) -> str:
        if name := str(raw_name or "").strip():
            return name[:120]
        raise ValueError("Bookmark collection name is required")

    @staticmethod
    def _dedupe_ids(ids: list[str]) -> list[str]:
        return list(dict.fromkeys(item_id for item_id in ids if isinstance(item_id, str) and item_id))

    @classmethod
    def _next_position(cls, user_id: str) -> int:
        max_position = db.session.execute(db.select(func.max(cls.position)).where(cls.user_id == user_id)).scalar()
        return int(max_position if max_position is not None else -1) + 1

    @classmethod
    def get_for_user(cls, bookmark_id: str, user: User | None) -> "StoryBookmark | None":
        if user is None:
            return None
        return cls.get_first(db.select(cls).where(cls.id == bookmark_id, cls.user_id == user.id))

    @classmethod
    def get_filter_query(cls, filter_args: dict[str, Any], user: User | None = None) -> Select:
        query = db.select(cls)
        if user:
            query = query.where(cls.user_id == user.id)
        if search := filter_args.get("search"):
            query = query.where(cls.name.ilike(f"%{search}%"))
        return query

    @classmethod
    def _add_sorting_to_query(cls, filter_args: dict[str, Any], query: Select) -> Select:
        sort = str(filter_args.get("sort") or filter_args.get("order") or "position_asc").lower()
        if sort == "name_asc":
            return query.order_by(db.asc(cls.name), db.asc(cls.position))
        if sort == "name_desc":
            return query.order_by(db.desc(cls.name), db.asc(cls.position))
        if sort == "position_desc":
            return query.order_by(db.desc(cls.position), db.asc(cls.name))
        return query.order_by(db.asc(cls.position), db.asc(cls.name))

    @classmethod
    def get_all_for_api(cls, filter_args: dict[str, Any] | None, user: User | None) -> tuple[dict[str, Any], int]:
        if user is None:
            return {"error": "User not found"}, 403
        filter_args = filter_args or {}
        base_query = cls.get_filter_query(filter_args, user)
        query = cls._add_sorting_to_query(filter_args, base_query)
        if filter_args.get("fetch_all") != "true":
            query = cls._add_paging_to_query(filter_args, query)
        bookmarks = cls.get_filtered(query) or []
        return {"items": [bookmark.to_dict() for bookmark in bookmarks], "total_count": cls.get_filtered_count(base_query)}, 200

    @classmethod
    def add(cls, data: dict[str, Any], user: User | None) -> tuple[dict[str, Any], int]:
        if user is None:
            return {"error": "User not found"}, 403
        try:
            bookmark = cls(name=cls._clean_name(data.get("name")), user_id=user.id, position=cls._next_position(user.id))
            db.session.add(bookmark)
            db.session.commit()
            return {"message": "Bookmark collection created", "id": bookmark.id, "bookmark": bookmark.to_detail_dict()}, 201
        except ValueError:
            db.session.rollback()
            return {"error": "Invalid bookmark collection data"}, 400
        except IntegrityError:
            db.session.rollback()
            return {"error": "A bookmark collection with this name already exists"}, 409
        except SQLAlchemyError:
            logger.exception("Failed to create story bookmark")
            db.session.rollback()
            return {"error": "Failed to create bookmark collection"}, 500

    @classmethod
    def update_for_api(cls, bookmark_id: str, data: dict[str, Any], user: User | None) -> tuple[dict[str, Any], int]:
        bookmark = cls.get_for_user(bookmark_id, user)
        if bookmark is None:
            return {"error": "Bookmark collection not found"}, 404
        try:
            bookmark.name = cls._clean_name(data.get("name"))
            bookmark.touch()
            db.session.commit()
            return {"message": "Bookmark collection updated", "id": bookmark.id, "bookmark": bookmark.to_detail_dict()}, 200
        except ValueError:
            db.session.rollback()
            return {"error": "Invalid bookmark collection data"}, 400
        except IntegrityError:
            db.session.rollback()
            return {"error": "A bookmark collection with this name already exists"}, 409
        except SQLAlchemyError:
            logger.exception("Failed to update story bookmark %s", bookmark_id)
            db.session.rollback()
            return {"error": "Failed to update bookmark collection"}, 500

    @classmethod
    def reorder_for_api(cls, bookmark_ids: list[str], user: User | None) -> tuple[dict[str, Any], int]:
        if user is None:
            return {"error": "User not found"}, 403
        normalized_ids = cls._dedupe_ids(bookmark_ids)
        if not normalized_ids or len(normalized_ids) != len(bookmark_ids):
            return {"error": "Bookmark ids must be unique"}, 400

        bookmarks = cls.get_filtered(db.select(cls).where(cls.user_id == user.id)) or []
        bookmarks_by_id = {bookmark.id: bookmark for bookmark in bookmarks if bookmark.id}
        if missing_ids := set(normalized_ids) - set(bookmarks_by_id):
            return {"error": f"Bookmark collection not found: {sorted(missing_ids)[0]}"}, 404

        ordered_bookmarks = [bookmarks_by_id[bookmark_id] for bookmark_id in normalized_ids]
        remaining_bookmarks = sorted(
            (bookmark for bookmark in bookmarks if bookmark.id not in normalized_ids),
            key=lambda bookmark: (bookmark.position, bookmark.name),
        )
        for position, bookmark in enumerate([*ordered_bookmarks, *remaining_bookmarks]):
            bookmark.position = position
        db.session.commit()
        return {"message": "Bookmark order updated"}, 200

    @classmethod
    def delete_for_api(cls, bookmark_id: str, user: User | None) -> tuple[dict[str, Any], int]:
        bookmark = cls.get_for_user(bookmark_id, user)
        if bookmark is None:
            return {"error": "Bookmark collection not found"}, 404
        db.session.delete(bookmark)
        db.session.commit()
        return {"message": "Bookmark collection deleted"}, 200

    @classmethod
    def get_for_api(cls, item_id: str, user: User | None = None) -> tuple[dict[str, Any], int]:
        if bookmark := cls.get_for_user(item_id, user):
            story_ids = [story.id for story in bookmark.stories if story and story.id]
            accessible_query = db.select(Story).where(Story.id.in_(story_ids))
            if user:
                accessible_query = Story._add_ACL_check(accessible_query, user)
                accessible_query = Story._add_TLP_check(accessible_query, user)
            stories_by_id = {story.id: story for story in db.session.execute(accessible_query).scalars().all() if story}
            visible_stories = [stories_by_id[story_id] for story_id in story_ids if story_id in stories_by_id]

            return bookmark.to_detail_dict(stories=visible_stories), 200
        return {"error": "Bookmark collection not found"}, 404

    @classmethod
    def _get_accessible_stories(cls, story_ids: list[str], user: User) -> list[Story] | None:
        query = db.select(Story).where(Story.id.in_(story_ids))
        query = Story._add_ACL_check(query, user)
        query = Story._add_TLP_check(query, user)
        stories_by_id = {story.id: story for story in db.session.execute(query).scalars().all()}
        if set(story_ids) - set(stories_by_id):
            return None
        return [stories_by_id[story_id] for story_id in story_ids]

    @classmethod
    def add_stories(cls, bookmark_id: str, story_ids: list[str], user: User | None) -> tuple[dict[str, Any], int]:
        if user is None:
            return {"error": "User not found"}, 403
        bookmark = cls.get_for_user(bookmark_id, user)
        if bookmark is None:
            return {"error": "Bookmark collection not found"}, 404
        normalized_story_ids = cls._dedupe_ids(story_ids)
        if not normalized_story_ids:
            return {"error": "No story ids provided"}, 400
        stories = cls._get_accessible_stories(normalized_story_ids, user)
        if stories is None:
            return {"error": "One of the provided stories was not found"}, 404

        existing_story_ids = {story.id for story in bookmark.stories}
        added = 0
        for story in stories:
            if story.id in existing_story_ids:
                continue
            bookmark.stories.append(story)
            existing_story_ids.add(story.id)
            added += 1
        bookmark.touch()
        db.session.commit()
        return {"message": f"{added} stories bookmarked", "added": added, "story_count": len(bookmark.stories)}, 200

    @classmethod
    def remove_stories(cls, bookmark_id: str, story_ids: list[str], user: User | None) -> tuple[dict[str, Any], int]:
        if user is None:
            return {"error": "User not found"}, 403
        bookmark = cls.get_for_user(bookmark_id, user)
        if bookmark is None:
            return {"error": "Bookmark collection not found"}, 404
        normalized_story_ids = set(cls._dedupe_ids(story_ids))
        if not normalized_story_ids:
            return {"error": "No story ids provided"}, 400

        remaining_stories = []
        removed = 0
        for story in bookmark.stories:
            if story.id in normalized_story_ids:
                removed += 1
                continue
            remaining_stories.append(story)
        bookmark.stories = remaining_stories
        bookmark.touch()
        db.session.commit()
        return {
            "message": f"{removed} stories removed from bookmark collection",
            "removed": removed,
            "story_count": len(bookmark.stories),
        }, 200

    def touch(self) -> None:
        self.updated = self.utcnow()

    def to_dict(self, stories: list[Story] | None = None) -> dict[str, Any]:
        data = super().to_dict()
        stories = self.stories if stories is None else stories
        data["story_count"] = len(stories)
        data["story_ids"] = [story.id for story in stories if story and story.id]
        return data

    def to_detail_dict(self, stories: list[Story] | None = None) -> dict[str, Any]:
        stories = stories if stories is not None else self.stories
        data = self.to_dict(stories=stories)
        data["stories"] = [story.to_dict() for story in stories if story]
        return data


class StoryBookmarkStory(BaseModel):
    __tablename__ = "story_bookmark_story"

    bookmark_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("story_bookmark.id", ondelete="CASCADE"), primary_key=True)
    story_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("story.id", ondelete="CASCADE"), primary_key=True)
    __table_args__ = (db.UniqueConstraint("bookmark_id", "story_id", name="ux_story_bookmark_story"),)
