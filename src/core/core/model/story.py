import uuid
from datetime import datetime, timedelta
from typing import Any, Sequence
from sqlalchemy import or_, func
from sqlalchemy.orm import aliased, Mapped
from sqlalchemy.sql.expression import false, null
from sqlalchemy.sql import Select

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


class Story(BaseModel):
    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    title: Mapped[str] = db.Column(db.String())
    description: Mapped[str] = db.Column(db.String())
    created: Mapped[datetime] = db.Column(db.DateTime)

    read: Mapped[bool] = db.Column(db.Boolean, default=False)
    important: Mapped[bool] = db.Column(db.Boolean, default=False)

    likes: Mapped[int] = db.Column(db.Integer, default=0)
    dislikes: Mapped[int] = db.Column(db.Integer, default=0)
    relevance: Mapped[int] = db.Column(db.Integer, default=0)

    comments: Any = db.Column(db.String(), default="")
    summary: Any = db.Column(db.Text, default="")
    news_items: Any = db.relationship("NewsItem")
    attributes: Any = db.relationship("NewsItemAttribute", secondary="story_news_item_attribute")

    def __init__(
        self,
        title: str,
        description: str = "",
        created: datetime | str = datetime.now(),
        read: bool = False,
        important: bool = False,
        summary: str = "",
        comments: str = "",
        attributes=None,
        news_items=None,
        id=None,
    ):
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.description = description
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        else:
            self.created = created
        self.read = read
        self.important = important
        self.summary = summary
        self.comments = comments
        self.news_items = self.load_news_items(news_items)
        if attributes:
            self.attributes = NewsItemAttribute.load_multiple(attributes)

    def load_news_items(self, news_items):
        if all(isinstance(item, str) for item in news_items):
            return [NewsItem.get(item_id) for item_id in news_items]
        elif all(isinstance(item, NewsItem) for item in news_items):
            return news_items
        elif all(isinstance(item, dict) for item in news_items):
            return [NewsItem.from_dict(item) for item in news_items]
        return []

    @classmethod
    def get_for_api(cls, item_id: str, user: User) -> tuple[dict[str, Any], int]:
        logger.debug(f"Getting {cls.__name__} {item_id}")
        if item := cls.get(item_id):
            return item.to_detail_dict(user.id), 200
        return {"error": f"{cls.__name__} {item_id} not found"}, 404

    @classmethod
    def get_story_clusters(cls, days: int = 7, limit: int = 10):
        start_date = datetime.now() - timedelta(days=days)
        clusters = (
            cls.query.join(NewsItem)
            .join(NewsItem)
            .filter(NewsItem.published >= start_date)
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
                "published": [ni.published.isoformat() for ni in cluster.news_items],
            }
            for cluster in clusters
        ]

    @classmethod
    def _add_filters_to_query(cls, filter_args: dict, query: Select) -> Select:
        query = query.join(NewsItem, NewsItem.story_id == Story.id)
        query = query.join(OSINTSource, NewsItem.osint_source_id == OSINTSource.id)

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
            )
            query = query.filter(ReportItemStory.story_id == null())

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

            query = query.filter(NewsItem.published >= date_limit)

        if timefrom := filter_args.get("timefrom"):
            query = query.filter(NewsItem.published >= datetime.fromisoformat(timefrom))

        if timeto := filter_args.get("timeto"):
            query = query.filter(NewsItem.published <= datetime.fromisoformat(timeto))

        return query

    @classmethod
    def _add_sorting_to_query(cls, filter_args: dict, query):
        if sort := filter_args.get("sort", "date_desc").lower():
            if sort == "date_desc":
                query = query.group_by(NewsItem.published).order_by(db.desc(NewsItem.published), db.desc(cls.id))

            elif sort == "date_asc":
                query = query.group_by(NewsItem.published).order_by(db.asc(NewsItem.published), db.asc(cls.id))

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
        query = db.select(cls).distinct().group_by(Story.id)
        query = cls._add_filters_to_query(filter_args, query)

        if user:
            query = cls._add_ACL_check(query, user)
            query = cls._add_TLP_check(query, user)

        query = cls._add_sorting_to_query(filter_args, query)
        query = cls._add_paging_to_query(filter_args, query)

        if filter_args.get("no_count", False):
            return cls.get_filtered(query), 0
        return cls.get_filtered(query), cls.get_filtered_count(query)

    @classmethod
    def get_date_counts(cls, news_items: list[dict[str, Any]]) -> Counter:
        return Counter(datetime.fromisoformat(news_item["published"]).strftime("%d-%m") for news_item in news_items)

    @classmethod
    def get_max_item_count(cls, news_items: list[dict[str, Any]]) -> int:
        date_counts = cls.get_date_counts(news_items)
        return max(date_counts.values(), default=0)

    @classmethod
    def get_item_dict(cls, story: "Story", user: User) -> dict[str, Any]:
        item = story.to_dict()
        item["in_reports_count"] = ReportItemStory.count(story.id)
        item["user_vote"] = NewsItemVote.get_user_vote(story.id, user.id)
        return item

    @classmethod
    def get_by_filter_json(cls, filter_args, user):
        stories, count = cls.get_by_filter(filter_args=filter_args, user=user)
        items = []
        max_item_count = 0

        if not stories:
            return {"items": []}, 404

        for story in stories:
            item = cls.get_item_dict(story, user)

            current_max_item = cls.get_max_item_count(item["news_items"])
            max_item_count = max(max_item_count, current_max_item)

            items.append(item)

        if filter_args.get("no_count", False):
            return {"items": items, "max_item": max_item_count}, 200

        return {"total_count": count, "items": items, "max_item": max_item_count}

    @classmethod
    def get_for_worker(cls, filter_args: dict) -> list[dict[str, Any]]:
        stories, _ = cls.get_by_filter(filter_args=filter_args)
        return [story.to_worker_dict() for story in stories] if stories else []

    @classmethod
    def add(cls, data) -> "Story":
        item = cls.from_dict(data)
        db.session.add(item)
        db.session.commit()
        StorySearchIndex.prepare(item)
        item.update_tlp()
        return item

    @classmethod
    def add_multiple(cls, json_data) -> Sequence["Story"]:
        items = cls.load_multiple(json_data)
        db.session.add_all(items)
        db.session.commit()
        for item in items:
            StorySearchIndex.prepare(item)
            item.update_tlp()
        return items

    @classmethod
    def add_from_news_item(cls, news_item: dict):
        return Story.add(
            {
                "title": news_item.get("title"),
                "description": news_item.get("review", news_item.get("content")),
                "created": news_item.get("published"),
                "news_items": [news_item],
            }
        ).id

    @classmethod
    def add_news_items(cls, news_items_list: list[dict]):
        ids = []
        try:
            ids.extend(cls.add_from_news_item(news_item) for news_item in news_items_list if not NewsItem.identical(news_item.get("hash")))
            db.session.commit()
        except Exception as e:
            logger.exception(f"Failed to add news items: {e}")
            return {"error": f"Failed to add news items: {e}"}, 400

        logger.debug(f"Added {len(ids)} news items - {ids}")
        return {"message": f"Added {len(ids)} news items", "ids": ids}, 200

    @classmethod
    def update(cls, story_id: str, data, user=None):
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

        if "summary" in data:
            cls.summary = data["summary"]

        if "attributes" in data:
            story.update_attributes(data["attributes"])

        story.update_status()
        db.session.commit()
        return {"message": "Story updated Successful", "id": f"{story_id}"}, 200

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
    def delete_by_id(cls, story_id, user):
        story = cls.get(story_id)
        if not story:
            return {"error": f"Story with id: {story_id} not found"}, 404

        if cls.is_assigned_to_report([story_id]):
            return {"error": f"Story with: {story_id} assigned to a report"}, 500

        for news_item in story.news_items:
            if news_item.allowed_with_acl(user, True):
                story.news_items.remove(news_item)
                news_item.delete_item()
            else:
                logger.debug(f"User {user.id} not allowed to remove news item {news_item.id}")
                return {"error": f"User {user.id} not allowed to remove news item {news_item.id}"}, 403

        story.update_status()

        db.session.commit()

        return {"message": "success"}, 200

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
            logger.log_debug_trace("Reset News Item Tags Failed")
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
            return {"message": "success"}, 200
        except Exception as e:
            logger.log_debug_trace("Update News Item Tags Failed")
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
                    story.relevance += news_item.relevance + 1
                    story.add(story)
                    story.update_status()
            cls.update_stories(story)
            db.session.commit()
            return {"message": "success"}, 200
        except Exception:
            logger.log_debug_trace("Grouping Stories Failed")
            return {"error": "grouping failed"}, 500

    @classmethod
    def group_stories(cls, story_ids: list[str], user: User | None = None):
        try:
            logger.debug(story_ids)
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
            return {"message": "success"}, 200
        except Exception:
            logger.log_debug_trace("Grouping Stories Failed")
            return {"error": "Grouping Stories Failed"}, 500

    @classmethod
    def ungroup_multiple_stories(cls, story_ids: list[int], user: User | None = None):
        results = [cls.ungroup_story(story_id, user) for story_id in story_ids]
        if any(result[1] == 500 for result in results):
            return {"error": "grouping failed"}, 400
        return {"message": "success"}, 200

    @classmethod
    def ungroup_story(cls, story_id: int, user: User | None = None):
        try:
            story = Story.get(story_id)
            if not story:
                return {"error": "not_found"}, 404
            for news_item in story.news_items[:]:
                if user is None or news_item.allowed_with_acl(user, True):
                    cls.create_from_item(news_item)
            cls.update_stories({story})
            db.session.commit()
            return {"message": "success"}, 200
        except Exception:
            logger.log_debug_trace("Ungrouping Stories Failed")
            return {"error": "ungroup failed"}, 500

    @classmethod
    def remove_news_items_from_story(cls, newsitem_ids: list, user: User | None = None):
        try:
            processed_stories = set()
            for item in newsitem_ids:
                news_item = NewsItem.get(item)
                if not news_item:
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
            logger.log_debug_trace("Grouping News Item stories Failed")
            return {"error": "ungroup failed"}, 500

    @classmethod
    def update_stories(cls, stories: set):
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

    def update_status(self):
        if len(self.news_items) == 0:
            StorySearchIndex.remove(self)
            NewsItemTag.remove_by_story(self)
            db.session.delete(self)
            logger.debug(f"Deleting empty Story - 'ID': {self.id}")
            return

        self.update_tlp()

    def update_tlp(self):
        highest_tlp = None
        for news_item in self.news_items:
            if tlp_level := news_item.get_tlp():
                tlp_level_enum = TLPLevel(tlp_level)
                if highest_tlp is None or tlp_level_enum > highest_tlp:
                    highest_tlp = tlp_level_enum

        if highest_tlp:
            logger.debug(f"Setting TLP level {highest_tlp} for story {self.id}")
            NewsItemAttribute.set_or_update(self.attributes, "TLP", highest_tlp.value)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["news_items"] = [news_item.to_dict() for news_item in self.news_items]
        data["tags"] = [tag.to_small_dict() for tag in self.tags]
        if attributes := self.attributes:
            data["attributes"] = [news_item_attribute.to_dict() for news_item_attribute in attributes]
        return data

    def to_detail_dict(self, user_id) -> dict[str, Any]:
        data = self.to_dict()
        data["in_reports_count"] = ReportItemStory.count(self.id)
        data["user_vote"] = NewsItemVote.get_user_vote(self.id, user_id)
        return data

    def to_worker_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["news_items"] = [news_item.to_dict() for news_item in self.news_items]
        data["tags"] = {tag.name: tag.to_dict() for tag in self.tags}
        if attributes := self.attributes:
            data["attributes"] = [news_item_attribute.to_dict() for news_item_attribute in attributes]
        return data


class StorySearchIndex(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    data: Any = db.Column(db.String)
    story_id: Any = db.Column(db.String(64), db.ForeignKey("story.id"), index=True)

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

            data_components.extend([attribute.value for attribute in news_item.attributes])

        search_index.data = " ".join(data_components).lower()
        db.session.commit()


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


class StoryNewsItemAttribute(BaseModel):
    story_id = db.Column(db.String(64), db.ForeignKey("story.id"), primary_key=True)
    news_item_attribute_id = db.Column(db.String(64), db.ForeignKey("news_item_attribute.id", ondelete="CASCADE"), primary_key=True)


class ReportItemStory(BaseModel):
    report_item_id = db.Column(db.String(64), db.ForeignKey("report_item.id", ondelete="CASCADE"), primary_key=True)
    story_id = db.Column(db.String(64), db.ForeignKey("story.id"), primary_key=True)

    @classmethod
    def assigned(cls, story_id):
        return db.session.query(db.exists().where(ReportItemStory.story_id == story_id)).scalar()

    @classmethod
    def count(cls, story):
        return cls.get_filtered_count(db.select(cls).filter_by(story_id=story))
