"""
task worker metadata
"""

from yoyo import step

__depends__ = {"20260327_01_g4M1a-rebuild-story-search-vectors"}

steps = [
    step(
        """
        ALTER TABLE task
        ADD COLUMN IF NOT EXISTS worker_id character varying;
        ALTER TABLE task
        ADD COLUMN IF NOT EXISTS worker_type character varying;
        """,
        """
        ALTER TABLE task
        DROP COLUMN IF EXISTS worker_id;
        ALTER TABLE task
        DROP COLUMN IF EXISTS worker_type;
        """,
    )
]
