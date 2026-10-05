from copy import deepcopy

import pytest
from models.user import ProfileSettings
from sqlalchemy import null

from core.managers.db_manager import db
from core.managers.db_seed_manager import pre_seed_update
from core.model.settings import Settings
from core.model.user import User


@pytest.mark.parametrize(
    "profile, expected_days",
    [
        (None, 7),
        (null(), 7),
        ({}, 7),
        ({"dashboard": None}, 7),
        ({"dashboard": {"trending_cluster_days": -1}}, 0),
        (
            ProfileSettings(onboarding_enabled=False).model_dump(mode="json")
            | {"dashboard": ProfileSettings().dashboard.model_dump() | {"trending_cluster_days": -1}},
            0,
        ),
    ],
)
def test_pre_seed_update_initializes_missing_profiles_and_preserves_preferences(session, profile, expected_days):
    _, status = Settings.update({"settings": {"onboarding_enabled": False}})
    assert status == 200
    user = User(username=User.uuid7_str(), name="Missing profile", organization=None, roles=[])
    preferences = {
        "dark_theme": True,
        "onboarding_enabled": True,
        "dashboard": {"source_distribution_limit": 0},
        "custom": {"value": "keep"},
    }
    customized_user = User(username=User.uuid7_str(), name="Partial profile", organization=None, roles=[])
    session.add_all([user, customized_user])
    session.flush()
    session.execute(db.update(User).where(User.id == user.id).values(profile=profile))
    session.execute(db.update(User).where(User.id == customized_user.id).values(profile=preferences))
    session.commit()

    pre_seed_update(db.engine)
    session.expire_all()

    assert user.profile == ProfileSettings(onboarding_enabled=False, dashboard={"trending_cluster_days": expected_days}).model_dump(
        mode="json"
    )
    assert customized_user.profile["dark_theme"] is True
    assert customized_user.profile["onboarding_enabled"] is True
    assert customized_user.profile["dashboard"]["source_distribution_limit"] == 0
    assert customized_user.profile["dashboard"]["show_charts"] is True
    assert customized_user.profile["custom"] == preferences["custom"]
    saved_profiles = deepcopy([user.profile, customized_user.profile])

    pre_seed_update(db.engine)
    session.expire_all()

    assert [user.profile, customized_user.profile] == saved_profiles
