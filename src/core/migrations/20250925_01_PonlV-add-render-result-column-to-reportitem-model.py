"""
Add render_result column to ReportItem model
"""

from yoyo import step

__depends__ = {"20250820_01_H1Omd-worker-status"}

steps = [
    step(
        """
        ALTER TABLE report_item
        ADD COLUMN IF NOT EXISTS render_result text;
        """,
        """
        ALTER TABLE report_item
        DROP COLUMN IF EXISTS render_result;
        """,
    )
]
