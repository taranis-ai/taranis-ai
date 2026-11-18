import pytest
from flask import url_for

from frontend import create_app
from frontend.config import Settings


@pytest.mark.parametrize(("trust_forwarded_proto", "scheme"), [(False, "http"), (True, "https")])
def test_absolute_url_uses_public_origin(trust_forwarded_proto: bool, scheme: str, monkeypatch) -> None:
    monkeypatch.setenv("TARANIS_PUBLIC_HOST", "taranis.example.org")
    monkeypatch.setenv("TRUSTED_HOSTS", '["alias.example.org"]')
    settings = Settings()
    app = create_app(
        {
            "TESTING": True,
            "APPLICATION_ROOT": "/taranis/frontend",
            "TARANIS_TRUST_FORWARDED_PROTO": trust_forwarded_proto,
            "TRUSTED_HOSTS": settings.TRUSTED_HOSTS,
        }
    )

    @app.get("/test-absolute-url")
    def absolute_url():
        return url_for("assess.assess", search="old", _external=True)

    client = app.test_client()
    headers = {
        "X-Forwarded-Proto": "https",
        "X-Forwarded-Host": "other.example.org",
        "X-Forwarded-Port": "9999",
        "X-Forwarded-Prefix": "/other",
    }
    response = client.get("/test-absolute-url", base_url="http://taranis.example.org:8443", headers=headers)

    assert client.get("/test-absolute-url", base_url="http://127.0.0.1").status_code == 200
    assert client.get("/test-absolute-url", base_url="http://alias.example.org").status_code == 200
    assert response.status_code == 200
    assert response.text == f"{scheme}://taranis.example.org:8443/taranis/frontend/assess?search=old"
    assert client.get("/test-absolute-url", base_url="http://other.example.org", headers=headers).status_code == 400
