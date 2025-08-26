"""
worker status
"""

from yoyo import step

__depends__ = {"20250530_01_bgjgJ-add-ppn-collector"}

steps = [
    step(
        """
    ALTER TABLE task
    ADD COLUMN IF NOT EXISTS last_run timestamp without time zone;
    ALTER TABLE task
    ADD COLUMN IF NOT EXISTS last_success timestamp without time zone;
    ALTER TABLE task
    ADD COLUMN IF NOT EXISTS task character varying;
    ALTER TABLE bot
    ADD COLUMN IF NOT EXISTS enabled boolean DEFAULT true;
    ALTER TABLE osint_source
    ADD COLUMN IF NOT EXISTS enabled boolean DEFAULT true;
    ALTER TABLE osint_source
    DROP COLUMN IF EXISTS last_collected;
    ALTER TABLE osint_source
    DROP COLUMN IF EXISTS last_attempted;
    ALTER TABLE osint_source
    DROP COLUMN IF EXISTS last_error_message;
    ALTER TABLE osint_source
    DROP COLUMN IF EXISTS state;
    """,
        """
    ALTER TABLE task
    DROP COLUMN IF EXISTS last_run;
    ALTER TABLE task
    DROP COLUMN IF EXISTS last_success;
    ALTER TABLE task
    DROP COLUMN IF EXISTS task;
    ALTER TABLE bot
    DROP COLUMN IF EXISTS enabled;
    ALTER TABLE osint_source
    DROP COLUMN IF EXISTS enabled;
    ALTER TABLE osint_source
    ADD COLUMN IF NOT EXISTS last_collected timestamp without time zone;
    ALTER TABLE osint_source
    ADD COLUMN IF NOT EXISTS last_attempted timestamp without time zone;
    ALTER TABLE osint_source
    ADD COLUMN IF NOT EXISTS last_error_message character varying;
    """,
    )
]
