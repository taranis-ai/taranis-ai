from __future__ import annotations

import uuid

import pytest

from core.model.story import Story
from tests.application.support.builders import create_story


def _search_story_ids(client, auth_header, search_term: str) -> set[str]:
    response = client.get(
        "/api/assess/stories",
        headers=auth_header,
        query_string={"search": search_term, "limit": 20, "offset": 0},
    )

    assert response.status_code == 200
    payload = response.get_json()
    return {item["id"] for item in payload["items"]}


@pytest.mark.usefixtures("session")
def test_story_search_does_not_match_updated_description(client, auth_header, story_search_story_payload):
    story = create_story(story_search_story_payload)
    description_search_term = f"updated description {uuid.uuid4().hex}"

    response, status = Story.update(story.id, {"description": description_search_term})

    assert status == 200
    assert response["id"] == story.id
    assert story.id not in _search_story_ids(client, auth_header, description_search_term)
    assert story.id in _search_story_ids(client, auth_header, story.title)


@pytest.mark.usefixtures("session")
def test_story_search_matches_updated_summary(client, auth_header, story_search_story_payload):
    story = create_story(story_search_story_payload)
    summary_search_term = f"updated summary {uuid.uuid4().hex}"

    response, status = Story.update(story.id, {"summary": summary_search_term})

    assert status == 200
    assert response["id"] == story.id
    assert story.id in _search_story_ids(client, auth_header, summary_search_term)


@pytest.mark.usefixtures("session")
def test_story_search_reflects_grouped_news_item_text(client, auth_header, story_search_story_payloads):
    target_story_payload, source_story_payload = story_search_story_payloads
    target_story = create_story(target_story_payload)
    source_story = create_story(source_story_payload)
    merged_news_title = source_story.news_items[0].title

    assert source_story.id in _search_story_ids(client, auth_header, merged_news_title)

    response, status = Story.group_stories([target_story.id, source_story.id])

    assert status == 200
    assert response["id"] == target_story.id

    search_results = _search_story_ids(client, auth_header, merged_news_title)
    assert target_story.id in search_results
    assert source_story.id not in search_results
