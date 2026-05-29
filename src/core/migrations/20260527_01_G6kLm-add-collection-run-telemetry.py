"""
add collection run telemetry
"""

from yoyo import step

__depends__ = {"20260423_01_Va9mQ-move-news-item-tags-to-news-items"}

steps = [
    step(
        """
        CREATE TABLE IF NOT EXISTS collection_run (
            id character varying(36) PRIMARY KEY,
            osint_source_id character varying(36) NOT NULL REFERENCES osint_source(id) ON DELETE CASCADE,
            collector_job_id character varying NOT NULL,
            collector_type character varying NOT NULL,
            manual boolean NOT NULL DEFAULT false,
            collector_started_at timestamp without time zone NOT NULL,
            collector_finished_at timestamp without time zone,
            collector_status character varying,
            news_items_count integer NOT NULL DEFAULT 0,
            stored_bytes integer NOT NULL DEFAULT 0,
            expected_post_collection_bots integer NOT NULL DEFAULT 0,
            pipeline_finished_at timestamp without time zone
        );

        CREATE INDEX IF NOT EXISTS ix_collection_run_osint_source_id ON collection_run (osint_source_id);
        CREATE INDEX IF NOT EXISTS ix_collection_run_collector_job_id ON collection_run (collector_job_id);
        CREATE INDEX IF NOT EXISTS ix_collection_run_collector_finished_at ON collection_run (collector_finished_at);

        CREATE TABLE IF NOT EXISTS collection_run_bot_completion (
            id character varying(36) PRIMARY KEY,
            collection_run_id character varying(36) NOT NULL REFERENCES collection_run(id) ON DELETE CASCADE,
            bot_id character varying(36) NOT NULL,
            bot_type character varying NOT NULL,
            status character varying NOT NULL,
            finished_at timestamp without time zone NOT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_collection_run_bot_completion_run_bot
            ON collection_run_bot_completion (collection_run_id, bot_id);
        CREATE INDEX IF NOT EXISTS ix_collection_run_bot_completion_collection_run_id
            ON collection_run_bot_completion (collection_run_id);
        """,
        """
        DROP TABLE IF EXISTS collection_run_bot_completion;
        DROP TABLE IF EXISTS collection_run;
        """,
    )
]
