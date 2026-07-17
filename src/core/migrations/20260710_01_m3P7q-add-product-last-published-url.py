# pyright: reportMissingTypeStubs=false
"""
add the last published URL to products
"""

from yoyo import step


__depends__ = {
    "20260417_01_pK8sR-migrate-primary-keys-to-uuidv7",
    "20260707_01_k9M2p-add-task-user-id",
}

steps = [
    step(
        """
        ALTER TABLE product
        ADD COLUMN IF NOT EXISTS last_published_url TEXT;
        """,
        """
        ALTER TABLE product
        DROP COLUMN IF EXISTS last_published_url;
        """,
    )
]
