"""
Add new MISP related enums
"""

from yoyo import step

__depends__ = {"20250324_02_vL3hN-add-last-change-column"}

steps = [
    step(
        """
        ALTER TYPE worker_types ADD VALUE 'MISP_CONNECTOR';
        ALTER TYPE worker_types ADD VALUE 'MISP_COLLECTOR';
        ALTER TYPE worker_category ADD VALUE 'CONNECTOR';
        """
    )
]
