"""
Add transaction table and story_version table for sqlalchemy-continuum
"""

from yoyo import step

__depends__ = {"20250530_01_bgjgJ-add-ppn-collector"}

steps = [
    step(
        """
        CREATE SEQUENCE IF NOT EXISTS transaction_id_seq START 1;

        CREATE TABLE IF NOT EXISTS transaction (
            id integer PRIMARY KEY DEFAULT nextval('transaction_id_seq'),
            remote_addr VARCHAR(255),
            issued_at TIMESTAMP WITHOUT TIME ZONE
        );

        CREATE TABLE IF NOT EXISTS story_version (
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
            transaction_id INTEGER NOT NULL REFERENCES transaction(id),
            end_transaction_id INTEGER REFERENCES transaction(id),
            operation_type SMALLINT NOT NULL,
            PRIMARY KEY (id, transaction_id)
        );

        CREATE INDEX IF NOT EXISTS ix_story_version_end_transaction_id ON story_version (end_transaction_id);
        CREATE INDEX IF NOT EXISTS ix_story_version_operation_type ON story_version (operation_type);
        CREATE INDEX IF NOT EXISTS ix_story_version_transaction_id ON story_version (transaction_id);
        """,
        """
        DROP TABLE IF EXISTS story_version;
        DROP TABLE IF EXISTS transaction;
        DROP SEQUENCE IF EXISTS transaction_id_seq;
        """,
    )
]
