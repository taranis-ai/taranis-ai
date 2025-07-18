"""
Add transaction table for sqlalchemy-continuum
"""

from yoyo import step

__depends__ = {"20250530_01_bgjgJ-add-ppn-collector"}

steps = [
    step(
        """
        CREATE SEQUENCE IF NOT EXISTS transaction_id_seq START 1;

        CREATE TABLE IF NOT EXISTS transaction (
            id integer PRIMARY KEY DEFAULT nextval('transaction_id_seq'),
            remote_addr VARCHAR(255),
            issued_at TIMESTAMP WITHOUT TIME ZONE
        );
        """,
        """
        DROP TABLE IF EXISTS transaction;
        DROP SEQUENCE IF EXISTS transaction_id_seq;
        """,
    )
]
