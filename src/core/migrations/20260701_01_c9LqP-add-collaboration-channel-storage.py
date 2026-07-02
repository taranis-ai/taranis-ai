"""
persist collaboration channels
"""

from yoyo import step

__depends__ = {"20260416_01_Q7vKp-add-task-worker-metadata"}

steps = [
    step(
        """
        CREATE TABLE IF NOT EXISTS collaboration_channel (
            channel_id character varying(64) PRIMARY KEY,
            topic character varying NOT NULL,
            status character varying(16) NOT NULL,
            owner_base_url character varying NOT NULL,
            created_at timestamp without time zone NULL,
            updated_at timestamp without time zone NULL,
            state json NOT NULL
        );
        """,
        """
        DROP TABLE IF EXISTS collaboration_channel;
        """,
    )
]
