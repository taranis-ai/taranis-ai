# pyright: reportMissingTypeStubs=false
"""
add triggering user to task records
"""

from yoyo import step

__depends__ = {"20260611_01_w4R9m-purge-task-history"}

steps = [
    step(
        """
        ALTER TABLE task
        ADD COLUMN IF NOT EXISTS user_id character varying(36);
        CREATE INDEX IF NOT EXISTS ix_task_user_id ON task (user_id);
        """,
        """
        DROP INDEX IF EXISTS ix_task_user_id;
        ALTER TABLE task
        DROP COLUMN IF EXISTS user_id;
        """,
    )
]
