from __future__ import annotations

import pytest

from core.model.report_item import ReportItem
from core.model.story import Story
from core.model.user import User
from tests.application.support.builders import create_osint_source, create_report, create_story


@pytest.mark.usefixtures("app")
def test_ranked_story_uses_ad_hoc_source_relevance_and_hides_breakdown(
    session, story_relevance_news_item_payload_factory, story_relevance_story_payload_factory
):
    source = create_osint_source(rank=4)
    story = create_story(story_relevance_story_payload_factory([story_relevance_news_item_payload_factory(source.id)]))

    detail = story.to_detail_dict()

    assert story.relevance == 4
    assert story.relevance_source == 4
    assert story.relevance_override == 0
    assert "relevance_breakdown" not in detail


@pytest.mark.usefixtures("app")
def test_explicit_relevance_payload_becomes_override(
    session, story_relevance_news_item_payload_factory, story_relevance_story_payload_factory
):
    story = create_story(story_relevance_story_payload_factory([story_relevance_news_item_payload_factory("manual")], relevance=5))

    assert story.relevance == 5
    assert story.relevance_source == 0
    assert story.relevance_override == 5


@pytest.mark.usefixtures("app")
def test_marking_story_important_adds_relevance_bonus(
    session, story_relevance_news_item_payload_factory, story_relevance_story_payload_factory
):
    story = create_story(story_relevance_story_payload_factory([story_relevance_news_item_payload_factory("manual")]))

    response, status = Story.update(story.id, {"important": True})
    assert status == 200

    updated_story = Story.get(story.id)
    assert updated_story is not None
    assert updated_story.relevance == 3
    assert updated_story.relevance_feedback == 3


@pytest.mark.usefixtures("app")
def test_report_assignment_adds_bonus_once(
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
):
    admin = User.find_by_name("admin")
    assert admin is not None

    story = create_story(story_relevance_story_payload_factory([story_relevance_news_item_payload_factory("manual")]))
    report_one = create_report(story_relevance_report_payload_factory(title="Relevance Report One"))
    report_two = create_report(story_relevance_report_payload_factory(title="Relevance Report Two"))

    response, status = ReportItem.add_stories(report_one.id, [story.id], admin)
    assert status == 200, response

    story = Story.get(story.id)
    assert story is not None
    assert story.relevance == 3
    assert story.relevance_feedback == 3

    response, status = ReportItem.add_stories(report_two.id, [story.id], admin)
    assert status == 200, response

    story = Story.get(story.id)
    assert story is not None
    assert story.relevance == 3
    assert story.relevance_feedback == 3


@pytest.mark.usefixtures("app")
def test_grouping_uses_max_source_rank_instead_of_size_bonus(
    session, story_relevance_news_item_payload_factory, story_relevance_story_payload_factory
):
    low_source = create_osint_source(rank=1)
    high_source = create_osint_source(rank=5)

    first_story = create_story(
        story_relevance_story_payload_factory([story_relevance_news_item_payload_factory(low_source.id)], title="Low rank story")
    )
    second_story = create_story(
        story_relevance_story_payload_factory([story_relevance_news_item_payload_factory(high_source.id)], title="High rank story")
    )

    response, status = Story.group_stories([first_story.id, second_story.id])
    assert status == 200, response

    grouped_story = Story.get(first_story.id)
    assert grouped_story is not None
    assert grouped_story.relevance_source == 5
    assert grouped_story.relevance == 5
    assert len(grouped_story.news_items) == 2


@pytest.mark.usefixtures("app")
def test_grouping_conflicting_votes_clears_feedback(
    session, story_relevance_news_item_payload_factory, story_relevance_story_payload_factory
):
    admin = User.find_by_name("admin")
    assert admin is not None

    first_story = create_story(
        story_relevance_story_payload_factory([story_relevance_news_item_payload_factory("manual")], title="Vote merge target")
    )
    second_story = create_story(
        story_relevance_story_payload_factory([story_relevance_news_item_payload_factory("manual")], title="Vote merge source")
    )

    Story.update(first_story.id, {"vote": "like"}, user=admin)
    Story.update(second_story.id, {"vote": "dislike"}, user=admin)

    response, status = Story.group_stories([first_story.id, second_story.id], user=admin)
    assert status == 200, response

    grouped_story = Story.get(first_story.id)
    assert grouped_story is not None
    assert grouped_story.likes == 0
    assert grouped_story.dislikes == 0
    assert grouped_story.relevance_feedback == 0


@pytest.mark.usefixtures("app")
def test_grouping_matching_votes_dedupes_feedback(session, story_relevance_news_item_payload_factory, story_relevance_story_payload_factory):
    admin = User.find_by_name("admin")
    assert admin is not None

    first_story = create_story(
        story_relevance_story_payload_factory(
            [story_relevance_news_item_payload_factory("manual")],
            title="Matching vote target",
        )
    )
    second_story = create_story(
        story_relevance_story_payload_factory(
            [story_relevance_news_item_payload_factory("manual")],
            title="Matching vote source",
        )
    )

    Story.update(first_story.id, {"vote": "like"}, user=admin)
    Story.update(second_story.id, {"vote": "like"}, user=admin)

    response, status = Story.group_stories([first_story.id, second_story.id], user=admin)
    assert status == 200, response

    grouped_story = Story.get(first_story.id)
    assert grouped_story is not None
    assert grouped_story.likes == 1
    assert grouped_story.dislikes == 0
    assert grouped_story.relevance_feedback == 1


@pytest.mark.usefixtures("app")
def test_partial_ungroup_keeps_original_feedback_and_new_story_starts_clean(
    session, story_relevance_news_item_payload_factory, story_relevance_story_payload_factory
):
    source = create_osint_source(rank=4)
    story = create_story(
        story_relevance_story_payload_factory(
            [
                story_relevance_news_item_payload_factory(source.id, title="Primary grouped item"),
                story_relevance_news_item_payload_factory(source.id, title="Secondary grouped item"),
            ],
            title="Ungroup feedback story",
        )
    )

    response, status = Story.update(story.id, {"important": True})
    assert status == 200, response

    news_item_to_split = story.news_items[1].id
    admin = User.find_by_name("admin")
    assert admin is not None
    response, status = Story.ungroup_news_items_from_story([news_item_to_split], user=admin)
    assert status == 200, response

    original_story = Story.get(story.id)
    assert original_story is not None
    assert original_story.relevance == 7
    assert original_story.relevance_feedback == 3

    new_story = Story.get(response["new_stories_ids"][0])
    assert new_story is not None
    assert new_story.relevance == 4
    assert new_story.important is False
    assert new_story.relevance_override == 0
    assert new_story.relevance_feedback == 0
