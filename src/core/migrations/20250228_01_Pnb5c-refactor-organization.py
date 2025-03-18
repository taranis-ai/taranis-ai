"""
refactor organization
"""

from yoyo import step

__depends__ = {"20250207_01_QyCEn-remove-obsolte-column-from-product"}

steps = [
    step(
        """
        -- 1. Add a new JSON column "address" to the organization table.
        ALTER TABLE organization ADD COLUMN address JSON;

        -- 2. Populate the new JSON column with the address data.
        UPDATE organization
        SET address = (
            SELECT row_to_json(a)
            FROM address a
            WHERE a.id = organization.address_id
        )
        WHERE address_id IS NOT NULL;

        -- 3. Drop the old foreign key column "address_id".
        ALTER TABLE organization DROP COLUMN address_id;

        -- 4. Drop the unneeded "address" table.
        DROP TABLE address;
        """
    )
]
