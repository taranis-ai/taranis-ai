from worker.presenters.pdf_presenter import PDFPresenter
from worker.presenters.html_presenter import HTMLPresenter
from worker.presenters.text_presenter import TextPresenter
from worker.presenters.json_presenter import JSONPresenter

PRESENTER_REGISTRY = {
    "pdf_presenter": PDFPresenter,
    "html_presenter": HTMLPresenter,
    "text_presenter": TextPresenter,
    "json_presenter": JSONPresenter,
}
