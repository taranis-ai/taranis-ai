"""
migrate model primary-key columns to string IDs

Existing primary-key values are preserved. Legacy integer IDs are converted to
their string representation, while rows created after this migration use UUIDv7
IDs from the application model defaults.
"""

from yoyo import step


__depends__ = {
    "20260408_01_t7KpQ-add-user-last-login",
    "20260416_01_Q7vKp-add-task-worker-metadata",
}


steps = [
    step(
        """
        CREATE TEMP TABLE taranis_legacy_id_columns (
            table_name TEXT NOT NULL,
            column_name TEXT NOT NULL,
            PRIMARY KEY (table_name, column_name)
        );

        INSERT INTO taranis_legacy_id_columns (table_name, column_name)
        VALUES
            ('asset', 'id'),
            ('asset_cpe', 'id'),
            ('asset_cpe', 'asset_id'),
            ('asset_group', 'organization_id'),
            ('asset_vulnerability', 'id'),
            ('asset_vulnerability', 'asset_id'),
            ('attribute', 'id'),
            ('attribute_enum', 'id'),
            ('attribute_enum', 'attribute_id'),
            ('attribute_group', 'id'),
            ('attribute_group', 'report_item_type_id'),
            ('attribute_group_item', 'id'),
            ('attribute_group_item', 'attribute_group_id'),
            ('attribute_group_item', 'attribute_id'),
            ('bot_parameter_value', 'parameter_value_id'),
            ('connector_parameter_value', 'parameter_value_id'),
            ('news_item_tag', 'id'),
            ('news_item_vote', 'id'),
            ('news_item_vote', 'user_id'),
            ('organization', 'id'),
            ('osint_source_group_word_list', 'word_list_id'),
            ('osint_source_parameter_value', 'parameter_value_id'),
            ('parameter_value', 'id'),
            ('product', 'product_type_id'),
            ('product_type', 'id'),
            ('product_type_parameter_value', 'product_type_id'),
            ('product_type_parameter_value', 'parameter_value_id'),
            ('product_type_report_type', 'product_type_id'),
            ('product_type_report_type', 'report_item_type_id'),
            ('publisher_preset_parameter_value', 'parameter_value_id'),
            ('rbac_role', 'acl_id'),
            ('rbac_role', 'role_id'),
            ('report_item', 'user_id'),
            ('report_item', 'report_item_type_id'),
            ('report_item_attribute', 'id'),
            ('report_item_cpe', 'id'),
            ('report_item_type', 'id'),
            ('report_revision', 'id'),
            ('report_revision', 'created_by_id'),
            ('role', 'id'),
            ('role_based_access', 'id'),
            ('role_permission', 'role_id'),
            ('settings', 'id'),
            ('story_revision', 'id'),
            ('story_revision', 'created_by_id'),
            ('token_blacklist', 'id'),
            ('user', 'id'),
            ('user', 'organization_id'),
            ('user_role', 'user_id'),
            ('user_role', 'role_id'),
            ('word_list', 'id'),
            ('word_list_entry', 'id'),
            ('word_list_entry', 'word_list_id'),
            ('worker_parameter_value', 'parameter_value_id');

        DO $migration$
        DECLARE
            rec RECORD;
            schema_name TEXT := current_schema();
            uuid_pattern TEXT := '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
        BEGIN
            IF to_regclass(format('%I.%I', schema_name, 'permission')) IS NOT NULL THEN
                EXECUTE format('ALTER TABLE %I.%I ADD COLUMN IF NOT EXISTS %I VARCHAR(128)', schema_name, 'permission', 'code');
                EXECUTE format(
                    'UPDATE %I.%I SET %I = "id"::TEXT WHERE %I IS NULL OR %I = ''''',
                    schema_name,
                    'permission',
                    'code',
                    'code',
                    'code'
                );
                EXECUTE format('ALTER TABLE %I.%I ALTER COLUMN %I SET NOT NULL', schema_name, 'permission', 'code');
                EXECUTE format('CREATE UNIQUE INDEX IF NOT EXISTS %I ON %I.%I (%I)', 'ux_permission_code', schema_name, 'permission', 'code');
            END IF;

            IF to_regclass(format('%I.%I', schema_name, 'task')) IS NOT NULL THEN
                EXECUTE format('ALTER TABLE %I.%I ADD COLUMN IF NOT EXISTS %I VARCHAR(256)', schema_name, 'task', 'job_id');
                EXECUTE format(
                    'UPDATE %I.%I SET %I = "id"::TEXT WHERE %I IS NULL OR %I = ''''',
                    schema_name,
                    'task',
                    'job_id',
                    'job_id',
                    'job_id'
                );
                EXECUTE format('ALTER TABLE %I.%I ALTER COLUMN %I SET NOT NULL', schema_name, 'task', 'job_id');
                EXECUTE format('CREATE UNIQUE INDEX IF NOT EXISTS %I ON %I.%I (%I)', 'ux_task_job_id', schema_name, 'task', 'job_id');
            END IF;

            IF to_regclass(format('%I.%I', schema_name, 'settings')) IS NOT NULL THEN
                EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT IF EXISTS %I', schema_name, 'settings', 'check_only_one_row');
                EXECUTE format('ALTER TABLE %I.%I ADD COLUMN IF NOT EXISTS %I VARCHAR(64)', schema_name, 'settings', 'singleton_key');
                EXECUTE format(
                    'UPDATE %I.%I SET %I = ''settings'' WHERE %I IS NULL OR %I = ''''',
                    schema_name,
                    'settings',
                    'singleton_key',
                    'singleton_key',
                    'singleton_key'
                );
                EXECUTE format('ALTER TABLE %I.%I ALTER COLUMN %I SET NOT NULL', schema_name, 'settings', 'singleton_key');
                EXECUTE format(
                    'CREATE UNIQUE INDEX IF NOT EXISTS %I ON %I.%I (%I)',
                    'ux_settings_singleton_key',
                    schema_name,
                    'settings',
                    'singleton_key'
                );
            END IF;

            FOR rec IN
                SELECT *
                FROM (
                    VALUES
                        ('asset_group', 'key', 'ux_asset_group_key'),
                        ('osint_source', 'key', 'ux_osint_source_key'),
                        ('osint_source_group', 'key', 'ux_osint_source_group_key')
                ) AS semantic_key(table_name, column_name, index_name)
            LOOP
                IF to_regclass(format('%I.%I', schema_name, rec.table_name)) IS NULL THEN
                    CONTINUE;
                END IF;

                EXECUTE format(
                    'ALTER TABLE %I.%I ADD COLUMN IF NOT EXISTS %I VARCHAR(64)',
                    schema_name,
                    rec.table_name,
                    rec.column_name
                );
                EXECUTE format(
                    'UPDATE %I.%I
                     SET %I = "id"::TEXT
                     WHERE (%I IS NULL OR %I = '''')
                       AND "id"::TEXT !~* %L',
                    schema_name,
                    rec.table_name,
                    rec.column_name,
                    rec.column_name,
                    rec.column_name,
                    uuid_pattern
                );
                EXECUTE format('CREATE UNIQUE INDEX IF NOT EXISTS %I ON %I.%I (%I)', rec.index_name, schema_name, rec.table_name, rec.column_name);
            END LOOP;
        END;
        $migration$;

        CREATE TEMP TABLE taranis_legacy_id_foreign_keys AS
        SELECT child.relname AS table_name,
               con.conname AS constraint_name,
               pg_get_constraintdef(con.oid, true) AS constraint_definition
        FROM pg_constraint con
        JOIN pg_class child ON child.oid = con.conrelid
        JOIN pg_namespace child_schema ON child_schema.oid = child.relnamespace
        JOIN pg_class parent ON parent.oid = con.confrelid
        JOIN pg_namespace parent_schema ON parent_schema.oid = parent.relnamespace
        WHERE con.contype = 'f'
          AND child_schema.nspname = current_schema()
          AND parent_schema.nspname = current_schema()
          AND (
              EXISTS (
                  SELECT 1
                  FROM unnest(con.conkey) AS child_key(attnum)
                  JOIN pg_attribute child_attr
                    ON child_attr.attrelid = con.conrelid
                   AND child_attr.attnum = child_key.attnum
                  JOIN taranis_legacy_id_columns legacy
                    ON legacy.table_name = child.relname
                   AND legacy.column_name = child_attr.attname
              )
              OR EXISTS (
                  SELECT 1
                  FROM unnest(con.confkey) AS parent_key(attnum)
                  JOIN pg_attribute parent_attr
                    ON parent_attr.attrelid = con.confrelid
                   AND parent_attr.attnum = parent_key.attnum
                  JOIN taranis_legacy_id_columns legacy
                    ON legacy.table_name = parent.relname
                   AND legacy.column_name = parent_attr.attname
              )
          );

        ALTER TABLE taranis_legacy_id_foreign_keys
        ADD PRIMARY KEY (table_name, constraint_name);

        DO $migration$
        DECLARE
            rec RECORD;
            schema_name TEXT := current_schema();
        BEGIN
            FOR rec IN
                SELECT table_name, constraint_name
                FROM taranis_legacy_id_foreign_keys
                ORDER BY table_name, constraint_name
            LOOP
                EXECUTE format(
                    'ALTER TABLE %I.%I DROP CONSTRAINT IF EXISTS %I',
                    schema_name,
                    rec.table_name,
                    rec.constraint_name
                );
            END LOOP;
        END;
        $migration$;

        DO $migration$
        DECLARE
            rec RECORD;
            schema_name TEXT := current_schema();
        BEGIN
            FOR rec IN
                SELECT table_name, column_name
                FROM taranis_legacy_id_columns
                ORDER BY table_name, column_name
            LOOP
                IF to_regclass(format('%I.%I', schema_name, rec.table_name)) IS NULL
                    OR NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = schema_name
                          AND table_name = rec.table_name
                          AND column_name = rec.column_name
                          AND udt_name IN ('int2', 'int4', 'int8')
                    )
                THEN
                    CONTINUE;
                END IF;

                EXECUTE format(
                    'ALTER TABLE %I.%I ALTER COLUMN %I DROP DEFAULT',
                    schema_name,
                    rec.table_name,
                    rec.column_name
                );
                EXECUTE format(
                    'ALTER TABLE %I.%I ALTER COLUMN %I TYPE VARCHAR(36) USING %I::TEXT',
                    schema_name,
                    rec.table_name,
                    rec.column_name,
                    rec.column_name
                );
            END LOOP;
        END;
        $migration$;

        DO $migration$
        DECLARE
            rec RECORD;
            schema_name TEXT := current_schema();
        BEGIN
            FOR rec IN
                SELECT table_name, constraint_name, constraint_definition
                FROM taranis_legacy_id_foreign_keys
                ORDER BY table_name, constraint_name
            LOOP
                IF to_regclass(format('%I.%I', schema_name, rec.table_name)) IS NULL THEN
                    CONTINUE;
                END IF;

                EXECUTE format(
                    'ALTER TABLE %I.%I ADD CONSTRAINT %I %s',
                    schema_name,
                    rec.table_name,
                    rec.constraint_name,
                    rec.constraint_definition
                );
            END LOOP;
        END;
        $migration$;

        DROP TABLE IF EXISTS taranis_legacy_id_foreign_keys;
        DROP TABLE IF EXISTS taranis_legacy_id_columns;
        """,
        """
        DO $rollback$
        BEGIN
            RAISE EXCEPTION 'String primary-key migration cannot reliably restore legacy integer primary keys once UUIDv7 rows exist.';
        END;
        $rollback$;
        """,
    )
]
