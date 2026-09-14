"""Add internal CTPH fingerprints and a scoped collection lookup index."""

from datetime import timedelta

from yoyo import step

from core.model.news_item import NewsItem
from core.model.settings import Settings


__depends__ = {"20260908_01_n8O2r-add-story-news-item-order"}


def backfill(connection):
    now = NewsItem.utcnow()
    with connection.cursor() as settings_cursor:
        settings_cursor.execute("SELECT settings FROM settings WHERE singleton_key = %s", (Settings.SINGLETON_KEY,))
        row = settings_cursor.fetchone()
        settings = Settings.with_defaults(row[0] if row else None)
        Settings._normalize_collection_settings(settings)
    with connection.cursor(name="fuzzy_hash_backfill") as rows, connection.cursor() as updates:
        rows.execute(
            "SELECT id, content FROM news_item WHERE fuzzy_hash IS NULL AND collected BETWEEN %s AND %s",
            (now - timedelta(days=settings["collection_lookback_days"]), now),
        )
        while batch := rows.fetchmany(500):
            updates.executemany(
                "UPDATE news_item SET fuzzy_hash = %s WHERE id = %s",
                [(NewsItem.get_fuzzy_hash(content), item_id) for item_id, content in batch],
            )


steps = [
    step(
        "ALTER TABLE news_item ADD COLUMN IF NOT EXISTS fuzzy_hash TEXT",
        "ALTER TABLE news_item DROP COLUMN IF EXISTS fuzzy_hash",
    ),
    step(
        "CREATE INDEX IF NOT EXISTS ix_news_item_source_collected ON news_item (osint_source_id, collected)",
        "DROP INDEX IF EXISTS ix_news_item_source_collected",
    ),
    step(backfill),
]
