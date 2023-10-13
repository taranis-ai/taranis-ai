from .base_presenter import BasePresenter


class HTMLPresenter(BasePresenter):
    type = "HTML_PRESENTER"
    name = "HTML Presenter"
    description = "Presenter for generating html documents"

    def generate(self, product, template) -> dict[str, bytes | str]:
        return super().generate(product, template)
