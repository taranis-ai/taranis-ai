from pathlib import Path

from dev.template_dev import template_dev


def test_template_dev_resolves_templates_from_script_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "template.html").write_text("wrong template", encoding="utf-8")

    resolved_path = template_dev._resolve_template_path("template.html")

    assert resolved_path == Path(template_dev.__file__).resolve().parent / "template.html"


def test_template_dev_returns_server_error_for_render_failures(monkeypatch, tmp_path):
    monkeypatch.setattr(template_dev, "TEMPLATE_BASE_PATH", tmp_path)
    (tmp_path / "broken.html").write_text("{% for item in %}", encoding="utf-8")

    response = template_dev.app.test_client().get("/broken.html")

    assert response.status_code == 500
    assert response.json == {"error": "Template rendering failed"}
