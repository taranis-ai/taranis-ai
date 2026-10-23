from copy import deepcopy

from core.managers.db_manager import db
from core.managers.db_seed_manager import pre_seed_update
from core.model.bot import Bot


def test_pre_seed_update_renames_only_default_classifier_names(session):
    parent = Bot.filter_by_type("wordlist_bot")
    assert parent is not None
    legacy_names = ["Cybersecurity Classifier Bot", "Topic Classifier Bot"]
    classifiers = [
        Bot.add(
            {
                "name": name,
                "type": "cybersec_classifier_bot",
                "enabled": False,
                "description": "Keep this description",
                "parameters": {"REFRESH_INTERVAL": "*/15 * * * *", "RUN_AFTER_BOTS": parent.id},
            }
        )
        for name in [*legacy_names, "My cybersecurity classifier", "Cybersecurity Classifier Bot - custom"]
    ]
    Bot.add(
        {
            "name": "Cybersecurity Classifier Bot",
            "type": "ioc_bot",
            "parameters": {"RUN_AFTER_BOTS": classifiers[0].id},
        }
    )
    # Preserve the enabled state of an upgraded classifier, including stale endpoint assignments.
    classifiers[0].enabled = True
    session.commit()
    before = {
        bot.id: {column.name: deepcopy(getattr(bot, column.name)) for column in Bot.__table__.columns}
        for bot in session.scalars(db.select(Bot))
    }
    expected = deepcopy(before)
    for classifier in classifiers[:2]:
        expected[classifier.id]["name"] = "Topic Classifier"

    for _ in range(2):
        pre_seed_update(db.engine)
        session.expire_all()

        after = {
            bot.id: {column.name: getattr(bot, column.name) for column in Bot.__table__.columns} for bot in session.scalars(db.select(Bot))
        }
        assert after == expected
