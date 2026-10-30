"""Run production scenarios using pytest-benchmark and native profiler outputs."""

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import statistics
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from tests.performance.orm.instrumentation import postgres_connection
from tests.performance.orm.registry import inventory_signature, load_manifest, reconcile_coverage


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def verify_source(output):
    root = Path(__file__).resolve().parents[5]
    expected = json.loads((output / "source-files.json").read_text())
    changed = []
    for name, digest in expected.items():
        path = root / name
        if not path.is_file():
            changed.append(name)
            continue
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                changed.append(name)
    write_json(output / "source-state.json", {"unchanged": not changed, "changed": changed})


def report(output):
    """Join native samples to coverage; unresolved inventory always remains visible."""
    if (output / "source-files.json").exists():
        verify_source(output)
    inventory_file = output / "inventory.json"
    inventory = json.loads(inventory_file.read_text()) if inventory_file.exists() else {"routes": [], "declarations": {}}
    from tests.performance.orm.scenarios import Scenario, scenarios

    specification_file = output / "specifications.json"
    cases = [Scenario(**case) for case in json.loads(specification_file.read_text())] if specification_file.exists() else scenarios()
    specifications = {case.id: case for case in cases}
    environment_file = output / "environment.json"
    manifest = json.loads(environment_file.read_text())["fixture_manifest"] if environment_file.exists() else load_manifest()
    measured = {}
    for path in output.glob("*/*/timing/sample-*.json"):
        sample = json.loads(path.read_text())
        if sample.get("warmup"):
            continue
        measured.setdefault((sample["scenario"], sample["profile"]), []).append(sample)
    native_by_phase = {}
    for benchmark_file in output.glob("benchmark*.json"):
        payload = json.loads(benchmark_file.read_text())
        for item in payload.get("benchmarks", []):
            info = item.get("extra_info", {})
            phase = info.get("phase", "timing" if benchmark_file.name == "benchmark.json" else "unknown")
            key = (info.get("scenario"), info.get("profile"))
            native_by_phase.setdefault(phase, {})[key] = item["stats"]["data"]
    timings = native_by_phase.get("timing", {})
    controls = native_by_phase.get("control", {})
    aggregates = []
    for (scenario_id, profile), samples in sorted(measured.items()):
        values = sorted(timings.get((scenario_id, profile), []))
        counter_names = ("cursor_seconds", "flushes", "commits", "rollbacks", "relationship_loads", "column_refreshes", "failed_statements")
        counters = [sample.get("sqlalchemy", {}).get("counters", {}) for sample in samples]
        control_values = controls.get((scenario_id, profile), [])
        control_median = statistics.median(control_values) if control_values else None
        timing_median = statistics.median(values) if values else None
        aggregates.append(
            {
                "scenario": scenario_id,
                "profile": profile,
                "samples": len(samples),
                "successful": len(values),
                "minimum": min(values) if values else None,
                "median": timing_median,
                "control_median": control_median,
                "instrumentation_overhead_percent": (
                    (timing_median - control_median) / control_median * 100
                    if timing_median is not None and control_median is not None and control_median != 0
                    else None
                ),
                "p95": values[math.ceil(len(values) * 0.95) - 1] if values else None,
                "maximum": max(values) if values else None,
                "wall_seconds_median": statistics.median(item["wall_seconds"] for item in samples if item["wall_seconds"] is not None)
                if any(item["wall_seconds"] is not None for item in samples)
                else None,
                "cpu_seconds_median": statistics.median(item["cpu_seconds"] for item in samples if item["cpu_seconds"] is not None)
                if any(item["cpu_seconds"] is not None for item in samples)
                else None,
                "payload_bytes_median": statistics.median(item["payload_bytes"] for item in samples if item["payload_bytes"] is not None)
                if any(item["payload_bytes"] is not None for item in samples)
                else None,
                "statements_median": statistics.median(item["sqlalchemy"]["counters"].get("statements", 0) for item in samples),
                "sqlalchemy_medians": {name: statistics.median(counter.get(name, 0) for counter in counters) for name in counter_names},
                "postgres": {
                    "complete_samples": sum(sample.get("postgres_available", False) for sample in samples),
                    "query_shapes": sorted({row["query"] for sample in samples for row in sample.get("postgres", [])}),
                    "total_exec_ms_median": statistics.median(
                        sum(row["total_exec_time"] for row in sample.get("postgres", []))
                        for sample in samples
                        if sample.get("postgres_available", False)
                    )
                    if any(sample.get("postgres_available", False) for sample in samples)
                    else None,
                    "shared_blks_hit_median": statistics.median(
                        sum(row["shared_blks_hit"] for row in sample.get("postgres", []))
                        for sample in samples
                        if sample.get("postgres_available", False)
                    )
                    if any(sample.get("postgres_available", False) for sample in samples)
                    else None,
                    "shared_blks_read_median": statistics.median(
                        sum(row["shared_blks_read"] for row in sample.get("postgres", []))
                        for sample in samples
                        if sample.get("postgres_available", False)
                    )
                    if any(sample.get("postgres_available", False) for sample in samples)
                    else None,
                    "wal_bytes_median": statistics.median(
                        sum(row["wal_bytes"] for row in sample.get("postgres", []))
                        for sample in samples
                        if sample.get("postgres_available", False)
                    )
                    if any(sample.get("postgres_available", False) for sample in samples)
                    else None,
                },
            }
        )
    reached = {}
    for path in output.glob("*/*/attribution/reached.json"):
        case_id = path.parents[1].name
        if not any(item["scenario"] == case_id and item["successful"] >= manifest["rounds"] for item in aggregates):
            continue
        for name in json.loads(path.read_text()):
            reached.setdefault(name, []).append(case_id)
    for samples in measured.values():
        if len(samples) < manifest["rounds"]:
            continue
        for sample in samples:
            for name in sample["sqlalchemy"].get("relationships", []):
                reached.setdefault(name, []).append(sample["scenario"])
    reached = {name: sorted(set(case_ids)) for name, case_ids in reached.items()}
    coverage, methods, entrypoints = reconcile_coverage(inventory, specifications.values(), aggregates, reached, manifest)
    pending = [item["id"] for item in coverage if item["status"] == "pending"]
    pending_methods = [item["id"] for item in methods if item["status"] == "pending"]
    pending_entrypoints = [item["id"] for item in entrypoints if item["status"] == "pending"]
    source_file = output / "source-state.json"
    source_verified = source_file.exists() and json.loads(source_file.read_text())["unchanged"]
    summary = {
        "complete": not pending
        and not pending_methods
        and not pending_entrypoints
        and bool(coverage)
        and manifest["profile_status"] == "frozen"
        and source_verified,
        "source_verified": source_verified,
        "pending_routes": pending,
        "coverage": coverage,
        "aggregates": aggregates,
        "control_comparisons": [
            {
                "scenario": scenario,
                "profile": profile,
                "timing_median": statistics.median(timing_values),
                "control_median": statistics.median(control_values),
                "instrumentation_overhead_percent": (
                    (statistics.median(timing_values) - statistics.median(control_values)) / statistics.median(control_values) * 100
                ),
            }
            for (scenario, profile), timing_values in sorted(timings.items())
            if (control_values := controls.get((scenario, profile))) and statistics.median(control_values) != 0
        ],
        "production_snapshot": "supplied" if (output / "snapshot.json").exists() else "not supplied",
        "method_coverage": methods,
        "pending_methods": pending_methods,
        "entrypoints": entrypoints,
        "pending_entrypoints": pending_entrypoints,
    }
    write_json(output / "report.json", summary)
    artifacts = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name not in {"checksums.json", "report.json", "runner.log", "compose.log", "teardown.log"}:
            with path.open("rb") as stream:
                artifacts[str(path.relative_to(output))] = hashlib.file_digest(stream, "sha256").hexdigest()
    write_json(output / "checksums.json", artifacts)
    print(
        f"Report: {output / 'report.json'}; pending routes: {len(pending)}, "
        f"methods: {len(pending_methods)}, entrypoints: {len(pending_entrypoints)}"
    )
    return summary


def environment_metadata(uri):
    with postgres_connection(uri) as connection:
        settings = connection.execute(
            "SELECT name, setting FROM pg_settings WHERE name IN ('server_version', 'shared_buffers', 'work_mem', 'max_connections', 'default_statistics_target', 'track_io_timing', 'shared_preload_libraries')"
        ).fetchall()
    packages = {
        name: importlib.metadata.version(name)
        for name in (
            "SQLAlchemy",
            "Flask-SQLAlchemy",
            "psycopg",
            "pytest",
            "pytest-benchmark",
            "memray",
            "opentelemetry-instrumentation-sqlalchemy",
        )
    }
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "packages": packages,
        "postgresql": settings,
        "baseline_commit": os.environ.get("ORM_BASE_COMMIT"),
        "telemetry": {"sentry": False, "otlp": False},
        "application": {"debug": False, "queue_enabled": True, "realtime_enabled": False},
        "cache_state": {"orm_session": "fresh", "redis": "empty before each invocation", "postgres": "warmups; OS caches uncontrolled"},
        "fixture_manifest": load_manifest(),
        "command": sys.argv,
        "container_limits": {
            name: Path(path).read_text().strip() if Path(path).exists() else "unknown"
            for name, path in {"memory": "/sys/fs/cgroup/memory.max", "cpu": "/sys/fs/cgroup/cpu.max"}.items()
        },
        "storage_type": "unknown",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("inventory", "pilot", "baseline", "report", "correctness"))
    parser.add_argument("--output", type=Path, default=Path(os.environ.get("ORM_ARTIFACT_DIR", ".")))
    parser.add_argument("--profile", default="empty,single,normal,stress_roots,stress_children")
    parser.add_argument("--path", default="")
    parser.add_argument("--pass", dest="phase", choices=("timing", "python", "allocation", "attribution", "control"))
    args = parser.parse_args()
    output = args.output.resolve()
    if args.operation == "report":
        report(output)
        return 0
    if output != Path(os.environ["ORM_ARTIFACT_DIR"]).resolve():
        raise ValueError("Select a host output directory with ORM_ARTIFACT_DIR on dev/profile_orm.sh")
    output.mkdir(parents=True, exist_ok=True)
    os.environ["ORM_ARTIFACT_DIR"] = str(output)
    uri = os.environ.get("ORM_POSTGRES_URI", "")
    os.environ["SQLALCHEMY_DATABASE_URI"] = uri
    metadata_path = output / "environment.json"
    if metadata_path.exists():
        raise ValueError("Choose a new output directory; completed and partial raw runs are immutable")
    write_json(metadata_path, environment_metadata(uri))
    from tests.performance.orm.scenarios import scenarios

    write_json(output / "specifications.json", [asdict(case) for case in scenarios()])
    if args.operation == "inventory":
        from core import create_app
        from tests.performance.orm.instrumentation import Observations
        from tests.performance.orm.registry import runtime_inventory

        with Observations(stacks=True) as bootstrap:
            app = create_app()
        with app.app_context():
            write_json(output / "inventory.json", runtime_inventory(app))
        write_json(output / "bootstrap.json", bootstrap.as_dict())
        write_json(output / "declarations.json", inventory_signature())
        report(output)
        return 0
    if args.operation == "correctness":
        from sqlalchemy.engine import make_url

        with postgres_connection(uri, database="postgres") as connection:
            connection.execute("CREATE DATABASE orm_correctness")
            connection.execute("COMMENT ON DATABASE orm_correctness IS 'taranis-orm-disposable-v1'")
        url = make_url(uri).set(database="orm_correctness").render_as_string(hide_password=False)
        env = {**os.environ, "ORM_TEST_POSTGRES_URI": url}
        with (output / "correctness.log").open("w") as log:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-p",
                    "no:cacheprovider",
                    "-p",
                    "tests.performance.orm.discovery",
                    "--junitxml",
                    str(output / "correctness.xml"),
                ],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        write_json(output / "correctness-status.json", {"exit_code": result.returncode, "role": "discovery; not benchmark evidence"})
        return result.returncode
    os.environ["ORM_RUN"] = "1"
    arguments = [
        "tests/performance/orm/test_scenarios.py",
        "-p",
        "no:cacheprovider",
        "--orm-profile",
        args.profile,
        "--orm-path",
        args.path,
        "--tb=short",
    ]
    if args.operation == "pilot":
        arguments.append("--orm-pilot")
    phases = (
        [args.phase] if args.phase else ["timing", "attribution", "allocation", "control"] if args.operation == "baseline" else ["timing"]
    )
    status = 0
    for phase in phases:
        benchmark_name = "benchmark.json" if phase == "timing" else f"benchmark-{phase}.json"
        command = [
            sys.executable,
            "-m",
            "pytest",
            *arguments,
            "--orm-pass",
            phase,
            "--benchmark-json",
            str(output / benchmark_name),
            "--junitxml",
            str(output / f"scenarios-{phase}.xml"),
        ]
        if phase == "timing":
            command.append("tests/performance/orm/test_contracts.py")
        result = subprocess.run(command, check=False)
        status = status or result.returncode
    verify_source(output)
    report(output)
    if args.operation == "baseline":
        summary = json.loads((output / "report.json").read_text())
        if not summary["complete"]:
            print("Baseline incomplete: unresolved route/method/scenario coverage remains.")
            return status or 2
    return status


if __name__ == "__main__":
    raise SystemExit(main())
