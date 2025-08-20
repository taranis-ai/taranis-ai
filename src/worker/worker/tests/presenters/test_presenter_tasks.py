import pytest
from unittest.mock import patch

from worker.presenters.presenter_tasks import TemplateValidationTask, PresenterTask, validate_jinja_template


class TestValidateJinjaTemplate:
    def test_validate_jinja_template_valid(self):
        result = validate_jinja_template("Hello {{ name }}!")
        assert result["is_valid"] is True
        assert result["error_message"] == ""
        assert result["error_type"] == ""

    def test_validate_jinja_template_invalid(self):
        result = validate_jinja_template("Hello {{ name !")
        assert result["is_valid"] is False
        assert result["error_type"] == "TemplateSyntaxError"
        assert isinstance(result["error_message"], str) and result["error_message"]


class TestTemplateValidationTask:
    def setup_method(self):
        self.task = TemplateValidationTask()

    def test_validate_template_valid_simple(self):
        result = self.task.validate_template("Hello {{ name }}!")
        assert result["is_valid"] is True
        assert result["error_message"] == ""
        assert result["error_type"] == ""

    def test_validate_template_valid_with_loop(self):
        result = self.task.validate_template("{% for item in items %}{{ item }}{% endfor %}")
        assert result["is_valid"] is True
        assert result["error_message"] == ""
        assert result["error_type"] == ""

    def test_validate_template_valid_with_condition(self):
        result = self.task.validate_template("{% if condition %}{{ value }}{% else %}No value{% endif %}")
        assert result["is_valid"] is True
        assert result["error_message"] == ""
        assert result["error_type"] == ""

    def test_validate_template_valid_with_filters(self):
        result = self.task.validate_template("{{ name | upper | default('Unknown') }}")
        assert result["is_valid"] is True
        assert result["error_message"] == ""
        assert result["error_type"] == ""

    def test_validate_template_empty_is_invalid(self):
        result = self.task.validate_template("")
        assert result["is_valid"] is False
        assert result["error_type"] == "EmptyFile"
        assert isinstance(result["error_message"], str) and result["error_message"]

    def test_validate_template_static_text(self):
        result = self.task.validate_template("This is just static text")
        assert result["is_valid"] is True
        assert result["error_message"] == ""
        assert result["error_type"] == ""

    def test_validate_template_invalid_missing_brace(self):
        result = self.task.validate_template("Hello {{ name !")
        assert result["is_valid"] is False
        assert result["error_type"] == "TemplateSyntaxError"
        assert result["error_message"]

    def test_validate_template_invalid_wrong_syntax(self):
        result = self.task.validate_template("{% if condition % {{ value }} {% endif %}")
        assert result["is_valid"] is False
        assert result["error_type"] == "TemplateSyntaxError"
        assert result["error_message"]

    def test_validate_template_invalid_unclosed_block(self):
        result = self.task.validate_template("{% for item in items %}{{ item }}")
        assert result["is_valid"] is False
        assert result["error_type"] == "TemplateSyntaxError"
        assert result["error_message"]

    def test_validate_template_invalid_unknown_tag(self):
        result = self.task.validate_template("{% unknown_tag %}")
        assert result["is_valid"] is False
        assert result["error_type"] == "TemplateSyntaxError"
        assert isinstance(result["error_message"], str) and result["error_message"]

    def test_validate_template_calls_utility(self):
        with patch('worker.presenters.presenter_tasks.validate_jinja_template') as mock_validate:
            mock_validate.return_value = {"is_valid": True, "error_message": "", "error_type": ""}
            template = "{{ variable }}"
            self.task.validate_template(template)
            mock_validate.assert_called_once_with(template)

    def test_run_method_calls_validate_template(self):
        with patch.object(self.task, 'validate_template') as mock_validate:
            mock_validate.return_value = {"is_valid": True, "error_message": "", "error_type": ""}
            template = "{{ variable }}"
            result = self.task.run(template)
            mock_validate.assert_called_once_with(template)
            assert result == {"is_valid": True, "error_message": "", "error_type": ""}

    def test_task_name(self):
        assert self.task.name == "template_validation_task"


class TestPresenterTaskValidation:
    def setup_method(self):
        with patch('worker.presenters.presenter_tasks.CoreApi'):
            self.task = PresenterTask()

    def test_presenter_task_has_validate_template_method(self):
        assert hasattr(self.task, 'validate_template') and callable(self.task.validate_template)

    def test_presenter_task_validate_template_valid(self):
        result = self.task.validate_template("Hello {{ name }}!")
        assert result["is_valid"] is True
        assert result["error_message"] == ""
        assert result["error_type"] == ""

    def test_presenter_task_validate_template_invalid(self):
        result = self.task.validate_template("Hello {{ name !")
        assert result["is_valid"] is False
        assert result["error_type"] == "TemplateSyntaxError"
        assert isinstance(result["error_message"], str) and result["error_message"]

    def test_presenter_task_validate_template_same_as_validation_task(self):
        validation_task = TemplateValidationTask()
        test_templates = [
            "{{ variable }}",
            "{% for item in items %}{{ item }}{% endfor %}",
            "{{ invalid",
            "static text",
        ]
        for template in test_templates:
            presenter_result = self.task.validate_template(template)
            validation_result = validation_task.validate_template(template)
            assert presenter_result == validation_result, f"Results differ for template: {template}"

    def test_presenter_task_name(self):
        assert self.task.name == "presenter_task"


class TestTemplateValidationIntegration:
    def test_complex_template_validation(self):
        task = TemplateValidationTask()
        complex_template = """
        {%- set greeting = "Hello" -%}
        {{ greeting }} {{ name | default("World") }}!
        {% if items %}
        <ul>
        {% for item in items %}
            <li>{{ item.title | e }}</li>
        {% endfor %}
        </ul>
        {% else %}
        <p>No items available.</p>
        {% endif %}
        {# This is a comment #}
        {% macro render_button(text, url="#") %}
        <a href="{{ url }}">{{ text }}</a>
        {% endmacro %}
        {{ render_button("Click me", "/example") }}
        """
        result = task.validate_template(complex_template)
        assert result["is_valid"] is True
        assert result["error_message"] == ""
        assert result["error_type"] == ""

    def test_template_with_inheritance(self):
        task = TemplateValidationTask()
        child_template = """
        {% extends "base.html" %}
        {% block title %}Page Title{% endblock %}
        {% block content %}
        <h1>{{ heading }}</h1>
        <p>{{ content }}</p>
        {% endblock %}
        """
        result = task.validate_template(child_template)
        assert result["is_valid"] is True

    def test_template_with_includes(self):
        task = TemplateValidationTask()
        template_with_include = """
        <header>
        {% include "header.html" %}
        </header>
        <main>
        {{ content }}
        </main>
        <footer>
        {% include "footer.html" ignore missing %}
        </footer>
        """
        result = task.validate_template(template_with_include)
        assert result["is_valid"] is True

    def test_template_with_custom_filters_and_tests(self):
        task = TemplateValidationTask()
        template_with_custom = """
        {% if value is defined and value is not none %}
        {{ value | custom_filter | safe }}
        {% endif %}
        {% for item in items | selectattr("active") %}
        {{ item.name }}
        {% endfor %}
        """
        result = task.validate_template(template_with_custom)
        assert result["is_valid"] is True

    @pytest.mark.parametrize("invalid_template,expected_error_type", [
        ("{{ unclosed", "TemplateSyntaxError"),
        ("{% for item in items %}", "TemplateSyntaxError"),
        ("{% if %}", "TemplateSyntaxError"),
        ("{{ variable | nonexistent_filter }", "TemplateSyntaxError"),
        ("{% unknown_tag %}", "TemplateSyntaxError"),
        ("", "EmptyFile"),
    ])
    def test_various_invalid_templates(self, invalid_template, expected_error_type):
        task = TemplateValidationTask()
        result = task.validate_template(invalid_template)
        assert result["is_valid"] is False
        assert result["error_type"] == expected_error_type
        assert isinstance(result["error_message"], str)

    @pytest.mark.parametrize("valid_template", [
        "{{ variable }}",
        "{% for item in items %}{{ item }}{% endfor %}",
        "{% if condition %}yes{% else %}no{% endif %}",
        "{{ value | default('default') | upper }}",
        "{# Just a comment #}",
        "Static text only",
        "{% set var = 'value' %}{{ var }}",
        "{% with %}{% set local = 'value' %}{{ local }}{% endwith %}",
    ])
    def test_various_valid_templates(self, valid_template):
        task = TemplateValidationTask()
        result = task.validate_template(valid_template)
        assert result["is_valid"] is True
        assert result["error_message"] == ""
        assert result["error_type"] == ""
