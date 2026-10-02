"""Core policy for configured and effective worker parameters."""

from typing import Any

from models.worker_parameters import (
    SECRET_MASK,
    configured_parameter_values,
    effective_parameter_values,
    get_worker_definition,
    normalize_parameter_values,
    secret_parameter_names,
)


def set_parameters(
    worker_type: str,
    current: dict[str, Any] | None,
    submitted: dict[str, Any] | None,
    *,
    patch: bool,
    complete: bool = True,
) -> dict[str, Any]:
    """Apply PUT/PATCH semantics and validate the resulting configuration."""
    current = dict(current or {})
    submitted = dict(submitted or {})
    secrets = secret_parameter_names(worker_type)

    if patch:
        candidate = current
    else:
        candidate = {name: value for name, value in current.items() if name in secrets and submitted.get(name, SECRET_MASK) == SECRET_MASK}

    for name, value in submitted.items():
        if name in secrets and value == SECRET_MASK:
            continue
        if value is None:
            candidate.pop(name, None)
        else:
            candidate[name] = value

    normalized = normalize_parameter_values(worker_type, candidate, complete=complete)
    if endpoint_id := normalized.get("LLM_ENDPOINT"):
        from core.managers.db_manager import db
        from core.model.settings import Settings

        # Serialize assignments with endpoint deletion so selected endpoints cannot disappear.
        entry = Settings.get_first(db.select(Settings).with_for_update().execution_options(populate_existing=True))
        if entry is None or endpoint_id not in Settings.with_defaults(entry.settings)["llm_endpoints"]:
            raise ValueError("Select a configured LLM endpoint")
    return normalized


def configured_parameters(worker_type: str, values: dict[str, Any] | None) -> dict[str, Any]:
    return configured_parameter_values(worker_type, dict(values or {}))


def effective_parameters(worker_type: str, values: dict[str, Any] | None) -> dict[str, Any]:
    return effective_parameter_values(worker_type, dict(values or {}))


def reveal_parameter(worker_type: str, values: dict[str, Any] | None, parameter: str) -> str:
    if parameter not in secret_parameter_names(worker_type):
        raise ValueError(f"{parameter} is not a secret parameter")
    try:
        value = dict(values or {})[parameter]
    except KeyError as exc:
        raise ValueError(f"{parameter} is not configured") from exc
    if not isinstance(value, str):
        raise TypeError(f"{parameter} has an invalid stored value")
    return value


def parameter_is_required(worker_type: str, parameter: str) -> bool:
    definition = get_worker_definition(worker_type)
    try:
        return definition.parameter_model.model_fields[parameter].is_required()
    except KeyError as exc:
        raise ValueError(f"Unknown parameter: {parameter}") from exc
