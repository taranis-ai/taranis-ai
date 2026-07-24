import pytest
from pydantic import ValidationError

import worker
from worker.config import WORKER_TYPE_PRIORITIES, Settings


def test_worker_types_default_to_priority_order():
    assert Settings.model_fields["WORKER_TYPES"].default == list(WORKER_TYPE_PRIORITIES)


def test_worker_types_reject_unknown_values():
    with pytest.raises(ValidationError, match="Unknown worker types: Unknown"):
        Settings(WORKER_TYPES=["Unknown"])


def test_get_queues_uses_default_priority_order(monkeypatch):
    monkeypatch.setattr(
        worker.Config,
        "WORKER_TYPES",
        ["Collectors", "Bots", "Misc", "Connectors", "Publishers", "Presenters"],
    )

    assert worker.get_queues() == ["presenters", "publishers", "connectors", "misc", "bots", "collectors"]


def test_get_queues_only_includes_enabled_worker_types(monkeypatch):
    monkeypatch.setattr(worker.Config, "WORKER_TYPES", ["Collectors"])

    assert worker.get_queues() == ["collectors"]
