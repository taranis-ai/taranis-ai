"""Rename the classifier type while preserving configured bots and completion markers."""

from yoyo import step


__depends__ = {"20261023_01_c4N8p-rename-default-topic-classifier"}


def rename_type(connection, old, new):
    with connection.cursor() as cursor:
        # Resolve the enum through the table, respecting the database search path.
        cursor.execute("SELECT atttypid::regtype::text FROM pg_attribute WHERE attrelid = 'bot'::regclass AND attname = 'type'")
        enum_type = cursor.fetchone()[0]
        cursor.execute("SELECT 1 FROM pg_enum WHERE enumtypid = %s::regtype AND enumlabel = %s", (enum_type, old))
        if cursor.fetchone():
            from psycopg import sql

            cursor.execute(sql.SQL("ALTER TYPE {} RENAME VALUE {} TO {}").format(sql.SQL(enum_type), sql.Literal(old), sql.Literal(new)))
        cursor.execute("UPDATE news_item_attribute SET key = %s WHERE upper(key) = %s", (new, old))
        cursor.execute("UPDATE task SET worker_type = %s WHERE upper(worker_type) = %s", (new, old))


def apply(connection):
    rename_type(connection, "CYBERSEC_CLASSIFIER_BOT", "TOPIC_CLASSIFIER_BOT")


def rollback(connection):
    rename_type(connection, "TOPIC_CLASSIFIER_BOT", "CYBERSEC_CLASSIFIER_BOT")


steps = [step(apply, rollback)]
