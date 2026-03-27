from unittest.mock import Mock

from sqlalchemy.exc import IntegrityError

from core.managers.db_manager import db
from core.model.word_list import WordList, WordListEntry


def test_update_word_list_rolls_back_when_async_refresh_hits_deleted_parent(app, session, monkeypatch):
    with app.app_context():
        word_list = WordList(
            id=4242,
            name="Async Word List",
            description="Used to test async refresh cleanup",
            entries=[WordListEntry("before")],
        )
        session.add(word_list)
        session.commit()

        rollback_spy = Mock(wraps=session.rollback)
        monkeypatch.setattr(db.session, "rollback", rollback_spy)

        def raise_integrity_error():
            raise IntegrityError("INSERT INTO word_list_entry ...", {}, Exception("word_list_entry_word_list_id_fkey"))

        monkeypatch.setattr(db.session, "commit", raise_integrity_error)

        result = WordList.update_word_list(
            content="value,category,description\nafter,Test,Updated entry\n",
            content_type="text/csv",
            word_list_id=word_list.id,
        )

        assert result is None
        rollback_spy.assert_called_once()
