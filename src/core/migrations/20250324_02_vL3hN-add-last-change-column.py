"""
Add last_change column to story and news_item tables
"""

from yoyo import step

__depends__ = {"20250228_01_Pnb5c-refactor-organization"}

steps = [
    step(
        """
        ALTER TABLE story ADD COLUMN last_change VARCHAR;
        ALTER TABLE news_item ADD COLUMN last_change VARCHAR;
        """,
        """
        ALTER TABLE news_item DROP COLUMN last_change;
        ALTER TABLE story DROP COLUMN last_change;
        """,
    )
]
