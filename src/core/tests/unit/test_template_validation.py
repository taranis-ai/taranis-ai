from models.template_validation import validate_template_content


def test_validate_template_valid_syntax():
    res = validate_template_content("Hello {{ name }}")
    assert res["is_valid"] is True
    assert res["error_message"] == ""
    assert res["error_type"] == ""


def test_validate_template_syntax_error():
    res = validate_template_content("{% for i in %}")
    assert res["is_valid"] is False
    assert res["error_type"] == "TemplateSyntaxError"
    assert "Expected an expression" in res["error_message"]


def test_validate_template_empty():
    res = validate_template_content("")
    assert res["is_valid"] is False
    assert res["error_type"] == "EmptyFile"
    assert "empty" in res["error_message"].lower()


def test_validate_template_render_undefined_ignored():
    # Undefined variables should not cause validation to fail
    res = validate_template_content("Value: {{ undefined_var }}")
    assert res["is_valid"] is True
