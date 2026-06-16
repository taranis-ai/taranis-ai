from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import core.service.dashboard as dashboard_module
from core.model.base_model import BaseModel
from core.model.news_item import NewsItem
from core.model.news_item_conflict import NewsItemConflict
from core.model.product import Product
from core.model.report_item import ReportItem
from core.model.story import Story
from core.model.story_conflict import StoryConflict
from core.model.task import Task
from core.service.dashboard import DashboardService
from tests.application.support.builders import build_news_item_payload, create_story


def _unique_value(prefix: str) -> str:
    return f"{prefix}-{BaseModel.uuid7_str()}"


def test_get_dashboard_data_includes_task_totals(monkeypatch):
    latest_collected = datetime(2026, 4, 13, 12, 30, tzinfo=timezone.utc)

    monkeypatch.setattr(NewsItem, "get_count", classmethod(lambda cls: 11))
    monkeypatch.setattr(Story, "get_count", classmethod(lambda cls: 7))
    monkeypatch.setattr(Product, "get_count", classmethod(lambda cls: 3))
    monkeypatch.setattr(ReportItem, "count_all", classmethod(lambda cls, completed: 5 if completed else 2))
    monkeypatch.setattr(NewsItem, "latest_collected", classmethod(lambda cls: latest_collected))
    monkeypatch.setattr(
        dashboard_module.queue_manager,
        "queue_manager",
        SimpleNamespace(get_scheduled_jobs=lambda: ({"total_count": 4}, None)),
        raising=False,
    )
    monkeypatch.setattr(StoryConflict, "conflict_store", [object(), object()])
    monkeypatch.setattr(NewsItemConflict, "conflict_store", [object()])
    monkeypatch.setattr("core.service.dashboard.get_health_response", lambda: ({"healthy": True}, 200))
    monkeypatch.setattr(
        Task,
        "get_status_totals",
        classmethod(
            lambda cls: {
                "failures": 1,
                "successes": 2,
                "success_pct": 66,
                "total": 3,
            }
        ),
    )

    dashboard = DashboardService.get_dashboard_data()["items"][0]

    assert dashboard["task_status_totals"] == {
        "failures": 1,
        "successes": 2,
        "success_pct": 66,
        "total": 3,
    }


def test_count_user_scheduled_jobs_ignores_housekeeping_and_malformed_entries():
    schedules = {
        "items": [
            {"id": dashboard_module.queue_manager.TOKEN_CLEANUP_JOB_ID},
            {"id": "collector-source-1"},
            "unexpected",
            None,
        ]
    }

    assert DashboardService._count_user_scheduled_jobs(schedules) == 1


def test_trending_clusters_include_tags_from_story_creation(app, client, auth_header):
    tag_type = _unique_value("created-type")
    tag_name = _unique_value("created-tag")
    story_id = None

    with app.app_context():
        news_item = build_news_item_payload(title_prefix="Tagged Created Story")
        news_item["tags"] = [{"name": tag_name, "tag_type": tag_type}]
        story = create_story(news_items=[news_item])
        story_id = story.id

    try:
        response = client.get("/api/dashboard/trending-clusters", headers=auth_header, query_string={"days": 7})
        payload = response.get_json()

        assert response.status_code == 200
        cluster = next(item for item in payload["items"] if item["name"] == tag_type)
        assert cluster["size"] == 1
        assert cluster["tags"] == [{"name": tag_name, "size": 1}]
    finally:
        with app.app_context():
            from core.managers.db_manager import db

            if story_id and (story := Story.get(story_id)):
                for news_item in list(story.news_items):
                    news_item.set_tags([], replace=True, update_story=False)
                    db.session.delete(news_item)
                db.session.delete(story)
            db.session.commit()


def test_trending_clusters_uses_recent_summary_activity_with_global_counts(app, client, auth_header):
    tag_type = _unique_value("trend-type")
    recent_tag = _unique_value("trend-recent")
    second_recent_tag = _unique_value("trend-second")
    old_tag = _unique_value("trend-old")
    other_tag_type = _unique_value("trend-other-type")
    other_tag = _unique_value("trend-other")
    now = BaseModel.utcnow().replace(microsecond=0)
    story_ids = []

    with app.app_context():
        from core.managers.db_manager import db

        first_story = create_story(
            created=(now - timedelta(days=1)).isoformat(),
            news_items=[build_news_item_payload(title_prefix="Trending One")],
        )
        second_story = create_story(
            created=(now - timedelta(days=2)).isoformat(),
            news_items=[build_news_item_payload(title_prefix="Trending Two")],
        )
        old_story = create_story(
            created=(now - timedelta(days=20)).isoformat(),
            news_items=[build_news_item_payload(title_prefix="Trending Old")],
        )
        other_story = create_story(
            created=(now - timedelta(days=1)).isoformat(),
            news_items=[build_news_item_payload(title_prefix="Trending Other")],
        )

        first_story.created = now - timedelta(days=1)
        second_story.created = now - timedelta(days=2)
        old_story.created = now - timedelta(days=20)
        other_story.created = now - timedelta(days=1)
        first_story.news_items[0].published = first_story.created
        second_story.news_items[0].published = second_story.created
        old_story.news_items[0].published = old_story.created
        other_story.news_items[0].published = other_story.created
        db.session.commit()

        first_story.news_items[0].set_tags(
            [
                {"name": recent_tag, "tag_type": tag_type},
                {"name": second_recent_tag, "tag_type": tag_type},
            ]
        )
        second_story.news_items[0].set_tags([{"name": recent_tag, "tag_type": tag_type}])
        old_story.news_items[0].set_tags(
            [
                {"name": recent_tag, "tag_type": tag_type},
                {"name": old_tag, "tag_type": tag_type},
            ]
        )
        other_story.news_items[0].set_tags([{"name": other_tag, "tag_type": other_tag_type}])
        story_ids = [first_story.id, second_story.id, old_story.id, other_story.id]

    try:
        response = client.get("/api/dashboard/trending-clusters", headers=auth_header, query_string={"days": 7})
        payload = response.get_json()
        assert response.status_code == 200

        cluster = next(item for item in payload["items"] if item["name"] == tag_type)
        assert cluster["size"] == 4
        assert {tag["name"]: tag["size"] for tag in cluster["tags"]} == {
            recent_tag: 3,
            second_recent_tag: 1,
        }

        response = client.get("/api/dashboard/trending-clusters", headers=auth_header, query_string={"days": 30})
        payload = response.get_json()

        cluster = next(item for item in payload["items"] if item["name"] == tag_type)
        assert cluster["size"] == 5
        assert {tag["name"]: tag["size"] for tag in cluster["tags"]} == {
            recent_tag: 3,
            second_recent_tag: 1,
            old_tag: 1,
        }

        assert any(item["name"] == other_tag_type for item in payload["items"])
    finally:
        with app.app_context():
            from core.managers.db_manager import db

            for story_id in story_ids:
                story = Story.get(story_id)
                if story is None:
                    continue
                for news_item in list(story.news_items):
                    news_item.set_tags([], replace=True, update_story=False)
                    db.session.delete(news_item)
                db.session.delete(story)
            db.session.commit()
