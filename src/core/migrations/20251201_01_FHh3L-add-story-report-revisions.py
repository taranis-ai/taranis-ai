"""
add story/report revisions
"""

from yoyo import step

__depends__ = {"20251106_01_U7YeD-migrate-search-vector"}

steps = [
    step(
        """
        CREATE TABLE IF NOT EXISTS story_revision (
            id SERIAL PRIMARY KEY,
            story_id VARCHAR(64) NOT NULL REFERENCES story(id) ON DELETE CASCADE,
            revision INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
            note TEXT,
            data JSON NOT NULL,
            CONSTRAINT uq_story_revision_story_rev UNIQUE (story_id, revision)
        );
        CREATE INDEX IF NOT EXISTS ix_story_revision_story_id ON story_revision (story_id);
        """,
        "DROP TABLE IF EXISTS story_revision;",
    ),
    step(
        """
        CREATE TABLE IF NOT EXISTS report_revision (
            id SERIAL PRIMARY KEY,
            report_item_id VARCHAR(64) NOT NULL REFERENCES report_item(id) ON DELETE CASCADE,
            revision INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
            note TEXT,
            data JSON NOT NULL,
            CONSTRAINT uq_report_revision_report_rev UNIQUE (report_item_id, revision)
        );
        CREATE INDEX IF NOT EXISTS ix_report_revision_report_id ON report_revision (report_item_id);
        """,
        "DROP TABLE IF EXISTS report_revision;",
    ),
]
