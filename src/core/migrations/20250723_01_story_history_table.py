"""
Add story_history table for custom versioning system
"""

from yoyo import step

__depends__ = {"20250530_01_bgjgJ-add-ppn-collector"}

steps = [
    step(
        """
        CREATE TABLE IF NOT EXISTS story_history (
            id VARCHAR(64) NOT NULL,
            title VARCHAR,
            description VARCHAR,
            created TIMESTAMP WITHOUT TIME ZONE,
            updated TIMESTAMP WITHOUT TIME ZONE,
            read BOOLEAN,
            important BOOLEAN,
            likes INTEGER,
            dislikes INTEGER,
            relevance INTEGER,
            comments VARCHAR,
            summary TEXT,
            links JSON,
            last_change VARCHAR,
            version INTEGER NOT NULL,
            changed TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            PRIMARY KEY (id, version)
        );

        CREATE INDEX IF NOT EXISTS ix_story_history_id ON story_history (id);
        CREATE INDEX IF NOT EXISTS ix_story_history_version ON story_history (version);
        CREATE INDEX IF NOT EXISTS ix_story_history_changed ON story_history (changed);
        """,
        """
        DROP TABLE IF EXISTS story_history;
        """,
    )
]
