from pathlib import Path


def test_misp_timeout_migration_targets_invalid_instance_values(app):
    migration_path = Path(app.root_path).parent / "migrations" / "20260817_01_K7x2m-remove-invalid-misp-request-timeouts.py"
    migration_source = migration_path.read_text(encoding="utf-8")

    assert "parameter.value <> ''" in migration_source
    assert "parameter.value ~ '^[[:space:]]*[+]?[0-9]+[[:space:]]*$'" in migration_source
    assert "parameter.value ~ '[1-9]'" in migration_source
    assert "connector.type = 'MISP_CONNECTOR'" in migration_source
    assert "osint_source.type = 'MISP_COLLECTOR'" in migration_source
    assert "worker_parameter_value" in migration_source
