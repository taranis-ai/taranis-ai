"""
Remove last_change in Story and NewsItem table
"""

from yoyo import step

__depends__ = {"20250424_01_cLXiI-story-news-item-fk"}


steps = [
    step(
        "ALTER TABLE story DROP COLUMN IF EXISTS last_change;",
    ),
    step(
        "ALTER TABLE news_item DROP COLUMN IF EXISTS last_change;",
    ),
]
