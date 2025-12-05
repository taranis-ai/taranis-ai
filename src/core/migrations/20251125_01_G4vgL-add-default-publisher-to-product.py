"""
Add default_publisher to product
"""

from yoyo import step

__depends__ = {"20251106_01_U7YeD-migrate-search-vector"}

steps = [
    step(
        """
        ALTER TABLE product
        ADD COLUMN default_publisher VARCHAR(64);

        ALTER TABLE product
        ADD CONSTRAINT fk_product_default_publisher
        FOREIGN KEY (default_publisher)
        REFERENCES publisher_preset(id)
        ON DELETE SET NULL;
        """,
        """
        ALTER TABLE product DROP CONSTRAINT fk_product_default_publisher;

        ALTER TABLE product DROP COLUMN default_publisher;
        """,
    )
]
