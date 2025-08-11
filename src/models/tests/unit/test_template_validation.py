from models.template_validation import validate_template_content


def test_models_validator_valid_template():
    res = validate_template_content("Hello {{ name }}")
    assert res["is_valid"] is True
    assert res["error_message"] == ""
    assert res["error_type"] == ""


def test_models_validator_syntax_error():
    res = validate_template_content("{% for i in %}")
    assert res["is_valid"] is False
    assert res["error_type"] == "TemplateSyntaxError"
    assert "Expected an expression" in res["error_message"]


def test_models_validator_empty_file():
    res = validate_template_content("")
    assert res["is_valid"] is False
    assert res["error_type"] == "EmptyFile"
    assert "empty" in res["error_message"].lower()


def test_models_validator_undefined_ignored():
    res = validate_template_content("Value: {{ missing }}")
    assert res["is_valid"] is True
