"""Index story publication and update dates for Assess paging and range filters."""

from yoyo import step


__depends__ = {"20261023_01_c4N8p-rename-default-topic-classifier"}

steps = [
    step(
        "CREATE INDEX IF NOT EXISTS ix_story_created ON story (created)",
        "DROP INDEX IF EXISTS ix_story_created",
    ),
    step(
        "CREATE INDEX IF NOT EXISTS ix_story_updated ON story (updated)",
        "DROP INDEX IF EXISTS ix_story_updated",
    ),
]
