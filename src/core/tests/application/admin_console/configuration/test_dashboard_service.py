from datetime import datetime, timezone
from types import SimpleNamespace

import core.service.dashboard as dashboard_module
from core.model.news_item import NewsItem
from core.model.news_item_conflict import NewsItemConflict
from core.model.product import Product
from core.model.report_item import ReportItem
from core.model.story import Story
from core.model.story_conflict import StoryConflict
from core.model.task import Task
from core.service.dashboard import DashboardService


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
