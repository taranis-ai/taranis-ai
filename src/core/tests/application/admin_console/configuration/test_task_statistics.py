from datetime import UTC, datetime

import pytest

from core.model.bot import Bot
from core.model.osint_source import OSINTSource
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


def test_get_task_statistics_includes_worker_metadata(monkeypatch):
    last_run = datetime(2026, 4, 13, 12, 30, tzinfo=UTC)
    last_success = datetime(2026, 4, 13, 11, 45, tzinfo=UTC)

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
                    "result": {"message": "ok", "retryable": False, "data": {"source_id": "source-1"}},
                }
            )
            Task.add(
                {
                    "id": task_ids[1],
                    "task": "collector_task",
                    "worker_id": "source-2",
                    "worker_type": "rss_collector",
                    "status": "SUCCESS",
                    "result": {"message": "ok", "retryable": False, "data": {"source_id": "source-2"}},
                }
            )
            Task.add(
                {
                    "id": task_ids[2],
                    "task": "collector_task",
                    "worker_id": "source-1",
                    "worker_type": "rss_collector",
                    "status": "FAILURE",
                    "result": {"message": "boom", "reason": "collection_failed", "retryable": False, "data": {"source_id": "source-1"}},
                }
            )

            stats = Task.get_status_counts_by_task()
            rss_stats = stats["rss_collector"]
            stats_with_timestamps = Task.get_status_counts_by_task(include_timestamps=True)
            rss_stats_with_timestamps = stats_with_timestamps["rss_collector"]

            assert rss_stats["successes"] == 1
            assert rss_stats["failures"] == 1
            assert rss_stats["total"] == 2
            assert rss_stats["success_pct"] == 50
            assert "last_run" not in rss_stats
            assert "last_success" not in rss_stats
            assert rss_stats_with_timestamps["successes"] == 1
            assert rss_stats_with_timestamps["failures"] == 1
            assert rss_stats_with_timestamps["total"] == 2
            assert rss_stats_with_timestamps["success_pct"] == 50
            assert rss_stats_with_timestamps["last_run"] is not None
            assert rss_stats_with_timestamps["last_success"] is not None
        finally:
            for task_id in task_ids:
                if Task.get(task_id):
                    Task.delete(task_id)


def test_get_status_totals_counts_latest_worker_statuses(app):
    test_worker_type = "WORDLIST_BOT_STATS_TEST"
    task_ids = [
        "task-status-success-1",
        "task-status-success-2",
        "task-status-failure-1",
        "task-status-ignored-1",
    ]

    with app.app_context():
        try:
            baseline_totals = Task.get_status_totals()
            Task.add(
                {
                    "id": task_ids[0],
                    "task": "collector_task",
                    "worker_id": "source-1",
                    "worker_type": "rss_collector",
                    "status": "SUCCESS",
                    "result": {"message": "ok", "retryable": False, "data": {"source_id": "source-1"}},
                }
            )
            Task.add(
                {
                    "id": task_ids[1],
                    "task": "bot_task",
                    "worker_id": "bot-1",
                    "worker_type": test_worker_type,
                    "status": "SUCCESS",
                    "result": {"message": "ok", "retryable": False, "data": {"bot_id": "bot-1", "result": {}}},
                }
            )
            Task.add(
                {
                    "id": task_ids[2],
                    "task": "bot_task",
                    "worker_id": "bot-1",
                    "worker_type": test_worker_type,
                    "status": "FAILURE",
                    "result": {"message": "boom", "reason": "bot_execution_failed", "retryable": False, "data": {"bot_id": "bot-1"}},
                }
            )
            Task.add(
                {
                    "id": task_ids[3],
                    "task": "bot_task",
                    "worker_id": "bot-2",
                    "worker_type": test_worker_type,
                    "status": "STARTED",
                    "result": {"message": "running", "retryable": False, "data": {"bot_id": "bot-2"}},
                }
            )

            totals = Task.get_status_totals()
            stats = Task.get_status_counts_by_task()

            assert totals["successes"] == baseline_totals["successes"] + 1
            assert totals["failures"] == baseline_totals["failures"] + 1
            assert totals["total"] == baseline_totals["total"] + 2
            assert totals["success_pct"] == int((totals["successes"] * 100) / totals["total"])
            assert stats["rss_collector"]["successes"] == 1
            assert stats["rss_collector"]["failures"] == 0
            assert stats[test_worker_type]["successes"] == 0
            assert stats[test_worker_type]["failures"] == 1
            assert totals == {
                "successes": sum(task_stats["successes"] for task_stats in stats.values()),
                "failures": sum(task_stats["failures"] for task_stats in stats.values()),
                "total": sum(task_stats["total"] for task_stats in stats.values()),
                "success_pct": int((totals["successes"] * 100) / totals["total"]),
            }
        finally:
            for task_id in task_ids:
                if Task.get(task_id):
                    Task.delete(task_id)


def test_get_admin_menu_badges_uses_model_failure_counts(monkeypatch):
    monkeypatch.setattr(OSINTSource, "get_current_failure_count", classmethod(lambda cls: 6))
    monkeypatch.setattr(Bot, "get_current_failure_count", classmethod(lambda cls: 7))

    assert Task.get_admin_menu_badges() == {
        "osint_source": 6,
        "bot": 7,
    }


def test_task_errors_current_and_history_follow_latest_worker_outcome(app):
    marker = Task.uuid7_str()
    url_worker = f"https://example.invalid/{marker}"
    source_worker = f"source-{marker}"
    task_ids = [f"{marker}-url-failure", f"{marker}-source-failure", f"{marker}-source-success"]

    with app.app_context():
        try:
            for task_id, worker_id, status, message in [
                (task_ids[0], url_worker, "FAILURE", "404"),
                (task_ids[1], source_worker, "FAILURE", "timeout"),
                (task_ids[2], source_worker, "NOT_MODIFIED", "unchanged"),
            ]:
                Task.add(
                    {
                        "id": task_id,
                        "task": "collector_task",
                        "worker_id": worker_id,
                        "worker_type": "simple_web_collector" if worker_id == url_worker else "rss_collector",
                        "status": status,
                        "result": {"message": message, "retryable": False},
                    }
                )

            current, current_count = Task.get_errors({"scope": "current", "category": "collector", "search": marker})
            history, history_count = Task.get_errors({"scope": "history", "category": "collector", "search": marker})

            assert current_count == 1
            assert [task.worker_id for task in current] == [url_worker]
            assert history_count == 2
            assert {task.worker_id for task in history} == {url_worker, source_worker}
        finally:
            for task_id in task_ids:
                if Task.get(task_id):
                    Task.delete(task_id)


def test_current_error_count_matches_filtered_error_total(app):
    marker = Task.uuid7_str()
    task_ids = [f"{marker}-collector", f"{marker}-bot"]

    with app.app_context():
        baseline = Task.get_current_error_counts()
        try:
            for task_id, task_name, worker_id, worker_type in [
                (task_ids[0], "collector_task", f"source-{marker}", "rss_collector"),
                (task_ids[1], f"bot_{marker}", f"bot-{marker}", "WORDLIST_BOT"),
            ]:
                Task.add(
                    {
                        "id": task_id,
                        "task": task_name,
                        "worker_id": worker_id,
                        "worker_type": worker_type,
                        "status": "FAILURE",
                        "result": {"message": marker, "retryable": False},
                    }
                )

            counts = Task.get_current_error_counts()
            _, collector_total = Task.get_errors({"scope": "current", "category": "collector"})
            _, bot_total = Task.get_errors({"scope": "current", "category": "bot"})

            assert counts == {"collector": baseline["collector"] + 1, "bot": baseline["bot"] + 1}
            assert collector_total == counts["collector"]
            assert bot_total == counts["bot"]
        finally:
            for task_id in task_ids:
                if Task.get(task_id):
                    Task.delete(task_id)
