import base64

import pytest

from models.types import COLLECTOR_TYPES

from core.model.osint_source import OSINTSource


_VALID_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg=="
_VALID_PNG_BYTES = base64.b64decode(_VALID_PNG_BASE64)
_INVALID_BASE64_IMAGE = base64.b64encode(b"not-an-image").decode("utf-8")


@pytest.mark.usefixtures("app")
def test_osint_source_creation_with_valid_icon(session):
    source = OSINTSource(
        name="Test Source",
        description="A test",
        type=COLLECTOR_TYPES.RSS_COLLECTOR,
        icon=_VALID_PNG_BASE64,
    )
    session.add(source)
    session.commit()

    assert source.icon == _VALID_PNG_BYTES


@pytest.mark.usefixtures("app")
def test_osint_source_creation_with_invalid_icon_raises(session):
    with pytest.raises(ValueError):
        OSINTSource(
            name="Invalid",
            description="A test",
            type=COLLECTOR_TYPES.RSS_COLLECTOR,
            icon=_INVALID_BASE64_IMAGE,
        )


@pytest.mark.usefixtures("app")
def test_update_icon_rejects_invalid_image(session):
    source = OSINTSource(
        name="Source",
        description="Desc",
        type=COLLECTOR_TYPES.RSS_COLLECTOR,
    )
    session.add(source)
    session.commit()

    with pytest.raises(ValueError):
        source.update_icon(_INVALID_BASE64_IMAGE)


@pytest.mark.usefixtures("app")
def test_update_icon_can_clear_icon(session):
    source = OSINTSource(
        name="Clearable",
        description="Desc",
        type=COLLECTOR_TYPES.RSS_COLLECTOR,
    )
    session.add(source)
    session.commit()

    source.update_icon(_VALID_PNG_BYTES)
    assert source.icon == _VALID_PNG_BYTES

    source.update_icon(None)
    assert source.icon is None