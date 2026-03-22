"""
bot disable toggle
"""

from yoyo import step


__depends__ = {"20260316_01_N6e5T-report-types-title-unique"}

steps = [
    step(
        """
        ALTER TABLE bot
        ADD COLUMN IF NOT EXISTS enabled boolean DEFAULT true;
        """
    )
]
