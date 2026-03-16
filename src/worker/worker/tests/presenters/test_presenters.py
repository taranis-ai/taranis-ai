import json

import pytest
from jinja2.exceptions import SecurityError

import worker.presenters.pandoc_presenter as pandocp
import worker.presenters.pdf_presenter as pdfp


def test_base_presenter_generate(base_presenter, fixed_datetime):
    from presenters_test_data import rendered_report, test_product, test_template

    # test correct rendering of Jinja2 template
    rendered_product = base_presenter.generate(test_product, test_template)
    assert rendered_product.strip() == rendered_report.strip()


def test_base_presenter_blocks_ssti_chain(base_presenter):
    malicious_template = "{{ self.__init__.__globals__.__builtins__.__import__('os').popen('cat /etc/passwd').read() }}"

    with pytest.raises(SecurityError):
        _ = base_presenter.generate({}, malicious_template)


def test_pdf_presenter_successful_render(pdf_presenter, fixed_datetime, monkeypatch):
    class FakeHTML:
        def __init__(self, string):
            self.string = string

        def write_pdf(self, target=None):
            assert target is None
            return b"%PDF-1.7\n%fake\n"

    monkeypatch.setattr(pdfp, "HTML", FakeHTML, raising=True)

    product = {"title": "A Test Report"}
    template = "<h1>{{ data.title }}</h1><small>{{ data.current_date }}</small>"

    out = pdf_presenter.generate(product, template)

    assert isinstance(out, (bytes, bytearray))
    assert out == b"%PDF-1.7\n%fake\n"
    assert product["current_date"] == "2025-01-02"


def test_pdf_presenter_failed_render(pdf_presenter, fixed_datetime, monkeypatch):
    class FakeHTML:
        def __init__(self, string):
            raise RuntimeError("Serious Error")

    monkeypatch.setattr(pdfp, "HTML", FakeHTML, raising=True)

    product = {"title": "A Test Report"}
    template = "<h1>{{ data.title }}</h1><small>{{ data.current_date }}</small>"

    with pytest.raises(ValueError) as exception:
        _ = pdf_presenter.generate(product, template)
    assert str(exception.value) == "PDF generation failed: Serious Error"


def test_pdf_presenter_no_data(pdf_presenter, fixed_datetime, monkeypatch):
    class FakeHTML:
        def __init__(self, string):
            self.string = string

        def write_pdf(self, target=None):
            return ""

    monkeypatch.setattr(pdfp, "HTML", FakeHTML, raising=True)

    product = {"title": "A Test Report"}
    template = "<h1>{{ data.title }}</h1><small>{{ data.current_date }}</small>"

    with pytest.raises(ValueError) as exception:
        _ = pdf_presenter.generate(product, template)
    assert str(exception.value) == "PDF generation failed: No data returned"


def test_pandoc_presenter_succesful_render(pandoc_presenter, fixed_datetime, monkeypatch):
    def fake_convert_text(input_text, to_format, *, format, outputfile):
        assert to_format == "docx"
        assert format == "html"
        assert outputfile.endswith(".docx")

        with open(outputfile, "wb") as f:
            f.write(b"fake-docx-data")

    monkeypatch.setattr(pandocp.pypandoc, "convert_text", fake_convert_text, raising=True)

    product = {"title": "A Test Report"}
    template = "<h1>{{ data.title }}</h1><small>{{ data.current_date }}</small>"
    params = {"CONVERT_FROM": "html", "CONVERT_TO": "docx"}

    out = pandoc_presenter.generate(product, template, params)

    assert out == b"fake-docx-data"
    assert product["current_date"] == "2025-01-02"


def test_pandoc_presenter_failed_render(pandoc_presenter, fixed_datetime, monkeypatch):
    def fake_convert_text(input_text, to_format, *, format, outputfile):
        raise RuntimeError("Serious Error!")

    monkeypatch.setattr(pandocp.pypandoc, "convert_text", fake_convert_text, raising=True)

    product = {"title": "A Test Report"}
    template = "<h1>{{ data.title }}</h1><small>{{ data.current_date }}</small>"
    params = {"CONVERT_FROM": "md", "CONVERT_TO": "odt"}

    with pytest.raises(ValueError) as exception:
        _ = pandoc_presenter.generate(product, template, params)
    assert str(exception.value) == "Document generation failed for odt format: Serious Error!"


def test_pandoc_presenter_no_data(pandoc_presenter, fixed_datetime, monkeypatch):
    def fake_convert_text(input_text, to_format, *, format, outputfile):
        return ""

    monkeypatch.setattr(pandocp.pypandoc, "convert_text", fake_convert_text, raising=True)

    product = {"title": "A Test Report"}
    template = "<h1>{{ data.title }}</h1><small>{{ data.current_date }}</small>"
    params = {"CONVERT_FROM": "md", "CONVERT_TO": "odt"}

    with pytest.raises(ValueError) as exception:
        _ = pandoc_presenter.generate(product, template, params)
    assert str(exception.value) == "Document generation failed: No data returned for odt format."


def test_generate_real_stix_bundle(stix_presenter):
    from presenters_test_data import test_stix_product

    result = stix_presenter.generate(test_stix_product, None)
    bundle = json.loads(result)

    assert bundle["type"] == "bundle"
    assert bundle["spec_version"] == "2.1"
    assert isinstance(bundle["objects"], list)
    assert any(obj["type"] == "report" for obj in bundle["objects"])


def test_stix_bundle_exports_report_groups_as_objects(stix_presenter):
    from presenters_test_data import test_stix_product

    result = stix_presenter.generate(test_stix_product, None)
    bundle = json.loads(result)

    report_group_objects = [
        obj for obj in bundle["objects"] if obj.get("type") == "x-misp-object" and obj.get("x_misp_name") == "taranis-report-group"
    ]
    assert len(report_group_objects) == 2

    grouped_fields = {}
    for obj in report_group_objects:
        group_name = None
        fields = []
        for attribute in obj.get("x_misp_attributes", []):
            if attribute.get("object_relation") == "group_name":
                group_name = attribute.get("value")
            if attribute.get("object_relation") == "field":
                fields.append(json.loads(attribute["value"]))

        assert group_name
        grouped_fields[group_name] = fields

    assert {"name": "Links", "type": "text", "value": "link2"} in grouped_fields["Identify and Act"]
    assert {"name": "Links", "type": "text", "value": "link1"} in grouped_fields["Vulnerability"]
    assert {"name": "TLP", "type": "text", "value": "clear"} in grouped_fields["Vulnerability"]


def test_stix_bundle_contains_product_grouping_context(stix_presenter):
    from presenters_test_data import test_stix_product

    result = stix_presenter.generate(test_stix_product, None)
    bundle = json.loads(result)

    grouping_objects = [obj for obj in bundle["objects"] if obj.get("type") == "grouping"]
    assert len(grouping_objects) == 1

    grouping_object = grouping_objects[0]
    report_ids = {obj["id"] for obj in bundle["objects"] if obj.get("type") == "report"}

    assert grouping_object["context"] == "unspecified"
    assert set(grouping_object["object_refs"]) == report_ids
    assert grouping_object["x_taranis_product_id"] == test_stix_product["id"]
    assert grouping_object["x_taranis_product_title"] == test_stix_product["title"]
    assert grouping_object["x_taranis_product_type"] == test_stix_product["type"]
    assert grouping_object["x_taranis_product_mime_type"] == test_stix_product["mime_type"]
    assert grouping_object["x_taranis_product_type_id"] == test_stix_product["type_id"]
    assert grouping_object["x_taranis_product_report_count"] == len(report_ids)
    assert grouping_object["x_taranis_product_description"] == test_stix_product["description"]
    assert "description" not in grouping_object
    assert "x_taranis_product_fields" not in grouping_object
