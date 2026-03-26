from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from models.assess import NewsItem as AssessNewsItem

from core.managers.db_manager import db
from core.model.osint_source import OSINTSource


if TYPE_CHECKING:
    from core.model.news_item import NewsItem
    from core.model.story import Story
    from core.model.user import User


class StoryOperationsService:
    IMPORTANT_RELEVANCE_BONUS = 3
    IN_REPORT_RELEVANCE_BONUS = 3

    @staticmethod
    def get_initial_relevance_for_source(osint_source_id: str | None) -> int:
        if not osint_source_id:
            return 0
        if osint_source := OSINTSource.get(osint_source_id):
            return osint_source.rank
        return 0

    @classmethod
    def get_initial_relevance_for_news_item(cls, news_item: "NewsItem | AssessNewsItem | dict[str, Any]") -> int:
        if isinstance(news_item, dict):
            return cls.get_initial_relevance_for_source(news_item.get("osint_source_id"))
        return cls.get_initial_relevance_for_source(getattr(news_item, "osint_source_id", None))

    @classmethod
    def calculate_source_relevance(cls, story: "Story") -> int:
        return max((cls.get_initial_relevance_for_news_item(news_item) for news_item in story.news_items), default=0)

    @staticmethod
    def calculate_vote_score(story: "Story") -> int:
        return (story.likes or 0) - (story.dislikes or 0)

    @classmethod
    def calculate_important_bonus(cls, story: "Story") -> int:
        return cls.IMPORTANT_RELEVANCE_BONUS if story.important else 0

    @classmethod
    def calculate_in_report_bonus(cls, story: "Story", in_reports_count: int | None = None) -> int:
        from core.model.story import ReportItemStory

        report_count = in_reports_count if in_reports_count is not None else ReportItemStory.count(story.id)
        return cls.IN_REPORT_RELEVANCE_BONUS if report_count > 0 else 0

    @classmethod
    def calculate_relevance_feedback(cls, story: "Story", in_reports_count: int | None = None) -> int:
        return cls.calculate_vote_score(story) + cls.calculate_important_bonus(story) + cls.calculate_in_report_bonus(story, in_reports_count)

    @classmethod
    def recompute_relevance(cls, story: "Story", in_reports_count: int | None = None) -> int:
        story.relevance = (
            cls.calculate_source_relevance(story)
            + cls.calculate_relevance_feedback(story, in_reports_count)
            + (story.relevance_override or 0)
        )
        return story.relevance

    @staticmethod
    def sync_vote_counts(story: "Story") -> None:
        from core.model.story import NewsItemVote

        votes = list(db.session.execute(db.select(NewsItemVote).filter(NewsItemVote.item_id == story.id)).scalars())
        story.likes = sum(1 for vote in votes if vote.like)
        story.dislikes = sum(1 for vote in votes if vote.dislike)

    @staticmethod
    def _vote_merge_key(vote: Any) -> tuple[bool, int | None]:
        return (vote.user_id is None, vote.user_id if vote.user_id is not None else vote.id)

    @classmethod
    def merge_votes_into_story(cls, target_story: "Story", absorbed_story_ids: list[str]) -> None:
        if not absorbed_story_ids:
            return

        from core.model.story import NewsItemVote

        merged_story_ids = [target_story.id, *absorbed_story_ids]
        votes = list(db.session.execute(db.select(NewsItemVote).filter(NewsItemVote.item_id.in_(merged_story_ids))).scalars())
        votes_by_user: dict[tuple[bool, int | None], list[Any]] = defaultdict(list)
        for vote in votes:
            votes_by_user[cls._vote_merge_key(vote)].append(vote)

        for user_votes in votes_by_user.values():
            active_votes = [vote for vote in user_votes if vote.user_vote]
            directions = {vote.user_vote for vote in active_votes}
            keeper = next((vote for vote in user_votes if vote.item_id == target_story.id), user_votes[0])

            if len(directions) == 1:
                direction = directions.pop()
                keeper.item_id = target_story.id
                keeper.like = direction == "like"
                keeper.dislike = direction == "dislike"
                for vote in user_votes:
                    if vote is not keeper:
                        db.session.delete(vote)
            else:
                for vote in user_votes:
                    db.session.delete(vote)

        cls.sync_vote_counts(target_story)

    @staticmethod
    def delete_votes_for_story_ids(story_ids: list[str]) -> None:
        if not story_ids:
            return

        from core.model.story import NewsItemVote

        db.session.execute(db.delete(NewsItemVote).where(NewsItemVote.item_id.in_(story_ids)))

    @staticmethod
    def cleanup_orphan_votes() -> int:
        from core.model.story import NewsItemVote, Story

        result = db.session.execute(
            db.delete(NewsItemVote).where(~db.exists().where(Story.id == NewsItemVote.item_id)).returning(NewsItemVote.id)
        )
        return len(result.scalars().all())

    @staticmethod
    def merge_story_tags(target_story: "Story", source_story: "Story") -> None:
        target_story.tags = list({tag.name: tag for tag in [*target_story.tags, *source_story.tags]}.values())

    @staticmethod
    def transfer_news_item_to_story(
        target_story: "Story",
        news_item: "NewsItem | None",
        source_stories_by_id: dict[str, "Story"],
        user: "User | None" = None,
    ) -> None:
        story_cls = type(target_story)
        if not news_item or (user is not None and not news_item.allowed_with_acl(user, True)) or news_item.story_id == target_story.id:
            return

        if source_story := story_cls.get(news_item.story_id):
            source_stories_by_id[source_story.id] = source_story
            if news_item in source_story.news_items:
                source_story.news_items.remove(news_item)

        target_story.news_items.append(news_item)

    @classmethod
    def finalize_story_merge(cls, target_story: "Story", source_stories: list["Story"]) -> set["Story"]:
        processed_stories = {target_story, *source_stories}
        absorbed_story_ids: list[str] = []
        absorbed_overrides = [target_story.relevance_override or 0]

        for source_story in source_stories:
            if len(source_story.news_items) == 0:
                absorbed_story_ids.append(source_story.id)
                absorbed_overrides.append(source_story.relevance_override or 0)

        target_story.relevance_override = max(absorbed_overrides)
        cls.merge_votes_into_story(target_story, absorbed_story_ids)
        type(target_story).update_stories(processed_stories)
        return processed_stories
