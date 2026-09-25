from uuid import uuid7

import pytest


def _bot(bot_type: str):
    from core.model.bot import Bot

    bot = Bot.filter_by_type(bot_type)
    assert bot is not None
    return bot


def test_seeded_bot_configs_do_not_define_ids_or_dependencies():
    from core.managers.pre_seed_data import bots

    assert all("id" not in bot for bot in bots)
    assert all("RUN_AFTER_BOTS" not in bot.get("parameters", {}) for bot in bots)


def test_collector_run_graph_uses_dependency_order(app, session):
    with app.app_context():
        from core.model.bot import Bot

        bots, dependencies_by_id = Bot.get_collector_run_graph()
        bot_types = [bot.type.name for bot in bots]

        assert bot_types == ["WORDLIST_BOT", "IOC_BOT", "NLP_BOT", "SUMMARY_BOT"]
        assert dependencies_by_id[_bot("ioc_bot").id] == [_bot("wordlist_bot").id]
        assert dependencies_by_id[_bot("nlp_bot").id] == [_bot("ioc_bot").id]
        assert dependencies_by_id[_bot("summary_bot").id] == [_bot("nlp_bot").id]


@pytest.mark.parametrize(
    "bot_type, parameters",
    [
        ("cybersec_classifier_bot", {}),
        ("tagging_bot", {"REGULAR_EXPRESSION": "test"}),
        ("intel_owl_bot", {"INTEL_OWL_URL": "https://intelowl.test", "INTEL_OWL_API_KEY": "test-key"}),
    ],
)
@pytest.mark.parametrize("existing", [True, False])
def test_dag_preview_uses_candidate_state(app, session, bot_type, parameters, existing):
    with app.app_context():
        from core.model.bot import Bot

        bot = Bot.add({"name": "Preview bot", "type": bot_type, "parameters": parameters, "enabled": False})
        preview = Bot.get_dag_preview(
            {
                "id": bot.id if existing else None,
                "type": bot.type,
                "index": bot.index,
                "enabled": True,
                "parameters": {"RUN_AFTER_COLLECTOR": "true", "RUN_AFTER_BOTS": ""},
            }
        )

        assert bot_type.upper() in [node["type"] for node in preview["order"]]
        assert preview["edges"] == []
        assert [node["type"] for node in preview["nodes"]] == [bot_type.upper()]
        assert Bot.get(bot.id).enabled is False
        assert Bot.get(bot.id).parameters == parameters


@pytest.mark.parametrize("scenario", ["invalid_id", "self", "cycle"])
def test_bot_dependency_validation(app, session, scenario):
    with app.app_context():
        from core.model.bot import Bot

        bot = _bot("wordlist_bot" if scenario == "cycle" else "ioc_bot")
        dependency = {
            "invalid_id": "NOT_A_BOT",
            "self": bot.id,
            "cycle": _bot("summary_bot").id,
        }[scenario]
        error = "Invalid bot ID" if scenario == "invalid_id" else "cannot run after itself" if scenario == "self" else "cycle"

        with pytest.raises(ValueError, match=error):
            Bot.update(bot.id, {"parameters": {"RUN_AFTER_BOTS": dependency}})


def test_duplicate_bot_types_use_instance_ids_in_dependencies(app, session):
    with app.app_context():
        from core.model.bot import Bot

        original_ioc = _bot("ioc_bot")
        duplicate_ioc = Bot.add(
            {
                "id": str(uuid7()),
                "name": "Second IOC",
                "description": "",
                "type": "ioc_bot",
                "index": Bot.get_highest_index() + 100,
                "parameters": {},
            }
        )
        dependent = _bot("cybersec_classifier_bot")
        Bot.update(dependent.id, {"parameters": {"RUN_AFTER_BOTS": duplicate_ioc.id}})

        original_dependents, _ = Bot.get_dependent_run_graph(original_ioc.id)
        duplicate_dependents, dependencies_by_id = Bot.get_dependent_run_graph(duplicate_ioc.id)

        assert len(Bot.get_all_by_type("ioc_bot")) == 2
        assert dependent.id not in {bot.id for bot in original_dependents}
        assert [bot.id for bot in duplicate_dependents] == [dependent.id]
        assert dependencies_by_id[dependent.id] == []
