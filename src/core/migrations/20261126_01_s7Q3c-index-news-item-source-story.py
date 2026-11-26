"""Index linked story IDs per source for Assess paging."""

from yoyo import step


__depends__ = {"20261124_01_p3K8c-index-story-dates"}

steps = [
    step(
        "CREATE INDEX IF NOT EXISTS ix_news_item_source_story ON news_item (osint_source_id, story_id)",
        "DROP INDEX IF EXISTS ix_news_item_source_story",
    ),
]
