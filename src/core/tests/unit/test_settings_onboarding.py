from core.model.settings import Settings


def test_settings_defaults_include_onboarding_tours():
    settings = Settings()

    assert settings.settings["onboarding_tours"] == {}


def test_settings_initialize_adds_onboarding_without_losing_existing_values(app, session):
    with app.app_context():
        settings = Settings.get_settings_entry()
        settings.settings = {
            "default_collector_proxy": "http://proxy.example",
            "onboarding_tours": {"existing_tour": "dismissed"},
        }
        session.flush()

        Settings.initialize()

        assert settings.settings["default_collector_proxy"] == "http://proxy.example"
        assert settings.settings["default_collector_interval"] == "0 */8 * * *"
        assert settings.settings["onboarding_tours"]["existing_tour"] == "dismissed"


def test_settings_update_preserves_existing_onboarding_tours(app, session):
    with app.app_context():
        settings = Settings.get_settings_entry()
        settings.settings = Settings.with_defaults({"onboarding_tours": {"admin_welcome_v1": "completed"}})
        session.flush()

        response, status = Settings.update({"settings": {"default_collector_proxy": "http://proxy.test", "onboarding_tours": {}}})

        assert status == 200
        assert response["settings"]["default_collector_proxy"] == "http://proxy.test"
        assert response["settings"]["onboarding_tours"]["admin_welcome_v1"] == "completed"


def test_settings_update_merges_onboarding_tours(app, session):
    with app.app_context():
        settings = Settings.get_settings_entry()
        settings.settings = Settings.with_defaults({"onboarding_tours": {"existing_tour": "dismissed"}})
        session.flush()

        response, status = Settings.update({"settings": {"onboarding_tours": {"admin_welcome_v1": "completed"}}})

        assert status == 200
        assert response["settings"]["onboarding_tours"] == {
            "existing_tour": "dismissed",
            "admin_welcome_v1": "completed",
        }


def test_settings_update_can_reset_existing_onboarding_tour_flags(app, session):
    with app.app_context():
        settings = Settings.get_settings_entry()
        settings.settings = Settings.with_defaults(
            {
                "onboarding_tours": {
                    "admin_welcome_v1": "completed",
                    "admin_advanced_v1": "dismissed",
                }
            }
        )
        session.flush()

        response, status = Settings.update(
            {
                "reset_onboarding_tours": "true",
                "settings": {
                    "default_collector_interval": "0 */8 * * *",
                },
            }
        )

        assert status == 200
        assert response["settings"]["onboarding_tours"] == {}


def test_settings_update_can_reset_onboarding_tours_without_settings_payload(app, session):
    with app.app_context():
        settings = Settings.get_settings_entry()
        settings.settings = Settings.with_defaults(
            {
                "default_collector_proxy": "http://proxy.test",
                "onboarding_tours": {
                    "admin_welcome_v1": "completed",
                    "admin_advanced_v1": "dismissed",
                },
            }
        )
        session.flush()

        response, status = Settings.update({"reset_onboarding_tours": True})

        assert status == 200
        assert response["settings"]["default_collector_proxy"] == "http://proxy.test"
        assert response["settings"]["onboarding_tours"] == {}
