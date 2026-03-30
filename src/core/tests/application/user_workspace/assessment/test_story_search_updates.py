from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from core.model.story import Story
from core.service.story import StoryService
from tests.application.support.builders import create_story


@pytest.mark.usefixtures("session")
def test_story_search_does_not_match_updated_description(client, auth_header, story_search_story_payload):
    story = create_story(story_search_story_payload)
    search_term = f"updated description {uuid.uuid4().hex}"
    indexed_search_term = story.title

    response, status = Story.update(story.id, {"description": search_term})

    assert status == 200
    assert response["id"] == story.id

    search_response = client.get(
        "/api/assess/stories",
        headers=auth_header,
        query_string={"search": search_term, "limit": 20, "offset": 0},
    )

    assert search_response.status_code == 200
    payload = search_response.get_json()
    assert story.id not in {item["id"] for item in payload["items"]}

    indexed_search_response = client.get(
        "/api/assess/stories",
        headers=auth_header,
        query_string={"search": indexed_search_term, "limit": 20, "offset": 0},
    )

    assert indexed_search_response.status_code == 200
    indexed_payload = indexed_search_response.get_json()
    assert story.id in {item["id"] for item in indexed_payload["items"]}


@pytest.mark.usefixtures("session")
def test_story_update_rebuilds_search_index_for_searchable_fields(monkeypatch, story_search_story_payload):
    story = create_story(story_search_story_payload)
    calls: list[dict[str, object]] = []

    def fake_update_search_vector(force: bool = False, story_ids=None, commit: bool = True) -> int:
        calls.append({"force": force, "story_ids": list(story_ids or []), "commit": commit})
        return len(story_ids or [])

    monkeypatch.setattr(StoryService, "update_search_vector", staticmethod(fake_update_search_vector))

    response, status = Story.update(story.id, {"summary": "updated summary"})

    assert status == 200
    assert response["id"] == story.id
    assert calls == [{"force": True, "story_ids": [story.id], "commit": False}]


@pytest.mark.usefixtures("session")
def test_story_update_does_not_rebuild_search_index_for_description(monkeypatch, story_search_story_payload):
    story = create_story(story_search_story_payload)
    calls: list[dict[str, object]] = []

    def fake_update_search_vector(force: bool = False, story_ids=None, commit: bool = True) -> int:
        calls.append({"force": force, "story_ids": list(story_ids or []), "commit": commit})
        return len(story_ids or [])

    monkeypatch.setattr(StoryService, "update_search_vector", staticmethod(fake_update_search_vector))

    response, status = Story.update(story.id, {"description": "updated description"})

    assert status == 200
    assert response["id"] == story.id
    assert calls == []


@pytest.mark.usefixtures("session")
def test_group_stories_rebuilds_search_indexes_for_all_affected_stories(monkeypatch, story_search_story_payloads):
    target_story_payload, source_story_payload = story_search_story_payloads
    target_story = create_story(target_story_payload)
    source_story = create_story(source_story_payload)
    calls: list[dict[str, object]] = []

    def fake_update_search_vector(force: bool = False, story_ids=None, commit: bool = True) -> int:
        calls.append({"force": force, "story_ids": list(story_ids or []), "commit": commit})
        return len(story_ids or [])

    monkeypatch.setattr(StoryService, "update_search_vector", staticmethod(fake_update_search_vector))

    response, status = Story.group_stories([target_story.id, source_story.id])

    assert status == 200
    assert response["id"] == target_story.id
    assert len(calls) == 1
    assert calls[0]["force"] is True
    assert calls[0]["commit"] is False
    assert set(calls[0]["story_ids"]) == {target_story.id, source_story.id}


def test_fulltext_search_sql_tracks_story_moves_only_for_searchable_story_fields():
    sql_path = Path(__file__).resolve().parents[4] / "core" / "sql" / "fulltext_search.sql"
    sql = " ".join(sql_path.read_text().split())

    assert "story_description" not in sql
    assert "UPDATE OF title, description, summary" not in sql
    assert "UPDATE OF title, summary" in sql
    assert "UPDATE OF story_id, title, content OR DELETE" in sql
    assert "old_story_id IS NOT NULL AND old_story_id IS DISTINCT FROM new_story_id" in sql
