"""Add internal CTPH fingerprints and a scoped collection lookup index."""

from yoyo import step


__depends__ = {"20260908_01_n8O2r-add-story-news-item-order"}

steps = [
    step(
        "ALTER TABLE news_item ADD COLUMN IF NOT EXISTS fuzzy_hash TEXT",
        "ALTER TABLE news_item DROP COLUMN IF EXISTS fuzzy_hash",
    ),
    step(
        "CREATE INDEX IF NOT EXISTS ix_news_item_source_collected ON news_item (osint_source_id, collected)",
        "DROP INDEX IF EXISTS ix_news_item_source_collected",
    ),
]
