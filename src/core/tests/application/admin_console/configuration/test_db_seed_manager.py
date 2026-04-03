from __future__ import annotations


def test_pre_seed_manual_source_runs_before_later_failures(monkeypatch):
    from core.managers import db_seed_manager

    calls: list[str] = []

    def record(name: str):
        def _step():
            calls.append(name)

        return _step

    def fail_report_items():
        calls.append("report_items")
        raise RuntimeError("boom")

    monkeypatch.setattr(db_seed_manager, "pre_seed_permissions", record("permissions"))
    monkeypatch.setattr(db_seed_manager, "pre_seed_source_groups", record("source_groups"))
    monkeypatch.setattr(db_seed_manager, "pre_seed_manual_source", record("manual_source"))
    monkeypatch.setattr(db_seed_manager, "pre_seed_roles", record("roles"))
    monkeypatch.setattr(db_seed_manager, "pre_seed_default_user", record("default_user"))
    monkeypatch.setattr(db_seed_manager, "pre_seed_attributes", record("attributes"))
    monkeypatch.setattr(db_seed_manager, "pre_seed_report_items", fail_report_items)
    monkeypatch.setattr(db_seed_manager, "sync_presenter_templates", record("templates"))
    monkeypatch.setattr(db_seed_manager, "pre_seed_workers", record("workers"))
    monkeypatch.setattr(db_seed_manager, "pre_seed_assets", record("assets"))

    db_seed_manager.pre_seed()

    assert calls[:6] == [
        "permissions",
        "source_groups",
        "manual_source",
        "roles",
        "default_user",
        "attributes",
    ]
    assert "report_items" in calls
    assert calls.index("manual_source") < calls.index("report_items")
