import base64

import pytest

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
        pytest.param("__INVALID_UTF8__", None, "UnicodeDecodeError", id="invalid-utf8-sentinel"),
        pytest.param("__EMPTY__", "", "EmptyFile", id="empty-template-sentinel"),
    ],
)
def test_build_template_response_handles_special_template_states(
    monkeypatch,
    template_content,
    expected_content,
    expected_error_type,
):
    monkeypatch.setattr(template_service, "get_template_content", lambda _: template_content)

    response = template_service.build_template_response("report_template.html")

    assert response["id"] == "report_template.html"
    assert response["content"] == expected_content
    assert response["validation_status"]["error_type"] == expected_error_type


def test_build_templates_list_returns_api_payloads(monkeypatch):
    templates = {
        "valid.html": "Hello {{ name }}",
        "empty.html": "__EMPTY__",
    }

    monkeypatch.setattr(template_service, "list_templates", lambda: list(templates))
    monkeypatch.setattr(template_service, "get_template_content", templates.__getitem__)

    items = template_service.build_templates_list()

    assert items == [
        {
            "id": "valid.html",
            "content": base64.b64encode(b"Hello {{ name }}").decode("utf-8"),
            "validation_status": {
                "is_valid": True,
                "error_message": "",
                "error_type": "",
            },
        },
        {
            "id": "empty.html",
            "content": "",
            "validation_status": {
                "is_valid": False,
                "error_message": "Template file is empty.",
                "error_type": "EmptyFile",
            },
        },
    ]
