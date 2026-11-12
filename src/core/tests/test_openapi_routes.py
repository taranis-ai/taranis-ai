import re
from collections import Counter, defaultdict
from pathlib import Path

import pytest
import yaml
from flask import Flask
from models.api_operations import OPERATIONS, find_operation

from core.config import Config
from core.managers import api_manager


OPENAPI_PATH = Path(__file__).resolve().parents[1] / "core" / "static" / "openapi3_1.yaml"
IGNORED_PATHS = set()


@pytest.fixture(params=["/", "/taranis/"])
def route_app(request, monkeypatch):
    monkeypatch.setattr(Config, "APPLICATION_ROOT", request.param)
    monkeypatch.setattr("core.api.auth.Config.APPLICATION_ROOT", request.param)
    app = Flask(__name__, static_url_path=f"{Config.APPLICATION_ROOT}static")
    app.config.from_object(Config)
    api_manager.initialize(app)
    return app


def _canonical_path(path: str) -> str:
    path = path.rstrip("/") if path != "/" else path
    path = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", path)
    return re.sub(r"\{[^}]+\}", "{}", path)


def _load_openapi_paths() -> dict[str, set[str]]:
    with OPENAPI_PATH.open("r", encoding="utf-8") as handle:
        spec = yaml.safe_load(handle)

    paths: dict[str, set[str]] = defaultdict(set)
    for path, operations in spec["paths"].items():
        canonical = _canonical_path(path)
        for method in operations:
            if method == "parameters":
                continue
            paths[canonical].add(method.upper())

    return paths


def _load_openapi_operations() -> tuple[dict[tuple[str, str], str], list[str], list[tuple[str, str]]]:
    with OPENAPI_PATH.open("r", encoding="utf-8") as handle:
        spec = yaml.safe_load(handle)

    operations: dict[tuple[str, str], str] = {}
    operation_ids: list[str] = []
    missing_operation_ids: list[tuple[str, str]] = []
    for path, methods in spec["paths"].items():
        canonical = _canonical_path(path)
        for method, operation in methods.items():
            if method == "parameters" or not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if operation_id:
                operations[(canonical, method.upper())] = operation_id
                operation_ids.append(operation_id)
            else:
                missing_operation_ids.append((canonical, method.upper()))

    return operations, operation_ids, missing_operation_ids


def _load_routes(app) -> dict[str, set[str]]:
    routes: dict[str, set[str]] = defaultdict(set)
    prefix = f"{app.config['APPLICATION_ROOT']}api"
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        path = (
            rule.rule.removeprefix(prefix)
            if rule.rule.startswith(f"{prefix}/")
            else "/" + rule.rule.removeprefix(app.config["APPLICATION_ROOT"])
        )
        canonical = _canonical_path(path)
        if canonical in IGNORED_PATHS:
            continue

        for method in rule.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes[canonical].add(method.upper())

    return routes


def _load_route_endpoints(app) -> dict[tuple[str, str], str]:
    endpoints: dict[tuple[str, str], str] = {}
    prefix = f"{app.config['APPLICATION_ROOT']}api"
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        path = (
            rule.rule.removeprefix(prefix)
            if rule.rule.startswith(f"{prefix}/")
            else "/" + rule.rule.removeprefix(app.config["APPLICATION_ROOT"])
        )
        canonical = _canonical_path(path)
        if canonical in IGNORED_PATHS:
            continue

        for method in rule.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            endpoints[(canonical, method.upper())] = rule.endpoint

    return endpoints


def test_openapi_covers_app_routes(route_app):
    app = route_app
    spec_paths = _load_openapi_paths()
    app_routes = _load_routes(app)

    missing_paths = sorted(path for path in app_routes if path not in spec_paths)
    missing_operations = sorted(
        (path, method) for path, methods in app_routes.items() if path in spec_paths for method in sorted(methods - spec_paths[path])
    )
    extra_paths = sorted(path for path in spec_paths if path not in app_routes)
    extra_operations = sorted(
        (path, method) for path, methods in spec_paths.items() if path in app_routes for method in sorted(methods - app_routes[path])
    )

    assert not missing_paths and not missing_operations and not extra_paths and not extra_operations, _format_failure(
        missing_paths,
        missing_operations,
        extra_paths,
        extra_operations,
    )


def test_openapi_operation_ids_match_view_funcs(route_app):
    app = route_app
    spec_operations, operation_ids, missing_operation_ids = _load_openapi_operations()
    route_endpoints = _load_route_endpoints(app)

    mismatches = sorted(
        (
            path,
            method,
            f"{expected}.{method.lower()}",
            spec_operations.get((path, method)),
        )
        for (path, method), expected in route_endpoints.items()
        if (path, method) in spec_operations and spec_operations[(path, method)] != f"{expected}.{method.lower()}"
    )
    duplicates = sorted(op_id for op_id, count in Counter(operation_ids).items() if count > 1)

    assert not mismatches and not duplicates and not missing_operation_ids, _format_operation_id_failure(
        mismatches,
        duplicates,
        missing_operation_ids,
    )


def _format_failure(
    missing_paths: list[str],
    missing_operations: list[tuple[str, str]],
    extra_paths: list[str],
    extra_operations: list[tuple[str, str]],
) -> str:
    lines = [
        "OpenAPI route coverage drift detected.",
        f"Missing paths: {len(missing_paths)}",
    ]
    if missing_paths:
        lines.extend(f"  - {path}" for path in missing_paths)
    lines.append(f"Missing operations: {len(missing_operations)}")
    if missing_operations:
        lines.extend(f"  - {method} {path}" for path, method in missing_operations)
    lines.append(f"Extra paths: {len(extra_paths)}")
    if extra_paths:
        lines.extend(f"  - {path}" for path in extra_paths)
    lines.append(f"Extra operations: {len(extra_operations)}")
    if extra_operations:
        lines.extend(f"  - {method} {path}" for path, method in extra_operations)
    return "\n".join(lines)


def _format_operation_id_failure(
    mismatches: list[tuple[str, str, str, str | None]],
    duplicates: list[str],
    missing_operation_ids: list[tuple[str, str]],
) -> str:
    lines = [
        "OpenAPI operationId drift detected.",
        f"OperationId mismatches: {len(mismatches)}",
    ]
    if mismatches:
        lines.extend(f"  - {method} {path}: expected {expected}, got {actual}" for path, method, expected, actual in mismatches)
    lines.append(f"Duplicate operationIds: {len(duplicates)}")
    if duplicates:
        lines.extend(f"  - {operation_id}" for operation_id in duplicates)
    lines.append(f"Missing operationIds: {len(missing_operation_ids)}")
    if missing_operation_ids:
        lines.extend(f"  - {method} {path}" for path, method in missing_operation_ids)
    return "\n".join(lines)


def test_declared_operation_contracts_are_executable(route_app):
    prefix = f"{Config.APPLICATION_ROOT}api"
    found = set()
    for rule in route_app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        relative = (
            rule.rule.removeprefix(prefix)
            if rule.rule.startswith(f"{prefix}/")
            else "/" + rule.rule.removeprefix(route_app.config["APPLICATION_ROOT"])
        )
        path = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", relative)
        view = route_app.view_functions[rule.endpoint]
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            operation = find_operation(method, path)
            assert operation is not None, f"Missing executable contract: {method} {rule.rule}"
            handler = getattr(getattr(view, "view_class", None), method.lower(), view)
            assert getattr(handler, "api_request_validated", False), (method, rule.rule)
            operation.query.model_json_schema()
            assert set(operation.parameters.model_fields) == set(re.findall(r"\{(\w+)\}", operation.path))
            operation.parameters.model_json_schema()
            operation.headers.model_json_schema()
            if operation.uploads is not None:
                operation.uploads.model_json_schema()
            for adapter in operation.alternate_bodies.values():
                adapter.json_schema()
            if operation.body is not None:
                operation.body.json_schema()
            for response in operation.responses.values():
                if response.body is not None:
                    response.body.json_schema()
                if response.json_body is not None:
                    response.json_body.json_schema()
            found.add((operation.method, operation.path))
    assert found == {(operation.method, operation.path) for operation in OPERATIONS}
