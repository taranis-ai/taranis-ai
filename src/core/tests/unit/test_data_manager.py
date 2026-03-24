import pytest

from core.config import Config
from core.managers.data_manager import (
    get_presenter_template_path,
    save_template_content,
    validate_presenter_template_id,
)


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


@pytest.mark.parametrize(
    "template_id",
    [
        "../secrets.txt",
        "nested/template.html",
        "/etc/passwd",
        ".hidden.html",
        "README.md",
        "template_hashes.json",
        " template.html",
    ],
)
def test_validate_presenter_template_id_rejects_invalid_paths(template_id):
    with pytest.raises(ValueError, match="Invalid presenter template path"):
        validate_presenter_template_id(template_id)


def test_save_template_content_rejects_invalid_template_path(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "DATA_FOLDER", str(tmp_path))

    with pytest.raises(ValueError, match="Invalid presenter template path"):
        save_template_content("../escape.txt", "secret")

    assert not (tmp_path / "escape.txt").exists()
