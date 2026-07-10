from pathlib import Path


def test_unique_bot_type_migration_rejects_duplicates_without_deleting_bots(app):
    migration_path = Path(app.root_path).parent / "migrations" / "20260708_01_5wQmV-unique-bot-type.py"
    migration_source = migration_path.read_text(encoding="utf-8")

    assert "RAISE EXCEPTION" in migration_source
    assert "duplicate types exist" in migration_source
    assert "DELETE FROM bot" not in migration_source
