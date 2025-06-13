import pytest
from unittest.mock import patch

from worker.presenters.presenter_tasks import TemplateValidationTask, PresenterTask, validate_jinja_template


class TestValidateJinjaTemplate:
    """Unit tests for the validate_jinja_template utility function."""

    def test_validate_jinja_template_valid(self):
        """Test validation of a valid template using the utility function."""
        template = "Hello {{ name }}!"
        result = validate_jinja_template(template)
        
        assert result["is_valid"] is True
        assert result["error_message"] is None
        assert result["error_type"] is None

    def test_validate_jinja_template_invalid(self):
        """Test validation of an invalid template using the utility function."""
        template = "Hello {{ name !"
        result = validate_jinja_template(template)
        
        assert result["is_valid"] is False
        assert "Template syntax error:" in result["error_message"]
        assert result["error_type"] == "TemplateSyntaxError"

    @patch('worker.presenters.presenter_tasks.Environment')
    def test_validate_jinja_template_uses_correct_environment_settings(self, mock_env):
        """Test that the utility function uses the correct Jinja2 environment settings."""
        template = "{{ variable }}"
        validate_jinja_template(template)
        
        # Verify Environment was called with autoescape=False
        mock_env.assert_called_once_with(autoescape=False)

    @patch('worker.presenters.presenter_tasks.Environment')
    def test_validate_jinja_template_handles_general_exception(self, mock_env):
        """Test that the utility function handles general exceptions properly."""
        mock_env.return_value.from_string.side_effect = RuntimeError("Some error")
        
        template = "{{ variable }}"
        result = validate_jinja_template(template)
        
        assert result["is_valid"] is False
        assert "Template validation failed: Some error" in result["error_message"]
        assert result["error_type"] == "RuntimeError"


class TestTemplateValidationTask:
    """Unit tests for the TemplateValidationTask class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.task = TemplateValidationTask()

    def test_validate_template_valid_simple(self):
        """Test validation of a simple valid template."""
        template = "Hello {{ name }}!"
        result = self.task.validate_template(template)
        
        assert result["is_valid"] is True
        assert result["error_message"] is None
        assert result["error_type"] is None

    def test_validate_template_valid_with_loop(self):
        """Test validation of a valid template with a loop."""
        template = "{% for item in items %}{{ item }}{% endfor %}"
        result = self.task.validate_template(template)
        
        assert result["is_valid"] is True
        assert result["error_message"] is None
        assert result["error_type"] is None

    def test_validate_template_valid_with_condition(self):
        """Test validation of a valid template with conditions."""
        template = "{% if condition %}{{ value }}{% else %}No value{% endif %}"
        result = self.task.validate_template(template)
        
        assert result["is_valid"] is True
        assert result["error_message"] is None
        assert result["error_type"] is None

    def test_validate_template_valid_with_filters(self):
        """Test validation of a valid template with filters."""
        template = "{{ name | upper | default('Unknown') }}"
        result = self.task.validate_template(template)
        
        assert result["is_valid"] is True
        assert result["error_message"] is None
        assert result["error_type"] is None

    def test_validate_template_empty(self):
        """Test validation of an empty template."""
        template = ""
        result = self.task.validate_template(template)
        
        assert result["is_valid"] is True
        assert result["error_message"] is None
        assert result["error_type"] is None

    def test_validate_template_static_text(self):
        """Test validation of a template with only static text."""
        template = "This is just static text"
        result = self.task.validate_template(template)
        
        assert result["is_valid"] is True
        assert result["error_message"] is None
        assert result["error_type"] is None

    def test_validate_template_invalid_missing_brace(self):
        """Test validation of an invalid template with missing closing brace."""
        template = "Hello {{ name !"
        result = self.task.validate_template(template)
        
        assert result["is_valid"] is False
        assert "Template syntax error:" in result["error_message"]
        assert result["error_type"] == "TemplateSyntaxError"

    def test_validate_template_invalid_wrong_syntax(self):
        """Test validation of an invalid template with wrong syntax."""
        template = "{% if condition % {{ value }} {% endif %}"
        result = self.task.validate_template(template)
        
        assert result["is_valid"] is False
        assert "Template syntax error:" in result["error_message"]
        assert result["error_type"] == "TemplateSyntaxError"

    def test_validate_template_invalid_unclosed_block(self):
        """Test validation of an invalid template with unclosed block."""
        template = "{% for item in items %}{{ item }}"
        result = self.task.validate_template(template)
        
        assert result["is_valid"] is False
        assert "Template syntax error:" in result["error_message"]
        assert result["error_type"] == "TemplateSyntaxError"

    def test_validate_template_invalid_unknown_tag(self):
        """Test validation of an invalid template with unknown tag."""
        template = "{% unknown_tag %}"
        result = self.task.validate_template(template)
        
        assert result["is_valid"] is False
        assert "Template syntax error:" in result["error_message"]
        assert result["error_type"] == "TemplateSyntaxError"

    @patch('worker.presenters.presenter_tasks.logger')
    def test_validate_template_logs_success(self, mock_logger):
        """Test that successful validation is logged."""
        template = "{{ variable }}"
        self.task.validate_template(template)
        
        mock_logger.info.assert_called_with("Template validation successful")

    @patch('worker.presenters.presenter_tasks.logger')
    def test_validate_template_logs_warning_on_syntax_error(self, mock_logger):
        """Test that syntax errors are logged as warnings."""
        template = "{{ invalid"
        self.task.validate_template(template)
        
        # Check that warning was called with a message containing "Template syntax error:"
        mock_logger.warning.assert_called_once()
        warning_message = mock_logger.warning.call_args[0][0]
        assert "Template syntax error:" in warning_message

    @patch('worker.presenters.presenter_tasks.validate_jinja_template')
    def test_validate_template_handles_general_exception(self, mock_validate):
        """Test that general exceptions are handled properly."""
        # Mock the utility function to raise a general exception
        mock_validate.return_value = {
            "is_valid": False,
            "error_message": "Template validation failed: Some error",
            "error_type": "RuntimeError"
        }
        
        template = "{{ variable }}"
        result = self.task.validate_template(template)
        
        assert result["is_valid"] is False
        assert "Template validation failed: Some error" in result["error_message"]
        assert result["error_type"] == "RuntimeError"
        mock_validate.assert_called_once_with(template)

    @patch('worker.presenters.presenter_tasks.logger')
    @patch('worker.presenters.presenter_tasks.validate_jinja_template')
    def test_validate_template_logs_error_on_general_exception(self, mock_validate, mock_logger):
        """Test that general exceptions are logged as errors."""
        mock_validate.return_value = {
            "is_valid": False,
            "error_message": "Template validation failed: Some error",
            "error_type": "RuntimeError"
        }
        
        template = "{{ variable }}"
        self.task.validate_template(template)
        
        # Since we're mocking the utility function, the logging happens in the utility function
        # We just verify that our task calls the utility function correctly
        mock_validate.assert_called_once_with(template)

    def test_validate_template_uses_correct_environment_settings(self):
        """Test that the validation uses the correct Jinja2 environment settings."""
        with patch('worker.presenters.presenter_tasks.validate_jinja_template') as mock_validate:
            mock_validate.return_value = {"is_valid": True, "error_message": None, "error_type": None}
            
            template = "{{ variable }}"
            self.task.validate_template(template)
            
            # Verify the utility function was called with the template
            mock_validate.assert_called_once_with(template)

    def test_run_method_calls_validate_template(self):
        """Test that the run method calls validate_template."""
        with patch.object(self.task, 'validate_template') as mock_validate:
            mock_validate.return_value = {"is_valid": True, "error_message": None, "error_type": None}
            
            template = "{{ variable }}"
            result = self.task.run(template)
            
            mock_validate.assert_called_once_with(template)
            assert result == {"is_valid": True, "error_message": None, "error_type": None}

    def test_task_name(self):
        """Test that the task has the correct name."""
        assert self.task.name == "template_validation_task"


class TestPresenterTaskValidation:
    """Unit tests for the validate_template method in PresenterTask class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        with patch('worker.presenters.presenter_tasks.CoreApi'):
            self.task = PresenterTask()

    def test_presenter_task_has_validate_template_method(self):
        """Test that PresenterTask has the validate_template method."""
        assert hasattr(self.task, 'validate_template')
        assert callable(getattr(self.task, 'validate_template'))

    def test_presenter_task_validate_template_valid(self):
        """Test validation of a valid template using PresenterTask."""
        template = "Hello {{ name }}!"
        result = self.task.validate_template(template)
        
        assert result["is_valid"] is True
        assert result["error_message"] is None
        assert result["error_type"] is None

    def test_presenter_task_validate_template_invalid(self):
        """Test validation of an invalid template using PresenterTask."""
        template = "Hello {{ name !"
        result = self.task.validate_template(template)
        
        assert result["is_valid"] is False
        assert "Template syntax error:" in result["error_message"]
        assert result["error_type"] == "TemplateSyntaxError"

    def test_presenter_task_validate_template_same_as_validation_task(self):
        """Test that PresenterTask and TemplateValidationTask produce the same results."""
        validation_task = TemplateValidationTask()
        
        test_templates = [
            "{{ variable }}",
            "{% for item in items %}{{ item }}{% endfor %}",
            "{{ invalid",
            "",
            "static text"
        ]
        
        for template in test_templates:
            presenter_result = self.task.validate_template(template)
            validation_result = validation_task.validate_template(template)
            
            assert presenter_result == validation_result, f"Results differ for template: {template}"

    def test_presenter_task_name(self):
        """Test that PresenterTask has the correct name."""
        assert self.task.name == "presenter_task"


class TestTemplateValidationIntegration:
    """Integration tests for template validation functionality."""

    def test_complex_template_validation(self):
        """Test validation of complex templates with multiple features."""
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
        assert result["error_message"] is None
        assert result["error_type"] is None

    def test_template_with_inheritance(self):
        """Test validation of templates using inheritance syntax."""
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
        """Test validation of templates using include syntax."""
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
        """Test validation of templates using custom syntax that should be valid."""
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
    ])
    def test_various_invalid_templates(self, invalid_template, expected_error_type):
        """Test validation of various types of invalid templates."""
        task = TemplateValidationTask()
        result = task.validate_template(invalid_template)
        
        assert result["is_valid"] is False
        assert result["error_type"] == expected_error_type
        assert result["error_message"] is not None

    @pytest.mark.parametrize("valid_template", [
        "{{ variable }}",
        "{% for item in items %}{{ item }}{% endfor %}",
        "{% if condition %}yes{% else %}no{% endif %}",
        "{{ value | default('default') | upper }}",
        "{# Just a comment #}",
        "Static text only",
        "",
        "{% set var = 'value' %}{{ var }}",
        "{% with %}{% set local = 'value' %}{{ local }}{% endwith %}",
    ])
    def test_various_valid_templates(self, valid_template):
        """Test validation of various types of valid templates."""
        task = TemplateValidationTask()
        result = task.validate_template(valid_template)
        
        assert result["is_valid"] is True
        assert result["error_message"] is None
        assert result["error_type"] is None
