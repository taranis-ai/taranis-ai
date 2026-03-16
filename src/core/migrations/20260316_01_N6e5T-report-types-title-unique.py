"""
report types title unique
"""

from yoyo import step


__depends__ = {"20260311_01_X8h2K-add-parent-revision-columns"}

steps = [
    step(
        """
        DO $$
        DECLARE
            report_type RECORD;
            new_title TEXT;
            title_suffix INTEGER;
        BEGIN
            FOR report_type IN
                SELECT id, title, ROW_NUMBER() OVER (PARTITION BY title ORDER BY id) AS row_num
                FROM report_item_type
                ORDER BY title, id
            LOOP
                IF report_type.row_num > 1 THEN
                    title_suffix := 2;
                    new_title := report_type.title || ' (' || title_suffix || ')';

                    WHILE EXISTS (
                        SELECT 1
                        FROM report_item_type
                        WHERE title = new_title
                          AND id <> report_type.id
                    ) LOOP
                        title_suffix := title_suffix + 1;
                        new_title := report_type.title || ' (' || title_suffix || ')';
                    END LOOP;

                    UPDATE report_item_type
                    SET title = new_title
                    WHERE id = report_type.id;
                END IF;
            END LOOP;
        END $$;

        ALTER TABLE report_item_type
            ADD CONSTRAINT report_item_type_title_key UNIQUE (title);
        """,
        """
        ALTER TABLE report_item_type
            DROP CONSTRAINT IF EXISTS report_item_type_title_key;
        """,
    )
]
