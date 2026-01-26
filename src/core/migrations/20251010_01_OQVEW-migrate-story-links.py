"""
migrate story links
"""

from yoyo import step


__depends__ = {"20250820_01_H1Omd-worker-status"}

steps = [
    step(
        """
        ALTER TABLE story DROP COLUMN IF EXISTS links;
        """,
        """
        ALTER TABLE story ADD COLUMN links JSON;
        """,
    )
]
