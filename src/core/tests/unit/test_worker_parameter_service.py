import pytest
from pydantic import ValidationError

from core.service.worker_parameters import effective_parameters, set_parameters


def test_patch_merges_and_null_removes_optional_values():
    current = {"FEED_URL": "https://example.test/feed", "USER_AGENT": "agent"}

    result = set_parameters(
        "RSS_COLLECTOR",
        current,
        {"USER_AGENT": None, "USE_GLOBAL_PROXY": "true"},
        patch=True,
    )

    assert result == {"FEED_URL": "https://example.test/feed", "USE_GLOBAL_PROXY": "true"}


def test_put_replaces_non_secrets_but_preserves_omitted_secrets():
    current = {"URL": "https://old.test", "API_KEY": "secret", "ORGANISATION_ID": "1", "USER_AGENT": "old"}

    result = set_parameters(
        "MISP_CONNECTOR",
        current,
        {"URL": "https://new.test", "ORGANISATION_ID": "2"},
        patch=False,
    )

    assert result == {"API_KEY": "secret", "URL": "https://new.test", "ORGANISATION_ID": "2"}


def test_required_value_cannot_be_removed_from_active_configuration():
    with pytest.raises(ValidationError):
        set_parameters(
            "MISP_CONNECTOR",
            {"URL": "https://misp.test", "API_KEY": "secret", "ORGANISATION_ID": "1"},
            {"API_KEY": None},
            patch=True,
        )


def test_incomplete_disabled_configuration_can_be_saved_but_not_executed():
    configured = set_parameters("RSS_COLLECTOR", {}, {"USER_AGENT": "agent"}, patch=False, complete=False)
    assert configured == {"USER_AGENT": "agent"}

    with pytest.raises(ValidationError):
        effective_parameters("RSS_COLLECTOR", configured)


def test_secret_marker_preserves_and_null_clears_optional_secret():
    current = {
        "SMTP_SERVER_ADDRESS": "smtp.example.test",
        "EMAIL_SENDER": "sender@example.test",
        "EMAIL_RECIPIENT": "recipient@example.test",
        "EMAIL_SUBJECT": "Subject",
        "EMAIL_PASSWORD": "secret",
    }

    preserved = set_parameters("EMAIL_PUBLISHER", current, {"EMAIL_PASSWORD": "********"}, patch=True)
    cleared = set_parameters("EMAIL_PUBLISHER", current, {"EMAIL_PASSWORD": None}, patch=True)

    assert preserved["EMAIL_PASSWORD"] == "secret"
    assert "EMAIL_PASSWORD" not in cleared
