"""Refresh the maintained OpenAPI and route inventory from executable contracts.

Run from src/core: uv run python ../../dev/update_api_contracts.py
"""

import re
from pathlib import Path

import yaml
from flask import Flask
from models.api import ERROR_RESPONSES
from models.api_operations import OPERATIONS
from pydantic import TypeAdapter

from core.config import Config
from core.managers.api_manager import initialize


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "src/core/core/static/openapi3_1.yaml"


def main():
    app = Flask(__name__)
    app.config.from_object(Config)
    initialize(app)
    endpoints = {}
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        path = rule.rule.removeprefix(f"{Config.APPLICATION_ROOT}api")
        path = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", path)
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            endpoints[(method, path)] = rule.endpoint
    assert set(endpoints) == {(op.method, op.path) for op in OPERATIONS}
    adapters = {}
    for index, op in enumerate(OPERATIONS):
        for location in ("query", "parameters", "headers", "uploads"):
            model = getattr(op, location)
            if model:
                adapters[f"{index}:{location}"] = TypeAdapter(model)
        if op.body:
            adapters[f"{index}:body"] = op.body
        for mime, adapter in op.alternate_bodies.items():
            adapters[f"{index}:{mime}"] = adapter
        for status, response in (ERROR_RESPONSES | op.responses).items():
            if response.body:
                adapters[f"{index}:response:{status}"] = response.body
            if response.json_body:
                adapters[f"{index}:json:{status}"] = response.json_body
    schemas, definitions = TypeAdapter.json_schemas(
        [(key, "validation", adapter) for key, adapter in adapters.items()], ref_template="#/components/schemas/{model}"
    )
    spec = yaml.safe_load(SPEC.read_text())
    old_paths = spec["paths"]
    spec["paths"] = {}
    spec.setdefault("components", {})["schemas"] = definitions.get("$defs", {})
    spec["components"]["responses"] = {}

    def schema(key):
        return schemas[(key, "validation")]

    def resolve(value):
        if "$ref" in value:
            return spec["components"]["schemas"][value["$ref"].rsplit("/", 1)[1]]
        return value

    rows = []
    for index, op in enumerate(OPERATIONS):
        old = old_paths.get(op.path, {}).get(op.method.lower(), {})
        operation = {key: value for key, value in old.items() if key not in {"parameters", "requestBody", "responses"}}
        operation["operationId"] = f"{endpoints[(op.method, op.path)]}.{op.method.lower()}"
        if not op.api_path or op.path in {"/", "/isalive", "/health", "/auth/login", "/auth/method"} or op.path.startswith("/static/"):
            operation["security"] = []
        if not op.api_path:
            operation["servers"] = [{"url": Config.APPLICATION_ROOT.rstrip("/") or "/"}]
        parameters = []
        for location, wire in (("parameters", "path"), ("query", "query"), ("headers", "header")):
            fields = resolve(schema(f"{index}:{location}"))
            for name, definition in fields.get("properties", {}).items():
                parameter = {"in": wire, "name": name, "required": wire == "path" or name in fields.get("required", []), "schema": definition}
                if wire == "query" and name in op.repeated_query:
                    parameter.update(style="form", explode=True)
                parameters.append(parameter)
        if parameters:
            operation["parameters"] = parameters
        content = {}
        if op.body:
            for mime in op.request_media_types:
                content[mime] = {"schema": schema(f"{index}:{mime}" if mime in op.alternate_bodies else f"{index}:body")}
        if op.uploads:
            fields = resolve(schema(f"{index}:uploads"))
            upload_schema = {
                "type": "object",
                "properties": {name: {"type": "string", "format": "binary"} for name in fields.get("properties", {})},
                "required": fields.get("required", []),
            }
            content["multipart/form-data"] = {"schema": upload_schema}
        if content:
            operation["requestBody"] = {"required": True, "content": content}
        responses = {}
        for status, response in (ERROR_RESPONSES | op.responses).items():
            entry = {"description": old.get("responses", {}).get(str(status), {}).get("description", "Validated response")}
            if response.body:
                entry["content"] = {
                    response.media_type or "*/*": {
                        "schema": {"type": "string", "format": "binary"} if response.download else schema(f"{index}:response:{status}")
                    }
                }
                if response.json_body:
                    entry["content"]["application/json"] = {"schema": schema(f"{index}:json:{status}")}
            if status not in op.responses:
                name = f"Error{status}"
                spec["components"]["responses"][name] = entry
                entry = {"$ref": f"#/components/responses/{name}"}
            responses[str(status)] = entry
        operation["responses"] = responses
        spec["paths"].setdefault(op.path, {})[op.method.lower()] = operation
        body = schema(f"{index}:body").get("$ref", "union").rsplit("/", 1)[-1] if op.body else "none"
        output = (
            ", ".join(
                f"{status}: {schema(f'{index}:response:{status}').get('$ref', 'download metadata' if contract.download else 'union').rsplit('/', 1)[-1] if contract.body else 'none'}"
                for status, contract in op.responses.items()
            )
            or "errors only"
        )
        rows.append(
            f"| `{op.method} {op.path}` | `{endpoints[(op.method, op.path)]}` | {body} | {op.query.__name__} | {op.parameters.__name__} | {op.headers.__name__} | {output} | yes | enforced |"
        )
    # Framework static files are the sole explicit exclusion.
    rows.append("| `GET /static/<path:filename>` | `static` | none | none | filename | none | file | n/a | framework static |")

    def numeric_discriminators(value):
        if isinstance(value, dict):
            if value.get("discriminator", {}).get("propertyName") == "version":
                # OpenAPI discriminators require strings; versioned transfers use integer consts.
                value.pop("discriminator")
            for item in value.values():
                numeric_discriminators(item)
        elif isinstance(value, list):
            for item in value:
                numeric_discriminators(item)

    numeric_discriminators(spec)
    SPEC.write_text(yaml.safe_dump(spec, sort_keys=False, allow_unicode=True, width=140))
    report = ROOT / "docs/api-contract-review.md"
    previous = report.read_text()
    notes = previous[previous.index("## Frontend") :] if "## Frontend" in previous else ""
    report.write_text(
        f"""# API contract review

The {len(OPERATIONS)} Core application operations below have executable request, path, query, application-header and response contracts. Both configuration aliases and public reports are included. Authentication executes before request validation; the response boundary also validates authentication failures. Framework HEAD uses GET contracts; generated OPTIONS and Flask static files are explicit framework exclusions. Downloads validate metadata without consuming file iterators. Historical revision snapshots and provider parameter maps remain intentional extension maps.

Regenerate this table and OpenAPI after route changes with `cd src/core && uv run python ../../dev/update_api_contracts.py`. The mandatory route test checks completeness, handler wiring and resolvable schemas under both application prefixes.

| Operation | Endpoint | Request body | Query | Path | Application headers | Explicit responses | OpenAPI | Boundary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
"""
        + "\n".join(sorted(rows))
        + "\n\n"
        + notes
    )
    print(f"Updated {len(OPERATIONS)} operations")


if __name__ == "__main__":
    main()
