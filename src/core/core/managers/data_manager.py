from core.log import logger
import json
from pathlib import Path
from shutil import copy
from core.config import Config

import hashlib
import base64

def file_hash(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def sync_presenter_templates_to_data() -> None:
    """Sync presenter templates from static to data folder, updating only if changed."""
    src = Path(__file__).parent.parent / "static" / "presenter_templates"
    dest = Path(Config.DATA_FOLDER) / "presenter_templates"
    hash_file_path = dest / "template_hashes.json"

    template_hashes = {}
    if hash_file_path.exists():
        with open(hash_file_path, "r") as f:
            template_hashes = json.load(f)

    dest.mkdir(parents=True, exist_ok=True)

    for file in filter(Path.is_file, src.glob("*")):
        dest_path = dest / file.name
        current_hash = file_hash(file)
        if not dest_path.exists() or template_hashes.get(file.name) != current_hash:
            logger.info(f"Updating {dest_path} with newer version.")
            copy(file, dest_path)
            template_hashes[file.name] = current_hash

    with open(hash_file_path, "w") as f:
        json.dump(template_hashes, f, indent=4)


def get_template_content(template_id: str) -> str | None:
    """Return the template content as a string, or None if not found."""
    try:
        path = Path(Config.DATA_FOLDER) / "presenter_templates" / template_id
        if not path.is_file():
            return None
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            logger.error(f"Template {template_id} is not valid UTF-8: {e}")
            return "__INVALID_UTF8__"
        return "__EMPTY__" if content.strip() == "" else content
    except Exception as e:
        logger.error(f"Error reading template {template_id}: {e}")
        return None


def list_templates() -> list[str]:
    """List all template IDs (filenames) in the presenter_templates directory."""
    try:
        path = Path(Config.DATA_FOLDER) / "presenter_templates"
        if not path.exists():
            return []
        return [f.name for f in path.iterdir() if f.is_file() and not f.name.startswith('.') and f.name not in ["README.md", "template_hashes.json"]]
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        return []


def save_template_content(template_id: str, content: str) -> None:
    """Save the template content to a file."""
    try:
        path = Path(Config.DATA_FOLDER) / "presenter_templates"
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / template_id
        file_path.write_text(content, encoding="utf-8")
    except Exception as e:
        logger.error(f"Error saving template {template_id}: {e}")
        raise


def delete_template(template_id: str) -> bool:
    """Delete the template file. Returns True if deleted, False otherwise."""
    try:
        path = Path(Config.DATA_FOLDER) / "presenter_templates" / template_id
        if path.is_file():
            path.unlink()
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}")
        return False


def get_presenter_template_path(presenter_template: str) -> str:
    """Return the absolute path to a presenter template file."""
    if Path(presenter_template).is_absolute():
        return Path(presenter_template).absolute().as_posix()
    path = Path(Config.DATA_FOLDER) / "presenter_templates" / presenter_template
    return path.absolute().as_posix()


def get_presenter_templates() -> list[str]:
    """List all presenter template filenames."""
    path = Path(Config.DATA_FOLDER) / "presenter_templates"
    return [file.name for file in path.glob("*") if file.is_file() and file.name not in ["README.md", "template_hashes.json"]]


def get_template_as_base64(presenter_template: str) -> str:
    """Return the template file as a base64-encoded string."""
    filepath = None
    try:
        filepath = get_presenter_template_path(presenter_template)
        with open(filepath, "rb") as f:
            file_content = f.read()
        return base64.b64encode(file_content).decode("utf-8")
    except Exception as e:
        logger.error(f"An error occurred while converting file: {filepath} to base64: {e}")
        return ""


def get_default_json(filename: str) -> str:
    package_file = Path(__file__).parent.parent / "static" / filename
    data_file = Path(Config.DATA_FOLDER) / filename
    source_file = data_file if data_file.exists() else package_file
    return source_file.parent.absolute().as_posix()


def initialize(initial_setup: bool = True) -> None:
    if initial_setup:
        sync_presenter_templates_to_data()








