# pyright: reportMissingTypeStubs=false
"""move worker parameter definitions to the shared model registry"""

import json
from typing import Any

from models.worker_parameters import get_worker_definition, normalize_parameter_values
from pydantic import ValidationError
from yoyo import step


__depends__ = {"20260710_01_m3P7q-add-product-last-published-url"}

_OWNERS = (
    ("osint_source", "osint_source_parameter_value", "osint_source_id", "enabled"),
    ("bot", "bot_parameter_value", "bot_id", "enabled"),
    ("connector", "connector_parameter_value", "connector_id", None),
    ("product_type", "product_type_parameter_value", "product_type_id", None),
    ("publisher_preset", "publisher_preset_parameter_value", "publisher_preset_id", None),
)


def _unsupported_downgrade(connection) -> None:
    raise RuntimeError("Worker parameter migration cannot be downgraded; restore the verified database snapshot")


def _migrate_parameters(connection) -> None:
    with connection.cursor() as cursor:
        for owner_table, join_table, owner_fk, enabled_column in _OWNERS:
            enabled_select = f", owner.{enabled_column}" if enabled_column else ""
            cursor.execute(
                f"""
                SELECT owner.id, owner.type{enabled_select}, parameter_value.parameter, parameter_value.value
                FROM {owner_table} owner
                LEFT JOIN {join_table} owner_parameter ON owner_parameter.{owner_fk} = owner.id
                LEFT JOIN parameter_value ON parameter_value.id = owner_parameter.parameter_value_id
                ORDER BY owner.id
                """
            )
            owners: dict[str, tuple[str, bool, dict[str, Any]]] = {}
            for row in cursor.fetchall():
                owner_id, worker_type = row[:2]
                requires_complete = bool(row[2]) if enabled_column else False
                parameter, value = row[3:5] if enabled_column else row[2:4]
                _, _, values = owners.setdefault(str(owner_id), (str(worker_type), requires_complete, {}))
                if parameter is None:
                    continue
                if parameter in values and values[parameter] != value:
                    raise RuntimeError(f"Conflicting duplicate {owner_table} parameter {owner_id}/{parameter}")
                values[parameter] = value

            for owner_id, (worker_type, requires_complete, values) in owners.items():
                try:
                    fields = get_worker_definition(worker_type).parameter_model.model_fields
                except (KeyError, ValueError) as exc:
                    raise RuntimeError(
                        f"Cannot migrate {owner_table} {owner_id} with worker type {worker_type}: unsupported worker type"
                    ) from exc
                if worker_type == "TAGGING_BOT" and values.get("KEYWORDS") and "REGULAR_EXPRESSION" not in values:
                    values["REGULAR_EXPRESSION"] = values["KEYWORDS"]
                if worker_type == "TAXII_PUBLISHER" and values.get("AUTH_TYPE") == "token":
                    values["AUTH_TYPE"] = "bearer"
                normalized: dict[str, str] = {}
                for name, value in values.items():
                    if name not in fields:
                        continue
                    try:
                        normalized.update(normalize_parameter_values(worker_type, {name: value}, complete=False))
                    except (ValidationError, ValueError, TypeError):
                        if value not in (None, ""):
                            normalized[name] = str(value)
                if requires_complete:
                    try:
                        normalize_parameter_values(worker_type, normalized, complete=True)
                    except (ValidationError, ValueError, TypeError) as exc:
                        raise RuntimeError(
                            f"Cannot migrate {owner_table} {owner_id} with worker type {worker_type}: invalid active configuration"
                        ) from exc
                cursor.execute(
                    f"UPDATE {owner_table} SET parameters = %s::jsonb WHERE id = %s",
                    (json.dumps(normalized, separators=(",", ":"), sort_keys=True), owner_id),
                )


steps = [
    step(
        """
        ALTER TABLE osint_source ADD COLUMN parameters JSONB NOT NULL DEFAULT '{}'::jsonb;
        ALTER TABLE bot ADD COLUMN parameters JSONB NOT NULL DEFAULT '{}'::jsonb;
        ALTER TABLE connector ADD COLUMN parameters JSONB NOT NULL DEFAULT '{}'::jsonb;
        ALTER TABLE product_type ADD COLUMN parameters JSONB NOT NULL DEFAULT '{}'::jsonb;
        ALTER TABLE publisher_preset ADD COLUMN parameters JSONB NOT NULL DEFAULT '{}'::jsonb;
        """,
        _unsupported_downgrade,
    ),
    step(_migrate_parameters, _unsupported_downgrade),
    step(
        """
        DROP TABLE worker_parameter_value;
        DROP TABLE osint_source_parameter_value;
        DROP TABLE bot_parameter_value;
        DROP TABLE connector_parameter_value;
        DROP TABLE product_type_parameter_value;
        DROP TABLE publisher_preset_parameter_value;
        DROP TABLE parameter_value;
        DROP TABLE worker;
        DROP TYPE IF EXISTS parameter_types;
        DROP TYPE IF EXISTS worker_category;
        DROP TYPE IF EXISTS worker_types;
        """,
        _unsupported_downgrade,
    ),
]
