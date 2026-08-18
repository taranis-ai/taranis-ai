def test_config_api_masks_and_explicitly_reveals_connector_secret(client, auth_header, cleanup_connector):
    connector_id = cleanup_connector["id"]

    configured = client.get(f"/api/config/connectors/{connector_id}", headers=auth_header)
    assert configured.status_code == 200
    assert configured.json["parameters"]["API_KEY"] == "********"

    revealed = client.post(
        f"/api/config/parameter-secrets/connectors/{connector_id}/API_KEY/reveal",
        headers=auth_header,
    )
    assert revealed.status_code == 200
    assert revealed.json == {"value": "super-secret-api-key"}
    assert "no-store" in revealed.headers["Cache-Control"]
    assert revealed.headers["Pragma"] == "no-cache"
