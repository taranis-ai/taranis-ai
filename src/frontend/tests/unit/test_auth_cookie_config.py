import pytest
from flask import Flask, render_template
from pydantic import ValidationError

from frontend.config import Settings


@pytest.mark.parametrize(
    ("base_path", "suffix", "expected_names"),
    [
        ("/", "", ("access_token_cookie", "csrf_access_token")),
        ("/q/", "_q", ("access_token_cookie_q", "csrf_access_token_q")),
    ],
)
def test_jwt_cookie_names_and_paths(base_path: str, suffix: str, expected_names: tuple[str, ...]) -> None:
    settings = Settings(TARANIS_BASE_PATH=base_path, JWT_COOKIE_SUFFIX=suffix)
    flask_app = Flask(__name__)
    flask_app.config.from_object(settings)
    names = (
        settings.JWT_ACCESS_COOKIE_NAME,
        settings.JWT_ACCESS_CSRF_COOKIE_NAME,
    )
    paths = (
        settings.JWT_ACCESS_COOKIE_PATH,
        settings.JWT_ACCESS_CSRF_COOKIE_PATH,
    )

    assert names == expected_names
    assert paths == (base_path,) * 2
    assert (
        tuple(
            flask_app.config[name]
            for name in (
                "JWT_ACCESS_COOKIE_NAME",
                "JWT_ACCESS_CSRF_COOKIE_NAME",
            )
        )
        == expected_names
    )
    assert all(
        flask_app.config[name] == base_path
        for name in (
            "JWT_ACCESS_COOKIE_PATH",
            "JWT_ACCESS_CSRF_COOKIE_PATH",
        )
    )


def test_jwt_cookie_suffix_rejects_invalid_characters() -> None:
    with pytest.raises(ValidationError, match="JWT_COOKIE_SUFFIX"):
        Settings(JWT_COOKIE_SUFFIX="/q")


def test_form_reads_configured_csrf_cookie(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(app.config, "JWT_ACCESS_CSRF_COOKIE_NAME", "csrf_access_token_q")

    with app.test_request_context(headers={"Cookie": "csrf_access_token_q=csrf-value"}):
        body = render_template(
            "default/admin_form.html",
            submit_text="Save",
            model_name="example",
            form_action="/example",
        )

    assert 'name="csrf_token" value="csrf-value"' in body
