from unittest.mock import Mock

import core


def test_initialize_managers_syncs_templates_before_database_setup(monkeypatch):
    app = Mock()
    call_order: list[str] = []

    monkeypatch.setattr(core.sentry_manager, "initialize", lambda: call_order.append("sentry"))
    monkeypatch.setattr(core.data_manager, "initialize", lambda initial_setup: call_order.append(f"data:{initial_setup}"))
    monkeypatch.setattr(core.db_manager, "initialize", lambda app, initial_setup: call_order.append(f"db:{initial_setup}"))
    monkeypatch.setattr(core.queue_manager, "initialize", lambda app, initial_setup: call_order.append(f"queue:{initial_setup}"))
    monkeypatch.setattr(core.auth_manager, "initialize", lambda app: call_order.append("auth"))
    monkeypatch.setattr(core.api_manager, "initialize", lambda app: call_order.append("api"))
    monkeypatch.setattr(core.schedule_manager, "initialize", lambda: call_order.append("schedule"))
    monkeypatch.setattr(core.queue_manager, "queue_manager", Mock(post_init=lambda: call_order.append("post_init")), raising=False)

    core.initialize_managers(app, True)

    assert call_order.index("data:True") < call_order.index("db:True")


def test_initilize_database_syncs_templates_before_database_setup(monkeypatch):
    app = Mock()
    call_order: list[str] = []

    monkeypatch.setattr(core.data_manager, "initialize", lambda initial_setup: call_order.append(f"data:{initial_setup}"))
    monkeypatch.setattr(core.db_manager, "initialize", lambda app, initial_setup: call_order.append(f"db:{initial_setup}"))
    monkeypatch.setattr(core.queue_manager, "initialize", lambda app, initial_setup: call_order.append(f"queue:{initial_setup}"))
    monkeypatch.setattr(core.schedule_manager, "initialize", lambda: call_order.append("schedule"))
    monkeypatch.setattr(core.queue_manager, "queue_manager", Mock(post_init=lambda: call_order.append("post_init")), raising=False)

    core.initilize_database(app)

    assert call_order.index("data:True") < call_order.index("db:True")
