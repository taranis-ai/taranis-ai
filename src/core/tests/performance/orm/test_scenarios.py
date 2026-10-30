"""Manual PostgreSQL measurements of declared production workflows."""

import cProfile
import json
import pstats
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack
from unittest.mock import patch

import pytest

from tests.performance.orm.instrumentation import Observations, capture_plans, postgres_connection, reset_server_statistics, server_statistics
from tests.performance.orm.registry import callable_id
from tests.performance.orm.scenarios import invocation


pytestmark = pytest.mark.orm_performance


def test_scenario(prepared_dataset, scenario, profile, measurement_contract, pytestconfig, request):
    environment = prepared_dataset
    if any(not environment.dataset.ids.get(key) for key in scenario.requires):
        pytest.skip("Dataset does not contain the scenario's required entity")
    phase = pytestconfig.getoption("--orm-pass")
    folder = environment.output / profile / scenario.id / phase
    folder.mkdir(parents=True, exist_ok=True)
    samples = []
    active = {}

    def setup():
        from core.managers.db_manager import db

        active.clear()
        if scenario.changes_state:
            environment.dataset.restore()
        environment.app.extensions["rq"].redis.flushdb()
        integrations = ExitStack()
        active["integrations"] = integrations
        active["open"] = True
        if scenario.transport == "chat":
            from core.config import Config
            from tests.performance.orm.transports import chat_response

            integrations.enter_context(patch.object(Config, "CHAT_ENABLED", True))
            integrations.enter_context(patch("requests.Session.send", side_effect=chat_response))
        if scenario.id == "realtime.connect":
            from pydantic import SecretStr

            from core.config import Config

            integrations.enter_context(patch.object(Config, "REALTIME_ENABLED", True))
            integrations.enter_context(patch.object(Config, "CENTRIFUGO_CONNECT_PROXY_SECRET", SecretStr("profiling-only")))
        if scenario.id == "connectors.story-conflict-resolve":
            from core.model.story import Story
            from core.model.story_conflict import StoryConflict

            integrations.enter_context(patch.object(StoryConflict, "conflict_store", new={}))
            with environment.app.app_context():
                story = Story.get(environment.dataset.ids["story_id"])
                incoming_story = story.to_dict()
                incoming_story["title"] = "ORM incoming conflict title"
                existing_story = json.dumps(story.to_dict())
            StoryConflict.conflict_store[story.id] = StoryConflict(
                story_id=story.id,
                existing_story=existing_story,
                incoming_story=json.dumps(incoming_story),
            )
        if scenario.id.startswith("config.template-") or scenario.id == "config.admin-template-delete":
            from core.config import Config
            from core.managers.data_manager import save_template_content, sync_presenter_templates_to_data

            data_folder = tempfile.TemporaryDirectory(prefix="orm-template-")
            integrations.callback(data_folder.cleanup)
            integrations.enter_context(patch.object(Config, "DATA_FOLDER", data_folder.name))
            sync_presenter_templates_to_data()
            if scenario.id in {"config.template-delete", "config.admin-template-delete"}:
                save_template_content("profile.html", "<h1>ORM profile</h1>")
        if scenario.id == "settings.llm-endpoint-delete":
            from core.model.settings import Settings

            with environment.app.app_context():
                Settings.update({"settings": {"llm_chat_endpoint": ""}})
        with environment.app.app_context():
            db.session.remove()
        context = environment.app.app_context() if scenario.operation.startswith("serialize-") else None
        if context:
            context.push()
        active["context"] = context
        target = invocation(scenario, environment)
        with postgres_connection(environment.uri) as connection:
            reset_server_statistics(connection)
        observations = Observations(stacks=phase == "attribution") if phase != "control" else None
        active["observations"] = observations
        if observations:
            observations.__enter__()
        return (target,), {}

    def invoke(target):
        active["status"] = "failed"
        started = time.perf_counter()
        cpu_started = time.process_time()
        try:
            result = target()
            active["result"] = result
            active["status"] = "ok"
            return result
        finally:
            active["wall_seconds"] = time.perf_counter() - started
            active["cpu_seconds"] = time.process_time() - cpu_started

    def teardown(*args):
        observations = active.get("observations")
        if observations:
            observations.__exit__(None, None, None)
            if scenario.operation in {"startup", "cli-roles", "cli-password"}:
                for engine in observations.engines:
                    engine.dispose()
        statistics = None
        evidence_available = True
        try:
            with postgres_connection(environment.uri) as connection:
                statistics = server_statistics(connection)
        except Exception:
            evidence_available = False
        finally:
            if active.get("context"):
                active["context"].pop()
            active["integrations"].close()
            active["open"] = False
        result = active.pop("result", None)
        if hasattr(result, "get_data"):
            active["payload_bytes"] = len(result.get_data())
            payload = result.get_json(silent=True)
            if isinstance(payload, dict):
                active["result_counts"] = {
                    key: value for key, value in payload.items() if key in {"count", "total_count", "updated"} and isinstance(value, int)
                }
                if isinstance(payload.get("counts"), dict):
                    active["result_counts"]["counts"] = {key: value for key, value in payload["counts"].items() if isinstance(value, int)}
        elif isinstance(result, (dict, list)):
            active["payload_bytes"] = len(json.dumps(result, default=str).encode())
        sample = {
            "scenario": scenario.id,
            "profile": profile,
            "phase": phase,
            "sample": len(samples),
            "warmup": phase in {"timing", "control"} and len(samples) < measurement_contract["warmups"],
            "status": active.get("status", "setup-failed"),
            "postgres_available": evidence_available,
            "wall_seconds": active.get("wall_seconds"),
            "cpu_seconds": active.get("cpu_seconds"),
            "payload_bytes": active.get("payload_bytes"),
            "result_counts": active.get("result_counts"),
            "postgres": statistics,
            "sqlalchemy": observations.as_dict() if observations else None,
        }
        samples.append(sample)
        (folder / f"sample-{len(samples):03d}.json").write_text(json.dumps(sample, indent=2))
        if not evidence_available:
            raise RuntimeError("PostgreSQL evidence collection failed; partial observations were retained")
        if observations and phase == "attribution":
            (folder / "plans.json").write_text(json.dumps(capture_plans(environment.uri, observations.explain_candidates), indent=2))

    try:
        if phase in {"timing", "control"}:
            benchmark = request.getfixturevalue("benchmark")
            benchmark.extra_info.update(scenario=scenario.id, profile=profile, phase=phase, variant=scenario.variant)
            benchmark.pedantic(
                invoke, setup=setup, teardown=teardown, rounds=measurement_contract["rounds"], warmup_rounds=measurement_contract["warmups"]
            )
        else:
            (target,), _ = setup()
            if phase in {"python", "attribution"}:
                profiler = cProfile.Profile()
                try:
                    profiler.runcall(invoke, target)
                finally:
                    profiler.dump_stats(str(folder / "calls.pstats"))
                    with (folder / "calls.txt").open("w") as output:
                        pstats.Stats(profiler, stream=output).sort_stats("cumulative").print_stats()
                    reached = sorted({identity for entry in profiler.getstats() if (identity := callable_id(entry.code))})
                    (folder / "reached.json").write_text(json.dumps(reached, indent=2))
            elif phase == "allocation":
                import memray

                with memray.Tracker(str(folder / "allocations.bin"), trace_python_allocators=True):
                    invoke(target)
            teardown()
            if phase == "allocation":
                with (folder / "report.log").open("w") as log:
                    subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "memray",
                            "flamegraph",
                            "--output",
                            str(folder / "allocations.html"),
                            str(folder / "allocations.bin"),
                        ],
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        check=True,
                    )
    finally:
        if active.get("open"):
            # Failed invocations retain their observations and release listeners as well.
            teardown()
