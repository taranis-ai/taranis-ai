import pytest
import worker.presenters.pdf_presenter as pdfp
import worker.presenters.pandoc_presenter as pandocp


def test_base_presenter_generate(base_presenter, fixed_datetime):
    from presenters_test_data import test_template, test_product, rendered_report

    # test correct rendering of Jinja2 template
    rendered_product = base_presenter.generate(test_product, test_template)
    assert rendered_product.strip() == rendered_report.strip()


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
