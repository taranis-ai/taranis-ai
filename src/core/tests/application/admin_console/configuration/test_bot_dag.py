from uuid import uuid4

import pytest


def _bot(bot_type: str):
    from core.model.bot import Bot

    bot = Bot.filter_by_type(bot_type)
    assert bot is not None
    return bot


def _task_submission(worker_type: str):
    from models.task import TaskResultEnvelope, TaskSubmission

    return TaskSubmission(
        id=str(uuid4()),
        worker_id=worker_type.lower(),
        worker_type=worker_type,
        status="success",
        result=TaskResultEnvelope(message="success", data={}),
    )


def test_collector_run_graph_uses_dependency_order(app, session):
    with app.app_context():
        from core.model.bot import Bot

        bots, dependencies_by_id = Bot.get_collector_run_graph()
        bot_types = [bot.type.name for bot in bots]

        assert bot_types == ["WORDLIST_BOT", "IOC_BOT", "NLP_BOT", "SUMMARY_BOT"]
        assert dependencies_by_id[_bot("ioc_bot").id] == [_bot("wordlist_bot").id]
        assert dependencies_by_id[_bot("nlp_bot").id] == [_bot("ioc_bot").id]
        assert dependencies_by_id[_bot("summary_bot").id] == [_bot("nlp_bot").id]


def test_dependent_run_graph_uses_only_parents_in_current_chain(app, session):
    with app.app_context():
        from core.model.bot import Bot

        bots, dependencies_by_id = Bot.get_dependent_run_graph("STORY_BOT")

        assert [bot.type.name for bot in bots] == ["SUMMARY_BOT"]
        assert dependencies_by_id[_bot("summary_bot").id] == []


def test_dependent_run_graph_branches_after_ioc(app, session):
    with app.app_context():
        from core.model.bot import Bot

        intelowl = _bot("intel_owl_bot")
        intelowl.enabled = True
        session.commit()

        bots, dependencies_by_id = Bot.get_dependent_run_graph("IOC_BOT")
        bot_types = {bot.type.name for bot in bots}

        assert bot_types == {"INTEL_OWL_BOT", "NLP_BOT", "SUMMARY_BOT"}
        assert dependencies_by_id[_bot("intel_owl_bot").id] == []
        assert dependencies_by_id[_bot("nlp_bot").id] == []
        assert dependencies_by_id[_bot("summary_bot").id] == [_bot("nlp_bot").id]


def test_bot_dependency_validation_rejects_unknown_type(app, session):
    with app.app_context():
        from core.model.bot import Bot

        with pytest.raises(ValueError, match="Unknown bot type"):
            Bot.update(_bot("ioc_bot").id, {"parameters": {"RUN_AFTER_BOTS": "NOT_A_BOT"}})


def test_bot_dependency_validation_rejects_self_dependency(app, session):
    with app.app_context():
        from core.model.bot import Bot

        with pytest.raises(ValueError, match="cannot run after itself"):
            Bot.update(_bot("ioc_bot").id, {"parameters": {"RUN_AFTER_BOTS": "IOC_BOT"}})


def test_bot_dependency_validation_rejects_cycles(app, session):
    with app.app_context():
        from core.model.bot import Bot

        with pytest.raises(ValueError, match="cycle"):
            Bot.update(_bot("wordlist_bot").id, {"parameters": {"RUN_AFTER_BOTS": "SUMMARY_BOT"}})


def test_bot_type_must_be_unique(app, session):
    with app.app_context():
        from core.model.bot import Bot

        with pytest.raises(ValueError, match="already exists"):
            Bot.add(
                {
                    "id": str(uuid4()),
                    "name": "Duplicate IOC",
                    "description": "",
                    "type": "ioc_bot",
                    "index": Bot.get_highest_index() + 100,
                    "parameters": {},
                }
            )


def test_successful_bot_result_schedules_dependents(monkeypatch):
    from core.managers import queue_manager
    from core.service.task import TaskService

    calls = []
    monkeypatch.setattr("core.service.task.NewsItemTagService.set_worker_execution_attribute", lambda **_: None)
    monkeypatch.setattr(
        queue_manager.queue_manager,
        "schedule_bot_dependents",
        lambda bot_type, filter_data=None, user_id=None: calls.append((bot_type, filter_data, user_id)),
    )

    TaskService._handle_bot_result(
        _task_submission("SUMMARY_BOT"),
        {"result": {}, "filter": {"story_id": "story-1"}, "trigger_dependents": True},
    )

    assert calls == [("SUMMARY_BOT", {"story_id": "story-1"}, None)]


def test_suppressed_bot_result_does_not_schedule_dependents(monkeypatch):
    from core.managers import queue_manager
    from core.service.task import TaskService

    calls = []
    monkeypatch.setattr("core.service.task.NewsItemTagService.set_worker_execution_attribute", lambda **_: None)
    monkeypatch.setattr(
        queue_manager.queue_manager,
        "schedule_bot_dependents",
        lambda bot_type, filter_data=None, user_id=None: calls.append((bot_type, filter_data, user_id)),
    )

    TaskService._handle_bot_result(
        _task_submission("SUMMARY_BOT"),
        {"result": {}, "filter": {"story_id": "story-1"}, "trigger_dependents": False},
    )

    assert calls == []
