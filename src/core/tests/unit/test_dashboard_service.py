from core.managers import schedule_manager
from core.service.dashboard import DashboardService


def test_get_dashboard_data_includes_health_status(monkeypatch):
    monkeypatch.setattr("core.service.dashboard.NewsItem.get_count", lambda: 12)
    monkeypatch.setattr("core.service.dashboard.Story.get_count", lambda: 3)
    monkeypatch.setattr("core.service.dashboard.Product.get_count", lambda: 2)
    monkeypatch.setattr("core.service.dashboard.ReportItem.count_all", lambda completed: 7 if completed else 1)
    monkeypatch.setattr("core.service.dashboard.NewsItem.latest_collected", lambda: None)
    monkeypatch.setattr(
        schedule_manager,
        "schedule",
        type("ScheduleStub", (), {"get_periodic_tasks": lambda self: {"total_count": 4}})(),
        raising=False,
    )
    monkeypatch.setattr("core.service.dashboard.StoryConflict.conflict_store", ["story-conflict"])
    monkeypatch.setattr("core.service.dashboard.NewsItemConflict.conflict_store", ["news-conflict"])
    monkeypatch.setattr("core.service.dashboard.Task.get_status_counts_by_task", lambda: {"collector_task": {"total": 8}})
    monkeypatch.setattr(
        "core.service.dashboard.get_health_response",
        lambda: ({"healthy": False, "services": {"database": "up", "broker": "down", "workers": "down"}}, 503),
    )

    response = DashboardService.get_dashboard_data()

    assert response == {
        "items": [
            {
                "total_news_items": 12,
                "total_story_items": 3,
                "total_products": 2,
                "report_items_completed": 7,
                "report_items_in_progress": 1,
                "latest_collected": None,
                "schedule_length": 4,
                "conflict_count": 2,
                "health_status": {
                    "healthy": False,
                    "services": {"database": "up", "broker": "down", "workers": "down"},
                },
                "worker_status": {"collector_task": {"total": 8}},
            }
        ]
    }
