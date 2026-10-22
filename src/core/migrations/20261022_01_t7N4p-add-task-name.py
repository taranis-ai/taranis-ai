"""Preserve the public action/story label in completed task history."""

from yoyo import step


__depends__ = {"20260911_01_f8H2q-add-news-item-fuzzy-hash"}

steps = [
    step(
        "ALTER TABLE task ADD COLUMN IF NOT EXISTS name TEXT",
        "ALTER TABLE task DROP COLUMN IF EXISTS name",
    ),
]
