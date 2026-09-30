from datetime import UTC, datetime, timedelta
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


def test_get_dashboard_data_includes_weekly_activity_and_task_totals(session, monkeypatch):
    latest_collected = datetime(2026, 4, 13, 12, 30, tzinfo=UTC)
    schedule_count_calls = []

    monkeypatch.setattr(NewsItem, "get_count", classmethod(lambda cls: 11))
    monkeypatch.setattr(Story, "get_count", classmethod(lambda cls: 7))
    monkeypatch.setattr(Product, "get_count", classmethod(lambda cls: 3))
    monkeypatch.setattr(ReportItem, "count_all", classmethod(lambda cls, completed: 5 if completed else 2))
    monkeypatch.setattr(NewsItem, "latest_collected", classmethod(lambda cls: latest_collected))
    monkeypatch.setattr(
        dashboard_module.queue_manager,
        "queue_manager",
        SimpleNamespace(get_scheduled_job_count=lambda: schedule_count_calls.append(True) or 4),
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

    now = datetime(2001, 1, 3, 12)
    week_start = datetime(2001, 1, 1)
    monkeypatch.setattr(BaseModel, "utcnow", staticmethod(lambda: now))
    for timestamp in [week_start - timedelta(microseconds=1), week_start, now, now + timedelta(microseconds=1)]:
        story = create_story(news_items=[build_news_item_payload()])
        story.created = timestamp
        story.news_items[0].published = timestamp
        report = ReportItem(title="Weekly report", report_item_type_id=None)
        product = Product(title="Weekly product", product_type_id=None)
        report.created = product.created = timestamp
        session.add_all([report, product])
    session.flush()

    dashboard = DashboardService.get_dashboard_data()["items"][0]

    for field in ["news_items_this_week", "stories_this_week", "reports_this_week", "products_this_week"]:
        assert dashboard[field] == 2
    assert dashboard["story_conflict_count"] == 2
    assert dashboard["news_item_conflict_count"] == 1
    assert dashboard["conflict_count"] == 3

    assert dashboard["task_status_totals"] == {
        "failures": 1,
        "successes": 2,
        "success_pct": 66,
        "total": 3,
    }
    assert schedule_count_calls == [True]


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


def test_summarize_source_counts_sorts_largest_first_with_percentages():
    result = NewsItem.summarize_source_counts([("Blog", 1), ("CERT", 3)])

    assert result == [
        {"name": "CERT", "count": 3, "percentage": 75.0},
        {"name": "Blog", "count": 1, "percentage": 25.0},
    ]


def test_summarize_source_counts_groups_sources_beyond_limit_into_other():
    counts = [("A", 50), ("B", 20), ("C", 10), ("D", 10), ("E", 5), ("F", 3), ("G", 2)]

    result = NewsItem.summarize_source_counts(counts, limit=5)

    assert [entry["name"] for entry in result] == ["A", "B", "C", "D", "E", "Other"]
    assert result[-1] == {"name": "Other", "count": 5, "percentage": 5.0}
    assert sum(entry["count"] for entry in result) == 100


def test_summarize_source_counts_has_no_other_entry_when_within_limit():
    result = NewsItem.summarize_source_counts([("A", 2), ("B", 1)], limit=5)

    assert [entry["name"] for entry in result] == ["A", "B"]


def test_summarize_source_counts_breaks_ties_alphabetically():
    result = NewsItem.summarize_source_counts([("Zeta", 2), ("Alpha", 2)])

    assert [entry["name"] for entry in result] == ["Alpha", "Zeta"]


def test_summarize_source_counts_rounds_percentages_to_one_decimal():
    result = NewsItem.summarize_source_counts([("A", 1), ("B", 1), ("C", 1)])

    assert [entry["percentage"] for entry in result] == [33.3, 33.3, 33.3]


def test_summarize_source_counts_returns_empty_list_without_news_items():
    assert NewsItem.summarize_source_counts([]) == []
    assert NewsItem.summarize_source_counts([("A", 0)]) == []


def test_get_source_distribution_counts_news_items_per_source(session):
    from models.types import COLLECTOR_TYPES

    from core.model.osint_source import OSINTSource

    busy_source = OSINTSource(name=_unique_value("busy-source"), description="test", type=COLLECTOR_TYPES.MANUAL_COLLECTOR)
    quiet_source = OSINTSource(name=_unique_value("quiet-source"), description="test", type=COLLECTOR_TYPES.MANUAL_COLLECTOR)
    session.add_all([busy_source, quiet_source])
    session.flush()

    for source, amount in [(busy_source, 3), (quiet_source, 1)]:
        create_story(news_items=[build_news_item_payload(source_id=source.id) for _ in range(amount)])
    session.flush()

    counts = {entry["name"]: entry["count"] for entry in NewsItem.get_source_distribution(limit=1000)}

    assert counts[busy_source.name] == 3
    assert counts[quiet_source.name] == 1


def test_get_dashboard_data_includes_top_sources(session, monkeypatch):
    top_sources = [{"name": "CERT", "count": 3, "percentage": 75.0}, {"name": "Blog", "count": 1, "percentage": 25.0}]
    requested_limits = []

    def fake_distribution(cls, limit=5):
        requested_limits.append(limit)
        return top_sources

    monkeypatch.setattr(NewsItem, "get_source_distribution", classmethod(fake_distribution))
    monkeypatch.setattr(
        dashboard_module.queue_manager,
        "queue_manager",
        SimpleNamespace(get_scheduled_job_count=lambda: 0),
        raising=False,
    )
    monkeypatch.setattr("core.service.dashboard.get_health_response", lambda: ({"healthy": True}, 200))

    dashboard = DashboardService.get_dashboard_data()["items"][0]

    assert dashboard["top_sources"] == top_sources
    assert requested_limits == [5]
