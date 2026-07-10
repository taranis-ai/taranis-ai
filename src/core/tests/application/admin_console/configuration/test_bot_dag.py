from uuid import uuid7

import pytest


def _bot(bot_type: str):
    from core.model.bot import Bot

    bot = Bot.filter_by_type(bot_type)
    assert bot is not None
    return bot


def test_collector_run_graph_uses_dependency_order(app, session):
    with app.app_context():
        from core.model.bot import Bot

        bots, dependencies_by_id = Bot.get_collector_run_graph()
        bot_types = [bot.type.name for bot in bots]

        assert bot_types == ["WORDLIST_BOT", "IOC_BOT", "NLP_BOT", "SUMMARY_BOT"]
        assert dependencies_by_id[_bot("ioc_bot").id] == [_bot("wordlist_bot").id]
        assert dependencies_by_id[_bot("nlp_bot").id] == [_bot("ioc_bot").id]
        assert dependencies_by_id[_bot("summary_bot").id] == [_bot("nlp_bot").id]


def test_dag_preview_uses_candidate_state(app):
    with app.app_context():
        from core.model.bot import Bot

        bot = _bot("cybersec_classifier_bot")
        preview = Bot.get_dag_preview(
            {
                "type": bot.type,
                "index": bot.index,
                "enabled": True,
                "parameters": {"RUN_AFTER_COLLECTOR": "true", "RUN_AFTER_BOTS": ""},
            }
        )

        assert "CYBERSEC_CLASSIFIER_BOT" in [node["type"] for node in preview["order"]]
        assert preview["edges"] == []
        assert [node["type"] for node in preview["nodes"]] == ["CYBERSEC_CLASSIFIER_BOT"]


@pytest.mark.parametrize(
    ("bot_type", "dependency", "error"),
    [
        ("ioc_bot", "NOT_A_BOT", "Unknown bot type"),
        ("ioc_bot", "IOC_BOT", "cannot run after itself"),
        ("wordlist_bot", "SUMMARY_BOT", "cycle"),
    ],
)
def test_bot_dependency_validation(app, session, bot_type, dependency, error):
    with app.app_context():
        from core.model.bot import Bot

        with pytest.raises(ValueError, match=error):
            Bot.update(_bot(bot_type).id, {"parameters": {"RUN_AFTER_BOTS": dependency}})


def test_bot_type_must_be_unique(app, session):
    with app.app_context():
        from core.model.bot import Bot

        with pytest.raises(ValueError, match="already exists"):
            Bot.add(
                {
                    "id": str(uuid7()),
                    "name": "Duplicate IOC",
                    "description": "",
                    "type": "ioc_bot",
                    "index": Bot.get_highest_index() + 100,
                    "parameters": {},
                }
            )
