from .base_presenter import BasePresenter


class JSONPresenter(BasePresenter):
    type = "JSON_PRESENTER"
    name = "JSON Presenter"
    description = "Presenter for generating JSON files"

    def generate(self, presenter_input, template) -> dict[str, str]:
        return super().generate(presenter_input, template)
