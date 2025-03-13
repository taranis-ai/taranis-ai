from worker.presenters.html_presenter import HTMLPresenter
from worker.presenters.json_presenter import JSONPresenter
from worker.presenters.pdf_presenter import PDFPresenter
from worker.presenters.base_presenter import BasePresenter
from worker.presenters.text_presenter import TextPresenter

# from worker.collectors.web_collector import WebCollector

__all__ = [
    "HTMLPresenter",
    "JSONPresenter",
    "PDFPresenter",
    "BasePresenter",
    "TextPresenter",
]
