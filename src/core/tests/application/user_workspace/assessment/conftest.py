import uuid
from contextlib import suppress

import pytest
from sqlalchemy.exc import SQLAlchemyError


@pytest.fixture
def assess_connector(app):
    with app.app_context():
        from core.model.connector import Connector

        connector_data = {
            "id": str(uuid.uuid4()),
            "name": f"Assess Connector {uuid.uuid4().hex[:8]}",
            "description": "Connector visible in the assess workspace",
            "type": "misp_connector",
            "parameters": {"API_KEY": "super-secret-api-key"},
        }

        if not Connector.get(connector_data["id"]):
            Connector.add(connector_data)

        yield connector_data

        with suppress(SQLAlchemyError):
            if Connector.get(connector_data["id"]):
                Connector.delete(connector_data["id"])
