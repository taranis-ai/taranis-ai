"""PostgreSQL checks for the harness's isolation and observation contract."""

import json

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from tests.performance.orm.dataset import identifier
from tests.performance.orm.instrumentation import Observations, postgres_connection


pytestmark = pytest.mark.orm_performance


def test_postgresql_observations_and_snapshot_restore(orm_environment):
    from core.managers.db_manager import db
    from core.model.organization import Organization
    from core.model.story import Story

    environment = orm_environment
    environment.dataset.prepare("single")
    with environment.app.app_context():
        original_counts = environment.dataset.row_counts()
    with Observations(stacks=True) as observations:
        response = environment.app.test_client().post(
            "/api/config/organizations",
            json={"id": identifier("contract-org"), "name": "Collector contract"},
            headers=environment.headers["admin"],
        )
        assert response.status_code == 201
        with environment.app.app_context():
            story = db.session.get(Story, environment.dataset.ids["story_id"])
            assert story.news_items
            db.session.add(Organization(id=identifier("contract-org"), name="Duplicate identity"))
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()
    assert observations.counters["commits"] >= 1
    assert observations.counters["flushes"] >= 1
    assert observations.counters["rollbacks"] >= 1
    assert observations.counters["failed_statements"] == 1
    assert observations.counters["relationship_loads"] >= 1
    assert any("core.model.base_model.BaseModel.add" in item.get("calls", []) for item in observations.statements)
    statement_count = observations.counters["statements"]
    environment.dataset.restore()
    with environment.app.app_context():
        assert environment.dataset.row_counts() == original_counts
        assert db.session.scalar(select(Organization).where(Organization.id == identifier("contract-org"))) is None
    assert observations.counters["statements"] == statement_count
    bootstrap = json.loads((environment.output / "bootstrap-timing.json").read_text())
    assert bootstrap["counters"]["statements"] > 0
    with pytest.raises(ValueError, match="disposable"):
        postgres_connection("sqlite:///ignored.db")
