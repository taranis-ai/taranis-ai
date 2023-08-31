from pathlib import Path
from werkzeug.datastructures import FileStorage
from core.config import Config
from shutil import copy


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
    src = Path(__file__).parent.parent / "static" / "presenter_templates"
    dest = Path(Config.DATA_FOLDER) / "presenter_templates"
    dest.mkdir(parents=True, exist_ok=True)

    for file in filter(Path.is_file, src.glob("*")):
        dest_path = dest / file.name
        if not dest_path.exists():
            copy(file, dest_path)


def initialize(first_worker: bool) -> None:
    if first_worker:
        sync_presenter_templates_to_data()
