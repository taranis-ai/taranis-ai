import pytest
from models.types import COLLECTOR_TYPES
from pydantic import ValidationError

from core.model.osint_source import OSINTSource
from core.model.parameter_value import ParameterValue


@pytest.mark.usefixtures("app")
def test_osint_source_constructor_validates_rank():
    with pytest.raises(ValidationError, match="less than or equal to 5"):
        OSINTSource(
            name="Invalid Rank",
            description="A test",
            type=COLLECTOR_TYPES.RSS_COLLECTOR,
            rank=6,
        )


@pytest.mark.usefixtures("app")
def test_osint_source_from_dict_accepts_parameter_dict():
    source = OSINTSource.from_dict(
        {
            "name": "Source",
            "description": "A test",
            "type": "rss_collector",
            "parameters": {"FEED_URL": "https://example.com/feed.xml"},
        }
    )

    assert ParameterValue.find_value_by_parameter(source.parameters, "FEED_URL") == "https://example.com/feed.xml"


@pytest.mark.usefixtures("app")
def test_osint_source_update_validates_rank(session):
    source = OSINTSource(
        name="Source",
        description="A test",
        type=COLLECTOR_TYPES.MANUAL_COLLECTOR,
    )
    session.add(source)
    session.commit()

    with pytest.raises(ValidationError, match="less than or equal to 5"):
        OSINTSource.update(source.id, {"rank": 6})


@pytest.mark.usefixtures("app")
def test_osint_source_partial_update_preserves_unsent_fields(session):
    source = OSINTSource(
        name="Source",
        description="A test",
        type=COLLECTOR_TYPES.RSS_COLLECTOR,
        parameters={"FEED_URL": "https://example.com/feed.xml"},
    )
    session.add(source)
    session.commit()

    updated_source = OSINTSource.update(source.id, {"description": ""})

    assert updated_source is not None
    assert updated_source.name == "Source"
    assert updated_source.description == ""
    assert ParameterValue.find_value_by_parameter(updated_source.parameters, "FEED_URL") == "https://example.com/feed.xml"


@pytest.mark.usefixtures("app")
def test_osint_source_partial_update_reparses_parameters(session):
    source = OSINTSource(
        name="Source",
        description="A test",
        type=COLLECTOR_TYPES.RSS_COLLECTOR,
        parameters={"FEED_URL": "https://example.com/feed.xml"},
    )
    session.add(source)
    session.commit()

    updated_source = OSINTSource.update(source.id, {"parameters": {"FEED_URL": "https://changed.example/feed.xml"}})

    assert updated_source is not None
    assert ParameterValue.find_value_by_parameter(updated_source.parameters, "FEED_URL") == "https://changed.example/feed.xml"
