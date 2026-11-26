"""Move the legacy analyst comment to the discussion table created by metadata."""

from uuid import uuid7

from yoyo import step


__depends__ = {"20261023_01_c4N8p-rename-default-topic-classifier"}


def migrate(connection):
    with connection.cursor() as cursor:
        cursor.execute("LOCK TABLE story IN ACCESS EXCLUSIVE MODE")
        cursor.execute("SELECT id, comments FROM story WHERE comments IS NOT NULL AND comments <> ''")
        rows = [(str(uuid7()), story_id, body) for story_id, body in cursor.fetchall() if body.strip()]
        if rows:
            cursor.executemany("INSERT INTO comment (id, story_id, body) VALUES (%s, %s, %s)", rows)
        cursor.execute("ALTER TABLE story DROP COLUMN comments")


steps = [step(migrate)]
