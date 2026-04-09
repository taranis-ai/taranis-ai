from contextlib import suppress

import pytest
from sqlalchemy.exc import SQLAlchemyError


@pytest.fixture
def publish_publisher_preset(app):
    with app.app_context():
        from core.model.publisher_preset import PublisherPreset

        publisher_preset = {
            "id": "publish-user-preset",
            "name": "publish_user_preset",
            "description": "User publish preset",
            "type": "ftp_publisher",
            "parameters": {
                "FTP_URL": "ftp://example.invalid/export",
                "PASSWORD": "super-secret-password",
            },
        }

        if not PublisherPreset.get(publisher_preset["id"]):
            PublisherPreset.add(publisher_preset)

        yield publisher_preset

        with suppress(SQLAlchemyError):
            if PublisherPreset.get(publisher_preset["id"]):
                PublisherPreset.delete(publisher_preset["id"])
