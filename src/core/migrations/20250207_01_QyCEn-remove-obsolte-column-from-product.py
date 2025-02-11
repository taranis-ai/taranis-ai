"""
remove obsolete column from product
"""

from yoyo import step

__depends__ = {"20241009_01_6d1Tn-cleanup-worker-types"}

steps = [
    step(
        """
    ALTER TABLE product DROP CONSTRAINT product_user_id_fkey;
    ALTER TABLE product DROP COLUMN user_id;
    """,
        """
    ALTER TABLE product ADD COLUMN user_id INTEGER;
    ALTER TABLE product ADD CONSTRAINT product_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user" (id);
    """,
    )
]
