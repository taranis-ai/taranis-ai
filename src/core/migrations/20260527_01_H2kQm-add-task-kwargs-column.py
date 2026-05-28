"""
add kwargs column for persisted task results
"""

from yoyo import step


__depends__ = {"20260423_01_Va9mQ-move-news-item-tags-to-news-items"}


steps = [
    step(
        """
        ALTER TABLE task
        ADD COLUMN IF NOT EXISTS kwargs character varying;
        """,
        """
        ALTER TABLE task
        DROP COLUMN IF EXISTS kwargs;
        """,
    )
]
