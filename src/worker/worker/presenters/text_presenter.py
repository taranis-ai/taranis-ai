from .base_presenter import BasePresenter


class TextPresenter(BasePresenter):
    type = "TEXT_PRESENTER"
    name = "TEXT Presenter"
    description = "Presenter for generating text documents"

    def generate(self, product, template, parameters: dict[str, str] | None = None) -> str | bytes:
        if parameters is None:
            parameters = {}
        return super().generate(product, template, parameters)
