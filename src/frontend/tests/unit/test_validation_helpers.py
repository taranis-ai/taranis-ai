import pytest
from models.admin import Job
from pydantic import ValidationError

from frontend.utils.validation_helpers import format_pydantic_errors


def test_format_pydantic_errors_delegates_to_taranis_model_formatter():
    with pytest.raises(ValidationError) as exc_info:
        Job.model_validate({})

    assert format_pydantic_errors(exc_info.value, Job) == Job.format_validation_errors(exc_info.value)
