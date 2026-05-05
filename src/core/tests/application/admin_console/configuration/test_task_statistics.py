from datetime import datetime, timezone

import pytest

from core.model.task import Task


@pytest.mark.parametrize(
    ("stats", "expected_label", "expected_variant"),
    [
        ({"successes": 0, "failures": 0, "total": 0}, "No Runs", "ghost"),
        ({"successes": 3, "failures": 0, "total": 3}, "All Success", "success"),
        ({"successes": 0, "failures": 1, "total": 1}, "First Failure", "warning"),
        ({"successes": 8, "failures": 2, "total": 10, "success_pct": 80}, "Mostly Success", "warning"),
        ({"successes": 0, "failures": 2, "total": 2, "success_pct": 0}, "Some Failures", "warning"),
        ({"successes": 1, "failures": 5, "total": 6, "success_pct": 16}, "Many Failures", "error"),
    ],
)
def test_build_task_status_badge(stats, expected_label, expected_variant):
    badge = Task._build_task_status_badge(stats)

    assert badge["label"] == expected_label
    assert badge["variant"] == expected_variant


def test_get_task_statistics_serializes_timestamps(monkeypatch):
    last_run = datetime(2026, 4, 13, 12, 30, tzinfo=timezone.utc)
    last_success = datetime(2026, 4, 13, 11, 45, tzinfo=timezone.utc)

    monkeypatch.setattr(
        Task,
        "get_status_counts_by_task",
        classmethod(
            lambda cls, include_timestamps=False: {
                "presenter_task": {
                    "failures": 1,
                    "successes": 2,
                    "success_pct": 66,
                    "total": 3,
                    "last_run": last_run,
                    "last_success": last_success,
                }
            }
        ),
    )

    statistics = Task.get_task_statistics()
    task_stats = statistics["task_stats"]["presenter_task"]

    assert task_stats["last_run"] == last_run.isoformat()
    assert task_stats["last_success"] == last_success.isoformat()
    assert task_stats["last_run_display"] == last_run.isoformat()
    assert task_stats["last_success_display"] == last_success.isoformat()


def test_get_task_statistics_includes_worker_metadata(monkeypatch):
    last_run = datetime(2026, 4, 13, 12, 30, tzinfo=timezone.utc)
    last_success = datetime(2026, 4, 13, 11, 45, tzinfo=timezone.utc)

    monkeypatch.setattr(
        Task,
        "get_status_counts_by_task",
        classmethod(
            lambda cls, include_timestamps=False: {
                "WORDLIST_BOT": {
                    "failures": 1,
                    "successes": 2,
                    "success_pct": 66,
                    "total": 3,
                    "last_run": last_run,
                    "last_success": last_success,
                    "worker_type": "WORDLIST_BOT",
                    "worker_id": "bot-123",
                }
            }
        ),
    )

    statistics = Task.get_task_statistics()
    task_stats = statistics["task_stats"]["WORDLIST_BOT"]

    assert task_stats["worker_type"] == "WORDLIST_BOT"
    assert task_stats["worker_id"] == "bot-123"
    assert task_stats["last_run"] == last_run.isoformat()
    assert task_stats["last_success"] == last_success.isoformat()


def test_get_status_counts_by_task_counts_latest_worker_outcomes_once(app):
    from core.model.task import Task

    task_ids = [
        "collect_rss_collector_source-1-run-1",
        "collect_rss_collector_source-2-run-1",
        "collect_rss_collector_source-1-run-2",
    ]

    with app.app_context():
        try:
            Task.add(
                {
                    "id": task_ids[0],
                    "task": "collector_task",
                    "worker_id": "source-1",
                    "worker_type": "rss_collector",
                    "status": "SUCCESS",
                    "result": {"message": "ok"},
                }
            )
            Task.add(
                {
                    "id": task_ids[1],
                    "task": "collector_task",
                    "worker_id": "source-2",
                    "worker_type": "rss_collector",
                    "status": "SUCCESS",
                    "result": {"message": "ok"},
                }
            )
            Task.add(
                {
                    "id": task_ids[2],
                    "task": "collector_task",
                    "worker_id": "source-1",
                    "worker_type": "rss_collector",
                    "status": "FAILURE",
                    "result": {"error": "boom"},
                }
            )

            stats = Task.get_status_counts_by_task()
            rss_stats = stats["rss_collector"]

            assert rss_stats["successes"] == 1
            assert rss_stats["failures"] == 1
            assert rss_stats["total"] == 2
            assert rss_stats["success_pct"] == 50
        finally:
            for task_id in task_ids:
                if Task.get(task_id):
                    Task.delete(task_id)
