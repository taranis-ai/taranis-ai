import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError


def _load_migration():
    path = Path(__file__).parents[2] / "migrations" / "20260818_01_Wp4rM-worker-parameter-registry.py"
    spec = importlib.util.spec_from_file_location("worker_parameter_registry_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    with patch("yoyo.step", side_effect=lambda *args: args):
        spec.loader.exec_module(module)
    return module


class FakeCursor:
    def __init__(self, rows_by_table):
        self.rows_by_table = rows_by_table
        self.rows = []
        self.updates = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=None):
        compact = " ".join(query.split())
        if compact.startswith("SELECT owner.id"):
            table = compact.split(" FROM ", 1)[1].split(" ", 1)[0]
            self.rows = self.rows_by_table.get(table, [])
        elif compact.startswith("UPDATE "):
            self.updates.append((compact.split()[1], params))

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows_by_table):
        self.fake_cursor = FakeCursor(rows_by_table)

    def cursor(self):
        return self.fake_cursor


def test_migration_collapses_equal_duplicates_and_normalizes_disabled_data():
    migration = _load_migration()
    connection = FakeConnection(
        {
            "osint_source": [
                ("source-1", "RSS_COLLECTOR", False, "USER_AGENT", "agent"),
                ("source-1", "RSS_COLLECTOR", False, "USER_AGENT", "agent"),
                ("source-1", "RSS_COLLECTOR", False, "UNKNOWN", "drop-me"),
                ("source-1", "RSS_COLLECTOR", False, "USE_GLOBAL_PROXY", ""),
            ]
        }
    )

    migration._migrate_parameters(connection)

    assert connection.fake_cursor.updates == [("osint_source", ('{"USER_AGENT":"agent"}', "source-1"))]


def test_migration_aborts_on_conflicting_duplicates():
    migration = _load_migration()
    connection = FakeConnection(
        {
            "bot": [
                ("bot-1", "TAGGING_BOT", True, "ITEM_FILTER", "first"),
                ("bot-1", "TAGGING_BOT", True, "ITEM_FILTER", "second"),
            ]
        }
    )

    with pytest.raises(RuntimeError, match="Conflicting duplicate"):
        migration._migrate_parameters(connection)


def test_migration_aborts_when_active_owner_is_incomplete():
    migration = _load_migration()
    connection = FakeConnection({"osint_source": [("source-1", "RSS_COLLECTOR", True, "USER_AGENT", "agent")]})

    with pytest.raises(ValidationError):
        migration._migrate_parameters(connection)


def test_migration_converts_every_owner_table():
    migration = _load_migration()
    connection = FakeConnection(
        {
            "osint_source": [("source-1", "MANUAL_COLLECTOR", True, None, None)],
            "bot": [("bot-1", "IOC_BOT", True, "RUN_AFTER_COLLECTOR", "1")],
            "connector": [
                ("connector-1", "MISP_CONNECTOR", "URL", "https://misp.test"),
                ("connector-1", "MISP_CONNECTOR", "API_KEY", "secret"),
                ("connector-1", "MISP_CONNECTOR", "ORGANISATION_ID", "1"),
            ],
            "product_type": [("product-1", "STIX_PRESENTER", None, None)],
            "publisher_preset": [("publisher-1", "TARANIS_PUBLISHER", None, None)],
        }
    )

    migration._migrate_parameters(connection)

    assert connection.fake_cursor.updates == [
        ("osint_source", ("{}", "source-1")),
        ("bot", ('{"RUN_AFTER_COLLECTOR":"true"}', "bot-1")),
        (
            "connector",
            ('{"API_KEY":"secret","ORGANISATION_ID":"1","URL":"https://misp.test"}', "connector-1"),
        ),
        ("product_type", ("{}", "product-1")),
        ("publisher_preset", ("{}", "publisher-1")),
    ]
