import json
import base64
import hashlib
from pathlib import Path
from werkzeug.datastructures import FileStorage
from core.config import Config
from shutil import copy

from core.log import logger


def file_hash(file_path):
    hash_md5 = hashlib.md5(usedforsecurity=False)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_files_by_suffix(suffix: str) -> list[Path]:
    return [file_path for file_path in Path(Config.DATA_FOLDER).rglob(f"*{suffix}") if file_path.is_file()]


def add_file_to_subfolder(file: FileStorage, subfolder: str) -> None:
    if file.filename is None:
        raise ValueError("File must have a filename.")

    dest_folder = Path(Config.DATA_FOLDER) / subfolder
    dest_folder.mkdir(parents=True, exist_ok=True)

    dest_path = dest_folder / file.filename
    file.save(dest_path)


def is_file_in_subfolder(subfolder: str, file_name: str) -> bool:
    full_path = Path(Config.DATA_FOLDER) / subfolder / file_name
    return full_path.is_file()


def sync_presenter_templates_to_data() -> None:
    logger.info("Syncing presenter templates to data folder")
    src = Path(__file__).parent.parent / "static" / "presenter_templates"
    dest = Path(Config.DATA_FOLDER) / "presenter_templates"
    hash_file_path = dest / "template_hashes.json"

    template_hashes = {}

    if hash_file_path.exists():
        with open(hash_file_path, "r") as f:
            template_hashes = json.load(f)

    dest.mkdir(parents=True, exist_ok=True)

    for file in filter(Path.is_file, src.glob("*")):
        current_hash = file_hash(file)
        dest_path = dest / file.name

        if dest_path.exists():
            current_hash = file_hash(dest_path)

        if not dest_path.exists() or template_hashes.get(file.name) != current_hash:
            logger.debug(f"Updating {dest_path} with newer version.")
            copy(file, dest_path)
            template_hashes[file.name] = current_hash

    with open(hash_file_path, "w") as f:
        json.dump(template_hashes, f, indent=4)


def get_presenter_template_path(presenter_template: str) -> str:
    if Path.is_absolute(Path(presenter_template)):
        return Path(presenter_template).absolute().as_posix()
    path = Path(Config.DATA_FOLDER) / "presenter_templates" / presenter_template
    return path.absolute().as_posix()


def get_presenter_templates() -> list[str]:
    path = Path(Config.DATA_FOLDER) / "presenter_templates"
    return [file.name for file in filter(Path.is_file, path.glob("*")) if file.name not in ["README.md", "template_hashes.json"]]


def get_default_json(filename: str) -> str:
    package_file = Path(__file__).parent.parent / "static" / filename
    data_file = Path(Config.DATA_FOLDER) / filename

    source_file = data_file if data_file.exists() else package_file

    return source_file.parent.absolute().as_posix()


def get_templates_as_base64() -> list[dict[str, str]]:
    return [get_for_api(template) for template in get_presenter_templates()]


def get_for_api(template: str) -> dict:
    return {"id": template, "content": get_template_as_base64(template)}


def get_template_as_base64(presenter_template: str) -> str:
    try:
        filepath = get_presenter_template_path(presenter_template)
        with open(filepath, "rb") as f:
            file_content = f.read()
        return base64.b64encode(file_content).decode("utf-8")
    except Exception as e:
        logger.error(f"An error occurred while converting file: {filepath} to base64: {e}")
        return ""


def write_base64_to_file(base64_string: str, presenter_template: str) -> bool:
    try:
        filepath = get_presenter_template_path(presenter_template)
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(base64_string))
        return True
    except Exception as e:
        logger.error(f"An error occurred while converting base64 to file {filepath}: {e}")
        return False


def delete_template(presenter_template: str) -> bool:
    try:
        filepath = get_presenter_template_path(presenter_template)
        Path(filepath).unlink()
        return True
    except Exception as e:
        logger.error(f"An error occurred while deleting file: {filepath}: {e}")
        return False


def initialize(initial_setup: bool = True) -> None:
    if initial_setup:
        sync_presenter_templates_to_data()
