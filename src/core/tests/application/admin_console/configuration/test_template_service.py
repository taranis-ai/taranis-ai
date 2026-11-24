import base64
from pathlib import Path

import pytest

from core.config import Config
from core.managers.pre_seed_data import product_types as seeded_product_types
from core.service import template_service


PRESENTER_TEMPLATES = Path(template_service.__file__).resolve().parents[1] / "static" / "presenter_templates"
CERT_DAILY_TEMPLATE = (PRESENTER_TEMPLATES / "cert_at_daily_report.html").read_text(encoding="utf-8")
PDF_TEMPLATE = (PRESENTER_TEMPLATES / "pdf_template.html").read_text(encoding="utf-8")
SEEDED_TEMPLATE_PRODUCT_TYPES = [seed for seed in seeded_product_types if "TEMPLATE_PATH" in seed.get("parameters", {})]


def _seeded_report_types(titles: list[str]) -> list:
    from core.model.report_item_type import ReportItemType

    report_types = []
    for title in titles:
        report_type = ReportItemType.get_by_title(title)
        assert report_type is not None, f"Seeded report type {title!r} is missing"
        report_types.append(report_type)
    return report_types


@pytest.mark.parametrize(
    ("template_content", "report_type_titles", "expected_warnings"),
    [
        pytest.param(CERT_DAILY_TEMPLATE, ["CERT Report"], [], id="compatible"),
        pytest.param(
            CERT_DAILY_TEMPLATE,
            ["OSINT Report"],
            ["The template uses 'Data', which is not available for report type 'OSINT Report'."],
            id="missing-attribute-group",
        ),
        pytest.param(PDF_TEMPLATE, ["OSINT Report", "CERT Report"], [], id="generic-template"),
        pytest.param("{% for item in %}", ["OSINT Report"], ["The template has a syntax error."], id="syntax-error"),
        pytest.param(
            "{{ data.report_items[0].revision + 'x' }}",
            ["OSINT Report"],
            ["The template could not be rendered for report type 'OSINT Report'."],
            id="render-error",
        ),
    ],
)
def test_check_template_compatibility(app, template_content, report_type_titles, expected_warnings):
    with app.app_context():
        report_types = _seeded_report_types(report_type_titles)

        assert template_service.check_template_compatibility(template_content, report_types) == expected_warnings


@pytest.mark.parametrize("seed", SEEDED_TEMPLATE_PRODUCT_TYPES, ids=lambda seed: seed["parameters"]["TEMPLATE_PATH"])
def test_seeded_product_type_templates_match_their_report_types(app, seed):
    from core.model.product_type import ProductType

    with app.app_context():
        product_type = ProductType.filter_by_title(seed["title"])
        assert product_type is not None
        assert {report_type.title for report_type in product_type.report_types} == set(seed["report_types"])

        assert template_service.product_type_compatibility_warnings(product_type) == []


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
