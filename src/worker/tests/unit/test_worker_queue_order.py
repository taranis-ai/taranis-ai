import worker


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
