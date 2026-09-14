"""Add local news-item display order to stories."""

from yoyo import step


__depends__ = {"20260903_01_a7K2p-osint-source-names-unique"}

steps = [
    step(
        "ALTER TABLE story ADD COLUMN IF NOT EXISTS news_item_order JSON NOT NULL DEFAULT '[]'",
        "ALTER TABLE story DROP COLUMN IF EXISTS news_item_order",
    )
]
