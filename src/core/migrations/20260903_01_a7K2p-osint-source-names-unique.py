"""Make OSINT source and group names unique."""

from yoyo import step


__depends__ = {"20260818_01_Wp4rM-worker-parameter-registry"}

steps = [
    step(
        """
        DO $$
        DECLARE
            duplicate RECORD;
            new_name TEXT;
        BEGIN
            FOR duplicate IN
                SELECT id, name, ROW_NUMBER() OVER (PARTITION BY name ORDER BY id) AS row_num
                FROM osint_source
                ORDER BY name, id
            LOOP
                IF duplicate.row_num > 1 THEN
                    new_name := duplicate.name || '*';
                    WHILE EXISTS (SELECT 1 FROM osint_source WHERE name = new_name) LOOP
                        new_name := new_name || '*';
                    END LOOP;
                    UPDATE osint_source SET name = new_name WHERE id = duplicate.id;
                END IF;
            END LOOP;
        END $$;

        DO $$
        DECLARE
            duplicate RECORD;
            new_name TEXT;
        BEGIN
            FOR duplicate IN
                SELECT id, name, ROW_NUMBER() OVER (PARTITION BY name ORDER BY id) AS row_num
                FROM osint_source_group
                ORDER BY name, id
            LOOP
                IF duplicate.row_num > 1 THEN
                    new_name := duplicate.name || '*';
                    WHILE EXISTS (SELECT 1 FROM osint_source_group WHERE name = new_name) LOOP
                        new_name := new_name || '*';
                    END LOOP;
                    UPDATE osint_source_group SET name = new_name WHERE id = duplicate.id;
                END IF;
            END LOOP;
        END $$;

        ALTER TABLE osint_source
            ADD CONSTRAINT osint_source_name_key UNIQUE (name);
        ALTER TABLE osint_source_group
            ADD CONSTRAINT osint_source_group_name_key UNIQUE (name);
        """,
        """
        ALTER TABLE osint_source
            DROP CONSTRAINT IF EXISTS osint_source_name_key;
        ALTER TABLE osint_source_group
            DROP CONSTRAINT IF EXISTS osint_source_group_name_key;
        """,
    )
]
