from .base_presenter import BasePresenter


class HTMLPresenter(BasePresenter):
    type = "HTML_PRESENTER"
    name = "HTML Presenter"
    description = "Presenter for generating html documents"

    def generate(self, presenter_input, template) -> dict[str, bytes | str]:
        return super().generate(presenter_input, template)
