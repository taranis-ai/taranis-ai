"""Attach scoped SQL evidence and outcomes to PostgreSQL correctness runs."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from tests.performance.orm.instrumentation import Observations


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    output = Path(os.environ["ORM_ARTIFACT_DIR"]) / "correctness-discovery"
    output.mkdir(exist_ok=True)
    key = hashlib.sha256(item.nodeid.encode()).hexdigest()[:20]
    with Observations(stacks=True) as observations:
        yield
    (output / f"{key}.json").write_text(json.dumps({"test": item.nodeid, **observations.as_dict()}, indent=2))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    result = yield
    report = result.get_result()
    output = Path(os.environ["ORM_ARTIFACT_DIR"]) / "correctness-discovery"
    output.mkdir(exist_ok=True)
    key = hashlib.sha256(item.nodeid.encode()).hexdigest()[:20]
    (output / f"{key}-{report.when}.result.json").write_text(
        json.dumps(
            {
                "test": item.nodeid,
                "phase": report.when,
                "outcome": report.outcome,
                "failure": report.longreprtext if report.failed else None,
            },
            indent=2,
        )
    )
