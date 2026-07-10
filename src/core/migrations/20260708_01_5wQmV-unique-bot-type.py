"""
unique bot type
"""

from yoyo import step


__depends__ = {"20260611_01_w4R9m-purge-task-history"}

steps = [
    step(
        """
        DO $$
        DECLARE
            duplicate_bot_types text;
        BEGIN
            SELECT string_agg(type::text, ', ' ORDER BY type::text)
            INTO duplicate_bot_types
            FROM (
                SELECT type
                FROM bot
                GROUP BY type
                HAVING count(*) > 1
            ) duplicates;

            IF duplicate_bot_types IS NOT NULL THEN
                RAISE EXCEPTION
                    'Cannot enforce unique bot types; duplicate types exist: %. Remove duplicate bot configurations and retry.',
                    duplicate_bot_types;
            END IF;
        END;
        $$;

        ALTER TABLE bot
            ADD CONSTRAINT bot_type_key UNIQUE (type);
        """,
        """
        ALTER TABLE bot
            DROP CONSTRAINT IF EXISTS bot_type_key;
        """,
    )
]
