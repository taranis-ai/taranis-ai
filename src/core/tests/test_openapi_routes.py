import re
from collections import Counter, defaultdict


IGNORED_PATHS = {"/"}


def _canonical_path(path: str) -> str:
    path = path.rstrip("/") if path != "/" else path
    path = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", path)
    return re.sub(r"\{[^}]+\}", "{}", path)


def _load_openapi_paths(app) -> dict[str, set[str]]:
    spec = app.api_doc

    paths: dict[str, set[str]] = defaultdict(set)
    for path, operations in spec["paths"].items():
        canonical = _canonical_path(path)
        for method in operations:
            if method == "parameters":
                continue
            paths[canonical].add(method.upper())

    return paths


def _load_openapi_operations(app) -> tuple[dict[tuple[str, str], str], list[str], list[tuple[str, str]]]:
    spec = app.api_doc

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
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api/"):
            continue
        if rule.rule.startswith("/api/static/"):
            continue
        if rule.rule.startswith("/api/admin/"):
            continue
        canonical = _canonical_path(rule.rule.removeprefix("/api"))
        if canonical in IGNORED_PATHS:
            continue

        for method in rule.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes[canonical].add(method.upper())

    return routes


def _load_route_endpoints(app) -> dict[tuple[str, str], str]:
    endpoints: dict[tuple[str, str], str] = {}
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api/"):
            continue
        if rule.rule.startswith("/api/static/"):
            continue
        if rule.rule.startswith("/api/admin/"):
            continue
        canonical = _canonical_path(rule.rule.removeprefix("/api"))
        if canonical in IGNORED_PATHS:
            continue

        for method in rule.methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            endpoint = rule.endpoint
            if rule.endpoint.startswith("tasks."):
                endpoint = endpoint.removesuffix(f"_{method.lower()}")
            endpoints[(canonical, method.upper())] = endpoint

    return endpoints


def test_openapi_covers_app_routes(app):
    spec_paths = _load_openapi_paths(app)
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


def test_openapi_operation_ids_match_view_funcs(app):
    spec_operations, operation_ids, missing_operation_ids = _load_openapi_operations(app)
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


def test_task_openapi_uses_shared_models_and_pending_response(app):
    paths = app.api_doc["paths"]
    submission = paths["/tasks"]["post"]
    retrieval = paths["/tasks/{task_id}"]["get"]

    assert submission["requestBody"]["content"]["application/json"]["schema"]["$ref"] == "#/components/schemas/TaskSubmission"
    assert app.api_doc["components"]["schemas"]["TaskSubmission"]["oneOf"] == [{"required": ["id"]}, {"required": ["task_id"]}]
    assert submission["responses"]["200"]["content"]["application/json"]["schema"]["$ref"] == "#/components/schemas/TaskResponse"
    assert "400" in submission["responses"] and "422" not in submission["responses"]
    assert submission["security"] == [{"APIKey": []}]
    assert paths["/tasks/user"]["get"]["security"] == [{"UserAuth": []}]
    assert retrieval["responses"]["404"]["content"]["application/json"]["schema"]["$ref"] == "#/components/schemas/MissingTaskResponse"

    assert (
        paths["/tasks"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/TaskHistoryResponse"
    )
    assert (
        paths["/tasks"]["delete"]["responses"]["400"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/TaskErrorResponse"
    )
    assert (
        paths["/tasks/{task_id}"]["delete"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/TaskDeleteResponse"
    )
    assert (
        paths["/tasks/runs"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/UserTaskList"
    )
    assert (
        paths["/tasks/user"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/UserTaskList"
    )
    job_ids = next(parameter for parameter in paths["/tasks/runs"]["get"]["parameters"] if parameter["name"] == "job_ids")
    assert job_ids["schema"]["anyOf"][0]["type"] == "array"
    assert job_ids.get("style", "form") == "form" and job_ids.get("explode", True) is True


def test_task_auth_runs_before_validation_and_dispatch(app, api_header, auth_header_user_permissions):
    client = app.test_client(use_cookies=False)
    assert client.get("/api/tasks?limit=invalid").status_code == 401
    assert client.get("/api/tasks?limit=invalid", headers=api_header).status_code == 400
    assert client.delete("/api/tasks/user", headers=auth_header_user_permissions).status_code == 403
    response = client.delete("/api/tasks", headers=api_header)
    assert response.status_code == 400
    assert response.get_json() == {"error": "No task_id provided"}
    assert client.options("/api/tasks").status_code == 200


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
