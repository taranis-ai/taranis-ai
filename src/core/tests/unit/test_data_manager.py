from core.config import Config
from core.managers.data_manager import get_presenter_template_path


def test_get_presenter_template_path_allows_relative_path(monkeypatch, tmp_path):
    templates_dir = tmp_path / "presenter_templates"
    templates_dir.mkdir(parents=True)
    monkeypatch.setattr(Config, "DATA_FOLDER", str(tmp_path))

    resolved_path = get_presenter_template_path("report_template.html")

    assert resolved_path == (templates_dir / "report_template.html").resolve().as_posix()


def test_get_presenter_template_path_rejects_parent_traversal(monkeypatch, tmp_path):
    templates_dir = tmp_path / "presenter_templates"
    templates_dir.mkdir(parents=True)
    monkeypatch.setattr(Config, "DATA_FOLDER", str(tmp_path))

    resolved_path = get_presenter_template_path("../secrets.txt")

    assert resolved_path == ""


def test_get_presenter_template_path_rejects_absolute_outside_path(monkeypatch, tmp_path):
    templates_dir = tmp_path / "presenter_templates"
    templates_dir.mkdir(parents=True)
    monkeypatch.setattr(Config, "DATA_FOLDER", str(tmp_path))

    outside_file = tmp_path / "outside.txt"
    resolved_path = get_presenter_template_path(str(outside_file))

    assert resolved_path == ""


def test_get_presenter_template_path_allows_absolute_inside_path(monkeypatch, tmp_path):
    templates_dir = tmp_path / "presenter_templates"
    templates_dir.mkdir(parents=True)
    monkeypatch.setattr(Config, "DATA_FOLDER", str(tmp_path))

    inside_file = templates_dir / "inside.html"
    resolved_path = get_presenter_template_path(str(inside_file))

    assert resolved_path == inside_file.resolve().as_posix()
