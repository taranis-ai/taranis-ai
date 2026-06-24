import datetime as _dt

import pytest

import worker.presenters.base_presenter as bp
from worker import presenters


class FixedDateTime(_dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2025, 1, 2, 12, 0, 0, tzinfo=tz)


@pytest.fixture
def fixed_datetime(monkeypatch):
    monkeypatch.setattr(bp.datetime, "datetime", FixedDateTime, raising=True)


@pytest.fixture
def base_presenter():
    return presenters.BasePresenter()


@pytest.fixture
def pdf_presenter():
    return presenters.PDFPresenter()


@pytest.fixture
def pandoc_presenter():
    return presenters.PANDOCPresenter()


@pytest.fixture
def stix_presenter():
    return presenters.STIXPresenter()
