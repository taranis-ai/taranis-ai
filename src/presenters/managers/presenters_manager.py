from presenters.pdf_presenter import PDFPresenter
from presenters.html_presenter import HTMLPresenter
from presenters.text_presenter import TEXTPresenter
from presenters.misp_presenter import MISPPresenter
from schema.presenter import PresenterInputSchema, PresenterOutputSchema

presenters = {}


def initialize():
    register_presenter(PDFPresenter())
    register_presenter(HTMLPresenter())
    register_presenter(TEXTPresenter())
    register_presenter(MISPPresenter())


def register_presenter(presenter):
    presenters[presenter.type] = presenter


def get_registered_presenters_info():
    presenters_info = []
    for key in presenters:
        presenters_info.append(presenters[key].get_info())

    return presenters_info


def generate(presenter_input_json):
    presenter_input_schema = PresenterInputSchema()
    presenter_input = presenter_input_schema.load(presenter_input_json)

    presenter_output = presenters[presenter_input.type].generate(presenter_input)

    if presenter_output is not None:
        presenter_output_schema = PresenterOutputSchema()
        return presenter_output_schema.dump(presenter_output)
    else:
        return "", 500
