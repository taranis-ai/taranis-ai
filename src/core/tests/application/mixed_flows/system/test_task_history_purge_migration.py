from pathlib import Path


def test_task_history_purge_migration_deletes_all_task_rows(app):
    from core.managers.db_manager import db
    from core.model.task import Task

    with app.app_context():
        Task.add(
            {
                "id": "purge-task-1",
                "task": "collector_task",
                "worker_id": "source-1",
                "worker_type": "rss_collector",
                "status": "SUCCESS",
                "result": {
                    "message": "ok",
                    "reason": None,
                    "retryable": False,
                    "data": {"source_id": "source-1"},
                },
            }
        )
        Task.add(
            {
                "id": "purge-task-2",
                "task": "bot_task",
                "worker_id": "bot-1",
                "worker_type": "WORDLIST_BOT",
                "status": "FAILURE",
                "result": {
                    "message": "boom",
                    "reason": "failed",
                    "retryable": False,
                    "data": {"worker_id": "bot-1"},
                },
            }
        )
        assert db.session.execute(db.select(Task)).scalars().all()

        db.session.execute(db.text("DELETE FROM task;"))
        db.session.commit()

        assert db.session.execute(db.select(Task)).scalars().all() == []

    migration_path = Path(app.root_path).parent / "migrations" / "20260611_01_w4R9m-purge-task-history.py"
    with migration_path.open(encoding="utf-8") as migration_file:
        migration_source = migration_file.read()

    assert "DELETE FROM task;" in migration_source
