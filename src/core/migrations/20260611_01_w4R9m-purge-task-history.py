"""
purge task history before strict task envelope rollout
"""

from yoyo import step

__depends__ = {"20260423_01_Va9mQ-move-news-item-tags-to-news-items"}

steps = [
    step(
        "DELETE FROM task;",
        "SELECT 1;",
    )
]
