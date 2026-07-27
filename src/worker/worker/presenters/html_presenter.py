from .base_presenter import BasePresenter


class HTMLPresenter(BasePresenter):
    type = "HTML_PRESENTER"
    name = "HTML Presenter"
    description = "Presenter for generating html documents"

    def generate(self, product: dict, template: str | None, parameters: dict[str, str] | None = None) -> bytes | str | None:
        if parameters is None:
            parameters = {}
        return super().generate(product, template, parameters)
