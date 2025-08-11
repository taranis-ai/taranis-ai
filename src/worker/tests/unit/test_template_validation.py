from models.template_validation import validate_template_content
from worker.presenters.presenter_tasks import validate_jinja_template


def test_worker_uses_shared_validator_success():
    res = validate_jinja_template("Hello {{ who }}")
    assert res["is_valid"] is True


def test_worker_uses_shared_validator_syntax_error():
    res = validate_jinja_template("{% for i in %}")
    assert res["is_valid"] is False
    assert res["error_type"] == "TemplateSyntaxError"


def test_worker_shared_module_direct_import():
    # Directly import shared validator to ensure availability
    res = validate_template_content("{{ x }}")
    assert res["is_valid"] is True
