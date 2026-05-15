"""
migrate model primary keys to UUIDv7 strings

Forward migration rewrites existing primary keys and dependent foreign keys to
canonical UUIDv7 strings. Rollback cannot reliably restore integer primary keys
for rows created after this migration.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from yoyo import step


__depends__ = {
    "20260408_01_t7KpQ-add-user-last-login",
    "20260416_01_Q7vKp-add-task-worker-metadata",
}


ID_TABLES = {
    "asset",
    "asset_cpe",
    "asset_group",
    "asset_vulnerability",
    "attribute",
    "attribute_enum",
    "attribute_group",
    "attribute_group_item",
    "bot",
    "connector",
    "news_item",
    "news_item_attribute",
    "news_item_tag",
    "news_item_vote",
    "organization",
    "osint_source",
    "osint_source_group",
    "parameter_value",
    "permission",
    "product",
    "product_type",
    "publisher_preset",
    "report_item",
    "report_item_attribute",
    "report_item_cpe",
    "report_item_type",
    "report_revision",
    "role",
    "role_based_access",
    "settings",
    "story",
    "story_revision",
    "task",
    "token_blacklist",
    "user",
    "word_list",
    "word_list_entry",
    "worker",
}


PRIMARY_KEYS = {
    "asset": ("id",),
    "asset_cpe": ("id",),
    "asset_group": ("id",),
    "asset_vulnerability": ("id",),
    "attribute": ("id",),
    "attribute_enum": ("id",),
    "attribute_group": ("id",),
    "attribute_group_item": ("id",),
    "bot": ("id",),
    "bot_parameter_value": ("bot_id", "parameter_value_id"),
    "connector": ("id",),
    "connector_parameter_value": ("connector_id", "parameter_value_id"),
    "news_item": ("id",),
    "news_item_attribute": ("id",),
    "news_item_news_item_attribute": ("news_item_id", "news_item_attribute_id"),
    "news_item_tag": ("id",),
    "news_item_vote": ("id",),
    "organization": ("id",),
    "osint_source": ("id",),
    "osint_source_group": ("id",),
    "osint_source_group_osint_source": ("osint_source_group_id", "osint_source_id"),
    "osint_source_group_word_list": ("osint_source_group_id", "word_list_id"),
    "osint_source_parameter_value": ("osint_source_id", "parameter_value_id"),
    "parameter_value": ("id",),
    "permission": ("id",),
    "product": ("id",),
    "product_report_item": ("product_id", "report_item_id"),
    "product_type": ("id",),
    "product_type_parameter_value": ("product_type_id", "parameter_value_id"),
    "product_type_report_type": ("product_type_id", "report_item_type_id"),
    "publisher_preset": ("id",),
    "publisher_preset_parameter_value": ("publisher_preset_id", "parameter_value_id"),
    "rbac_role": ("acl_id", "role_id"),
    "report_item": ("id",),
    "report_item_attribute": ("id",),
    "report_item_cpe": ("id",),
    "report_item_story": ("report_item_id", "story_id"),
    "report_item_type": ("id",),
    "report_revision": ("id",),
    "role": ("id",),
    "role_based_access": ("id",),
    "role_permission": ("role_id", "permission_id"),
    "settings": ("id",),
    "story": ("id",),
    "story_news_item_attribute": ("story_id", "news_item_attribute_id"),
    "story_revision": ("id",),
    "task": ("id",),
    "token_blacklist": ("id",),
    "user": ("id",),
    "user_role": ("user_id", "role_id"),
    "word_list": ("id",),
    "word_list_entry": ("id",),
    "worker": ("id",),
    "worker_parameter_value": ("worker_id", "parameter_value_id"),
}


FK_REFERENCES = {
    "asset": {"asset_group_id": "asset_group"},
    "asset_cpe": {"asset_id": "asset"},
    "asset_group": {"organization_id": "organization"},
    "asset_vulnerability": {"asset_id": "asset", "report_item_id": "report_item"},
    "attribute_enum": {"attribute_id": "attribute"},
    "attribute_group": {"report_item_type_id": "report_item_type"},
    "attribute_group_item": {"attribute_group_id": "attribute_group", "attribute_id": "attribute"},
    "bot_parameter_value": {"bot_id": "bot", "parameter_value_id": "parameter_value"},
    "connector_parameter_value": {"connector_id": "connector", "parameter_value_id": "parameter_value"},
    "news_item": {"osint_source_id": "osint_source", "story_id": "story"},
    "news_item_news_item_attribute": {"news_item_id": "news_item", "news_item_attribute_id": "news_item_attribute"},
    "news_item_tag": {"story_id": "story"},
    "news_item_vote": {"user_id": "user"},
    "osint_source_group_osint_source": {"osint_source_group_id": "osint_source_group", "osint_source_id": "osint_source"},
    "osint_source_group_word_list": {"osint_source_group_id": "osint_source_group", "word_list_id": "word_list"},
    "osint_source_parameter_value": {"osint_source_id": "osint_source", "parameter_value_id": "parameter_value"},
    "product": {"product_type_id": "product_type", "default_publisher": "publisher_preset"},
    "product_report_item": {"product_id": "product", "report_item_id": "report_item"},
    "product_type_parameter_value": {"product_type_id": "product_type", "parameter_value_id": "parameter_value"},
    "product_type_report_type": {"product_type_id": "product_type", "report_item_type_id": "report_item_type"},
    "publisher_preset_parameter_value": {"publisher_preset_id": "publisher_preset", "parameter_value_id": "parameter_value"},
    "rbac_role": {"acl_id": "role_based_access", "role_id": "role"},
    "report_item": {"user_id": "user", "report_item_type_id": "report_item_type"},
    "report_item_attribute": {"report_item_id": "report_item"},
    "report_item_cpe": {"report_item_id": "report_item"},
    "report_item_story": {"report_item_id": "report_item", "story_id": "story"},
    "report_revision": {"report_item_id": "report_item", "created_by_id": "user"},
    "role_permission": {"role_id": "role", "permission_id": "permission"},
    "story_news_item_attribute": {"story_id": "story", "news_item_attribute_id": "news_item_attribute"},
    "story_revision": {"story_id": "story", "created_by_id": "user"},
    "user": {"organization_id": "organization"},
    "user_role": {"user_id": "user", "role_id": "role"},
    "word_list_entry": {"word_list_id": "word_list"},
    "worker_parameter_value": {"worker_id": "worker", "parameter_value_id": "parameter_value"},
}


SEMANTIC_COLUMNS = {
    "permission": ("code", "VARCHAR(128)"),
    "task": ("job_id", "VARCHAR(256)"),
    "osint_source": ("key", "VARCHAR(64)"),
    "osint_source_group": ("key", "VARCHAR(64)"),
    "asset_group": ("key", "VARCHAR(64)"),
    "settings": ("singleton_key", "VARCHAR(64)"),
}


def apply_migration(conn):
    if _is_sqlite(conn):
        _apply_sqlite(conn)
    else:
        _apply_postgres(conn)


def rollback_migration(_conn):
    raise RuntimeError("UUIDv7 primary-key migration cannot reliably restore legacy integer primary keys.")


def _is_sqlite(conn) -> bool:
    return conn.__class__.__module__.startswith("sqlite3")


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _temp_map(table: str) -> str:
    return f"uuid_map_{table}"


def _uuid7() -> str:
    return str(uuid.uuid7())


def _is_uuid(value: Any) -> bool:
    try:
        uuid.UUID(str(value))
    except TypeError, ValueError:
        return False
    return True


def _table_exists(cursor, table: str) -> bool:
    cursor.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,))
    return cursor.fetchone() is not None


def _sqlite_columns(cursor, table: str) -> list[dict[str, Any]]:
    cursor.execute(f"PRAGMA table_info({_quote(table)})")
    return [{"cid": row[0], "name": row[1], "type": row[2], "notnull": row[3], "default": row[4], "pk": row[5]} for row in cursor.fetchall()]


def _add_sqlite_column_if_missing(cursor, table: str, column: str, column_type: str) -> None:
    if not _table_exists(cursor, table):
        return
    if column in {col["name"] for col in _sqlite_columns(cursor, table)}:
        return
    cursor.execute(f"ALTER TABLE {_quote(table)} ADD COLUMN {_quote(column)} {column_type}")


def _prepare_sqlite_semantic_columns(cursor) -> None:
    for table, (column, column_type) in SEMANTIC_COLUMNS.items():
        _add_sqlite_column_if_missing(cursor, table, column, column_type)

    if _table_exists(cursor, "permission"):
        cursor.execute('UPDATE "permission" SET "code" = CAST("id" AS TEXT) WHERE "code" IS NULL OR "code" = ""')
    if _table_exists(cursor, "task"):
        cursor.execute('UPDATE "task" SET "job_id" = CAST("id" AS TEXT) WHERE "job_id" IS NULL OR "job_id" = ""')
    if _table_exists(cursor, "settings"):
        cursor.execute('UPDATE "settings" SET "singleton_key" = \'settings\' WHERE "singleton_key" IS NULL OR "singleton_key" = ""')

    for table in ("osint_source", "osint_source_group", "asset_group"):
        if not _table_exists(cursor, table):
            continue
        cursor.execute(f'SELECT "id" FROM {_quote(table)} WHERE "key" IS NULL OR "key" = ""')
        for (old_id,) in cursor.fetchall():
            if not _is_uuid(old_id):
                cursor.execute(f'UPDATE {_quote(table)} SET "key" = ? WHERE "id" = ?', (str(old_id), old_id))


def _create_sqlite_maps(cursor) -> None:
    for table in sorted(ID_TABLES):
        if not _table_exists(cursor, table):
            continue
        cursor.execute(f'CREATE TEMP TABLE {_quote(_temp_map(table))} ("old_id" TEXT PRIMARY KEY, "new_id" TEXT NOT NULL)')
        cursor.execute(f'SELECT "id" FROM {_quote(table)}')
        mappings = [(str(old_id), _uuid7()) for (old_id,) in cursor.fetchall()]
        if mappings:
            cursor.executemany(f'INSERT INTO {_quote(_temp_map(table))} ("old_id", "new_id") VALUES (?, ?)', mappings)


def _sqlite_column_type(table: str, column: str, original_type: str) -> str:
    if table in ID_TABLES and column == "id":
        return "VARCHAR(36)"
    if column in FK_REFERENCES.get(table, {}):
        return "VARCHAR(36)"
    if column in PRIMARY_KEYS.get(table, ()) and column.endswith("_id"):
        return "VARCHAR(36)"
    return original_type or "TEXT"


def _sqlite_column_expr(table: str, column: str) -> str:
    quoted_column = _quote(column)
    if table in ID_TABLES and column == "id":
        return f'(SELECT "new_id" FROM {_quote(_temp_map(table))} WHERE "old_id" = CAST("old".{quoted_column} AS TEXT))'
    if parent := FK_REFERENCES.get(table, {}).get(column):
        return (
            f'CASE WHEN "old".{quoted_column} IS NULL THEN NULL ELSE '
            f'COALESCE((SELECT "new_id" FROM {_quote(_temp_map(parent))} '
            f'WHERE "old_id" = CAST("old".{quoted_column} AS TEXT)), CAST("old".{quoted_column} AS TEXT)) END'
        )
    return f'"old".{quoted_column}'


def _rebuild_sqlite_table(cursor, table: str) -> None:
    if not _table_exists(cursor, table):
        return

    columns = _sqlite_columns(cursor, table)
    if not columns:
        return

    new_table = f"{table}_uuidv7_new"
    pk_columns = PRIMARY_KEYS.get(table) or tuple(col["name"] for col in columns if col["pk"])
    composite_pk = len(pk_columns) > 1

    definitions = []
    for col in columns:
        column_type = _sqlite_column_type(table, col["name"], col["type"])
        definition = f"{_quote(col['name'])} {column_type}"
        if col["notnull"] and col["name"] not in pk_columns:
            definition += " NOT NULL"
        if col["default"] is not None:
            definition += f" DEFAULT {col['default']}"
        if not composite_pk and col["name"] in pk_columns:
            definition += " PRIMARY KEY"
        definitions.append(definition)

    if composite_pk:
        definitions.append("PRIMARY KEY (" + ", ".join(_quote(column) for column in pk_columns) + ")")

    cursor.execute(f"CREATE TABLE {_quote(new_table)} ({', '.join(definitions)})")

    column_names = [col["name"] for col in columns]
    insert_columns = ", ".join(_quote(name) for name in column_names)
    select_exprs = ", ".join(_sqlite_column_expr(table, name) for name in column_names)
    cursor.execute(f'INSERT INTO {_quote(new_table)} ({insert_columns}) SELECT {select_exprs} FROM {_quote(table)} AS "old"')

    cursor.execute(f"DROP TABLE {_quote(table)}")
    cursor.execute(f"ALTER TABLE {_quote(new_table)} RENAME TO {_quote(table)}")


def _create_sqlite_indexes(cursor) -> None:
    unique_indexes = {
        "asset_group": ("key",),
        "organization": ("name",),
        "osint_source": ("key",),
        "osint_source_group": ("key",),
        "permission": ("code",),
        "product_type": ("title",),
        "report_item_type": ("title",),
        "role": ("name",),
        "settings": ("singleton_key",),
        "task": ("job_id",),
        "user": ("username",),
    }
    for table, columns in unique_indexes.items():
        if not _table_exists(cursor, table):
            continue
        existing_columns = {col["name"] for col in _sqlite_columns(cursor, table)}
        if not set(columns).issubset(existing_columns):
            continue
        index_name = f"ux_{table}_{'_'.join(columns)}"
        quoted_columns = ", ".join(_quote(column) for column in columns)
        cursor.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {_quote(index_name)} ON {_quote(table)} ({quoted_columns})")


def _apply_sqlite(conn) -> None:
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys=OFF")
    _prepare_sqlite_semantic_columns(cursor)
    _create_sqlite_maps(cursor)

    tables = set(PRIMARY_KEYS) | set(FK_REFERENCES) | ID_TABLES
    for table in sorted(tables):
        _rebuild_sqlite_table(cursor, table)

    _create_sqlite_indexes(cursor)
    cursor.execute("PRAGMA foreign_keys=ON")


def _pg_table_exists(cursor, table: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = current_schema()
          AND table_name = %s
        """,
        (table,),
    )
    return cursor.fetchone() is not None


def _pg_column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = %s
          AND column_name = %s
        """,
        (table, column),
    )
    return cursor.fetchone() is not None


def _prepare_pg_semantic_columns(cursor) -> None:
    for table, (column, column_type) in SEMANTIC_COLUMNS.items():
        if not _pg_table_exists(cursor, table):
            continue
        cursor.execute(f"ALTER TABLE {_quote(table)} ADD COLUMN IF NOT EXISTS {_quote(column)} {column_type}")

    if _pg_table_exists(cursor, "permission"):
        cursor.execute('UPDATE "permission" SET "code" = "id"::text WHERE "code" IS NULL OR "code" = \'\'')
    if _pg_table_exists(cursor, "task"):
        cursor.execute('UPDATE "task" SET "job_id" = "id"::text WHERE "job_id" IS NULL OR "job_id" = \'\'')
    if _pg_table_exists(cursor, "settings"):
        cursor.execute('UPDATE "settings" SET "singleton_key" = \'settings\' WHERE "singleton_key" IS NULL OR "singleton_key" = \'\'')

    for table in ("osint_source", "osint_source_group", "asset_group"):
        if not _pg_table_exists(cursor, table):
            continue
        cursor.execute(f'SELECT "id" FROM {_quote(table)} WHERE "key" IS NULL OR "key" = \'\'')
        for (old_id,) in cursor.fetchall():
            if not _is_uuid(old_id):
                cursor.execute(f'UPDATE {_quote(table)} SET "key" = %s WHERE "id" = %s', (str(old_id), old_id))


def _drop_pg_constraints(cursor, tables: set[str]) -> list[tuple[str, str, str]]:
    cursor.execute(
        """
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
          AND (child.relname = ANY(%s) OR parent.relname = ANY(%s))
        ORDER BY child.relname, con.conname
        """,
        (list(tables), list(tables)),
    )
    foreign_keys = cursor.fetchall()
    for table, constraint, _definition in foreign_keys:
        cursor.execute(f"ALTER TABLE {_quote(table)} DROP CONSTRAINT IF EXISTS {_quote(constraint)}")

    cursor.execute(
        """
        SELECT table_class.relname AS table_name, con.conname AS constraint_name
        FROM pg_constraint con
        JOIN pg_class table_class ON table_class.oid = con.conrelid
        JOIN pg_namespace table_schema ON table_schema.oid = table_class.relnamespace
        WHERE con.contype = 'p'
          AND table_schema.nspname = current_schema()
          AND table_class.relname = ANY(%s)
        ORDER BY table_class.relname, con.conname
        """,
        (list(tables),),
    )
    for table, constraint in cursor.fetchall():
        cursor.execute(f"ALTER TABLE {_quote(table)} DROP CONSTRAINT IF EXISTS {_quote(constraint)}")
    return foreign_keys


def _create_pg_maps(cursor) -> None:
    for table in sorted(ID_TABLES):
        if not _pg_table_exists(cursor, table):
            continue
        cursor.execute(f'CREATE TEMP TABLE {_quote(_temp_map(table))} ("old_id" TEXT PRIMARY KEY, "new_id" TEXT NOT NULL) ON COMMIT DROP')
        cursor.execute(f'SELECT "id"::text FROM {_quote(table)}')
        mappings = [(str(old_id), _uuid7()) for (old_id,) in cursor.fetchall()]
        if mappings:
            cursor.executemany(f'INSERT INTO {_quote(_temp_map(table))} ("old_id", "new_id") VALUES (%s, %s)', mappings)


def _pg_uuid_columns() -> dict[str, set[str]]:
    columns = defaultdict(set)
    for table in ID_TABLES:
        columns[table].add("id")
    for table, refs in FK_REFERENCES.items():
        columns[table].update(refs)
    for table, pk_columns in PRIMARY_KEYS.items():
        columns[table].update(column for column in pk_columns if column.endswith("_id") or column == "acl_id")
    return columns


def _alter_pg_columns(cursor) -> None:
    for table, columns in sorted(_pg_uuid_columns().items()):
        if not _pg_table_exists(cursor, table):
            continue
        for column in sorted(columns):
            if _pg_column_exists(cursor, table, column):
                cursor.execute(f"ALTER TABLE {_quote(table)} ALTER COLUMN {_quote(column)} TYPE VARCHAR(36) USING {_quote(column)}::text")


def _update_pg_fk_values(cursor) -> None:
    for table, refs in sorted(FK_REFERENCES.items()):
        if not _pg_table_exists(cursor, table):
            continue
        for column, parent in sorted(refs.items()):
            if not _pg_column_exists(cursor, table, column):
                continue
            cursor.execute(
                f"""
                UPDATE {_quote(table)} AS child
                SET {_quote(column)} = map."new_id"
                FROM {_quote(_temp_map(parent))} AS map
                WHERE child.{_quote(column)} IS NOT NULL
                  AND child.{_quote(column)}::text = map."old_id"
                """
            )


def _update_pg_pk_values(cursor) -> None:
    for table in sorted(ID_TABLES):
        if not _pg_table_exists(cursor, table):
            continue
        cursor.execute(
            f"""
            UPDATE {_quote(table)} AS parent
            SET "id" = map."new_id"
            FROM {_quote(_temp_map(table))} AS map
            WHERE parent."id"::text = map."old_id"
            """
        )


def _recreate_pg_constraints(cursor, foreign_keys: list[tuple[str, str, str]]) -> None:
    for table, pk_columns in sorted(PRIMARY_KEYS.items()):
        if not _pg_table_exists(cursor, table):
            continue
        quoted_columns = ", ".join(_quote(column) for column in pk_columns if _pg_column_exists(cursor, table, column))
        if quoted_columns:
            cursor.execute(f"ALTER TABLE {_quote(table)} ADD PRIMARY KEY ({quoted_columns})")

    for table, constraint, definition in foreign_keys:
        if not _pg_table_exists(cursor, table):
            continue
        cursor.execute(f"ALTER TABLE {_quote(table)} ADD CONSTRAINT {_quote(constraint)} {definition}")


def _create_pg_unique_indexes(cursor) -> None:
    unique_indexes = {
        "asset_group": ("key",),
        "organization": ("name",),
        "osint_source": ("key",),
        "osint_source_group": ("key",),
        "permission": ("code",),
        "product_type": ("title",),
        "report_item_type": ("title",),
        "role": ("name",),
        "settings": ("singleton_key",),
        "task": ("job_id",),
        "user": ("username",),
    }
    for table, columns in unique_indexes.items():
        if not _pg_table_exists(cursor, table):
            continue
        if not all(_pg_column_exists(cursor, table, column) for column in columns):
            continue
        index_name = f"ux_{table}_{'_'.join(columns)}"
        quoted_columns = ", ".join(_quote(column) for column in columns)
        cursor.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {_quote(index_name)} ON {_quote(table)} ({quoted_columns})")


def _apply_postgres(conn) -> None:
    cursor = conn.cursor()
    tables = set(PRIMARY_KEYS) | set(FK_REFERENCES) | ID_TABLES
    _prepare_pg_semantic_columns(cursor)
    foreign_keys = _drop_pg_constraints(cursor, tables)
    _create_pg_maps(cursor)
    _alter_pg_columns(cursor)
    _update_pg_fk_values(cursor)
    _update_pg_pk_values(cursor)
    _recreate_pg_constraints(cursor, foreign_keys)
    _create_pg_unique_indexes(cursor)


steps = [step(apply_migration, rollback_migration)]
