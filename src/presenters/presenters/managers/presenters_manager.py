from presenters.presenters.pdf_presenter import PDFPresenter
from presenters.presenters.html_presenter import HTMLPresenter
from presenters.presenters.text_presenter import TEXTPresenter
from presenters.presenters.misp_presenter import MISPPresenter
from shared.schema.presenter import PresenterInputSchema, PresenterOutputSchema

presenters = {}


def initialize():
    register_presenter(PDFPresenter())
    register_presenter(HTMLPresenter())
    register_presenter(TEXTPresenter())
    register_presenter(MISPPresenter())


def register_presenter(presenter):
    presenters[presenter.type] = presenter


def get_registered_presenters_info():
    return [presenters[key].get_info() for key in presenters]


def generate(presenter_input_json):
    presenter_input_schema = PresenterInputSchema()
    presenter_input = presenter_input_schema.load(presenter_input_json)
    presenter_output = presenters[presenter_input.type].generate(presenter_input)
    if presenter_output is None:
        return "", 500
    presenter_output_schema = PresenterOutputSchema()
    return presenter_output_schema.dump(presenter_output)
