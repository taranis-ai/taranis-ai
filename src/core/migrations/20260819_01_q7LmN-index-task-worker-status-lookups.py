# pyright: reportMissingTypeStubs=false
"""
index task worker status lookups
"""

from yoyo import step


__depends__ = {"20260710_01_m3P7q-add-product-last-published-url"}

steps = [
    step(
        """
        CREATE INDEX IF NOT EXISTS ix_task_worker_task_last_run
        ON task (worker_id, task, last_run DESC);
        """,
        """
        DROP INDEX IF EXISTS ix_task_worker_task_last_run;
        """,
    )
]
