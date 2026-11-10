"""Index case-insensitive tag substring searches."""

from yoyo import step


__depends__ = {"20261023_01_c4N8p-rename-default-topic-classifier"}

steps = [
    step(
        "CREATE INDEX IF NOT EXISTS ix_news_item_tag_name_trgm ON news_item_tag USING GIN (name gin_trgm_ops)",
        "DROP INDEX IF EXISTS ix_news_item_tag_name_trgm",
    ),
]
