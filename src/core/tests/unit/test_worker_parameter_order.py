from types import SimpleNamespace

from core.model.worker import Worker


def make_parameter(name: str) -> SimpleNamespace:
    return SimpleNamespace(parameter=name, type="text", rules=None)


def test_order_parameters_uses_core_worker_definition_order():
    parameters = [
        make_parameter("RUN_AFTER_COLLECTOR"),
        make_parameter("ITEM_FILTER"),
        make_parameter("REQUESTS_TIMEOUT"),
        make_parameter("REFRESH_INTERVAL"),
        make_parameter("BOT_ENDPOINT"),
        make_parameter("BOT_API_KEY"),
    ]

    ordered = Worker._order_parameters("story_bot", parameters)

    assert [parameter.parameter for parameter in ordered] == [
        "ITEM_FILTER",
        "REQUESTS_TIMEOUT",
        "BOT_API_KEY",
        "BOT_ENDPOINT",
        "RUN_AFTER_COLLECTOR",
        "REFRESH_INTERVAL",
    ]


def test_order_parameters_keeps_unknown_parameters_stable_after_known_ones():
    parameters = [
        make_parameter("UNKNOWN_ONE"),
        make_parameter("BOT_ENDPOINT"),
        make_parameter("UNKNOWN_TWO"),
        make_parameter("ITEM_FILTER"),
    ]

    ordered = Worker._order_parameters("story_bot", parameters)

    assert [parameter.parameter for parameter in ordered] == [
        "ITEM_FILTER",
        "BOT_ENDPOINT",
        "UNKNOWN_ONE",
        "UNKNOWN_TWO",
    ]


def test_order_parameters_returns_unknown_worker_type_unchanged():
    parameters = [
        make_parameter("UNKNOWN_ONE"),
        make_parameter("BOT_ENDPOINT"),
    ]

    ordered = Worker._order_parameters("unknown_bot_type", parameters)

    assert ordered == parameters
