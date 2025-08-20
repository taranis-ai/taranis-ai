"""
worker status
"""

from yoyo import step

__depends__ = {"20250530_01_bgjgJ-add-ppn-collector"}

steps = [
    step(
        """
    ALTER TABLE task
    ADD COLUMN last_change timestamp without time zone;
    ALTER TABLE task
    ADD COLUMN last_success timestamp without time zone;
    """,
        """
    ALTER TABLE task
    DROP COLUMN IF EXISTS last_change;
    ALTER TABLE task
    DROP COLUMN IF EXISTS last_success;
    """,
    )
]
