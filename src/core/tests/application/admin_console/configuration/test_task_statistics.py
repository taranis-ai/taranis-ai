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
