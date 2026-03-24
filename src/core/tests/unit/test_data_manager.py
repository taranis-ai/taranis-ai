import pytest

from core.config import Config
from core.managers.data_manager import (
    InvalidPresenterTemplatePathError,
    get_presenter_template_path,
    save_template_content,
    validate_existing_presenter_template_id,
    validate_presenter_template_id,
    validate_presenter_template_name,
)


@pytest.fixture
def templates_dir(monkeypatch, tmp_path):
    templates_dir = tmp_path / "presenter_templates"
    templates_dir.mkdir(parents=True)
    monkeypatch.setattr(Config, "DATA_FOLDER", str(tmp_path))
    return templates_dir


@pytest.mark.parametrize(
    ("template_ref", "expected"),
    [
        pytest.param("report_template.html", "report_template.html", id="relative-in-dir"),
        pytest.param("../secrets.txt", "", id="parent-traversal"),
        pytest.param("inside.html", "inside.html", id="absolute-in-dir"),
        pytest.param("outside.txt", "", id="absolute-outside-dir"),
    ],
)
def test_get_presenter_template_path(templates_dir, tmp_path, template_ref, expected):
    if template_ref == "inside.html":
        template_ref = str(templates_dir / template_ref)
        expected = (templates_dir / expected).resolve().as_posix()
    elif template_ref == "outside.txt":
        template_ref = str(tmp_path / template_ref)
    elif expected:
        expected = (templates_dir / expected).resolve().as_posix()

    assert get_presenter_template_path(template_ref) == expected


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
def test_validate_presenter_template_name_rejects_invalid_paths(template_id):
    with pytest.raises(InvalidPresenterTemplatePathError, match="Invalid presenter template path"):
        validate_presenter_template_name(template_id)


def test_validate_presenter_template_id_accepts_existing_template(templates_dir):
    template = templates_dir / "report_template.html"
    template.write_text("hello", encoding="utf-8")

    assert validate_presenter_template_id("report_template.html") == "report_template.html"
    assert validate_existing_presenter_template_id("report_template.html") == "report_template.html"


@pytest.mark.parametrize("template_id", ["missing_template.html", "escaped.html"])
def test_validate_presenter_template_id_rejects_invalid_resolved_paths(templates_dir, tmp_path, template_id):
    if template_id == "escaped.html":
        outside_file = tmp_path / "outside.html"
        outside_file.write_text("secret", encoding="utf-8")
        (templates_dir / template_id).symlink_to(outside_file)

    with pytest.raises(InvalidPresenterTemplatePathError, match="Invalid presenter template path"):
        validate_presenter_template_id(template_id)


def test_validate_existing_presenter_template_id_rejects_missing_template(templates_dir):
    with pytest.raises(InvalidPresenterTemplatePathError, match="Invalid presenter template path"):
        validate_existing_presenter_template_id("missing_template.html")


def test_save_template_content_accepts_valid_template_path(templates_dir):
    save_template_content("report_template.html", "content")

    assert (templates_dir / "report_template.html").read_text(encoding="utf-8") == "content"


def test_save_template_content_rejects_invalid_template_path(templates_dir, tmp_path):
    with pytest.raises(InvalidPresenterTemplatePathError, match="Invalid presenter template path"):
        save_template_content("../escape.txt", "secret")

    assert not (tmp_path / "escape.txt").exists()
