import uuid
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import or_, func
from sqlalchemy.orm import aliased, Mapped, relationship
from sqlalchemy.sql.expression import false, null, true
from sqlalchemy.sql import Select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.exc import IntegrityError
from collections import Counter

from core.managers.history_meta import Versioned
from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.log import logger
from core.model.user import User
from core.model.role import TLPLevel
from core.model.news_item_tag import NewsItemTag
from core.model.role_based_access import ItemType
from core.model.osint_source import OSINTSourceGroup, OSINTSource, OSINTSourceGroupOSINTSource
from core.model.news_item import NewsItem
from core.model.news_item_attribute import NewsItemAttribute
from core.service.role_based_access import RBACQuery, RoleBasedAccessService
from core.model.story_conflict import StoryConflict
from core.model.news_item_conflict import NewsItemConflict
from core.model.report_item import ReportItem


class Story(Versioned, BaseModel):
    __tablename__ = "story"

    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    title: Mapped[str] = db.Column(db.String())
    description: Mapped[str] = db.Column(db.String())
    created: Mapped[datetime] = db.Column(db.DateTime)
    updated: Mapped[datetime] = db.Column(db.DateTime, default=datetime.now)

    read: Mapped[bool] = db.Column(db.Boolean, default=False)
    important: Mapped[bool] = db.Column(db.Boolean, default=False)

    likes: Mapped[int] = db.Column(db.Integer, default=0)
    dislikes: Mapped[int] = db.Column(db.Integer, default=0)
    relevance: Mapped[int] = db.Column(db.Integer, default=0)

    comments: Mapped[str] = db.Column(db.String(), default="")
    summary: Mapped[str] = db.Column(db.Text, default="")
    news_items: Mapped[list["NewsItem"]] = relationship("NewsItem")
    links: Mapped[list[str]] = db.Column(db.JSON, default=[])
    last_change: Mapped[str] = db.Column(db.String())
    attributes: Mapped[list["NewsItemAttribute"]] = relationship(
        "NewsItemAttribute", secondary="story_news_item_attribute", cascade="all, delete"
    )
    tags: Mapped[list["NewsItemTag"]] = relationship("NewsItemTag", back_populates="story", cascade="all, delete")
    report_items: Mapped[list["ReportItem"]] = relationship("ReportItem", secondary="report_item_story", back_populates="stories")
    search_index: Mapped["StorySearchIndex"] = relationship(
        "StorySearchIndex",
        back_populates="story",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __init__(
        self,
        title: str,
        description: str = "",
        created: datetime | str = datetime.now(),
        id: str | None = None,
        likes: int = 0,
        dislikes: int = 0,
        relevance: int = 0,
        read: bool = False,
        important: bool = False,
        summary: str = "",
        comments: str = "",
        links=None,
        attributes: list[dict] | None = None,
        tags=None,
        news_items=None,
        last_change: str = "external",
    ):
        self.id = id or str(uuid.uuid4())
        self.likes = likes
        self.dislikes = dislikes
        self.relevance = relevance
        self.title = title
        self.description = description
        self.created = self.get_creation_date(created)
        self.read = read
        self.important = important
        self.summary = summary
        self.comments = comments
        self.news_items = self.load_news_items(news_items)
        self.links = links or []
        self.last_change = "external" if last_change is None else last_change
        if attributes:
            self.attributes = NewsItemAttribute.load_multiple(attributes)
        if tags:
            self.tags = NewsItemTag.load_multiple(tags)

    def get_creation_date(self, created):
        if isinstance(created, datetime):
            return created
        if isinstance(created, str):
            return datetime.fromisoformat(created)
        return datetime.now()

    def load_news_items(self, news_items) -> list["NewsItem"]:
        if not news_items:
            return []
        elif isinstance(news_items[0], dict):
            return NewsItem.load_multiple(news_items)
        elif isinstance(news_items[0], str):
            news_items = [NewsItem.get(item_id) for item_id in news_items]
            return [news_item for news_item in news_items if news_item]
        elif isinstance(news_items[0], NewsItem):
            return news_items
        return []

    @classmethod
    def get_for_api(cls, item_id: str, user: User | None) -> tuple[dict[str, Any], int]:
        logger.debug(f"Getting {cls.__name__} {item_id}")
        query = db.select(cls).filter(cls.id == item_id)
        if user:
            query = cls._add_ACL_check(query, user)
            query = cls._add_TLP_check(query, user)

        if item := db.session.execute(query).scalar():
            return item.to_detail_dict(), 200
        return {"error": f"{cls.__name__} {item_id} not found"}, 404

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
                StorySearchIndex,
                Story.id == StorySearchIndex.story_id,
            )
            for word in words:
                query = query.filter(StorySearchIndex.data.ilike(f"%{word}%"))

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
                alias = aliased(NewsItemTag)
                query = query.join(alias, Story.id == alias.story_id).filter(or_(alias.name == tag, alias.tag_type == tag))

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

            query = query.filter(cls.created >= date_limit)

        if timefrom := filter_args.get("timefrom"):
            query = query.filter(cls.created >= datetime.fromisoformat(timefrom))

        if timeto := filter_args.get("timeto"):
            query = query.filter(cls.updated <= datetime.fromisoformat(timeto))

        return query

    @classmethod
    def _add_sorting_to_query(cls, filter_args: dict, query: Select) -> Select:
        if sort := filter_args.get("sort", "date_desc").lower():
            if sort == "date_desc":
                query = query.order_by(db.desc(cls.created), db.desc(cls.title))

            elif sort == "date_asc":
                query = query.order_by(db.asc(cls.created), db.asc(cls.title))

            elif sort == "relevance_desc":
                query = query.order_by(db.desc(cls.relevance), db.desc(cls.created))

            elif sort == "relevance_asc":
                query = query.order_by(db.asc(cls.relevance), db.asc(cls.created))

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
    def _add_paging_to_query(cls, filter_args: dict, query: Select) -> Select:
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
    def enhance_with_user_votes(cls, query: Select, user_id: int) -> Select:
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
            db.select(ReportItemStory.story_id, func.count().label("report_count")).group_by(ReportItemStory.story_id).subquery()
        )
        query = query.outerjoin(report_subquery, Story.id == report_subquery.c.story_id)
        query = query.add_columns(func.coalesce(report_subquery.c.report_count, 0).label("report_count"))
        query = query.group_by(Story.id, report_subquery.c.report_count)
        return query

    @classmethod
    def get_by_filter(cls, filter_args: dict, user: User | None = None) -> tuple[list[dict[str, Any]], dict[str, int] | None]:
        base_query = cls.get_filter_query(filter_args)
        if user:
            base_query = cls._add_ACL_check(base_query, user)
            base_query = cls._add_TLP_check(base_query, user)

        query = cls._add_sorting_to_query(filter_args, base_query)
        query = cls._add_paging_to_query(filter_args, query)

        if filter_args.get("worker", False) or not user:
            return [s.to_worker_dict() for s in cls.get_filtered(query) or []], None

        if filter_args.get("no_count", False):
            return [s.to_dict() for s in cls.get_filtered(query) or []], None

        stories = []
        biggest_story = 0
        query = cls.enhance_with_user_votes(query, user.id)
        query = cls.enhance_with_report_count(query)

        for story, user_vote, report_count in db.session.execute(query):
            story_data = story.to_dict()
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
    def get_by_filter_json(cls, filter_args, user):
        stories, count = cls.get_by_filter(filter_args=filter_args, user=user)

        if count:
            return {"items": stories, "counts": count}, 200

        return {"items": stories}, 200

    @classmethod
    def get_for_worker(cls, filter_args: dict) -> list[dict[str, Any]]:
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
            return {"error": f"Story being added {data['id']} contains existing content. A news item conflict is raised."}, 409
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
    def _process_news_items(cls, data) -> "tuple[list[str], list[str]]":
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
    def add(cls, data) -> "tuple[dict, int]":
        try:
            if tags := data.get("tags"):
                data["tags"] = NewsItemTag.unify_tags(tags)
            if attributes := data.get("attributes"):
                data["attributes"] = NewsItemAttribute.unify_attributes_to_old_format(attributes)
            
            with db.session.no_autoflush:
                story = cls.from_dict(data)
                db.session.add(story)

                StorySearchIndex.prepare(story)
                # Use the last_change from data if provided, otherwise use the old logic
                if "last_change" in data:
                    story.update_status(change=data["last_change"])
                elif story.news_items[0].osint_source_id == "manual":
                    story.update_status()
                else:
                    story.update_status(change="external")

            db.session.commit()
            logger.info(f"Story added successfully: {story.id}")
            return {
                "message": "Story added successfully",
                "story_id": story.id,
                "news_item_ids": [item.id for item in story.news_items],
            }, 200
        except IntegrityError:
            logger.exception()
            # Rollback the transaction to ensure session is clean
            db.session.rollback()
            logger.warning(f"Story being added {data.get('id')} contains existing content. A news item conflict is raised.")
            return cls.handle_conflicting_news_items(data)

        except Exception:
            logger.exception(f"Failed to add story: {data}")
            # Rollback on any other exception
            db.session.rollback()
            return {"error": "Failed to add story"}, 400

    @classmethod
    def add_from_news_item(cls, news_item: dict) -> "tuple[dict, int]":
        if NewsItem.identical(news_item.get("hash")):
            logger.warning("Identical news item found. Skipping...")
            news_item_obj = NewsItem.get(news_item.get("id", ""))
            return {
                "error": "Identical news item found. Skipping...",
                "skipped_news_item_story_id": news_item_obj.story_id if news_item_obj else None,
            }, 400

        data = {
            "title": news_item.get("title"),
            "description": news_item.get("review", news_item.get("content")),
            "created": news_item.get("published"),
            "news_items": [news_item],
            "last_change": "internal" if news_item.get("osint_source_id") == "manual" else "external",
        }

        return cls.add(data)

    @classmethod
    def add_or_update_for_misp(cls, data: list, force: bool = False) -> "tuple[dict, int]":
        if not data:
            return {"error": "No data provided"}, 400
        prepared_stories = cls.prepare_misp_stories(data, force=force)
        results = []
        story_ids = []
        for story in prepared_stories:
            result, status = cls.add_or_update(story)
            if status != 200:
                results.append(result)
            elif status == 200:
                story_ids.append(result.get("story_id", result.get("id", result)))

        if results:
            return {"error": "Some stories could not be added", "details": {"errors": results}}, status
        return {"message": "Stories added or updated successfully", "details": {"story_ids": story_ids}}, 200

    @classmethod
    def check_news_item_data(cls, news_item: dict) -> dict | None:
        title = news_item.get("title", "")
        link = news_item.get("link", "")
        content = news_item.get("content", "")
        if not news_item.get("source"):
            return {"error": "Source not provided"}
        if not title and not link and not content:
            return {"error": "At least one of the following parameters must be provided: title, link, content"}
        return None

    @classmethod
    def add_single_news_item(cls, news_item: dict) -> tuple[dict, int]:
        if err := cls.check_news_item_data(news_item):
            return err, 400
        try:
            return cls.add_from_news_item(news_item)
        except Exception as e:
            logger.exception("Failed to add news items")
            return {"error": f"Failed to add news items: {e}"}, 400

    @classmethod
    def add_news_items(cls, news_items_list: list[dict]):
        story_ids = []
        news_item_ids = []
        skipped_items = []
        try:
            for news_item in news_items_list:
                if err := cls.check_news_item_data(news_item):
                    logger.warning(err)
                    skipped_items.append(err)
                    continue
                message, status = cls.add_from_news_item(news_item)
                if status > 299:
                    skipped_items.append(news_item.get("title", "Unknown Title"))
                    continue
                story_ids.append(message["story_id"])
                news_item_ids += message["news_item_ids"]
            db.session.commit()
        except Exception as e:
            logger.exception("Failed to add news items")
            return {"error": f"Failed to add news items: {e}"}, 400

        result = {"story_ids": story_ids, "news_item_ids": news_item_ids, "message": f"{len(news_item_ids)} News items added successfully"}
        if len(skipped_items) == len(news_items_list):
            result["message"] = "All news items were skipped"
            logger.warning(result)
            return result, 200
        if skipped_items:
            result["warning"] = f"Some items were skipped: {', '.join(skipped_items)}"
            logger.warning(result)
        logger.info(f"News items added successfully: {result}")
        return result, 200

    @classmethod
    def update(cls, story_id: str, data, user=None, external: bool = False) -> tuple[dict, int]:

        story = cls.get(story_id)
        if not story:
            return {"error": "Story not found", "id": f"{story_id}"}, 404

        # Handle vote separately as it has its own transaction
        if "vote" in data and user:
            story.vote(data["vote"], user.id)

        # Perform all other updates in a single transaction with no_autoflush
        try:
            with db.session.no_autoflush:
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

                if "tags" in data:
                    story.set_tags(data["tags"], commit=False)

                if summary := data.get("summary"):
                    story.summary = summary

                if "attributes" in data:
                    story.set_attributes(data["attributes"])

                if "links" in data:
                    story.links = data["links"]

                story.last_change = "external" if external else "internal"
                story.update_timestamps()

                # Single commit for all changes including vote
                StorySearchIndex.prepare(story)
            
            db.session.commit()
            return {"message": "Story updated successfully", "id": f"{story_id}"}, 200
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Failed to update story {story_id}")
            return {"error": f"Failed to update story: {str(e)}"}, 500

    @classmethod
    def update_with_conflicts(cls, story_id: str, upstream_data: dict) -> tuple[dict, int]:
        from core.model.story import Story
        from core.model.news_item import NewsItemAttribute  # adjust import if needed

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

        existing_conflict = StoryConflict.conflict_store.get(story_id)
        if existing_conflict:
            existing_conflict.original = original_str
            existing_conflict.updated = updated_str
            existing_conflict.has_proposals = has_proposals_value
            logger.debug(f"Updated existing conflict for story {story_id}")
        else:
            StoryConflict.conflict_store[story_id] = StoryConflict(
                story_id=story_id,
                original=original_str,
                updated=updated_str,
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
        if not (vote := NewsItemVote.get_by_filter(item_id=self.id, user_id=user_id)):
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
            self.relevance = self.relevance + 1
            vote.like = True
        elif vote_data == "dislike":
            self.dislikes = self.dislikes + 1
            self.relevance = self.relevance - 1
            vote.dislike = True

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

    def create_new_vote(self, user_id):
        vote = NewsItemVote(item_id=self.id, user_id=user_id)
        db.session.add(vote)
        return vote

    @classmethod
    def delete_by_id(cls, story_id, user):
        story = cls.get(story_id)
        if not story:
            logger.debug(f"Story with id: {story_id} not found")
            return {"error": f"Story with id: {story_id} not found"}, 404

        if cls.is_assigned_to_report([story_id]):
            logger.debug(f"Story with: {story_id} assigned to a report")
            return {"error": f"Story with: {story_id} assigned to a report"}, 500

        for news_item in story.news_items[:]:
            if news_item.allowed_with_acl(user, True):
                story.news_items.remove(news_item)
                news_item.delete_item()
            else:
                logger.debug(f"User {user.id} not allowed to remove news item {news_item.id}")
                return {"error": f"User {user.id} not allowed to remove news item {news_item.id}"}, 403

        story.update_status()

        db.session.commit()

        return {"message": f"Successfully deleted story: {story_id}"}, 200

    def delete(self, user):
        return self.delete_by_id(self.id, user)

    @classmethod
    def is_assigned_to_report(cls, story_ids: list) -> bool:
        return any(ReportItemStory.is_assigned(story_id) for story_id in story_ids)

    def get_tags_to_remove(self, tags: dict[str, NewsItemTag]) -> set[str]:
        incoming_tag_names = set(tags.keys())
        existing_tag_names = {tag.name for tag in self.tags}
        return existing_tag_names - incoming_tag_names

    def set_tags(self, incoming_tags: list | dict, commit: bool = True) -> tuple[dict, int]:
        try:
            return self._update_tags(incoming_tags, commit=commit)
        except Exception as e:
            logger.exception("Update News Item Tags Failed")
            db.session.rollback()
            return {"error": str(e)}, 500

    def _update_tags(self, incoming_tags: list | dict, commit: bool = True) -> tuple[dict, int]:
        parsed_tags = NewsItemTag.parse_tags(incoming_tags)
        if not parsed_tags:
            return {"error": "No valid tags provided"}, 400

        tags_to_remove = self.get_tags_to_remove(parsed_tags)
        self.patch_tags(parsed_tags)
        self.remove_tags(tags_to_remove)

        if commit:
            db.session.commit()
        return {"message": f"Successfully updated story: {self.id}, with {len(self.tags)} new tags"}, 200

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

    @classmethod
    def group_multiple_stories(cls, story_mappings: list[list[str]]):
        results = [cls.group_stories(story_ids) for story_ids in story_mappings]
        if any(result[1] == 500 for result in results):
            return {"error": "grouping failed"}, 500
        return {"message": "success"}, 200

    @classmethod
    def move_items_to_story(cls, story_id: str, news_item_ids: list[int], user: User | None = None):
        try:
            story = cls.get(story_id)
            if not story:
                return {"error": "not_found"}, 404
            for item in news_item_ids:
                news_item = NewsItem.get(item)
                if not news_item:
                    continue
                if user is None or news_item.allowed_with_acl(user, True):
                    story.news_items.append(news_item)
                    story.relevance += 1
                    story.update_status()
            cls.update_stories({story})
            db.session.commit()
            return {"message": "success"}, 200
        except Exception:
            logger.exception("Grouping Stories Failed")
            return {"error": "grouping failed"}, 500

    @classmethod
    def group_stories(cls, story_ids: list[str], user: User | None = None):
        try:
            if not isinstance(story_ids, list):
                return {"error": "story_ids must be a list"}, 400

            if len(story_ids) < 2 or any(not isinstance(a_id, str) or len(a_id) == 0 for a_id in story_ids):
                return {"error": "at least two valid Story ids needed"}, 404

            first_story = Story.get(story_ids.pop(0))
            if not first_story:
                return {"error": "Story not found"}, 404
            processed_stories = {first_story}
            for item in story_ids:
                story = Story.get(item)
                if not story:
                    continue

                first_story.tags = list({tag.name: tag for tag in first_story.tags + story.tags}.values())
                for news_item in story.news_items[:]:
                    if user is None or news_item.allowed_with_acl(user, True):
                        first_story.news_items.append(news_item)
                        first_story.relevance += 1
                        story.news_items.remove(news_item)
                processed_stories.add(story)

            cls.update_stories(processed_stories)
            db.session.commit()
            return {"message": "Clustering Stories successful", "id": first_story.id}, 200
        except Exception as e:
            logger.exception(f"Grouping Stories Failed - {str(e)}")
            return {"error": f"Grouping Stories Failed - {str(e)}"}, 500

    @classmethod
    def ungroup_multiple_stories(cls, story_ids: list[int], user: User | None = None):
        results = [cls.ungroup_story(story_id, user) for story_id in story_ids]
        if errors := [res[0].get("error") for res in results if res[1] != 200 and res[0].get("error") is not None]:
            error_message = "; ".join(filter(None, errors))
            logger.error(f"Errors ungrouping stories: {error_message}")
            return {"error": error_message}, 400
        return {"message": "success"}, 200

    @classmethod
    def ungroup_story(cls, story_id: int, user: User | None = None):
        try:
            if ReportItemStory.is_assigned(story_id):
                return {"error": f"Story {story_id} is assigned to a report"}, 400
            story = cls.get(story_id)
            if not story:
                return {"error": "Story not found"}, 404
            for tag in story.tags:
                if tag.to_dict().get("tag_type", "").startswith("report"):
                    return {"error": f"Story {story.id} is part of a report, you need to remove the news items manually"}, 500
            for news_item in story.news_items[:]:
                if user is None or news_item.allowed_with_acl(user, True):
                    cls.create_from_item(news_item)
            story.update_status()
            db.session.commit()
            return {"message": "Ungrouping Stories successful"}, 200
        except Exception as e:
            logger.exception(f"Ungrouping Stories Failed - {str(e)}")
            return {"error": f"Ungrouping Stories failed - {str(e)}"}, 500

    @classmethod
    def remove_news_items_from_story(cls, newsitem_ids: list, user: User | None = None):
        try:
            processed_stories = set()
            new_stories_ids = []
            for item in newsitem_ids:
                news_item = NewsItem.get(item)
                if not news_item or not user:
                    continue
                if not news_item.allowed_with_acl(user, True):
                    continue
                story = Story.get(news_item.story_id)
                if not story:
                    continue
                story.news_items.remove(news_item)
                processed_stories.add(story)
                new_stories_ids.append(cls.create_from_item(news_item))
            cls.update_stories(processed_stories)
            db.session.commit()
            return {"message": "success", "new_stories_ids": new_stories_ids}, 200
        except Exception:
            logger.exception("Grouping News Item stories Failed")
            return {"error": "ungroup failed"}, 500

    @classmethod
    def update_stories(cls, stories: set["Story"]):
        for story in stories:
            try:
                story.update_status()
            except Exception:
                logger.exception(f"Update Story: {story.id} Failed")

    @classmethod
    def prepare_misp_stories(cls, story_lists: list[dict], force) -> list[dict]:
        stories = []
        for story in story_lists:
            if story_id := story.get("id"):
                if existing_story := cls.get(story_id):
                    if not force and cls.check_internal_changes(existing_story.to_detail_dict()):
                        logger.info(f"Internal changes detected in story {existing_story.id}, story conflict raised.")
                        story["conflict"] = True
                    else:
                        if news_items_to_delete := cls.get_news_items_to_delete(story, existing_story.to_detail_dict()):
                            story["news_items_to_delete"] = news_items_to_delete
            else:
                logger.debug(f"Story does not have an ID: {story}")
                continue

            stories.append(story)
        return stories

    @classmethod
    def check_internal_changes(cls, existing_story: dict) -> bool:
        return existing_story.get("last_change") == "internal"

    @classmethod
    def get_news_items_to_delete(cls, new_story: dict, existing_story: dict) -> list:
        existing_news_items = existing_story.get("news_items", [])
        new_news_items = new_story.get("news_items", [])

        existing_ids = {item.get("id") for item in existing_news_items if item.get("id") is not None}
        new_ids = {item.get("id") for item in new_news_items if item.get("id") is not None}

        return list(existing_ids - new_ids)

    @classmethod
    def create_from_item(cls, news_item) -> str | None:
        new_story = Story(
            title=news_item.title,
            created=news_item.published,
            description=news_item.review or news_item.content,
            news_items=[news_item.id],
        )
        db.session.add(new_story)
        db.session.commit()

        StorySearchIndex.prepare(new_story)
        new_story.update_status()
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
            StorySearchIndex.remove(self)
            NewsItemTag.remove_by_story(self)
            db.session.delete(self)
            logger.debug(f"Deleting empty Story - 'ID': {self.id}")
            return True
        return False

    def update_status(self, change: str = "internal"):
        if self.remove_empty_story():
            return
        self.update_timestamps()
        self.update_status_attributes()
        self.last_change = change

    def update_status_attributes(self):
        attributes = [
            NewsItemAttribute(key="TLP", value=self.get_story_tlp()),
            NewsItemAttribute(key="cybersecurity", value=self.get_cybersecurity_status()),
            NewsItemAttribute(key="sentiment", value=self.get_story_sentiment()),
        ]
        for attribute in attributes:
            if attribute.value != "none":
                self.upsert_attribute(attribute)

    def update_timestamps(self):
        self.updated = datetime.now()
        if self.news_items:  # Only update if news_items are already loaded
            self.created = min(news_item.published for news_item in self.news_items)

    def get_story_tlp(self, input_tlp: TLPLevel | None = None) -> TLPLevel:
        most_restrictive_tlp = input_tlp or TLPLevel.CLEAR

        tlp_levels: list[TLPLevel] = []
        for news_item in self.news_items:
            if not news_item.tlp_level:
                news_item.add_attribute(NewsItemAttribute("TLP", news_item.osint_source.tlp_level))
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
        data["tags"] = [tag.to_dict() for tag in self.tags[:5]]
        return data

    def to_detail_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["news_items"] = [news_item.to_detail_dict() for news_item in self.news_items]
        data["tags"] = [tag.to_dict() for tag in self.tags]
        data["attributes"] = [attribute.to_small_dict() for attribute in self.attributes]
        data["detail_view"] = True
        return data

    def to_worker_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["news_items"] = [news_item.to_dict() for news_item in self.news_items]
        data["tags"] = {tag.name: tag.to_dict() for tag in self.tags}
        if attributes := self.attributes:
            data["attributes"] = {attribute.key: attribute.to_small_dict() for attribute in attributes}

        return data


class StorySearchIndex(BaseModel):
    __tablename__ = "story_search_index"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    data: Mapped[str] = db.Column(db.String)
    story_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("story.id", ondelete="CASCADE"), index=True)
    story: Mapped["Story"] = relationship(back_populates="search_index")

    def __init__(self, story_id, data=None):
        self.story_id = story_id
        self.data = data or ""

    @classmethod
    def remove(cls, story: "Story"):
        search_index = db.session.execute(db.select(cls).filter_by(story_id=story.id)).scalar_one_or_none()
        if search_index is not None:
            db.session.delete(search_index)
            db.session.commit()

    @classmethod
    def prepare(cls, story: "Story"):
        if not story.search_index:
            story.search_index = cls(story_id=story.id)

        data_components = [
            story.title,
            story.description,
            story.comments,
            story.summary,
        ]

        for news_item in story.news_items:
            data_components.extend(
                [
                    news_item.title,
                    news_item.review,
                    news_item.content,
                    news_item.author,
                    news_item.link,
                ]
            )
        story.search_index.data = " ".join(data_components).lower()


class NewsItemVote(BaseModel):
    __tablename__ = "news_item_vote"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    like: Mapped[bool] = db.Column(db.Boolean, default=False)
    dislike: Mapped[bool] = db.Column(db.Boolean, default=False)
    item_id: Mapped[str] = db.Column(db.String(64))
    user_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=True)

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
        self.item_id = item_id
        self.user_id = user_id
        self.like = like
        self.dislike = dislike

    @classmethod
    def get_by_filter(cls, item_id: str, user_id: int):
        return cls.get_first(db.select(cls).filter_by(item_id=item_id, user_id=user_id))

    @classmethod
    def get_user_vote(cls, item_id: str, user_id: int):
        if vote := cls.get_by_filter(item_id, user_id):
            return {"like": vote.like, "dislike": vote.dislike}
        return {"like": False, "dislike": False}


class StoryNewsItemAttribute(BaseModel):
    __tablename__ = "story_news_item_attribute"

    story_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("story.id", ondelete="CASCADE"), primary_key=True)
    news_item_attribute_id: Mapped[str] = db.Column(
        db.String(64), db.ForeignKey("news_item_attribute.id", ondelete="CASCADE"), primary_key=True
    )


class ReportItemStory(BaseModel):
    __tablename__ = "report_item_story"

    report_item_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("report_item.id", ondelete="CASCADE"), primary_key=True)
    story_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("story.id", ondelete="CASCADE"), primary_key=True)

    @classmethod
    def is_assigned(cls, story_id):
        return db.session.query(db.exists().where(cls.story_id == story_id)).scalar()

    @classmethod
    def count(cls, story_id):
        return cls.get_filtered_count(db.select(cls).where(cls.story_id == story_id))
