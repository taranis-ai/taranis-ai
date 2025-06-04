import uuid
from datetime import datetime, timedelta
from typing import Any, Sequence
from sqlalchemy import or_, func
from sqlalchemy.orm import aliased, Mapped, relationship
from sqlalchemy.sql.expression import false, null, true
from sqlalchemy.sql import Select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.exc import IntegrityError
from collections import Counter

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


class Story(BaseModel):
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
        self.last_change = last_change
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

        story_ids = [data.get("id")]
        conflict = data.pop("conflict", None)

        if Story.get(data["id"]) is None:
            message, code = cls.add(data)
            if code != 200 and message.get("error") == "Story already exists":
                logger.warning(f"Story being added {data['id']} contains existing content. A conflict is raised.")
                cls.handle_conflicting_news_items(data)
                return {"error": f"Story being added {data['id']} contains existing content. A conflict is raised."}, code
            return message, code

        if not conflict:
            if "news_items_to_delete" in data:
                cls.delete_news_items(data.pop("news_items_to_delete"))

            for news_item in data.get("news_items", []):
                logger.debug(f"{NewsItem.get(news_item.get('id'))}")
                if not NewsItem.get(news_item.get("id")):
                    result, _ = cls.add_single_news_item(news_item)
                    story_id = result.get("story_id")
                    if story_id is not None:
                        story_ids.append(story_id)

            cls.group_stories(story_ids)
            return cls.update(data["id"], data, external=True)

        result = cls.update_with_conflicts(data["id"], data)
        return result

    @classmethod
    def add(cls, data) -> "tuple[dict, int]":
        try:
            story = cls.from_dict(data)
            db.session.add(story)
            db.session.commit()
            StorySearchIndex.prepare(story)
            story.update_status()
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
    def add_multiple(cls, json_data) -> Sequence["Story"]:
        items = cls.load_multiple(json_data)
        db.session.add_all(items)
        db.session.commit()
        for item in items:
            StorySearchIndex.prepare(item)
        return items

    @classmethod
    def add_from_news_item(cls, news_item: dict) -> "tuple[dict, int]":
        if NewsItem.identical(news_item.get("hash")):
            return {"error": "Identical news item found. Skipping..."}, 400

        data = {
            "title": news_item.get("title"),
            "description": news_item.get("review", news_item.get("content")),
            "created": news_item.get("published"),
            "news_items": [news_item],
            "last_change": "internal" if news_item.get("source") == "manual" else "external",
        }

        return cls.add(data)

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
                    error_message = message.get("error", "Unknown error")
                    logger.warning(error_message)
                    skipped_items.append(error_message)
                    continue
                story_ids.append(message["story_id"])
                news_item_ids += message["news_item_ids"]
            db.session.commit()
        except Exception as e:
            logger.exception("Failed to add news items")
            return {"error": f"Failed to add news items: {e}"}, 400

        result = {
            "story_ids": story_ids,
            "news_item_ids": news_item_ids,
        }
        if skipped_items:
            result["warning"] = f"Some items were skipped: {', '.join(skipped_items)}"
        logger.info(f"News items added successfully: {result}")
        return result, 200

    @classmethod
    def update(cls, story_id: str, data, user=None, external: bool = False) -> tuple[dict, int]:
        story = cls.get(story_id)
        if not story:
            return {"error": "Story not found", "id": f"{story_id}"}, 404

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

        if "tags" in data:
            cls.reset_tags(story_id)
            cls.update_tags(story_id, data["tags"])

        if summary := data.get("summary"):
            story.summary = summary

        if "attributes" in data:
            story.set_attributes(data["attributes"])

        if "links" in data:
            story.links = data["links"]

        story.last_change = "external" if external else "internal"

        story.update_timestamps()
        db.session.commit()
        return {"message": "Story updated successfully", "id": f"{story_id}"}, 200

    @classmethod
    def update_with_conflicts(cls, id: str, data: dict) -> tuple[dict, int]:
        if current_data := Story.get(id):
            has_proposals = data.pop("has_proposals", None)
            current_data_dict = current_data.to_detail_dict()
            current_data_dict_normalized, new_data_dict_normalized = StoryConflict.normalize_data(current_data_dict, data)
            conflict = StoryConflict(
                story_id=id, original=current_data_dict_normalized, updated=new_data_dict_normalized, has_proposals=has_proposals
            )
            logger.warning(f"Conflict detected for story {id}")
            StoryConflict.conflict_store[id] = conflict
            return {
                "warning": "Conflict detected",
                "conflict": {
                    "original": current_data_dict,
                    "updated": data,
                },
            }, 409
        return {"message": "Update successful"}, 200

    @classmethod
    def handle_conflicting_news_items(cls, data: dict) -> tuple[dict, int]:
        news_items: list[dict] = data.get("news_items", [])
        if not news_items:
            return {"error": "No news items provided"}, 400

        incoming_story_id = data.get("id")
        if not incoming_story_id:
            return {"error": "Missing story ID"}, 400

        conflicts = []

        for news_item in news_items:
            news_item_id = news_item.get("id")
            if not news_item_id:
                continue

            if existing_item := NewsItem.get(news_item_id):
                existing_news_item = existing_item
                existing_story_id = existing_news_item.story_id
                logger.debug(f"CONFLICT: incoming {news_item_id} already in story {existing_story_id}")
                conflict = NewsItemConflict.register(
                    incoming_story_id=incoming_story_id,
                    news_item_id=news_item_id,
                    existing_story_id=existing_story_id,
                    incoming_story_data=data,
                )
                conflicts.append(conflict.to_dict())

        if conflicts:
            return {"conflicts": conflicts}, 409

        return {"message": "Update successful"}, 200

    def set_attributes(self, attributes: list[dict]):
        """
        Synchronize story attributes to match the provided list.
        Calls patch_attributes() for add/update,
        remove_attributes() for deletions.
        """
        input_keys = {attr["key"] for attr in attributes}
        existing_keys = {attr.key for attr in self.attributes}

        self.patch_attributes(attributes)

        keys_to_remove = existing_keys - input_keys
        self.remove_attributes(list(keys_to_remove))

    def patch_attributes(self, attributes: list[dict]):
        for attribute in attributes:
            attr_key = attribute.get("key")
            attr_value = attribute.get("value")
            if attr_key == "TLP":
                attr_value = self.get_story_tlp(TLPLevel.get_tlp_level(attr_value))  # type: ignore
            self.upsert_attribute(NewsItemAttribute(key=attr_key, value=attr_value))

    def remove_attributes(self, keys: list[str]):
        """
        Remove attributes from the story whose keys are in the provided list.
        """
        for key in keys:
            if attr := self.find_attribute_by_key(key):
                self.attributes.remove(attr)
                db.session.delete(attr)

    def upsert_attribute(self, attribute: NewsItemAttribute) -> None:
        if existing_attribute := self.find_attribute_by_key(attribute.key):
            existing_attribute.value = attribute.value
        else:
            self.attributes.append(attribute)
        db.session.commit()

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
        return any(ReportItemStory.assigned(story_id) for story_id in story_ids)

    @classmethod
    def reset_tags(cls, story_id: str) -> tuple[dict, int]:
        try:
            story = cls.get(story_id)
            if not story:
                logger.error(f"Story {story_id} not found")
                return {"error": "not_found"}, 404

            story.tags = []
            db.session.commit()
            return {"message": "success"}, 200
        except Exception as e:
            logger.exception("Reset News Item Tags Failed")
            return {"error": str(e)}, 500

    @classmethod
    def update_tags(cls, story_id: str, tags: list | dict, bot_type: str = "") -> tuple[dict, int]:
        try:
            story = cls.get(story_id)
            if not story:
                logger.error(f"Story {story_id} not found")
                return {"error": "not_found"}, 404

            new_tags = NewsItemTag.parse_tags(tags)
            for tag_name, new_tag in new_tags.items():
                if tag_name in [tag.name for tag in story.tags]:
                    continue
                if existing_tag := NewsItemTag.find_by_name(tag_name):
                    new_tag.name = existing_tag.name
                    new_tag.tag_type = existing_tag.tag_type
                story.tags.append(new_tag)
            if bot_type:
                story.attributes.append(NewsItemAttribute(key=bot_type, value=f"{len(new_tags)}"))
            db.session.commit()
            return {"message": f"Successfully updated story: {story_id}, with {len(tags)} new tags"}, 200
        except Exception as e:
            logger.exception("Update News Item Tags Failed")
            return {"error": str(e)}, 500

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
                cls.create_from_item(news_item)
            db.session.commit()
            cls.update_stories(processed_stories)
            return {"message": "success"}, 200
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
    def create_from_item(cls, news_item):
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

    def update_status(self):
        if self.remove_empty_story():
            return
        self.update_timestamps()
        self.update_status_attributes()

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
        self.created = min(news_item.published for news_item in self.news_items)

    def get_story_tlp(self, input_tlp: TLPLevel | None = None) -> TLPLevel:
        most_restrictive_tlp = input_tlp or TLPLevel.CLEAR

        tlp_levels: list[TLPLevel] = []
        for news_item in self.news_items:
            if not news_item.tlp_level:
                news_item.add_attribute(NewsItemAttribute("TLP", news_item.osint_source.tlp_level))
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
        data["tags"] = [{"name": tag.name, "tag_type": tag.tag_type} for tag in self.tags]
        if attributes := self.attributes:
            data["attributes"] = [attribute.to_dict() for attribute in attributes]
        return data


class StorySearchIndex(BaseModel):
    __tablename__ = "story_search_index"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    data: Mapped[str] = db.Column(db.String)
    story_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("story.id", ondelete="CASCADE"), index=True)

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
        search_index = db.session.execute(db.select(cls).filter_by(story_id=story.id)).scalar_one_or_none()
        if search_index is None:
            search_index = StorySearchIndex(story.id)
            db.session.add(search_index)

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

        search_index.data = " ".join(data_components).lower()
        db.session.commit()


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
    def assigned(cls, story_id):
        return db.session.query(db.exists().where(cls.story_id == story_id)).scalar()

    @classmethod
    def count(cls, story_id):
        return cls.get_filtered_count(db.select(cls).where(cls.story_id == story_id))
