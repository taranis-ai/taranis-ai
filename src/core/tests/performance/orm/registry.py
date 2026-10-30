"""Reconcile source declarations with runtime registrations and measured scenarios."""

import ast
import hashlib
import inspect
import json
import textwrap
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[3] / "core"
BASELINE = Path(__file__).parent / "baseline"


def source_inventory() -> dict[str, dict]:
    """Keep declarations and call sites, including methods not yet classified as reachable."""
    declarations = {}
    call_sites = {}
    for root in (CORE_ROOT, CORE_ROOT.parents[1] / "worker" / "worker"):
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text())
            module = ".".join(path.relative_to(root.parent).with_suffix("").parts)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = ast.unparse(node.func)
                    call_sites.setdefault(name.split(".")[-1], []).append(f"{module}:{node.lineno}")
                    if root == CORE_ROOT and name.endswith("add_url_rule"):
                        key = f"{module}.registration:{ast.unparse(node)}"
                        declarations[key] = {"kind": "route_registration", "source": f"{module}:{node.lineno}"}
            if root != CORE_ROOT:
                continue
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    declarations[f"{module}.{node.name}"] = _declaration(module, node)
                elif isinstance(node, ast.ClassDef):
                    declarations[f"{module}.{node.name}"] = {
                        "kind": "class",
                        "source": f"{module}:{node.lineno}",
                        "fingerprint": _fingerprint(node),
                    }
                    for member in node.body:
                        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            declarations[f"{module}.{node.name}.{member.name}"] = _declaration(module, member)
                        elif (
                            isinstance(member, ast.AnnAssign)
                            and isinstance(member.value, ast.Call)
                            and ast.unparse(member.value.func).endswith("relationship")
                        ):
                            key = f"{module}.{node.name}.{ast.unparse(member.target)}"
                            declarations[key] = {
                                "kind": "relationship",
                                "source": f"{module}:{member.lineno}",
                                "fingerprint": _fingerprint(member),
                            }
                        elif (
                            isinstance(member, ast.Assign)
                            and isinstance(member.value, ast.Call)
                            and ast.unparse(member.value.func).endswith("relationship")
                        ):
                            for target in member.targets:
                                key = f"{module}.{node.name}.{ast.unparse(target)}"
                                declarations[key] = {
                                    "kind": "relationship",
                                    "source": f"{module}:{member.lineno}",
                                    "fingerprint": _fingerprint(member),
                                }
    for key, entry in declarations.items():
        entry["call_sites"] = call_sites.get(key.split(".")[-1], [])
    return declarations


def _declaration(module, node):
    return {
        "kind": "serializer" if node.name.startswith("to_") else "callable",
        "source": f"{module}:{node.lineno}",
        "decorators": [ast.unparse(item) for item in node.decorator_list],
        "calls": sorted({ast.unparse(item.func) for item in ast.walk(node) if isinstance(item, ast.Call)}),
        "transactions": sorted(
            {
                item.func.attr
                for item in ast.walk(node)
                if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute) and item.func.attr in {"commit", "flush", "rollback"}
            }
        ),
        "fingerprint": _fingerprint(node),
    }


def _fingerprint(node):
    source = ast.dump(node, annotate_fields=True, include_attributes=False)
    return hashlib.sha256(source.encode()).hexdigest()


def inventory_signature() -> dict[str, str]:
    """Database-free guard against unreviewed declaration and call-path changes."""
    return {name: entry.get("fingerprint") or entry["kind"] for name, entry in source_inventory().items()}


def runtime_inventory(app) -> dict:
    from core.managers.db_manager import db

    routes = []
    for rule in sorted(app.url_map.iter_rules(), key=lambda item: item.rule):
        view = app.view_functions[rule.endpoint]
        for method in sorted(rule.methods):
            handler = getattr(view.view_class, method.lower(), None) if hasattr(view, "view_class") else view
            if handler is None:
                # Flask implements HEAD/OPTIONS on behalf of the registered view.
                handler = getattr(view.view_class, "get", view) if hasattr(view, "view_class") else view
            unwrapped = inspect.unwrap(handler)
            routes.append(
                {
                    "id": f"{method} {rule.rule}",
                    "rule": rule.rule,
                    "method": method,
                    "endpoint": rule.endpoint,
                    "handler": f"{unwrapped.__module__}.{unwrapped.__qualname__}",
                    "automatic": method == "OPTIONS" and rule.provide_automatic_options or method == "HEAD",
                    "authorization": authorization(handler)
                    + [
                        f"before_request:{hook.__module__}.{hook.__qualname__}:{authorization(hook)}"
                        for scope in (None, rule.endpoint.rpartition(".")[0])
                        for hook in app.before_request_funcs.get(scope, [])
                    ],
                    "arguments": sorted(rule.arguments),
                }
            )
    mappers = []
    for mapper in sorted(db.Model.registry.mappers, key=lambda item: item.class_.__name__):
        mappers.append(
            {
                "model": f"{mapper.class_.__module__}.{mapper.class_.__qualname__}",
                "table": mapper.local_table.name,
                "relationships": [str(item) for item in mapper.relationships],
            }
        )
    from core.cli import main
    from core.managers.queue_manager import QueueManager

    return {
        "routes": routes,
        "mappers": mappers,
        "declarations": source_inventory(),
        "cli": {name: f"{command.callback.__module__}.{command.callback.__qualname__}" for name, command in main.commands.items()},
        "housekeeping": {name: spec.func_path for name, spec in QueueManager._get_housekeeping_cron_specs().items()},
    }


def authorization(handler) -> list[str]:
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(inspect.unwrap(handler))))
        decorators = next((node.decorator_list for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))), [])
    except (SyntaxError, OSError, TypeError):
        return ["unknown"]
    return [ast.unparse(item) for item in decorators if "auth" in ast.unparse(item) or "api_key" in ast.unparse(item)] or ["public"]


def load_manifest():
    return json.loads((BASELINE / "manifest-v1.json").read_text())


def callable_id(code):
    if not hasattr(code, "co_filename"):
        return None
    try:
        module = ".".join(Path(code.co_filename).relative_to(CORE_ROOT).with_suffix("").parts)
    except ValueError:
        return None
    return f"core.{module}.{code.co_qualname}"


def reconcile_coverage(inventory, specifications, aggregates, reached, manifest):
    exclusions = json.loads((BASELINE / "exclusions-v1.json").read_text())
    by_route = {}
    for route in inventory["routes"]:
        matches = [case for case in specifications if f"{case.method} {case.rule}" == route["id"] and case.variant == "normal"]
        by_route[route["id"]] = matches
    coverage = []
    for route in inventory["routes"]:
        matches = by_route[route["id"]]
        aliases = []
        if not matches and not route["automatic"]:
            for candidate in inventory["routes"]:
                if (candidate["handler"], candidate["method"], candidate.get("arguments"), candidate["authorization"]) == (
                    route["handler"],
                    route["method"],
                    route.get("arguments"),
                    route["authorization"],
                ) and by_route[candidate["id"]]:
                    matches.extend(by_route[candidate["id"]])
                    aliases.append(candidate["id"])
        case_ids = {case.id for case in matches}
        observations = [item for item in aggregates if item["scenario"] in case_ids and item["successful"] >= manifest["rounds"]]
        profiles = {item["profile"] for item in observations}
        status = "measured" if {"normal", "stress_roots", "stress_children"}.issubset(profiles) else "pending"
        evidence = exclusions.get(route["id"])
        if route["automatic"]:
            evidence = {"reason": "Flask-generated HEAD/OPTIONS", "source": route["handler"]}
        if evidence:
            status = "excluded"
        coverage.append({**route, "status": status, "scenarios": sorted(case_ids), "aliases": aliases, "exclusion_evidence": evidence})
    methods = []
    for name, declaration in inventory["declarations"].items():
        if declaration["kind"] not in {"callable", "serializer", "relationship"}:
            continue
        if not name.startswith("core.model.") and not declaration.get("transactions"):
            continue
        evidence = exclusions.get(name)
        matches = reached.get(name, [])
        methods.append(
            {
                "id": name,
                **declaration,
                "scenarios": matches,
                "status": "excluded" if evidence else "measured" if matches else "pending",
                "exclusion_evidence": evidence,
            }
        )
    scenario_by_id = {case.id: case for case in specifications}
    scenario_aggregates = {}
    for item in aggregates:
        if item["successful"] >= manifest["rounds"]:
            scenario_aggregates.setdefault(item["scenario"], set()).add(item["profile"])

    def entry_status(case_ids):
        profiles = set().union(*(scenario_aggregates.get(case_id, set()) for case_id in case_ids))
        return "measured" if {"normal", "stress_roots", "stress_children"}.issubset(profiles) else "pending"

    entrypoints = []
    cli_scenarios = {
        "set-password": "cli.password",
        "set-roles": "cli.roles",
    }
    for name, callback in sorted(inventory.get("cli", {}).items()):
        case_id = cli_scenarios.get(name)
        entrypoints.append(
            {
                "id": f"cli:{name}",
                "kind": "cli",
                "handler": callback,
                "scenarios": [case_id] if case_id in scenario_by_id else [],
                "status": entry_status([case_id]) if case_id in scenario_by_id else "pending",
            }
        )
    housekeeping_scenarios = {
        "cleanup_token_blacklist": "housekeeping.cleanup-token-blacklist",
        "cleanup_task_history": "worker.cleanup",
    }
    for name, callback in sorted(inventory.get("housekeeping", {}).items()):
        case_id = housekeeping_scenarios.get(name)
        entrypoints.append(
            {
                "id": f"housekeeping:{name}",
                "kind": "housekeeping",
                "handler": callback,
                "scenarios": [case_id] if case_id in scenario_by_id else [],
                "status": entry_status([case_id]) if case_id in scenario_by_id else "pending",
            }
        )
    startup_case = "startup.existing"
    entrypoints.append(
        {
            "id": "startup:create_app",
            "kind": "startup",
            "handler": "core.create_app",
            "scenarios": [startup_case] if startup_case in scenario_by_id else [],
            "status": entry_status([startup_case]) if startup_case in scenario_by_id else "pending",
        }
    )
    return coverage, methods, entrypoints
