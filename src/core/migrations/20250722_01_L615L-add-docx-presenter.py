"""
add_docx_presenter
"""

from yoyo import step

__depends__ = {"20250530_01_bgjgJ-add-ppn-collector"}

steps = [
    step("ALTER TYPE worker_types ADD VALUE IF NOT EXISTS 'PANDOC_PRESENTER';"),
    step("ALTER TYPE presenter_types ADD VALUE IF NOT EXISTS 'PANDOC_PRESENTER';"),
]
