import base64

import pytest

from core.config import Config
from core.service import template_service


def test_build_validation_and_content_accepts_memoryview():
    encoded_content, validation_status = template_service._build_validation_and_content(memoryview(b"Hello {{ name }}"))

    assert encoded_content == base64.b64encode(b"Hello {{ name }}").decode("utf-8")
    assert validation_status == {
        "is_valid": True,
        "error_message": "",
        "error_type": "",
    }


@pytest.mark.parametrize(
    ("template_content", "expected_content", "expected_error_type"),
    [
        pytest.param(None, None, "NotFound", id="missing-template"),
        pytest.param(b"\xff\xfe", None, "UnicodeDecodeError", id="invalid-utf8"),
        pytest.param("", "", "EmptyFile", id="empty-template"),
        pytest.param("Hello {{ name }}", base64.b64encode(b"Hello {{ name }}").decode("utf-8"), "", id="valid-template"),
    ],
)
def test_build_template_response_handles_real_template_states(
    monkeypatch,
    template_content,
    expected_content,
    expected_error_type,
):
    monkeypatch.setattr(template_service, "get_template_content", lambda _: template_content)

    response = template_service.build_template_response("report_template.html")

    assert response.name == "report_template.html"
    assert response.content == expected_content
    assert response.validation_status["error_type"] == expected_error_type


def test_build_templates_list_returns_api_payloads(monkeypatch):
    templates = {
        "valid.html": "Hello {{ name }}",
        "empty.html": "",
        "invalid.html": b"\xff\xfe",
    }

    monkeypatch.setattr(template_service, "list_templates", lambda: list(templates))
    monkeypatch.setattr(template_service, "get_template_content", templates.__getitem__)

    items = template_service.build_templates_list()

    assert [item.model_dump() for item in items] == [
        {
            "name": "valid.html",
            "content": base64.b64encode(b"Hello {{ name }}").decode("utf-8"),
            "validation_status": {
                "is_valid": True,
                "error_message": "",
                "error_type": "",
            },
        },
        {
            "name": "empty.html",
            "content": "",
            "validation_status": {
                "is_valid": False,
                "error_message": "Template file is empty.",
                "error_type": "EmptyFile",
            },
        },
        {
            "name": "invalid.html",
            "content": None,
            "validation_status": {
                "is_valid": False,
                "error_message": "Template file is not valid UTF-8.",
                "error_type": "UnicodeDecodeError",
            },
        },
    ]


@pytest.mark.parametrize(
    ("order", "expected_names"),
    [
        ("name_asc", ["alpha.html", "Beta.html", "zulu.html"]),
        ("name_desc", ["zulu.html", "Beta.html", "alpha.html"]),
    ],
)
def test_templates_endpoint_orders_by_name(client, auth_header, monkeypatch, order, expected_names):
    templates = ["zulu.html", "alpha.html", "Beta.html"]
    monkeypatch.setattr(template_service, "list_templates", lambda: templates)
    monkeypatch.setattr(template_service, "get_template_content", lambda _: "Hello")

    response = client.get("/api/config/templates", query_string={"order": order}, headers=auth_header)

    assert response.status_code == 200
    assert [item["name"] for item in response.json["items"]] == expected_names


def test_templates_api_lifecycle(client, auth_header, monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "DATA_FOLDER", str(tmp_path))
    (tmp_path / "presenter_templates").mkdir()
    name = "report.html"
    content = base64.b64encode(b"Hello {{ name }}").decode()
    endpoint = f"/api/config/templates/{name}"

    response = client.post("/api/config/templates", json={"name": name, "content": content}, headers=auth_header)
    assert response.status_code == 200
    assert (tmp_path / "presenter_templates" / name).read_text() == "Hello {{ name }}"

    response = client.get(endpoint, headers=auth_header)
    assert response.status_code == 200
    assert response.json == {
        "name": name,
        "content": content,
        "validation_status": {"is_valid": True, "error_message": "", "error_type": ""},
    }

    content = base64.b64encode(b"Updated").decode()
    assert client.put(endpoint, json={"content": content}, headers=auth_header).status_code == 200
    assert client.get(endpoint, headers=auth_header).json["content"] == content
    assert client.delete(endpoint, headers=auth_header).status_code == 200
    assert client.get(endpoint, headers=auth_header).json == {
        "name": name,
        "content": None,
        "validation_status": {"is_valid": False, "error_message": "Template file not found.", "error_type": "NotFound"},
    }
