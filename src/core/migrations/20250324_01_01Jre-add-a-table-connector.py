"""
Add a table Connector
"""

from yoyo import step

__depends__ = {"20250228_01_Pnb5c-refactor-organization"}

steps = [
    step(
        """
        CREATE TABLE IF NOT EXISTS connector (
            id VARCHAR(64) PRIMARY KEY,
            name VARCHAR NOT NULL,
            description VARCHAR,
            type connector_types,
            icon BYTEA,
            state SMALLINT DEFAULT -1,
            last_collected TIMESTAMP,
            last_attempted TIMESTAMP,
            last_error_message VARCHAR
        );
        """,
        """
        DROP TABLE IF EXISTS connector;
        """,
    )
]
