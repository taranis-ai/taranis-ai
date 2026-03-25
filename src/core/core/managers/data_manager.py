import base64
import hashlib
import json
from pathlib import Path
from shutil import copy

from core.config import Config
from core.log import logger


_PRESENTER_TEMPLATES_DIRNAME = "presenter_templates"
_INTERNAL_TEMPLATE_FILES = {"README.md", "template_hashes.json"}


class InvalidPresenterTemplatePathError(ValueError):
    def __init__(self, message: str = "Invalid presenter template path") -> None:
        super().__init__(message)


def file_hash(file_path: Path) -> str:
    hash_md5 = hashlib.md5(usedforsecurity=False)
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def _get_static_presenter_templates_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "static" / _PRESENTER_TEMPLATES_DIRNAME


def _get_presenter_templates_dir() -> Path:
    return Path(Config.DATA_FOLDER) / _PRESENTER_TEMPLATES_DIRNAME


def validate_presenter_template_name(template_id: str) -> str:
    return validate_presenter_template_id(template_id, must_exist=False)


def _resolve_presenter_template_path(presenter_template: str, *, must_exist: bool = False) -> Path:
    templates_dir = _get_presenter_templates_dir().resolve()
    candidate = Path(presenter_template)

    try:
        if candidate.is_absolute():
            resolved_candidate = candidate.resolve(strict=must_exist)
        else:
            resolved_candidate = (templates_dir / validate_presenter_template_name(presenter_template)).resolve(strict=must_exist)
    except FileNotFoundError as exc:
        raise InvalidPresenterTemplatePathError from exc

    if resolved_candidate.parent != templates_dir:
        raise InvalidPresenterTemplatePathError

    if candidate.is_absolute() and not is_valid_presenter_template_id(resolved_candidate.name):
        raise InvalidPresenterTemplatePathError

    if must_exist and not resolved_candidate.is_file():
        raise InvalidPresenterTemplatePathError

    return resolved_candidate


def sync_presenter_templates_to_data() -> None:
    """Sync presenter templates from static to data folder, updating only if changed."""
    src = _get_static_presenter_templates_dir()
    dest = _get_presenter_templates_dir()
    hash_file_path = dest / "template_hashes.json"

    template_hashes = {}
    if hash_file_path.exists():
        with hash_file_path.open("r", encoding="utf-8") as f:
            template_hashes = json.load(f)

    dest.mkdir(parents=True, exist_ok=True)

    for file in filter(Path.is_file, src.glob("*")):
        dest_path = dest / file.name
        current_hash = file_hash(file)
        if not dest_path.exists() or template_hashes.get(file.name) != current_hash:
            logger.info(f"Updating {dest_path} with newer version.")
            copy(file, dest_path)
            template_hashes[file.name] = current_hash

    with hash_file_path.open("w", encoding="utf-8") as f:
        json.dump(template_hashes, f, indent=4)


def get_template_content(template_id: str) -> str | None:
    """Return the template content as a string, or None if not found."""
    try:
        path = _resolve_presenter_template_path(template_id, must_exist=True)
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            logger.error(f"Template {path.name} is not valid UTF-8: {e}")
            return "__INVALID_UTF8__"
        return "__EMPTY__" if content.strip() == "" else content
    except Exception as e:
        logger.error(f"Error reading template {template_id}: {e}")
        return None


def list_templates() -> list[str]:
    """List all template IDs (filenames) in the presenter_templates directory."""
    try:
        templates_dir = _get_presenter_templates_dir()
        if not templates_dir.exists():
            return []
        return [file.name for file in templates_dir.iterdir() if file.is_file() and is_valid_presenter_template_id(file.name)]
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        return []


def save_template_content(template_id: str, content: str) -> None:
    """Save the template content to a file."""
    try:
        template_id = validate_presenter_template_name(template_id)
        path = _get_presenter_templates_dir()
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / template_id
        file_path.write_text(content, encoding="utf-8")
    except Exception as e:
        logger.error(f"Error saving template {template_id}: {e}")
        raise


def delete_template(template_id: str) -> bool:
    """Delete the template file. Returns True if deleted, False otherwise."""
    try:
        path = _resolve_presenter_template_path(template_id, must_exist=True)
        path.unlink()
        return True
    except InvalidPresenterTemplatePathError:
        return False
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}")
        return False


def get_presenter_template_path(presenter_template: str) -> str:
    """Return an absolute presenter template path if it stays within the trusted template directory."""
    try:
        return _resolve_presenter_template_path(presenter_template).as_posix()
    except InvalidPresenterTemplatePathError:
        logger.warning(f"Rejected presenter template path outside allowed directory: {presenter_template}")
        return ""


def get_presenter_templates() -> list[str]:
    """List all presenter template filenames."""
    return list_templates()


def get_template_as_base64(presenter_template: str) -> str:
    """Return the template file as a base64-encoded string."""
    filepath = None
    try:
        path = _resolve_presenter_template_path(presenter_template, must_exist=True)
        filepath = path.as_posix()
        return base64.b64encode(path.read_bytes()).decode("utf-8")
    except Exception as e:
        logger.error(f"An error occurred while converting file: {filepath} to base64: {e}")
        return ""


def get_default_json(filename: str) -> str:
    package_file = Path(__file__).resolve().parent.parent / "static" / filename
    data_file = Path(Config.DATA_FOLDER) / filename
    source_file = data_file if data_file.exists() else package_file
    return source_file.parent.absolute().as_posix()


def is_valid_presenter_template_id(template_id: str) -> bool:
    if not isinstance(template_id, str) or not template_id or template_id != template_id.strip():
        return False

    candidate = Path(template_id)
    return (
        not candidate.is_absolute()
        and candidate.name == template_id
        and template_id not in {".", ".."}
        and not template_id.startswith(".")
        and template_id not in _INTERNAL_TEMPLATE_FILES
    )


def validate_presenter_template_id(template_id: str, *, must_exist: bool = True) -> str:
    if not is_valid_presenter_template_id(template_id):
        raise InvalidPresenterTemplatePathError

    if must_exist:
        return _resolve_presenter_template_path(template_id, must_exist=True).name

    return template_id


def validate_existing_presenter_template_id(template_id: str) -> str:
    return validate_presenter_template_id(template_id, must_exist=True)
