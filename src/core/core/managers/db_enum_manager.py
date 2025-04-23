from typing import Type
from enum import StrEnum
from sqlalchemy import text
from core.log import logger


def sync_enum_with_db(enum_type: Type[StrEnum], connection, table_column: str | None = None) -> None:
    enum_name = enum_type.__name__.lower()
    if table_column:
        table_name, column_name = table_column.split(".")
    else:
        table_name, column_name = _infer_table_and_column_from_enum_name(enum_name)

    existing_values = _fetch_existing_enum_values(connection, enum_name)
    new_values = {e.name for e in enum_type}

    if existing_values == new_values:
        return

    logger.debug(
        f"Syncing enum '{enum_name}' for {table_name}.{column_name} (existing: {sorted(existing_values)}, new: {sorted(new_values)})"
    )

    _handle_invalid_rows(connection, table_name, column_name, existing_values - new_values)
    _replace_enum_type(connection, enum_name, new_values)
    _alter_column_type(connection, table_name, column_name, enum_name)
    _drop_old_enum_type(connection, enum_name)

    connection.commit()


def _infer_table_and_column_from_enum_name(enum_name: str) -> tuple[str, str]:
    table, column = enum_name.split("_")
    return table, "type" if column == "types" else column


def _fetch_existing_enum_values(connection, enum_name: str) -> set[str]:
    result = connection.execute(text(f"SELECT unnest(enum_range(NULL::{enum_name}))"))
    return {row[0] for row in result}


def _handle_invalid_rows(connection, table: str, column: str, invalid_values: set[str]) -> None:
    if not invalid_values:
        return

    values_sql = ", ".join(f"'{v}'" for v in invalid_values)
    logger.debug(f"Deleting rows from {table} where {column} in {sorted(invalid_values)}")
    connection.execute(text(f"DELETE FROM {table} WHERE {column} IN ({values_sql})"))


def _replace_enum_type(connection, enum_name: str, new_values: set[str]) -> None:
    logger.debug(f"Renaming old enum type {enum_name} to {enum_name}_old")
    connection.execute(text(f"ALTER TYPE {enum_name} RENAME TO {enum_name}_old"))
    values_sql = ", ".join(f"'{v}'" for v in sorted(new_values))
    logger.debug(f"Creating new enum type {enum_name} with values {sorted(new_values)}")
    connection.execute(text(f"CREATE TYPE {enum_name} AS ENUM ({values_sql})"))


def _alter_column_type(connection, table: str, column: str, enum_name: str) -> None:
    logger.debug(f"Altering column {table}.{column} to use new enum type {enum_name}")
    connection.execute(
        text(f"""
        ALTER TABLE {table}
        ALTER COLUMN {column}
        TYPE {enum_name}
        USING {column}::text::{enum_name}
    """)
    )


def _drop_old_enum_type(connection, enum_name: str) -> None:
    logger.debug(f"Dropping old enum type {enum_name}_old")
    connection.execute(text(f"DROP TYPE {enum_name}_old"))
